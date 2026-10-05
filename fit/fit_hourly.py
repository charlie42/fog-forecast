"""Weights for the chance of mist (MIST_HOUR) and fog (FOG_HOUR) in a single clock hour, 03 to 11 h.

Run: python fit_hourly.py
Same 14 airports and mornings as fit_morning.py. An hour counts if any report in that clock hour
shows the visibility limit (5 km for mist, 1 km for fog) without rain or snow.
The test leaves out one month at a time."""
import numpy as np
from sklearn.metrics import roc_auc_score

import common
from common import HOUR_INPUTS, MORNING_INPUTS, logistic, logit, raw_weights, skill, calibration

COLUMNS = HOUR_INPUTS + MORNING_INPUTS
LOW = 0.003   # usual rates are kept between 0.3% and 99.7% before the log-odds


def inputs(table, rate):
    x = table[COLUMNS].copy()
    x['usual'] = logit(rate.values, LOW)
    return x


def held_out_month(table):
    """Chance for every hour from a fit on the other months, and the usual rate for that city and hour."""
    y = table.flag.values.astype(float)
    chance = np.zeros(len(table))
    usual = np.zeros(len(table))
    for month in sorted(table.fold.unique()):
        test = (table.fold == month).values
        rate = table.city_hour.map(table[~test].groupby('city_hour').flag.mean()).fillna(y[~test].mean())
        model = logistic(3000).fit(inputs(table, rate)[~test], y[~test])
        chance[test] = model.predict_proba(inputs(table, rate)[test])[:, 1]
        usual[test] = rate[test]
    return chance, usual


def timing(table, chance, usual):
    """On mornings with both flagged and clear hours: how often a flagged hour is ranked above a clear one."""
    scores = {'formula': [], 'usual pattern': []}
    table = table.assign(chance=chance, usual=usual)
    for _, day in table.groupby(['city', 'day']):
        if 0 < day.flag.sum() < len(day) and len(day) >= 7:
            scores['formula'].append(roc_auc_score(day.flag, day.chance))
            scores['usual pattern'].append(roc_auc_score(day.flag, day.usual))
    n = len(scores['formula'])
    print(f'  ranking a flagged hour above a clear one, {n} mornings: ' +
          ', '.join(f'{k} {np.mean(v):.0%}' for k, v in scores.items()))


def report_test(table, name):
    y = table.flag.values.astype(float)
    p, usual = held_out_month(table)
    print(f'\n{name}: {len(table)} hours, {y.mean():.1%} flagged; skill over the usual rate for the '
          f'city and hour, each month predicted from the others: {skill(p, usual, y):.0%}')
    print('  said -> happened: ' + calibration(p, y))
    timing(table, p, usual)


def fit_all(table):
    """Weights fitted on every hour: five hourly inputs, six morning inputs, usual rate (log-odds), constant."""
    rate = table.city_hour.map(table.groupby('city_hour').flag.mean())
    return raw_weights(logistic(3000).fit(inputs(table, rate), table.flag.astype(float)))


if __name__ == '__main__':
    mornings, reports, forecasts = common.load_europe()
    weights = {}
    for flag, name in (('mist', 'MIST_HOUR'), ('fog', 'FOG_HOUR')):
        table = common.hour_table(mornings, reports, forecasts, flag)
        report_test(table, name)
        weights[name] = fit_all(table)
    print()
    for name, values in weights.items():
        print(f'{name} =', values)
