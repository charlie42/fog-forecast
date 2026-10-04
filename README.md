# Fog forecast

Chance of fog and mist on each of the next mornings, hour by hour, for 14 European cities.

Live at https://charlie42.github.io/fog-forecast/

I photograph fog in Berlin and wanted to know the day before how likely it is.

## How the number is made

The page asks [Open-Meteo](https://open-meteo.com/) for the ICON-EU forecast at one site per city and takes six things from it:

- highest humidity between 4 and 10 h
- mean wind in those hours
- rain overnight and in the morning
- cloud cover the evening before
- how far the evening air is from saturation (temperature minus dew point)
- how much it cools overnight

A logistic regression turns those, plus how often the site usually has fog, into a chance. There are four sets of weights: fog and mist, each for a whole morning and for a single hour. Fog means visibility under 1 km and mist under 5 km. A morning counts when that lasts at least two hours between 4 and 10 h.

The weights were fitted once on all 14 cities together. A new place needs its usual fog and mist rates from its own visibility record and no fitting.

## How well it works

Fitted and tested on October to March mornings since January 2024: 6,115 mornings at 14 airports, 1,083 with mist and 460 with fog. Observations are airport METAR reports from the Iowa State archive, plus DWD station data for Berlin Tempelhof. The forecasts are day-ahead ICON-EU runs from Open-Meteo's previous-runs archive.

Skill below is the Brier skill score against always saying the site's usual rate. 0% is no better than that, 100% is perfect.

| Left out of fitting | Mist | Fog |
|---|---|---|
| Single months | 28% | 24% |
| Whole winters | 28% | 23% |
| Whole winters, and the city | 27% | 22% |

Against a harder baseline (usual rate, time of year, and whether yesterday was foggy) the skill is 21% for both.

Calibration with months left out: mornings given about 2, 9, 22, 39, 60 and 76% for mist had mist 2, 9, 23, 40, 57 and 76% of the time.

Where it is weak:

- Ranking mornings, it ties with the fog code in ICON's own output. At the same 1,133 alarms the fog code caught 623 mist mornings and the formula 621. What the formula adds is a percentage.
- Fog skill differs by city: Prague 35%, Vienna 34%, Milan 31%, down to London 8%, Madrid 3% and Frankfurt 0%.
- The page uses the day-ahead weights for mornings up to four days out. Mist skill falls from 28% at one day to 25, 21 and 17% at two, three and four days. Among mornings given 40% or more for mist, mist came on 60% at one day ahead and on 51% at four days.
- Within a morning, the hourly formula ranks a misty hour above a clear one 69% of the time. The site's usual daily pattern alone manages 65%.
- An airport is one point, often outside the city. Heathrow has mist on 7% of mornings, Stansted and Luton on 27%.
- The forecast archive holds two and a half winters, and I chose the inputs and time windows while looking at the same data.

## What is in the repo

| | |
|---|---|
| `cities.json` | site, coordinates and usual rates for each city |
| `src/model.js` | the four formulas |
| `src/page.js` | fetches the forecast and draws it |
| `src/city.html`, `src/index.html`, `src/style.css` | page templates and styles |
| `src/how-to-predict-fog.html` | a short article on reading fog from a forecast |
| `build.py` | writes one page per city into `_site/` |
| `test/` | checks the model against a saved forecast |

The analysis that produced the weights is not in this repo.

## Running it

It needs Python 3 to build and Node 20 or later for the tests. There are no packages to install.

```sh
node --test                        # run the tests
python3 build.py                   # write the site to _site/
python3 -m http.server -d _site    # serve it at http://localhost:8000
```

Each push to `main` runs the tests, builds the site and publishes it to GitHub Pages (`.github/workflows/deploy.yml`).

## Data

Weather data by [Open-Meteo.com](https://open-meteo.com/) (CC BY 4.0), from the ICON-EU model of Deutscher Wetterdienst. Visibility reports from the [Iowa Environmental Mesonet](https://mesonet.agron.iastate.edu/) and [DWD open data](https://opendata.dwd.de/).
