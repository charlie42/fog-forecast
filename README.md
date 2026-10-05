# Fog forecast

Chance of fog and mist on each of the next mornings, hour by hour, for 63 cities in Europe, the United States, New Zealand, India and Pakistan. Meant for photographers; it says nothing about road or flight conditions.

Live at https://chanceoffog.com/

The numbers come from a logistic regression on six values of the ICON weather forecast, fitted on two and a half winters of airport visibility reports. [HOW-IT-WORKS.md](HOW-IT-WORKS.md) has the formula, the test results and the cities that were left out.

## Running it

It needs Python 3 and Node 20 or later. There are no packages to install.

```sh
node --test                        # run the tests
node prerender.js                  # fetch the forecasts into forecasts.json (optional)
python3 build.py                   # write the site to _site/
python3 -m http.server -d _site    # serve it at http://localhost:8000
```

Each push to `main` tests, builds and publishes the site to GitHub Pages. The same workflow runs every three hours to refresh the numbers.

## Data

Weather data by [Open-Meteo.com](https://open-meteo.com/) (CC BY 4.0), from the ICON-EU and ICON global models of Deutscher Wetterdienst. Visibility reports from the [Iowa Environmental Mesonet](https://mesonet.agron.iastate.edu/) and [DWD open data](https://opendata.dwd.de/).
