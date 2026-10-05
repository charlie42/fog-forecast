"""Test for a new city: does the page's formula beat the airport's own usual rate?

Run: python keep_test.py europe        (or: north, south, us, nearer-europe, nearer-us, germany, poland, netherlands,
                                        uk, italy-north, city-stations; no argument runs all)
The weights from fit_morning.py are used as they are. Only the usual rate comes from the airport, taken
from its other months. A city is kept if the fog skill is at least 10%, the 90% range (months resampled)
stays above zero, and there are at least 15 fog mornings. Mist skill is printed alongside.
Entries for the city list (usual rates for the morning and for each hour 03 to 11 h) are printed for the cities that pass.
Inputs come from the ICON-EU model in Europe and from the worldwide ICON model elsewhere.
The airport reports are visibility alone, as when the weights were fitted, except in the groups tested after the
humidity condition came in: fog and mist count there only in air within 2 C of saturation. Those are the two
"nearer" groups (airports nearer the city centre than the one first tested) and the five groups by country, which
hold the cities that passed out of 45 airfields in Germany, 46 in Poland, the Netherlands and the United Kingdom and
16 in northern Italy and have at least 100,000 people and the station within about 20 km (Friedrichshafen and
Treviso are smaller).
"city-stations" compares the weather station inside Munich with the one at its airport, both from the
German weather service, with one visibility reading per hour. No entries are printed for that group."""
import json
import sys

import numpy as np

import common
import fit_morning
from common import MORNING_INPUTS, WINTER, logit, skill, skill_range

SUMMER = (4, 5, 6, 7, 8, 9)    # for the southern cities
GROUPS = {
    'europe': ('icon_eu', WINTER, [
        ('EPKK', 'Krakow', 'Europe/Warsaw'), ('LIPZ', 'Venice', 'Europe/Rome'), ('LIPE', 'Bologna', 'Europe/Rome'),
        ('LIMF', 'Turin', 'Europe/Rome'), ('EGSS', 'London Stansted', 'Europe/London'),
        ('EGGW', 'London Luton', 'Europe/London'), ('EGKK', 'London Gatwick', 'Europe/London')]),
    'north': ('icon_global', WINTER, [
        ('VIDP', 'Delhi', 'Asia/Kolkata'), ('OPLA', 'Lahore', 'Asia/Karachi'), ('OPIS', 'Islamabad', 'Asia/Karachi'),
        ('VIAR', 'Amritsar', 'Asia/Kolkata'), ('OMDB', 'Dubai', 'Asia/Dubai'), ('CYVR', 'Vancouver', 'America/Vancouver'),
        ('CYYZ', 'Toronto', 'America/Toronto'), ('BFL', 'Bakersfield', 'America/Los_Angeles'),
        ('SAN', 'San Diego', 'America/Los_Angeles'), ('GLS', 'Galveston', 'America/Chicago'),
        ('HAF', 'Half Moon Bay', 'America/Los_Angeles')]),
    'south': ('icon_global', SUMMER, [
        ('YMML', 'Melbourne', 'Australia/Melbourne'), ('NZAA', 'Auckland', 'Pacific/Auckland'),
        ('NZCH', 'Christchurch', 'Pacific/Auckland')]),
    'us': ('icon_global', WINTER, [
        ('SMF', 'Sacramento', 'America/Los_Angeles'), ('FAT', 'Fresno', 'America/Los_Angeles'),
        ('SFO', 'San Francisco', 'America/Los_Angeles'), ('LAX', 'Los Angeles', 'America/Los_Angeles'),
        ('SEA', 'Seattle', 'America/Los_Angeles'), ('PDX', 'Portland', 'America/Los_Angeles'),
        ('DEN', 'Denver', 'America/Denver'), ('ORD', 'Chicago', 'America/Chicago'),
        ('MSP', 'Minneapolis', 'America/Chicago'), ('IAH', 'Houston', 'America/Chicago'),
        ('ATL', 'Atlanta', 'America/New_York'), ('JFK', 'New York', 'America/New_York'),
        ('BOS', 'Boston', 'America/New_York'), ('IAD', 'Washington', 'America/New_York')]),
    'nearer-europe': ('icon_eu', WINTER, [
        ('ESSB', 'Stockholm Bromma', 'Europe/Stockholm'), ('LFPO', 'Paris Orly', 'Europe/Paris'),
        ('LFPB', 'Paris Le Bourget', 'Europe/Paris'), ('LFPV', 'Paris Villacoublay', 'Europe/Paris')]),
    'nearer-us': ('icon_global', WINTER, [
        ('SAC', 'Sacramento Executive', 'America/Los_Angeles'), ('BFI', 'Seattle Boeing Field', 'America/Los_Angeles'),
        ('HOU', 'Houston Hobby', 'America/Chicago')]),
    'germany': ('icon_eu', WINTER, [(station, city, 'Europe/Berlin') for station, city in [
        ('EDDS', 'Stuttgart'), ('EDDP', 'Leipzig'), ('EDDV', 'Hanover'), ('EDDW', 'Bremen'), ('EDFM', 'Mannheim'),
        ('ETOU', 'Wiesbaden'), ('EDMA', 'Augsburg'), ('EDLN', 'Mönchengladbach'), ('EDVE', 'Braunschweig'), ('EDHK', 'Kiel'),
        ('EDHL', 'Lübeck'), ('EDDE', 'Erfurt'), ('EDVK', 'Kassel'), ('EDDR', 'Saarbrücken'), ('ETSI', 'Ingolstadt'),
        ('EDDG', 'Münster'), ('ETHL', 'Ulm'), ('ETNL', 'Rostock'), ('EDNY', 'Friedrichshafen')]]),
    'poland': ('icon_eu', WINTER, [(station, city, 'Europe/Warsaw') for station, city in [
        ('EPWR', 'Wroclaw'), ('EPLL', 'Lodz'), ('EPPO', 'Poznan'), ('EPGD', 'Gdansk'), ('EPLB', 'Lublin'),
        ('EPBY', 'Bydgoszcz'), ('EPRA', 'Radom'), ('EPRZ', 'Rzeszow')]]),
    'netherlands': ('icon_eu', WINTER, [(station, city, 'Europe/Amsterdam') for station, city in [
        ('EHRD', 'Rotterdam'), ('EHGG', 'Groningen'), ('EHEH', 'Eindhoven'), ('EHGR', 'Breda'), ('EHDL', 'Arnhem'),
        ('EHLW', 'Leeuwarden')]]),
    'uk': ('icon_eu', WINTER, [(station, city, 'Europe/London') for station, city in [
        ('EGBB', 'Birmingham'), ('EGSH', 'Norwich'), ('EGGP', 'Liverpool'), ('EGPF', 'Glasgow'), ('EGCC', 'Manchester')]]),
    'italy-north': ('icon_eu', WINTER, [(station, city, 'Europe/Rome') for station, city in [
        ('LIPO', 'Brescia'), ('LIPH', 'Treviso'), ('LIPI', 'Udine'), ('LIPR', 'Rimini')]]),
}
BY_COUNTRY = ('germany', 'poland', 'netherlands', 'uk', 'italy-north')
NEAR_SATURATION = ('nearer-europe', 'nearer-us') + BY_COUNTRY
GROUPS['city-stations'] = ('icon_eu', WINTER, [
    ('03379', 'Munich city', 'Europe/Berlin'), ('01262', 'Munich airport', 'Europe/Berlin')])
GERMAN_WEATHER_SERVICE = ('city-stations',)


def load_group(model, months, stations, near_saturation=False, german_weather_service=False):
    """Reports, forecasts and the morning table for the stations of one group."""
    reports, forecasts, rows = {}, {}, []
    for station, city, tz in stations:
        if german_weather_service:
            reports[city] = common.dwd_reports(station, tz, '2024-01-19', '2026-10-04')
        else:
            reports[city] = common.airport_reports(station, tz, '2024-01-19', '2026-10-04', near_saturation)
        forecasts[city] = common.forecast(f'fcs_{station}_{model}.json', reports[city].lat.iloc[0],
                                          reports[city].lon.iloc[0], tz, model, '2026-10-03')
        labels = common.morning_labels(reports[city], ['mist', 'fog'])
        rows.append(common.morning_table(city, labels, forecasts[city], months))
    return common.finish_table(rows), reports, forecasts


def test_city(t, formula, target):
    """Chance from the page's formula with the city's usual rate from its other months; skill and range."""
    y = t[target].values.astype(float)
    chance = np.zeros(len(t))
    usual = np.zeros(len(t))
    for month in t.fold.unique():
        test = (t.fold == month).values
        rate = t[~test][target].mean()
        x = t[MORNING_INPUTS].copy()
        x['usual'] = logit(rate, fit_morning.LOW)
        chance[test] = formula.predict_proba(x[test])[:, 1]
        usual[test] = rate
    low, high = skill_range(chance, usual, y, t.fold.values) if y.sum() >= 3 else (np.nan, np.nan)
    return dict(n=int(y.sum()), skill=skill(chance, usual, y), low=low, high=high, said=chance.mean(), rate=y.mean())


def entry(station, city, tz, model, reports, t, hours):
    """Entry for the city list: usual morning rates and usual rate per hour, floored at 0.3%.

    `lat` and `lon` are the centre of the city, which the page asks the weather forecast for. They are left empty
    here and filled in by hand. The station the reports come from goes into `stationLat` and `stationLon`."""
    r3 = lambda x: float(f'{max(x, .003):.3f}')
    e = dict(name=city, site=f'{station} airport', lat=None, lon=None, stationLat=round(float(reports.lat.iloc[0]), 4),
             stationLon=round(float(reports.lon.iloc[0]), 4), tz=tz)
    if model != 'icon_eu':
        e['model'] = model
    e.update(mist=r3(t.mist.mean()), fog=r3(t.fog.mean()))
    e['mistByHour'] = [r3(v) for v in hours['mist'].groupby(hours['mist'].h).flag.mean()]
    e['fogByHour'] = [r3(v) for v in hours['fog'].groupby(hours['fog'].h).flag.mean()]
    return e


if __name__ == '__main__':
    europe, _, _ = common.load_europe()
    formulas = {target: fit_morning.fit_all(europe, target) for target in ('mist', 'fog')}
    for group in sys.argv[1:] or GROUPS:
        model, months, stations = GROUPS[group]
        table, reports, forecasts = load_group(model, months, stations, group in NEAR_SATURATION,
                                               group in GERMAN_WEATHER_SERVICE)
        print(f'\n== {group}: inputs from {model}, months {months}')
        print(f'{"city":22s}{"mornings":>9s} | {"mist":>5s} {"skill":>6s} {"90% range":>12s} | {"fog":>5s} {"skill":>6s} '
              f'{"90% range":>12s} | said / happened fog | keep?')
        results = {}
        for city in table.city.unique():
            t = table[table.city == city]
            mist, fog = (test_city(t, formulas[target], target) for target in ('mist', 'fog'))
            keep = fog['skill'] >= .1 and fog['low'] > 0 and fog['n'] >= 15
            results[city] = (t, keep)
            print(f'{city:22s}{len(t):9d} | {mist["n"]:5d} {mist["skill"]:6.0%} {mist["low"]:5.0%} to {mist["high"]:4.0%} | '
                  f'{fog["n"]:5d} {fog["skill"]:6.0%} {fog["low"]:5.0%} to {fog["high"]:4.0%} | '
                  f'{fog["said"]:5.1%} / {fog["rate"]:5.1%}    | {"KEEP" if keep else "drop"}')
        if group in GERMAN_WEATHER_SERVICE:
            continue
        print('\nEntries for the city list:')
        for station, city, tz in stations:
            if city in results and results[city][1]:
                t = results[city][0]
                hours = {flag: common.hour_table(t, {city: reports[city]}, forecasts, flag) for flag in ('mist', 'fog')}
                print('  ' + json.dumps(entry(station, city, tz, model, reports[city], t, hours)) + ',')
