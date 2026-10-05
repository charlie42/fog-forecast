"""Weights for the whole-morning chance of mist (MIST_MORNING) and fog (FOG_MORNING).

Run: python fit_morning.py
Fitted on October to March mornings at 14 European airports. Mist is visibility under 5 km and fog
under 1 km, in 2 or more of the clock hours 04 to 09. The test leaves out one month at a time."""
import numpy as np

import common
from common import (MORNING_INPUTS, bootstrap_skill_range, brier_skill_score, format_calibration, logit,
                    make_logistic, to_raw_weights)

RATE_FLOOR = 0.005   # usual rates are kept between 0.5% and 99.5% before the log-odds


def compute_usual_rates(table, target, rows):
    """The usual rate of each city, from the mornings in `rows`."""
    return table.city.map(table[rows].groupby('city')[target].mean())


def build_features(table, rate):
    X = table[MORNING_INPUTS].copy()
    X['usual'] = logit(rate.values, RATE_FLOOR)
    return X


def predict_held_out_months(table, target):
    """Chance for every morning from a fit on the other months, and the usual rate from those months."""
    y = table[target].astype(float)
    chance = np.zeros(len(table))
    usual = np.zeros(len(table))
    for month in sorted(table.fold.unique()):
        test_mask = (table.fold == month).values
        rate = compute_usual_rates(table, target, ~test_mask)
        model = make_logistic().fit(build_features(table, rate)[~test_mask], y[~test_mask])
        chance[test_mask] = model.predict_proba(build_features(table, rate)[test_mask])[:, 1]
        usual[test_mask] = rate[test_mask]
    return chance, usual


def report_test(table, target, name):
    y = table[target].values.astype(float)
    p, usual = predict_held_out_months(table, target)
    low, high = bootstrap_skill_range(p, usual, y, table.fold.values)
    print(f'\n{name}: skill over the usual rate, each month predicted from the others: '
          f'{brier_skill_score(p, usual, y):.0%} (90% range {low:.0%} to {high:.0%})')
    print('  said -> happened: ' + format_calibration(p, y))
    for threshold, label in ((.3, 'given 30% or more'), (.5, 'given 50% or more')):
        mask = p >= threshold
        print(f'  {label}: {mask.sum()} mornings, came on {y[mask].mean():.0%}, said {p[mask].mean():.0%}, '
              f'{y[mask].sum() / y.sum():.0%} of all')
    mask = p < .05
    print(f'  given under 5%: {mask.sum()} mornings, came on {y[mask].mean():.1%}')


def fit_all(table, target):
    """The formula fitted on every morning: six inputs, usual rate (log-odds), constant."""
    rate = compute_usual_rates(table, target, slice(None))
    return make_logistic().fit(build_features(table, rate), table[target].astype(float))


def main():
    table, _, _ = common.load_europe()
    print(f"{len(table)} mornings at {table.city.nunique()} airports, "
          f"{int(table.mist.sum())} with mist and {int(table.fog.sum())} with fog")
    report_test(table, 'mist', 'MIST')
    report_test(table, 'fog', 'FOG')
    print('\nMIST_MORNING =', to_raw_weights(fit_all(table, 'mist')))
    print('FOG_MORNING  =', to_raw_weights(fit_all(table, 'fog')))


if __name__ == '__main__':
    main()
