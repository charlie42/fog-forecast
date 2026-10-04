# How the fog forecast works

## How the number is made

The page asks [Open-Meteo](https://open-meteo.com/) for the ICON-EU forecast at one site per city (the worldwide ICON forecast for the cities outside Europe, which ICON-EU does not reach) and takes six things from it:

- highest humidity between 4 and 10 h
- mean wind in those hours
- rain overnight and in the morning
- cloud cover the evening before
- how far the evening air is from saturation (temperature minus dew point)
- how much it cools overnight

A logistic regression turns those, plus how often the site usually has fog, into a chance. There are four sets of weights: fog and mist, each for a whole morning and for a single hour. Fog means visibility under 1 km and mist under 5 km. A morning counts when that lasts at least two hours between 4 and 10 h.

The weights were fitted once on 14 European airports together. A new place needs its usual fog and mist rates from its own visibility record and no fitting.

Delhi is the exception. The European weights rank its mornings correctly but say a third of the fog that happens, so it has fog weights of its own, fitted on 13 airports on the plain of the Indus and Ganges. Fog there is tied to the season far more than in Europe (4% of October mornings, 75% in January), so the usual rate that goes in is the one for the calendar month, from the last five years of airport reports. There is no mist number for Delhi: smog keeps visibility under 5 km on almost every winter morning.

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

The same for fog, with the number of mornings behind each step:

| Chance given for fog | Mornings | Fog came on |
|---|---|---|
| about 1% | 4,276 | 1% |
| about 9% | 879 | 10% |
| about 22% | 432 | 20% |
| about 39% | 356 | 40% |
| about 58% | 157 | 55% |
| about 74% | 15 | 67% |

Fog came on 7.5% of all mornings. The mornings given 30% or more (528, or 9% of all) had fog 46% of the time and held 52% of all fog mornings. Those given 50% or more (172) had fog 56% of the time, a little under the 59% they were given on average; the 90% range is 50 to 63%. Those given under 5% (4,276, or 70% of all) had fog 1.1% of the time. For mist the same three figures are 52% (713 of 1,359 mornings given 30% or more), 64% (446 of 697 given 50% or more) and 1.7% (43 of 2,535 given under 5%).

These figures are for the 14 airports the weights were fitted on, with the tested month left out. Four of them (Frankfurt, London Heathrow, Madrid and Warsaw) are not on the site.

Where it is weak:

- Ranking mornings, it ties with the fog code in ICON's own output. At the same 1,133 alarms the fog code caught 623 mist mornings and the formula 621. What the formula adds is a percentage.
- Fog skill differs by city: Prague 35%, Vienna 34%, Milan 31%, down to London Heathrow 8%, Madrid 3% and Frankfurt 0%. See "Which cities are shown".
- The page uses the day-ahead weights for mornings up to four days out. Mist skill falls from 28% at one day to 25, 21 and 17% at two, three and four days. Among mornings given 40% or more for mist, mist came on 60% at one day ahead and on 51% at four days.
- Within a morning, the hourly formula ranks a misty hour above a clear one 69% of the time. The site's usual daily pattern alone manages 65%.
- An airport is one point, often outside the city. Heathrow has mist on 7% of mornings, Stansted and Luton on 27%.
- The forecast archive holds two and a half winters, and the inputs and time windows were chosen while looking at the same data.

## Which cities are shown

A city gets a page only if its fog forecast is clearly better than its usual rate: fog skill of at least 10%, a 90% range (months resampled) that stays above zero, and at least 15 fog mornings in the test to judge by. Of the 14 European airports used for fitting, that leaves out Frankfurt (0%), Madrid (3%), London Heathrow (8%) and Warsaw (10%, range from -3%).

Cities added later use the same weights, unchanged, and give only their usual rates. Outside Europe the inputs come from the worldwide ICON model. Skill over each airport's own usual rate, October to March (April to September for the two New Zealand cities):

| | Mist | Fog |
|---|---|---|
| Sacramento | 43% | 36% |
| Venice | 43% | 34% |
| Krakow | 43% | 33% |
| Seattle | 18% | 30% |
| Fresno | 39% | 26% |
| Bakersfield | 40% | 22% |
| Christchurch | 29% | 21% |
| Galveston | 25% | 18% |
| London (Gatwick) | 22% | 17% |
| Auckland | 27% | 14% |
| Bologna | 30% | 13% |
| Houston | 20% | 10% |
| Atlanta | 17% | 10% |

Across the 14 US airports first tested (6,131 mornings, 349 with fog) skill was 24% for mist and 18% for fog.

Things to know about some of these:

- London is shown at Gatwick, 40 km south of the centre, where the numbers matched what happened. Stansted has the same skill but the formula says half of what happens there.
- At Galveston and Houston the fog number is less than half of what happens (Galveston: said 4% on average, fog came on 10% of mornings). It still ranks the mornings.
- Bologna passes narrowly (range 1 to 24%).

Tested and left out:

- Fog skill not clearly above zero, or under 10%: Los Angeles, New York, Denver, Portland, Chicago, Washington, San Diego, Vancouver, Turin, Lahore, Amritsar and London Luton.
- Fewer than 15 fog mornings: San Francisco, Boston, Minneapolis, Toronto, Melbourne and Dubai.
- Islamabad: the formula never says more than about 9% there, and 15 of its 22 fog mornings fell in one month.

Delhi was tested with Delhi left out of the fit, the tested month left out too, and its monthly rates taken from the years before the test (136 fog mornings in 437). Fog skill was 40% (90% range 25 to 53) over its flat winter rate and 20% (7 to 31) over its usual rate for the month, which is the fairer comparison there. By hour it was 36% and 16%. It reads high: it said 39% on average and fog came on 31% of mornings, because the last two winters had less fog than the five before. Mornings given about 60% had fog 44% of the time, and those given about 84% had it 76% of the time. In October it said 12% and fog came on 3%. Lahore and Amritsar would work with the same weights (26% and 19% over their monthly rates) and are not on the site.

The formula knows fog that forms on calm, clear nights. It does not know fog that drifts in from the sea, which is most of what Los Angeles and the San Francisco coast get.

Fog has a season, and outside it the numbers mean less. At the 21 northern cities fog came on 1% of April to August mornings (101 of 9,509), against 10% from October to March, and the page says so in those months. Auckland is the other way round, with 3 fog mornings in 438 from October to March. Christchurch has fog all year (15% of mornings from April to September, 8% from October to March) and the forecast works in both halves, so its page carries no such note. In the US the formula had no skill from April to September. In Europe it had almost none from April to July; August and September were about as good as winter, August on few fog mornings.
