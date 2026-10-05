# Fitting the weights

Python scripts that fit the logistic-regression weights in `../src/model.js`.

| Script | Produces |
|---|---|
| `fit_morning.py` | `MIST_MORNING` and `FOG_MORNING`, with the month-held-out test |
| `fit_hourly.py` | `MIST_HOUR` and `FOG_HOUR`, with the month-held-out test |
| `fit_south_asia.py` | the `south-asia` morning and hour weights, without and with the fog morning one to four mornings before, with the test for Delhi, Lahore and Amritsar |
| `keep_test.py` | the test for a new city, and its entry for the city list |
| `city_correction.py` | `mistShift` and `fogShift` for the city list: half of the constant that makes the average chance at a city equal to how often mist or fog came |
| `common.py` | downloads, the six morning inputs, conversion of weights to raw units |

Weights are printed in the order used in `model.js`: one per input, then the usual rate (log-odds), then the constant.

## Run

```
pip install -r requirements.txt
python fit_morning.py
python fit_hourly.py
python fit_south_asia.py
python keep_test.py europe          # or: north, south, us, nearer-europe, nearer-us, city-stations
python city_correction.py
```

## Data

- Airport reports: Iowa State Mesonet archive (METAR, visibility and weather codes).
- Hourly visibility and rain at two stations in Munich: open data of the German weather service (DWD), for `keep_test.py city-stations`.
- Forecasts: day-ahead runs from the Open-Meteo archive of past forecasts (ICON-EU for Europe, ICON global elsewhere).

Downloads are kept in `cache/` and are only fetched when missing. A first run downloads about 200 MB (the five
years of reports for `fit_south_asia.py` are most of it) and takes roughly 15 to 30 minutes, mostly waiting between
requests. With the cache filled the scripts take about 5 seconds (`fit_morning.py`), 40 seconds (`fit_hourly.py`)
and about 10 minutes (`fit_south_asia.py`).

Date ranges are fixed in the scripts: European reports and forecasts from 20 January 2024 to 2 October 2026,
South Asian reports from July 2019 to 3 October 2026 (forecasts from 20 January 2024). The same weights come out
on every run, as long as the downloaded data is unchanged.
