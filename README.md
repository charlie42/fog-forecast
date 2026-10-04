# Fog forecast

Chance of fog and mist on each of the next mornings, hour by hour, for 23 cities in Europe, the United States and New Zealand.

Live at https://charlie42.github.io/fog-forecast/

I photograph fog in Berlin and wanted to know the day before how likely it is.

## How the number is made

The page asks [Open-Meteo](https://open-meteo.com/) for the ICON-EU forecast at one site per city (the worldwide ICON forecast for the US cities, which ICON-EU does not reach) and takes six things from it:

- highest humidity between 4 and 10 h
- mean wind in those hours
- rain overnight and in the morning
- cloud cover the evening before
- how far the evening air is from saturation (temperature minus dew point)
- how much it cools overnight

A logistic regression turns those, plus how often the site usually has fog, into a chance. There are four sets of weights: fog and mist, each for a whole morning and for a single hour. Fog means visibility under 1 km and mist under 5 km. A morning counts when that lasts at least two hours between 4 and 10 h.

The weights were fitted once on 14 European airports together. A new place needs its usual fog and mist rates from its own visibility record and no fitting.

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
- Fog skill differs by city: Prague 35%, Vienna 34%, Milan 31%, down to London 8%, Madrid 3% and Frankfurt 0%. See "Which cities are shown".
- The page uses the day-ahead weights for mornings up to four days out. Mist skill falls from 28% at one day to 25, 21 and 17% at two, three and four days. Among mornings given 40% or more for mist, mist came on 60% at one day ahead and on 51% at four days.
- Within a morning, the hourly formula ranks a misty hour above a clear one 69% of the time. The site's usual daily pattern alone manages 65%.
- An airport is one point, often outside the city. Heathrow has mist on 7% of mornings, Stansted and Luton on 27%.
- The forecast archive holds two and a half winters, and I chose the inputs and time windows while looking at the same data.

## Which cities are shown

A city gets a page only if its fog forecast is clearly better than its usual rate: fog skill of at least 10%, a 90% range (months resampled) that stays above zero, and at least 15 fog mornings in the test to judge by. Of the 14 European airports used for fitting, that leaves out Frankfurt (0%), Madrid (3%), London (8%) and Warsaw (10%, range from -3%).

The US cities use the same weights, unchanged, with inputs from the worldwide ICON model. Tested on 14 US airports (6,131 October to March mornings, 349 with fog), skill over each airport's usual rate was 24% for mist and 18% for fog. Five pass the rule above:

| | Mist | Fog |
|---|---|---|
| Sacramento | 43% | 36% |
| Seattle | 18% | 30% |
| Fresno | 39% | 26% |
| Houston | 20% | 10% |
| Atlanta | 17% | 10% |

Left out: Los Angeles, New York, Denver, Portland, Chicago and Washington (fog skill not clearly above zero), and San Francisco, Boston and Minneapolis (fewer than 15 fog mornings). The formula knows fog that forms on calm, clear nights. It does not know fog that drifts in from the sea, which is most of what Los Angeles gets.

Outside October to March fog is rare and the numbers mean less. At the 15 cities shown, fog came on 1% of April to August mornings (73 of 6,822), against 9% from October to March, and the page says so in those months. In the US the formula had no skill from April to September. In Europe it had almost none from April to July; August and September were about as good as winter, August on few fog mornings.

## What is in the repo

| | |
|---|---|
| `cities.json` | site, coordinates and usual rates for each city, and its German name where it has a German page |
| `src/model.js` | the four formulas |
| `src/page.js` | fetches the forecast and draws it, in English or German |
| `prerender.js` | fetches every city's forecast at build time, so the pages already contain the numbers |
| `src/city.html`, `src/index.html`, `src/style.css` | page templates and styles |
| `src/city.de.html`, `src/index.de.html` | the same templates in German |
| `src/how-to-predict-fog.html` | a short article on reading fog from a forecast |
| `build.py` | writes one page per city and language into `_site/` |
| `test/` | checks the model against a saved forecast |

The analysis that produced the weights is not in this repo.

Berlin, Hamburg, Munich, Vienna and Zurich also have a German page under `de/`. A page in another language needs its words in `src/page.js`, two templates named after it, an entry in `LANGUAGES` in `build.py`, and the translated names in `cities.json`.

## Running it

It needs Python 3 and Node 20 or later. There are no packages to install.

```sh
node --test                        # run the tests
node prerender.js                  # fetch the forecasts into forecasts.json (optional)
python3 build.py                   # write the site to _site/
python3 -m http.server -d _site    # serve it at http://localhost:8000
```

Each push to `main` runs the tests, builds the site and publishes it to GitHub Pages (`.github/workflows/deploy.yml`). The same workflow runs every three hours to refresh the numbers written into the pages. GitHub switches a schedule off after 60 days without a commit, so each run enables its own workflow again. A browser fetches the latest forecast again when a page is opened. Search engines cannot, because Open-Meteo's robots.txt keeps crawlers out, so they read what the build wrote.

## Data

Weather data by [Open-Meteo.com](https://open-meteo.com/) (CC BY 4.0), from the ICON-EU and ICON global models of Deutscher Wetterdienst. Visibility reports from the [Iowa Environmental Mesonet](https://mesonet.agron.iastate.edu/) and [DWD open data](https://opendata.dwd.de/).
