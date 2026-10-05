"""Weights for the whole-morning chance of mist (MIST_MORNING) and fog (FOG_MORNING).

Run: python fit_morning.py
Fitted on October to March mornings at 14 European airports. Mist is visibility under 5 km and fog
under 1 km, in 2 or more of the clock hours 04 to 09. The test leaves out one month at a time."""
import numpy as np

import common
from common import MORNING_INPUTS, logistic, logit, raw_weights, skill, skill_range, calibration

LOW = 0.005   # usual rates are kept between 0.5% and 99.5% before the log-odds


def usual_rates(table, target, rows):
    """The usual rate of each city, from the mornings in `rows`."""
    return table.city.map(table[rows].groupby('city')[target].mean())


def inputs(table, rate):
    x = table[MORNING_INPUTS].copy()
    x['usual'] = logit(rate.values, LOW)
    return x


def held_out_month(table, target):
    """Chance for every morning from a fit on the other months, and the usual rate from those months."""
    y = table[target].astype(float)
    chance = np.zeros(len(table))
    usual = np.zeros(len(table))
    for month in sorted(table.fold.unique()):
        test = (table.fold == month).values
        rate = usual_rates(table, target, ~test)
        model = logistic().fit(inputs(table, rate)[~test], y[~test])
        chance[test] = model.predict_proba(inputs(table, rate)[test])[:, 1]
        usual[test] = rate[test]
    return chance, usual


def report_test(table, target, name):
    y = table[target].values.astype(float)
    p, usual = held_out_month(table, target)
    low, high = skill_range(p, usual, y, table.fold.values)
    print(f'\n{name}: skill over the usual rate, each month predicted from the others: '
          f'{skill(p, usual, y):.0%} (90% range {low:.0%} to {high:.0%})')
    print('  said -> happened: ' + calibration(p, y))
    for cut, label in ((.3, 'given 30% or more'), (.5, 'given 50% or more')):
        k = p >= cut
        print(f'  {label}: {k.sum()} mornings, came on {y[k].mean():.0%}, said {p[k].mean():.0%}, '
              f'{y[k].sum() / y.sum():.0%} of all')
    k = p < .05
    print(f'  given under 5%: {k.sum()} mornings, came on {y[k].mean():.1%}')


def fit_all(table, target):
    """The formula fitted on every morning: six inputs, usual rate (log-odds), constant."""
    rate = usual_rates(table, target, slice(None))
    return logistic().fit(inputs(table, rate), table[target].astype(float))


if __name__ == '__main__':
    table, _, _ = common.load_europe()
    print(f"{len(table)} mornings at {table.city.nunique()} airports, "
          f"{int(table.mist.sum())} with mist and {int(table.fog.sum())} with fog")
    report_test(table, 'mist', 'MIST')
    report_test(table, 'fog', 'FOG')
    print('\nMIST_MORNING =', raw_weights(fit_all(table, 'mist')))
    print('FOG_MORNING  =', raw_weights(fit_all(table, 'fog')))
