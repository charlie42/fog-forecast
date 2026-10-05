"""Weights for the chance of mist (MIST_HOUR) and fog (FOG_HOUR) in a single clock hour, 03 to 11 h.

Run: python fit_hourly.py
Same 14 airports and mornings as fit_morning.py. An hour counts if any report in that clock hour
shows the visibility limit (5 km for mist, 1 km for fog) without rain or snow.
The test leaves out one month at a time."""
import numpy as np
from sklearn.metrics import roc_auc_score

import common
from common import (HOUR_INPUTS, MORNING_INPUTS, brier_skill_score, format_calibration, logit, make_logistic,
                    to_raw_weights)

COLUMNS = HOUR_INPUTS + MORNING_INPUTS
RATE_FLOOR = 0.003   # usual rates are kept between 0.3% and 99.7% before the log-odds


def build_features(table, rate):
    X = table[COLUMNS].copy()
    X['usual'] = logit(rate.values, RATE_FLOOR)
    return X


def predict_held_out_months(table):
    """Chance for every hour from a fit on the other months, and the usual rate for that city and hour."""
    y = table.flag.values.astype(float)
    chance = np.zeros(len(table))
    usual = np.zeros(len(table))
    for month in sorted(table.fold.unique()):
        test_mask = (table.fold == month).values
        rate = table.city_hour.map(table[~test_mask].groupby('city_hour').flag.mean()).fillna(y[~test_mask].mean())
        model = make_logistic(3000).fit(build_features(table, rate)[~test_mask], y[~test_mask])
        chance[test_mask] = model.predict_proba(build_features(table, rate)[test_mask])[:, 1]
        usual[test_mask] = rate[test_mask]
    return chance, usual


def print_hour_ranking(table, chance, usual):
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
    p, usual = predict_held_out_months(table)
    print(f'\n{name}: {len(table)} hours, {y.mean():.1%} flagged; skill over the usual rate for the '
          f'city and hour, each month predicted from the others: {brier_skill_score(p, usual, y):.0%}')
    print('  said -> happened: ' + format_calibration(p, y))
    print_hour_ranking(table, p, usual)


def fit_all(table):
    """Weights fitted on every hour: five hourly inputs, six morning inputs, usual rate (log-odds), constant."""
    rate = table.city_hour.map(table.groupby('city_hour').flag.mean())
    return to_raw_weights(make_logistic(3000).fit(build_features(table, rate), table.flag.astype(float)))


def main():
    mornings, reports, forecasts = common.load_europe()
    weights = {}
    for flag, name in (('mist', 'MIST_HOUR'), ('fog', 'FOG_HOUR')):
        table = common.build_hour_table(mornings, reports, forecasts, flag)
        report_test(table, name)
        weights[name] = fit_all(table)
    print()
    for name, values in weights.items():
        print(f'{name} =', values)


if __name__ == '__main__':
    main()
