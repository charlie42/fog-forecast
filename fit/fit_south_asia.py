"""Weights of the "south-asia" formula, for the plain of the Indus and Ganges.

Run: python fit_south_asia.py
Fog mornings (SOUTH_ASIA morning) and fog hours (SOUTH_ASIA hour), fitted on airports there with the same
inputs as the European formula, but taken from the worldwide ICON model. Two differences from Europe:
  - A report counts as fog only if visibility is under 1 km, there is no rain or snow, and the
    temperature is within 2 C of the dew point (this leaves out dry smog).
  - The usual rate fed in is the airport's rate for the calendar month, from July 2019 to 19 January 2024,
    that is, from before the first morning in the fit.
Fog on the plain comes in runs of days, so there are four more sets of weights with one more input: whether the airport
had a fog morning one morning before ("1 before"), or two, three or four mornings before. Each row of a page uses the
newest of the four that is known, and the weights without it otherwise. Four reach the last row of a page.
All of them are fitted and tested with the day-ahead weather forecast. The page's later rows have an older one.
The test leaves out the airport and the month, and fits on the other airports."""
import numpy as np
import pandas as pd

import common
from common import (HOUR, HOURS, HOUR_INPUTS, MORNING_INPUTS, WINTER, logistic, logit, raw_weights,
                    skill, skill_range, calibration)

LOW = 0.005          # usual rates are kept between 0.5% and 99.5% before the log-odds
MODEL = 'icon_global'
STATIONS = [
    ('VIDP', 'Delhi', 'Asia/Kolkata'), ('OPLA', 'Lahore', 'Asia/Karachi'), ('OPIS', 'Islamabad', 'Asia/Karachi'),
    ('VIAR', 'Amritsar', 'Asia/Kolkata'), ('VILK', 'Lucknow', 'Asia/Kolkata'), ('VIJP', 'Jaipur', 'Asia/Kolkata'),
    ('VEBN', 'Varanasi', 'Asia/Kolkata'), ('VEPT', 'Patna', 'Asia/Kolkata'), ('VICG', 'Chandigarh', 'Asia/Kolkata'),
    ('VECC', 'Kolkata', 'Asia/Kolkata'), ('OPPS', 'Peshawar', 'Asia/Karachi'), ('OPMT', 'Multan', 'Asia/Karachi'),
    ('OPST', 'Sialkot', 'Asia/Karachi'), ('OPFA', 'Faisalabad', 'Asia/Karachi'), ('VNKT', 'Kathmandu', 'Asia/Kathmandu'),
    ('VGHS', 'Dhaka', 'Asia/Dhaka')]
LEFT_OUT = ['Kathmandu']             # a mountain valley with one fog morning, not the plain
SITES = ['Delhi', 'Lahore', 'Amritsar']   # the airports with a page
BEFORE_TEST = ('2019-07-01', '2024-01-20')
LAGS = (1, 2, 3, 4)                  # the fog morning one to four mornings before, as extra inputs


def load():
    """Reports (fog in the 2 C sense), forecasts and the morning table for the airports.

    The columns `before1` to `before4` say whether one to four mornings before were fog mornings (1 or 0),
    and are empty where that morning has no label (reports in fewer than 5 of its six hours)."""
    reports, forecasts, rows = {}, {}, []
    for station, city, tz in STATIONS:
        r = common.airport_reports(station, tz, '2019-07-01', '2026-10-04', near_saturation=True)
        reports[city] = r
        forecasts[city] = common.forecast(f'fcs_{station}_{MODEL}.json', r.lat.iloc[0], r.lon.iloc[0], tz, MODEL, '2026-10-03')
        labels = common.morning_labels(r, ['fog'])
        table = common.morning_table(city, labels, forecasts[city], WINTER)
        for lag in LAGS:
            table[f'before{lag}'] = labels.fog.reindex(table.day - pd.Timedelta(days=lag)).values.astype(float)
        rows.append(table)
    return common.finish_table(rows), reports, forecasts


def usual_rates(reports):
    """From the reports before the test: fog rate per calendar month (and the mornings behind it),
    the October to March rate, and the October to March share of foggy hours at 03 to 11 h."""
    r = reports[(reports.t >= BEFORE_TEST[0]) & (reports.t < BEFORE_TEST[1])].copy()
    r['day'] = r.t.dt.normalize()
    r['h'] = r.t.dt.hour
    hours = r.groupby(['day', 'h']).fog.any()
    morning = hours[(hours.index.get_level_values('h') >= 4) & (hours.index.get_level_values('h') < 10)]
    per_day = morning.groupby('day').agg(['size', 'sum'])
    per_day = per_day[per_day['size'] >= 5]
    fog = per_day['sum'] >= 2
    by_month = fog.groupby(fog.index.month).agg(['size', 'mean']).reindex(range(1, 13))
    winter = fog[fog.index.month.isin(WINTER)]
    hours = hours.reset_index()
    hours = hours[hours.day.isin(winter.index) & hours.h.isin(HOURS)]
    return dict(n=by_month['size'].fillna(0).values, month=by_month['mean'].values, winter=winter.mean(),
                hour=hours.groupby('h').fog.mean().reindex(HOURS).values)


def hour_rate(usual, month, hour):
    """Usual rate for one hour in one month: the winter's pattern over the hours, scaled by how the month compares with the winter."""
    return np.clip(usual['hour'][hour - 3] * usual['month'][month - 1] / usual['winter'], .003, .97)


def flat_rate(table, target, key):
    """Usual rate over all the winter, from the other months, for each value of `key`."""
    rate = np.zeros(len(table))
    y = table[target].values.astype(float)
    for month in table.fold.unique():
        test = (table.fold == month).values
        rate[test] = table[key].map(table[~test].groupby(key)[target].mean()).fillna(y[~test].mean()).values[test]
    return rate


def held_out(table, target, columns, rate, fit_cities, fallback=None):
    """Chance for every row from a fit on the other airports and the other months. `rate` is the usual rate fed in.

    A row with an empty input (no label for the morning before) is left out of the fit and takes its chance from `fallback`."""
    y = table[target].values.astype(float)
    chance = np.zeros(len(table)) if fallback is None else fallback.copy()
    x = table[columns].copy()
    x['usual'] = logit(rate, LOW)
    known = x.notna().all(axis=1).values
    for month in sorted(table.fold.unique()):
        test = (table.fold == month).values
        for city in table.city.unique():
            rows = test & (table.city == city).values & known
            train = ~test & (table.city != city).values & table.city.isin(fit_cities).values & known
            if rows.any():
                chance[rows] = logistic().fit(x[train], y[train]).predict_proba(x[rows])[:, 1]
    return chance, y


def report_sites(table, p, y, flat, monthly, label, resamples):
    print(f'\n{label}: skill over the flat winter rate | over the rate for the month (90% ranges) | said / came on')
    for city in SITES:
        k = (table.city == city).values
        fold = table.fold.values[k]
        a = skill_range(p[k], flat[k], y[k], fold, resamples)
        b = skill_range(p[k], monthly[k], y[k], fold, resamples)
        print(f'  {city:9s}{int(y[k].sum()):4d} | {skill(p[k], flat[k], y[k]):4.0%} ({a[0]:.0%} to {a[1]:.0%})'
              f' | {skill(p[k], monthly[k], y[k]):4.0%} ({b[0]:.0%} to {b[1]:.0%}) | {p[k].mean():.1%} / {y[k].mean():.1%}')
        print('    said -> happened: ' + calibration(p[k], y[k]))


def report_gain(table, p, base, y, label, resamples):
    """Skill of `p` over the chance without the morning before, at the airports with a page and at all three together."""
    parts = []
    for city in SITES + ['all three']:
        k = table.city.isin(SITES).values if city == 'all three' else (table.city == city).values
        low, high = skill_range(p[k], base[k], y[k], table.fold.values[k], resamples)
        parts.append(f'{city} {skill(p[k], base[k], y[k]):.0%} ({low:.0%} to {high:.0%})')
    print(f'  {label}, skill over the chance without it: ' + ' | '.join(parts))


def fit_all(table, target, columns, rate):
    """The formula fitted on every row with all of `columns`: one weight per column, the usual rate (log-odds), the constant."""
    x = table[columns].copy()
    x['usual'] = logit(rate, LOW)
    known = x.notna().all(axis=1).values
    return logistic().fit(x[known], table[target].values.astype(float)[known])


if __name__ == '__main__':
    mornings, reports, forecasts = load()
    usual = {city: usual_rates(r) for city, r in reports.items()}
    fit = [c for c in mornings.city.unique() if c not in LEFT_OUT and (mornings.city == c).sum() >= 200
           and all(usual[c]['n'][m - 1] >= 100 for m in WINTER)]
    mornings = mornings[mornings.city.isin(fit)].reset_index(drop=True)
    month = mornings.day.dt.month.values
    print(f'{len(fit)} airports in the fit: ' + ', '.join(fit))

    # Morning: the usual rate is the airport's rate for the calendar month.
    mornings['rate'] = [usual[c]['month'][m - 1] for c, m in zip(mornings.city, month)]
    y = mornings.fog.values.astype(float)
    flat = flat_rate(mornings, 'fog', 'city')
    monthly = np.clip(mornings.rate.values, .005, .995)
    p, _ = held_out(mornings, 'fog', MORNING_INPUTS, mornings.rate.values, fit)
    print(f'\nMORNING: {len(mornings)} mornings, {int(y.sum())} with fog; label known for '
          + ', '.join(f'{mornings[f"before{lag}"].notna().mean():.1%} ({lag} before)' for lag in LAGS))
    report_sites(mornings, p, y, flat, monthly, 'MORNING test, airport and month left out', 500)
    formulas = {'morning': fit_all(mornings, 'fog', MORNING_INPUTS, mornings.rate.values)}
    for lag in LAGS:
        columns = MORNING_INPUTS + [f'before{lag}']
        q, _ = held_out(mornings, 'fog', columns, mornings.rate.values, fit, fallback=p)
        report_sites(mornings, q, y, flat, monthly, f'MORNING test with the fog morning {lag} before', 500)
        report_gain(mornings, q, p, y, f'MORNING with {lag} before', 1000)
        formulas[f'morning, {lag} before'] = fit_all(mornings, 'fog', columns, mornings.rate.values)

    # Hour: the usual rate for the hour is scaled to the month.
    hours = common.hour_table(mornings, {c: reports[c] for c in fit}, forecasts, 'fog')
    hours = hours.merge(mornings[['city', 'day'] + [f'before{lag}' for lag in LAGS]], on=['city', 'day'], how='left')
    hours['rate'] = [hour_rate(usual[c], m, h) for c, m, h in zip(hours.city, hours.day.dt.month, hours.h)]
    y = hours.flag.values.astype(float)
    flat = flat_rate(hours, 'flag', 'city_hour')
    p, _ = held_out(hours, 'flag', HOUR_INPUTS + MORNING_INPUTS, hours.rate.values, fit)
    print(f'\nHOUR: {len(hours)} hours')
    report_sites(hours, p, y, flat, hours.rate.values, 'HOUR test, airport and month left out', 300)
    formulas['hour'] = fit_all(hours, 'flag', HOUR_INPUTS + MORNING_INPUTS, hours.rate.values)
    for lag in LAGS:
        columns = HOUR_INPUTS + MORNING_INPUTS + [f'before{lag}']
        q, _ = held_out(hours, 'flag', columns, hours.rate.values, fit, fallback=p)
        report_sites(hours, q, y, flat, hours.rate.values, f'HOUR test with the fog morning {lag} before', 300)
        report_gain(hours, q, p, y, f'HOUR with {lag} before', 300)
        formulas[f'hour, {lag} before'] = fit_all(hours, 'flag', columns, hours.rate.values)

    print('\nWeights for "south-asia" in model.js. With "before": the inputs, the morning before (1 or 0), the usual rate, the constant.')
    for name, values in formulas.items():
        print(f'{name:18s} =', raw_weights(values))
