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
from common import (HOURS, HOUR_INPUTS, MORNING_INPUTS, WINTER, bootstrap_skill_range, brier_skill_score,
                    format_calibration, logit, make_logistic, to_raw_weights)

RATE_FLOOR = 0.005          # usual rates are kept between 0.5% and 99.5% before the log-odds
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


def load_mornings():
    """Reports (fog in the 2 C sense), forecasts and the morning table for the airports.

    The columns `before1` to `before4` say whether one to four mornings before were fog mornings (1 or 0),
    and are empty where that morning has no label (reports in fewer than 5 of its six hours)."""
    reports, forecasts, rows = {}, {}, []
    for station, city, tz in STATIONS:
        city_reports = common.load_airport_reports(station, tz, '2019-07-01', '2026-10-04', near_saturation=True)
        reports[city] = city_reports
        forecasts[city] = common.load_forecast(f'fcs_{station}_{MODEL}.json', city_reports.lat.iloc[0],
                                               city_reports.lon.iloc[0], tz, MODEL, '2026-10-03')
        labels = common.label_mornings(city_reports, ['fog'])
        table = common.build_morning_table(city, labels, forecasts[city], WINTER)
        for lag in LAGS:
            table[f'before{lag}'] = labels.fog.reindex(table.day - pd.Timedelta(days=lag)).values.astype(float)
        rows.append(table)
    return common.finish_table(rows), reports, forecasts


def compute_usual_rates(reports):
    """From the reports before the test: fog rate per calendar month (and the mornings behind it),
    the October to March rate, and the October to March share of foggy hours at 03 to 11 h."""
    before = reports[(reports.t >= BEFORE_TEST[0]) & (reports.t < BEFORE_TEST[1])].copy()
    before['day'] = before.t.dt.normalize()
    before['h'] = before.t.dt.hour
    hours = before.groupby(['day', 'h']).fog.any()
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


def compute_hour_rate(usual, month, hour):
    """Usual rate for one hour in one month: the winter's pattern over the hours, scaled by how the month compares with the winter."""
    return np.clip(usual['hour'][hour - 3] * usual['month'][month - 1] / usual['winter'], .003, .97)


def compute_flat_rate(table, target, key):
    """Usual rate over all the winter, from the other months, for each value of `key`."""
    rate = np.zeros(len(table))
    y = table[target].values.astype(float)
    for month in table.fold.unique():
        test_mask = (table.fold == month).values
        rate_by_key = table[~test_mask].groupby(key)[target].mean()
        rate[test_mask] = table[key].map(rate_by_key).fillna(y[~test_mask].mean()).values[test_mask]
    return rate


def predict_held_out(table, target, columns, rate, fit_cities, fallback=None):
    """Chance for every row from a fit on the other airports and the other months. `rate` is the usual rate fed in.

    A row with an empty input (no label for the morning before) is left out of the fit and takes its chance from `fallback`."""
    y = table[target].values.astype(float)
    chance = np.zeros(len(table)) if fallback is None else fallback.copy()
    X = table[columns].copy()
    X['usual'] = logit(rate, RATE_FLOOR)
    known = X.notna().all(axis=1).values
    for month in sorted(table.fold.unique()):
        test_mask = (table.fold == month).values
        for city in table.city.unique():
            test_rows = test_mask & (table.city == city).values & known
            train_rows = ~test_mask & (table.city != city).values & table.city.isin(fit_cities).values & known
            if test_rows.any():
                model = make_logistic().fit(X[train_rows], y[train_rows])
                chance[test_rows] = model.predict_proba(X[test_rows])[:, 1]
    return chance, y


def report_sites(table, p, y, flat, monthly, label, resamples):
    print(f'\n{label}: skill over the flat winter rate | over the rate for the month (90% ranges) | said / came on')
    for city in SITES:
        mask = (table.city == city).values
        p_city, y_city, fold = p[mask], y[mask], table.fold.values[mask]
        flat_skill = brier_skill_score(p_city, flat[mask], y_city)
        flat_low, flat_high = bootstrap_skill_range(p_city, flat[mask], y_city, fold, resamples)
        monthly_skill = brier_skill_score(p_city, monthly[mask], y_city)
        monthly_low, monthly_high = bootstrap_skill_range(p_city, monthly[mask], y_city, fold, resamples)
        print(f'  {city:9s}{int(y_city.sum()):4d} | {flat_skill:4.0%} ({flat_low:.0%} to {flat_high:.0%})'
              f' | {monthly_skill:4.0%} ({monthly_low:.0%} to {monthly_high:.0%})'
              f' | {p_city.mean():.1%} / {y_city.mean():.1%}')
        print('    said -> happened: ' + format_calibration(p_city, y_city))


def report_gain(table, p, base, y, label, resamples):
    """Skill of `p` over the chance without the morning before, at the airports with a page and at all three together."""
    parts = []
    for city in SITES + ['all three']:
        mask = table.city.isin(SITES).values if city == 'all three' else (table.city == city).values
        low, high = bootstrap_skill_range(p[mask], base[mask], y[mask], table.fold.values[mask], resamples)
        parts.append(f'{city} {brier_skill_score(p[mask], base[mask], y[mask]):.0%} ({low:.0%} to {high:.0%})')
    print(f'  {label}, skill over the chance without it: ' + ' | '.join(parts))


def fit_all(table, target, columns, rate):
    """The formula fitted on every row with all of `columns`: one weight per column, the usual rate (log-odds), the constant."""
    X = table[columns].copy()
    X['usual'] = logit(rate, RATE_FLOOR)
    known = X.notna().all(axis=1).values
    return make_logistic().fit(X[known], table[target].values.astype(float)[known])


def main():
    mornings, reports, forecasts = load_mornings()
    usual = {city: compute_usual_rates(city_reports) for city, city_reports in reports.items()}
    fit_cities = [city for city in mornings.city.unique()
                  if city not in LEFT_OUT and (mornings.city == city).sum() >= 200
                  and all(usual[city]['n'][month - 1] >= 100 for month in WINTER)]
    mornings = mornings[mornings.city.isin(fit_cities)].reset_index(drop=True)
    months = mornings.day.dt.month.values
    print(f'{len(fit_cities)} airports in the fit: ' + ', '.join(fit_cities))

    # Morning: the usual rate is the airport's rate for the calendar month.
    mornings['rate'] = [usual[city]['month'][month - 1] for city, month in zip(mornings.city, months)]
    y = mornings.fog.values.astype(float)
    flat = compute_flat_rate(mornings, 'fog', 'city')
    monthly = np.clip(mornings.rate.values, .005, .995)
    p, _ = predict_held_out(mornings, 'fog', MORNING_INPUTS, mornings.rate.values, fit_cities)
    print(f'\nMORNING: {len(mornings)} mornings, {int(y.sum())} with fog; label known for '
          + ', '.join(f'{mornings[f"before{lag}"].notna().mean():.1%} ({lag} before)' for lag in LAGS))
    report_sites(mornings, p, y, flat, monthly, 'MORNING test, airport and month left out', 500)
    formulas = {'morning': fit_all(mornings, 'fog', MORNING_INPUTS, mornings.rate.values)}
    for lag in LAGS:
        columns = MORNING_INPUTS + [f'before{lag}']
        q, _ = predict_held_out(mornings, 'fog', columns, mornings.rate.values, fit_cities, fallback=p)
        report_sites(mornings, q, y, flat, monthly, f'MORNING test with the fog morning {lag} before', 500)
        report_gain(mornings, q, p, y, f'MORNING with {lag} before', 1000)
        formulas[f'morning, {lag} before'] = fit_all(mornings, 'fog', columns, mornings.rate.values)

    # Hour: the usual rate for the hour is scaled to the month.
    hours = common.build_hour_table(mornings, {city: reports[city] for city in fit_cities}, forecasts, 'fog')
    hours = hours.merge(mornings[['city', 'day'] + [f'before{lag}' for lag in LAGS]], on=['city', 'day'], how='left')
    hours['rate'] = [compute_hour_rate(usual[city], month, hour)
                     for city, month, hour in zip(hours.city, hours.day.dt.month, hours.h)]
    y = hours.flag.values.astype(float)
    flat = compute_flat_rate(hours, 'flag', 'city_hour')
    p, _ = predict_held_out(hours, 'flag', HOUR_INPUTS + MORNING_INPUTS, hours.rate.values, fit_cities)
    print(f'\nHOUR: {len(hours)} hours')
    report_sites(hours, p, y, flat, hours.rate.values, 'HOUR test, airport and month left out', 300)
    formulas['hour'] = fit_all(hours, 'flag', HOUR_INPUTS + MORNING_INPUTS, hours.rate.values)
    for lag in LAGS:
        columns = HOUR_INPUTS + MORNING_INPUTS + [f'before{lag}']
        q, _ = predict_held_out(hours, 'flag', columns, hours.rate.values, fit_cities, fallback=p)
        report_sites(hours, q, y, flat, hours.rate.values, f'HOUR test with the fog morning {lag} before', 300)
        report_gain(hours, q, p, y, f'HOUR with {lag} before', 300)
        formulas[f'hour, {lag} before'] = fit_all(hours, 'flag', columns, hours.rate.values)

    print('\nWeights for "south-asia" in model.js. With "before": the inputs, the morning before (1 or 0), the usual rate, the constant.')
    for name, values in formulas.items():
        print(f'{name:18s} =', to_raw_weights(values))


if __name__ == '__main__':
    main()
