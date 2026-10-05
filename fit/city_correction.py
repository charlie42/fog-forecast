"""The correction per city (`mistShift` and `fogShift` in cities.json).

Run: python city_correction.py
For some cities the formula's average is off: at Houston it says 3% for fog where fog comes on 8% of mornings.
The full correction is the constant which, added to the log-odds, makes the average chance over the city's
mornings equal to how often it happened. The city list holds half of it, and the page adds that to the
morning chance and to each hour's chance. The weights are those of fit_morning.py, unchanged.
Not for Delhi, Lahore and Amritsar, which have weights of their own.
Berlin is taken at the weather station Tempelhof, as on its page: readings from the German weather service,
and the usual rate from the station's record since October 2022."""
import json

import numpy as np
import pandas as pd

import common
import fit_morning
import keep_test
from common import WINTER

FITTING_CITIES_SHOWN = ['Hamburg', 'Munich', 'Paris', 'Amsterdam', 'Vienna', 'Prague', 'Zurich', 'Milan']
# Model, months, whether fog and mist count only near saturation, stations: as each city was tested in keep_test.py.
ADDED_LATER = [
    ('icon_eu', WINTER, False, [('EPKK', 'Krakow', 'Europe/Warsaw'), ('LIPZ', 'Venice', 'Europe/Rome'),
                                ('LIPE', 'Bologna', 'Europe/Rome'), ('EGKK', 'London', 'Europe/London')]),
    ('icon_eu', WINTER, True, [('ESSB', 'Stockholm', 'Europe/Stockholm')]),
    ('icon_global', WINTER, False, [('IAH', 'Houston', 'America/Chicago'), ('GLS', 'Galveston', 'America/Chicago')]),
    # Fresno and Bakersfield: 7 mist mornings each were dry haze, and their rates in the city list leave those out.
    ('icon_global', WINTER, True, [
        ('SAC', 'Sacramento', 'America/Los_Angeles'), ('BFI', 'Seattle', 'America/Los_Angeles'),
        ('FAT', 'Fresno', 'America/Los_Angeles'), ('BFL', 'Bakersfield', 'America/Los_Angeles')]),
    ('icon_global', keep_test.SUMMER, False, [('NZAA', 'Auckland', 'Pacific/Auckland'),
                                              ('NZCH', 'Christchurch', 'Pacific/Auckland')]),
]
# The cities added on 5 October 2026, all tested with the humidity condition. A list of its own: the tests of the
# later mornings were made on the 13 cities of ADDED_LATER.
BY_COUNTRY = [('icon_eu', WINTER, True, keep_test.GROUPS[group][2]) for group in keep_test.BY_COUNTRY]
STRENGTH = 0.5


def load_tempelhof():
    """Morning table for Berlin's page, and the mornings of the station's longer record, which give the usual rates."""
    reports = common.load_dwd_reports('00433', 'Europe/Berlin', '2022-10-01', '2026-10-04')
    labels = common.label_mornings(reports, ['mist', 'fog'])
    record = labels[labels.index.month.isin(WINTER)]
    forecast = common.load_forecast('fcs_B00433_icon_eu.json', 52.4675, 13.4021, 'Europe/Berlin', 'icon_eu',
                                    '2026-10-03')
    table = common.finish_table([common.build_morning_table('Berlin', labels, forecast, WINTER)])
    return table, record


def load_site_tables(europe):
    """For each city with the formula "europe": its morning table, and the mornings its usual rates come from."""
    berlin, record = load_tempelhof()
    tables = [(berlin, record)]
    tables += [(europe[europe.city == city], europe[europe.city == city]) for city in FITTING_CITIES_SHOWN]
    for model, months, near_saturation, stations in ADDED_LATER + BY_COUNTRY:
        table, _, _ = keep_test.load_group(model, months, stations, near_saturation)
        tables += [(table[table.city == city], table[table.city == city]) for _, city, _ in stations]
    return tables


def solve_full_correction(log_odds, y):
    """The constant c with mean(chance from log_odds + c) = mean(y), by bisection, kept within -3 to 3."""
    low, high = -3.0, 3.0
    for _ in range(40):
        middle = (low + high) / 2
        if (1 / (1 + np.exp(-(log_odds + middle)))).mean() < y.mean():
            low = middle
        else:
            high = middle
    return (low + high) / 2


def compute_city_numbers(table, formula, target, rate):
    """Usual rate as in the city list (3 decimals), what the formula says on average, what happened, the full correction."""
    rate = float(f'{max(rate, .003):.3f}')
    p = formula.predict_proba(fit_morning.build_features(table, pd.Series(rate, index=table.index)))[:, 1]
    y = table[target].values.astype(float)
    return dict(n=int(y.sum()), said=p.mean(), happened=y.mean(),
                full=solve_full_correction(np.log(p / (1 - p)), y))


def main():
    europe, _, _ = common.load_europe()
    formulas = {target: fit_morning.fit_all(europe, target) for target in ('mist', 'fog')}
    tables = load_site_tables(europe)

    print(f'{"city":14s}{"mornings":>9s} | mist: {"n":>4s} {"said":>6s} {"happened":>9s} {"full":>6s} {"in list":>8s}'
          f' | fog: {"n":>4s} {"said":>6s} {"happened":>9s} {"full":>6s} {"in list":>8s}')
    entries = {}
    for table, record in tables:
        city = table.city.iloc[0]
        numbers = {target: compute_city_numbers(table, formulas[target], target, record[target].mean())
                   for target in ('mist', 'fog')}
        entries[city] = dict(mistShift=round(STRENGTH * numbers['mist']['full'], 2),
                             fogShift=round(STRENGTH * numbers['fog']['full'], 2))
        columns = []
        for target in ('mist', 'fog'):
            n = numbers[target]
            columns.append(f'      {n["n"]:4d} {n["said"]:6.1%} {n["happened"]:9.1%} {n["full"]:+6.2f} '
                           f'{entries[city][target + "Shift"]:+8.2f}')
        print(f'{city:14s}{len(table):9d} | ' + ' | '.join(columns))
    for target in ('mist', 'fog'):
        print(f'weights {target}:', common.to_raw_weights(formulas[target]))
    print('\nFor cities.json:')
    print(json.dumps(entries, indent=1))


if __name__ == '__main__':
    main()
