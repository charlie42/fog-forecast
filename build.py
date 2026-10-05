#!/usr/bin/env python3
"""Builds the site into _site/: a page per city and language, the lists of cities, two pages of text, a sitemap, and the scripts, stylesheet and fonts from src/."""
import json
import shutil
from pathlib import Path
from string import Template

ROOT = Path(__file__).parent
SRC = ROOT / 'src'
OUT = ROOT / '_site'
SITE_URL = 'https://chanceoffog.com/'   # used for canonical links and the sitemap
STATIC = ['style.css', 'model.js', 'page.js', 'google7870e9be589df912.html']   # the last one proves ownership to Google Search Console
ARTICLE = 'how-to-predict-fog'
ACCURACY = 'accuracy'
ICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Crect width='16' height='16' rx='3' fill='%2335434d'/%3E"
        "%3Cpath d='M3 5h10M3 8h10M3 11h6' stroke='%23fff' stroke-width='1.6' stroke-linecap='round'/%3E%3C/svg%3E")
# English has a page for every city. Another language has one for each city that carries its code in cities.json,
# plus templates named after it in src/ and its words in page.js.
LANGUAGES = {'en': 'English', 'de': 'Deutsch', 'it': 'Italiano'}
LOADING = {'en': 'loading…', 'de': 'lädt…', 'it': 'caricamento…'}
AND = {'en': ' and ', 'de': ' und ', 'it': ' e '}
# The usual rates in cities.json are for the foggier half of the year: north of the equator, then south of it.
SEASON = {'en': ['October to March', 'April to September'], 'de': ['Oktober bis März', 'April bis September'],
          'it': ['ottobre a marzo', 'aprile a settembre']}
PLACE_KEYS = ['lat', 'lon', 'tz', 'model', 'formula', 'rare', 'mist', 'fog', 'mistShift', 'fogShift', 'mistByHour', 'fogByMonth', 'fogByHour', 'fogBefore']   # what page.js and model.js need; model, formula and rare only where they differ from the usual


def percent(share):
    return f'{int(share * 100 + 0.5)}%'


def slug(city):
    return city['name'].lower().translate(str.maketrans({'ä': 'ae', 'ö': 'oe', 'ü': 'ue'}))


def in_language(city, lang):
    """The city with its name and site in that language, or None where cities.json has no translation."""
    if lang == 'en':
        return city
    return {**city, **city[lang]} if lang in city else None


def folder(lang):
    return '' if lang == 'en' else lang + '/'


def address(city, lang):
    """Where the city's page in that language sits under the site root, e.g. 'de/muenchen/'."""
    return folder(lang) + slug(in_language(city, lang)) + '/'


def alternates(addresses):
    """The lines that tell search engines which pages are translations of each other. `addresses` maps language to address."""
    if len(addresses) < 2:
        return ''
    links = [*addresses.items(), ('x-default', addresses['en'])]
    return ''.join(f'<link rel="alternate" hreflang="{lang}" href="{SITE_URL}{to}">\n' for lang, to in links)


def template(name, lang):
    """The template of that name in that language: src/city.html for English, src/city.de.html for German."""
    return Template((SRC / (name + ('' if lang == 'en' else '.' + lang) + '.html')).read_text(encoding='utf-8'))


def by_month(city):
    """The usual fog rate for each month from October to March, where it differs too much for one number:
    '4% of October mornings, 46% in November, ... and 6% in March'."""
    months = ['October', 'November', 'December', 'January', 'February', 'March']
    rates = [percent(city['fogByMonth'][i]) for i in (9, 10, 11, 0, 1, 2)]
    parts = [f'{rates[0]} of {months[0]} mornings'] + [f'{rate} in {month}' for rate, month in zip(rates[1:], months[1:])]
    return ', '.join(parts[:-1]) + AND['en'] + parts[-1]


def city_page(city, cities, lang, forecast):
    """The list under the forecast names the cities with a page in this language; `rest` links to the others in English."""
    root = '../' if lang == 'en' else '../../'
    here = in_language(city, lang)
    addresses = {other: address(city, other) for other in LANGUAGES if in_language(city, other)}
    nav = [f'<li><b>{here["name"]}</b></li>' if c is city else f'<li><a href="{root}{address(c, lang)}">{in_language(c, lang)["name"]}</a></li>'
           for c in cities if in_language(c, lang)]
    switch = ''.join(f'<br>\n<a href="{root}{to}" lang="{other}" hreflang="{other}">{LANGUAGES[other]}</a>'
                     for other, to in addresses.items() if other != lang)
    rest = [f'<li><a href="{root}{address(c, "en")}" lang="en" hreflang="en">{c["name"]}</a></li>' for c in cities if not in_language(c, lang)]
    # A city that people search for by its region has the region next to its name: 'Lahore, Punjab'.
    region = city.get('region', '')
    # A place without a usual mist rate has a template of its own, which leaves mist out of the wording.
    return template('city' if 'mist' in city else 'city.fog', lang).substitute(
        name=here['name'], region=region and f', {region}', regionAside=region and f', {region},', inRegion=region and f' in {region}',
        site=here['site'], nav='\n'.join(nav), rest='\n'.join(rest), switch=switch, forecast=forecast,
        fog=percent(city['fog']), mist=percent(city.get('mist', 0)), season=SEASON[lang][city['lat'] < 0],
        months=by_month(city) if 'fogByMonth' in city else '',
        place=json.dumps({key: city[key] for key in PLACE_KEYS if key in city}),
        url=SITE_URL + addresses[lang], alternates=alternates(addresses), root=root, icon=ICON)


def index_page(cities, lang):
    """`rest` lists the cities without a page in this language, linked to their English one."""
    places = [in_language(c, lang) for c in cities if in_language(c, lang)]
    names = [c['name'] for c in places]
    rows = '\n'.join(
        f'<li><a href="{slug(c)}/">{c["name"]}</a></li>' for c in places)
    rest = '\n'.join(
        f'<li><a href="../{address(c, "en")}" lang="en" hreflang="en">{c["name"]}</a></li>' for c in cities if not in_language(c, lang))
    switch = ' · '.join(f'<a href="{"../" if lang != "en" else ""}{folder(other)}" lang="{other}" hreflang="{other}">{name}</a>'
                        for other, name in LANGUAGES.items() if other != lang)
    return template('index', lang).substitute(
        switch=switch, count=len(places), names=', '.join(names), names_and=', '.join(names[:-1]) + AND[lang] + names[-1], rows=rows, rest=rest,
        url=SITE_URL + folder(lang), alternates=alternates({other: folder(other) for other in LANGUAGES}), icon=ICON)


def main():
    cities = sorted(json.loads((ROOT / 'cities.json').read_text(encoding='utf-8')), key=lambda c: c['name'])
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir()
    for name in STATIC:
        shutil.copy(SRC / name, OUT)
    shutil.copytree(SRC / 'fonts', OUT / 'fonts')   # the typeface and its licence

    # The forecast rows come from prerender.js. Without them the pages start empty and fill in once opened.
    made = ROOT / 'forecasts.json'
    forecasts = json.loads(made.read_text(encoding='utf-8')) if made.exists() else {}
    # Whether the last mornings had fog at the airport, also from prerender.js, for the cities whose formula takes that in.
    # It goes into the page so that the rows worked out in the browser are the same as the ones from the build.
    made = ROOT / 'reports.json'
    before = json.loads(made.read_text(encoding='utf-8')) if made.exists() else {}
    cities = [{**city, 'fogBefore': before[city['name']]} if city['name'] in before else city for city in cities]
    urls = []
    for lang in LANGUAGES:
        having = [c for c in cities if in_language(c, lang)]
        (OUT / folder(lang)).mkdir(exist_ok=True)
        (OUT / folder(lang) / 'index.html').write_text(index_page(cities, lang), encoding='utf-8')
        urls.append(SITE_URL + folder(lang))

        for city in having:
            forecast = forecasts.get(city['name'], {}).get(lang, LOADING[lang])
            (OUT / address(city, lang)).mkdir()
            page = city_page(city, cities, lang, forecast)
            (OUT / address(city, lang) / 'index.html').write_text(page, encoding='utf-8')
            urls.append(SITE_URL + address(city, lang))

    by_fog = sorted((c for c in cities if c['tz'].startswith('Europe/')), key=lambda c: c['fog'])   # the article's numbers are from Europe
    low = percent(by_fog[0]['fog'])
    lowest = ' and '.join(c['name'] for c in by_fog if percent(c['fog']) == low)   # Berlin and Amsterdam are level
    (OUT / ARTICLE).mkdir()
    (OUT / ARTICLE / 'index.html').write_text(template(ARTICLE, 'en').substitute(
        low=low, lowest=lowest, high=percent(by_fog[-1]['fog']), highest=by_fog[-1]['name'],
        url=SITE_URL + ARTICLE + '/', icon=ICON), encoding='utf-8')
    urls.append(SITE_URL + ARTICLE + '/')

    (OUT / ACCURACY).mkdir()
    (OUT / ACCURACY / 'index.html').write_text(
        template(ACCURACY, 'en').substitute(url=SITE_URL + ACCURACY + '/', icon=ICON), encoding='utf-8')
    urls.append(SITE_URL + ACCURACY + '/')

    (OUT / 'sitemap.xml').write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + ''.join(f'<url><loc>{url}</loc></url>\n' for url in urls) + '</urlset>\n', encoding='utf-8')
    print(f'Wrote {len(urls)} pages to {OUT}')


if __name__ == '__main__':
    main()
