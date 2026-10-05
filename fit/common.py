"""Pieces shared by the fitting scripts: downloads, the six morning inputs, weights in raw units."""
import io
import json
import os
import re
import time
import urllib.parse
import urllib.request
import zipfile

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
HOUR = pd.Timedelta(hours=1)
WINTER = (10, 11, 12, 1, 2, 3)
RAIN_CODES = 'RA|SN|DZ|SG|PL|GR|GS|UP'

# Visibility is stored in miles: 5 km is 3.11 miles, 1 km is stored as 0.62.
MIST_MILES = 3.11
FOG_MILES = 0.62

# Order of the weights in src/model.js.
MORNING_INPUTS = ['rhmax', 'wind', 'rain', 'evecloud', 'eve_gap', 'cool']
HOUR_INPUTS = ['rh_h', 'wind_h', 'gap_h', 'prec3', 'cloud_h']
HOURS = range(3, 12)

# The archive lists these three airports at the town, 7 to 16 km from the runway, which is another
# cell of the worldwide ICON model. Positions from OurAirports.
STATION_POSITIONS = {'VIAR': (31.7096, 74.7973), 'OPST': (32.5359, 74.3646), 'OPPS': (33.9939, 71.5146)}
# And these two in another place altogether: Lublin 477 km from its airport, Braunschweig 8 km. Positions from aviationweather.gov.
STATION_POSITIONS.update({'EPLB': (51.2403, 22.7136), 'EDVE': (52.319, 10.558)})

FORECAST_VARIABLES = ['relative_humidity_2m', 'temperature_2m', 'dew_point_2m',
                      'wind_speed_10m', 'precipitation', 'cloud_cover']

EUROPE_STATIONS = [
    ('EDDB', 'Berlin', 'Europe/Berlin'), ('EDDH', 'Hamburg', 'Europe/Berlin'),
    ('EDDM', 'Munich', 'Europe/Berlin'), ('EDDF', 'Frankfurt', 'Europe/Berlin'),
    ('EGLL', 'London', 'Europe/London'), ('LFPG', 'Paris', 'Europe/Paris'),
    ('EHAM', 'Amsterdam', 'Europe/Amsterdam'), ('LOWW', 'Vienna', 'Europe/Vienna'),
    ('EPWA', 'Warsaw', 'Europe/Warsaw'), ('LKPR', 'Prague', 'Europe/Prague'),
    ('LSZH', 'Zurich', 'Europe/Zurich'), ('LIML', 'Milan', 'Europe/Rome'),
    ('LEMD', 'Madrid', 'Europe/Madrid'), ('ESSA', 'Stockholm', 'Europe/Stockholm'),
]


def download(url, name):
    """Path of the cached file `name`; the file is fetched from `url` first if it is missing."""
    path = os.path.join(CACHE_DIR, name)
    if os.path.exists(path):
        return path
    os.makedirs(CACHE_DIR, exist_ok=True)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=120) as response:
                body = response.read()
            with open(path, 'wb') as out:
                out.write(body)
            time.sleep(2)
            return path
        except Exception as error:
            print('download failed:', error)
            time.sleep(8 * (attempt + 1))
    raise RuntimeError('could not download ' + url)


def load_airport_reports(station, tz, first, last, near_saturation=False):
    """Airport reports from the Iowa State Mesonet, from `first` up to but not including `last`.

    Adds the columns `mist` (visibility under 5 km) and `fog` (under 1 km), both
    only for reports without rain, snow or similar in the weather codes.
    With `near_saturation`, the temperature also has to be within 2 C of the dew point,
    which leaves out smoke, haze and dry smog."""
    first, last = pd.Timestamp(first), pd.Timestamp(last)
    data = ['vsby', 'wxcodes'] + (['tmpf', 'dwpf'] if near_saturation else [])
    query = urllib.parse.urlencode(
        [('station', station)] + [('data', d) for d in data]
        + [('year1', first.year), ('month1', first.month), ('day1', first.day),
           ('year2', last.year), ('month2', last.month), ('day2', last.day),
           ('tz', tz), ('format', 'onlycomma'), ('latlon', 'yes'), ('missing', 'M'),
           ('trace', 'T'), ('direct', 'no'), ('report_type', 3), ('report_type', 4)])
    name = ('obsT_' if near_saturation else 'obs_') + station + '.csv'
    path = download('https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?' + query, name)
    reports = pd.read_csv(path, na_values='M')
    reports['t'] = pd.to_datetime(reports['valid'])
    reports = reports.dropna(subset=['vsby']).copy()
    if station in STATION_POSITIONS:
        reports['lat'], reports['lon'] = STATION_POSITIONS[station]
    dry = ~reports.wxcodes.fillna('').str.contains(RAIN_CODES)
    reports['mist'] = (reports.vsby < MIST_MILES) & dry
    reports['fog'] = (reports.vsby < FOG_MILES) & dry
    if near_saturation:
        humid = ((reports.tmpf - reports.dwpf) / 1.8).round() <= 2     # the airports report whole degrees C
        reports['mist'] &= humid
        reports['fog'] &= humid
    return reports


DWD_URL = 'https://opendata.dwd.de/climate_environment/CDC/observations_germany/climate/hourly/'


def load_dwd_hourly(kind, code, station):
    """Hourly values of one kind ('visibility', 'VV' or 'precipitation', 'RR') from a station of the
    German weather service: the historical and the recent file joined, and the station's position."""
    with urllib.request.urlopen(f'{DWD_URL}{kind}/historical/', timeout=60) as response:
        historical = re.search(f'stundenwerte_{code}_{station}_\\d+_\\d+_hist.zip', response.read().decode()).group(0)
    parts = []
    urls = (f'{DWD_URL}{kind}/historical/{historical}', f'{DWD_URL}{kind}/recent/stundenwerte_{code}_{station}_akt.zip')
    for url in urls:
        with open(download(url, 'dwd_' + url.split('/')[-1]), 'rb') as file:
            archive = zipfile.ZipFile(io.BytesIO(file.read()))
        values = [n for n in archive.namelist() if n.startswith('produkt')][0]
        part = pd.read_csv(archive.open(values), sep=';', skipinitialspace=True)
        part.columns = [c.strip() for c in part.columns]
        parts.append(part)
    place = [n for n in archive.namelist() if n.startswith('Metadaten_Geographie')][0]
    place = pd.read_csv(archive.open(place), sep=';', skipinitialspace=True, encoding='latin1').iloc[-1]
    table = pd.concat(parts).drop_duplicates('MESS_DATUM', keep='last')
    table.index = pd.to_datetime(table.MESS_DATUM.astype(str), format='%Y%m%d%H')
    return table, float(place['Geogr.Breite']), float(place['Geogr.Laenge'])


def load_dwd_reports(station, tz, first, last):
    """Readings from a station of the German weather service, in the shape of `load_airport_reports`.

    One visibility reading per hour, in metres. An hour counts as wet if rain was measured or flagged."""
    visibility, lat, lon = load_dwd_hourly('visibility', 'VV', station)
    rain, _, _ = load_dwd_hourly('precipitation', 'RR', station)
    reports = pd.DataFrame({'metres': visibility.V_VV.where(visibility.V_VV >= 0)})
    reports = reports.join(pd.DataFrame({'wet': (rain.R1 > 0) | (rain.RS_IND == 1)}), how='left').dropna(subset=['metres'])
    dry = ~reports.wet.fillna(False).astype(bool)
    reports['t'] = reports.index.tz_localize('UTC').tz_convert(tz).tz_localize(None)
    reports['mist'] = (reports.metres < 5000) & dry
    reports['fog'] = (reports.metres < 1000) & dry
    reports['lat'], reports['lon'] = lat, lon
    return reports[(reports.t >= first) & (reports.t < last)].reset_index(drop=True)


def load_forecast(name, lat, lon, tz, model, last):
    """Day-ahead forecast (the run made the day before) from the Open-Meteo archive of past runs.

    One row per hour, indexed by the clock at the place, from 2024-01-20 to `last`.
    Open-Meteo counts every hour of an answer from the UTC offset on the day of the download, so a file
    fetched in summer has its winter hours an hour late. The times are taken back to UTC with that offset
    and then to the clock at the place, as the reports have it. Of an hour that comes twice when the
    clocks go back, the first is kept."""
    query = urllib.parse.urlencode(dict(
        latitude=lat, longitude=lon, models=model, start_date='2024-01-20', end_date=last,
        hourly=','.join(v + '_previous_day1' for v in FORECAST_VARIABLES), timezone=tz))
    path = download('https://previous-runs-api.open-meteo.com/v1/forecast?' + query, name)
    with open(path) as file:
        answer = json.load(file)
    table = pd.DataFrame(answer['hourly'])
    table.columns = [c.replace('_previous_day1', '') for c in table.columns]
    utc = pd.to_datetime(table.time) - pd.Timedelta(seconds=answer['utc_offset_seconds'])
    table['t'] = utc.dt.tz_localize('UTC').dt.tz_convert(tz).dt.tz_localize(None)
    table = table.set_index('t').drop(columns='time').apply(pd.to_numeric, errors='coerce')
    return table[~table.index.duplicated()]


def label_mornings(reports, flags):
    """For each day with reports in at least 5 of the clock hours 04 to 09: is each flag set in 2 or more of them?"""
    window = reports[(reports.t.dt.hour >= 4) & (reports.t.dt.hour < 10)].copy()
    window['day'] = window.t.dt.normalize()
    window['hour'] = window.t.dt.hour
    flagged = window.groupby(['day', 'hour'])[list(flags)].any()
    hours_flagged = flagged.groupby('day').sum()
    hours_reported = flagged.groupby('day').size()
    return hours_flagged[hours_reported >= 5] >= 2


def compute_morning_inputs(forecast, day):
    """The six inputs for one morning from the day-ahead `forecast`, or None if the forecast has gaps."""
    morning = forecast.loc[day + 4 * HOUR:day + 9 * HOUR]          # 04 to 09 h
    night = forecast.loc[day - 3 * HOUR:day + 6 * HOUR]            # 21 h the day before to 06 h
    evening = forecast.loc[day - 6 * HOUR:day - 4 * HOUR]          # 18 to 20 h the day before
    if len(morning) < 6 or len(evening) < 3:
        return None
    if morning.relative_humidity_2m.isna().any() or evening.temperature_2m.isna().any():
        return None
    return dict(
        rhmax=morning.relative_humidity_2m.max(),
        wind=morning.wind_speed_10m.mean(),
        rain=np.log1p(night.precipitation.sum() + morning.precipitation.sum()),
        evecloud=evening.cloud_cover.mean(),
        eve_gap=(evening.temperature_2m - evening.dew_point_2m).mean(),
        cool=evening.temperature_2m.mean() - morning.temperature_2m.min())


def build_morning_table(city, labels, forecast, months):
    """One row per labelled morning in `months`: the labels and the six inputs."""
    rows = []
    for day in labels.index[labels.index.month.isin(months)]:
        inputs = compute_morning_inputs(forecast, day)
        if inputs is not None:
            rows.append(dict(city=city, day=day, **labels.loc[day].to_dict(), **inputs))
    return pd.DataFrame(rows)


def finish_table(rows):
    """Join the per-city tables, drop mornings with a missing input, add the month used for holding out."""
    table = pd.concat(rows).dropna(subset=MORNING_INPUTS).reset_index(drop=True)
    table['fold'] = table.day.dt.year * 100 + table.day.dt.month
    return table


def build_hour_table(mornings, reports, forecasts, flag):
    """One row per morning and hour 03 to 11 h: was `flag` set in that clock hour, and the hourly inputs.

    The six morning inputs are copied onto each row. `reports` and `forecasts` are dicts by city."""
    rows = []
    for city, reported in reports.items():
        seen = reported.groupby(reported.t.dt.floor('h'))[flag].any()
        forecast = forecasts[city]
        for _, morning in mornings[mornings.city == city].iterrows():
            for hour in HOURS:
                hour_start = morning.day + hour * HOUR
                if hour_start not in seen.index or hour_start not in forecast.index:
                    continue
                now = forecast.loc[hour_start]
                rows.append(dict(
                    city=city, day=morning.day, h=hour, flag=bool(seen[hour_start]),
                    rh_h=now.relative_humidity_2m, wind_h=now.wind_speed_10m,
                    gap_h=now.temperature_2m - now.dew_point_2m,
                    prec3=np.log1p(forecast.precipitation.loc[hour_start - 2 * HOUR:hour_start].sum()),
                    cloud_h=now.cloud_cover, **{k: morning[k] for k in MORNING_INPUTS}))
    table = pd.DataFrame(rows).dropna().reset_index(drop=True)
    table['fold'] = table.day.dt.year * 100 + table.day.dt.month
    table['city_hour'] = table.city + table.h.astype(str)
    return table


def load_europe():
    """Reports, forecasts and the morning table (columns `mist`, `fog`) for the 14 European airports."""
    reports, forecasts, rows = {}, {}, []
    for station, city, tz in EUROPE_STATIONS:
        reports[city] = load_airport_reports(station, tz, '2024-01-20', '2026-10-03')
        forecasts[city] = load_forecast(f'fc_{station}.json', reports[city].lat.iloc[0], reports[city].lon.iloc[0],
                                        tz, 'icon_eu', '2026-10-02')
        labels = label_mornings(reports[city], ['mist', 'fog'])
        rows.append(build_morning_table(city, labels, forecasts[city], WINTER))
    return finish_table(rows), reports, forecasts


def logit(rate, low):
    """Log-odds of a usual rate, with the rate kept between `low` and 1 - `low`."""
    rate = np.clip(rate, low, 1 - low)
    return np.log(rate / (1 - rate))


def make_logistic(max_iter=2000):
    """Standardised inputs into a logistic regression."""
    return make_pipeline(StandardScaler(), LogisticRegression(max_iter=max_iter))


def to_raw_weights(model):
    """Weights in the units of the inputs, as used in model.js: one per input, then the constant."""
    scaler, regression = model[0], model[1]
    weights = regression.coef_[0] / scaler.scale_
    constant = regression.intercept_[0] - (weights * scaler.mean_).sum()
    return [round(float(w), 5) for w in weights] + [round(float(constant), 5)]


def brier_skill_score(p, usual, y):
    """Brier skill score against always saying the usual rate."""
    return 1 - np.mean((p - y) ** 2) / np.mean((usual - y) ** 2)


def bootstrap_skill_range(p, usual, y, fold, resamples=2000):
    """90% range of the skill when the months are resampled."""
    months = sorted(set(fold))
    rows = {m: np.where(fold == m)[0] for m in months}
    rng = np.random.default_rng(0)
    scores = []
    for _ in range(resamples):
        idx = np.concatenate([rows[m] for m in rng.choice(months, len(months))])
        scores.append(brier_skill_score(p[idx], usual[idx], y[idx]))
    return np.nanpercentile(scores, 5), np.nanpercentile(scores, 95)


def format_calibration(p, y, edges=(0, .05, .15, .3, .5, .7, 1.01)):
    """Chance given against what happened, for bands of the given chance."""
    parts = []
    for low, high in zip(edges[:-1], edges[1:]):
        band = (p >= low) & (p < high)
        if band.any():
            parts.append(f'{p[band].mean():.0%} -> {y[band].mean():.0%} (n={band.sum()})')
    return ' | '.join(parts)
