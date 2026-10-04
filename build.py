#!/usr/bin/env python3
"""Builds the site into _site/: a page per city, the list of cities, a sitemap, and the scripts and stylesheet from src/."""
import json
import shutil
from pathlib import Path
from string import Template

ROOT = Path(__file__).parent
SRC = ROOT / 'src'
OUT = ROOT / '_site'
SITE_URL = 'https://charlie42.github.io/fog-forecast/'   # used for canonical links and the sitemap
STATIC = ['style.css', 'model.js', 'page.js']
ARTICLE = 'how-to-predict-fog'
ICON = ("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3E%3Crect width='16' height='16' rx='3' fill='%2335434d'/%3E"
        "%3Cpath d='M3 5h10M3 8h10M3 11h6' stroke='%23fff' stroke-width='1.6' stroke-linecap='round'/%3E%3C/svg%3E")
PLACE_KEYS = ['lat', 'lon', 'tz', 'mist', 'fog', 'mistByHour', 'fogByHour']   # what page.js needs


def percent(share):
    return f'{int(share * 100 + 0.5)}%'


def slug(city):
    return city['name'].lower()


def city_page(template, city, cities):
    nav = '<br>\n'.join(
        f'<b>{c["name"]}</b>' if c is city else f'<a href="../{slug(c)}/">{c["name"]}</a>'
        for c in cities)
    return template.substitute(
        name=city['name'], site=city['site'], nav=nav,
        fog=percent(city['fog']), mist=percent(city['mist']),
        place=json.dumps({key: city[key] for key in PLACE_KEYS}),
        url=SITE_URL + slug(city) + '/', icon=ICON)


def index_page(template, cities):
    rows = '\n'.join(
        f'<li><a href="{slug(c)}/">{c["name"]}</a> <small>{c["site"]}</small></li>' for c in cities)
    return template.substitute(
        count=len(cities), names=', '.join(c['name'] for c in cities), rows=rows,
        url=SITE_URL, icon=ICON)


def main():
    cities = json.loads((ROOT / 'cities.json').read_text(encoding='utf-8'))
    shutil.rmtree(OUT, ignore_errors=True)
    OUT.mkdir()
    for name in STATIC:
        shutil.copy(SRC / name, OUT)

    template = Template((SRC / 'city.html').read_text(encoding='utf-8'))
    for city in cities:
        (OUT / slug(city)).mkdir()
        (OUT / slug(city) / 'index.html').write_text(city_page(template, city, cities), encoding='utf-8')

    template = Template((SRC / 'index.html').read_text(encoding='utf-8'))
    (OUT / 'index.html').write_text(index_page(template, cities), encoding='utf-8')

    template = Template((SRC / f'{ARTICLE}.html').read_text(encoding='utf-8'))
    by_fog = sorted(cities, key=lambda c: c['fog'])
    (OUT / ARTICLE).mkdir()
    (OUT / ARTICLE / 'index.html').write_text(template.substitute(
        low=percent(by_fog[0]['fog']), lowest=by_fog[0]['name'], high=percent(by_fog[-1]['fog']), highest=by_fog[-1]['name'],
        url=SITE_URL + ARTICLE + '/', icon=ICON), encoding='utf-8')

    urls = [SITE_URL] + [SITE_URL + slug(c) + '/' for c in cities] + [SITE_URL + ARTICLE + '/']
    (OUT / 'sitemap.xml').write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + ''.join(f'<url><loc>{url}</loc></url>\n' for url in urls) + '</urlset>\n', encoding='utf-8')
    print(f'Wrote {len(urls)} pages to {OUT}')


if __name__ == '__main__':
    main()
