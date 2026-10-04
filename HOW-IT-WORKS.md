# How the fog forecast works

## How the number is made

The page asks [Open-Meteo](https://open-meteo.com/) for the ICON-EU forecast at one site per city (the worldwide ICON forecast for the cities outside Europe, which ICON-EU does not reach) and takes six things from it:

- highest humidity between 4 and 10 h
- mean wind in those hours
- rain overnight and in the morning
- cloud cover the evening before
- how far the evening air is from saturation (temperature minus dew point)
- how much it cools overnight

A logistic regression turns those, plus how often the site usually has fog, into a chance. There are four sets of weights: fog and mist, each for a whole morning and for a single hour. Fog means visibility under 1 km and mist under 5 km, in air close to saturation: the temperature reported by the airport is within 2 °C of the dew point. Smoke, haze and dry smog are left out that way. A morning counts when that lasts at least two hours between 4 and 10 h.

The weights were fitted once on 14 European airports together. A new place needs its usual fog and mist rates from its own visibility record and no fitting.

Delhi, Lahore and Amritsar are the exception. The European weights rank Delhi's mornings correctly but say a third of the fog that happens, so these three have fog weights of their own, fitted on 13 airports on the plain of the Indus and Ganges. Fog there is tied to the season far more than in Europe (Delhi: 3% of October mornings, 73% in January), so the usual rate that goes in is the one for the calendar month, from the last five years of airport reports. There is no mist number for these three: smog keeps visibility under 5 km on almost every winter morning, humid or not.

The humidity condition matters in few places. Of Delhi's 136 mornings with visibility under 1 km in the test, 21 are not counted as fog (13 of them in November), nor are 21 of Lahore's 101 (14 of them in October and November) and 2 of Amritsar's 192. Reports of smoke or haze there are mostly 4 °C or more from saturation. At Fresno and Bakersfield 7 mist mornings each were dry haze. At the other 28 airports checked, the condition changes no fog morning and at most one mist morning, so the weights fitted on visibility alone were kept. Winter fog on the plain of the Indus and Ganges forms in polluted air, so a fog morning there is not a morning of clean air. Only the mornings without the humidity that fog needs are left out.

## How well it works

Fitted and tested on October to March mornings since January 2024: 6,115 mornings at 14 airports, 1,083 with mist and 460 with fog. Observations are airport METAR reports from the Iowa State archive. Berlin's page takes its usual rates from DWD station data for Tempelhof; in the fit, Berlin is the airport. The forecasts are day-ahead ICON-EU runs from Open-Meteo's previous-runs archive.

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

These figures are for the 14 airports the weights were fitted on, with the tested month left out. Five of them are not on the site: Frankfurt, London Heathrow, Madrid and Warsaw, and Stockholm Arlanda, since Stockholm is now shown at Bromma.

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
| Sacramento (Executive) | 40% | 35% |
| Venice | 43% | 34% |
| Krakow | 43% | 33% |
| Seattle (Boeing Field) | 23% | 29% |
| Fresno | 38% | 26% |
| Bakersfield | 39% | 22% |
| Stockholm (Bromma) | 25% | 22% |
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
- Stockholm, Sacramento and Seattle are shown at an airport nearer the centre than the one first tested: Bromma (11 km from the centre) in place of Arlanda (34 km), Sacramento Executive (8 km) in place of Sacramento International (15 km), and Boeing Field (9 km) in place of Seattle-Tacoma (18 km). Fog skill is the same within a point or two at both airports of each pair, and fog is rarer nearer the city: 21 fog mornings at Bromma against 35 at Arlanda, 19 at Boeing Field against 34 at Seattle-Tacoma, 51 at Sacramento Executive against 63 at Sacramento International.
- Seattle's fog skill rests on 19 fog mornings, so its range is wide (7 to 45%).
- At Galveston and Houston the fog number is less than half of what happens (Galveston: said 4% on average, fog came on 10% of mornings). It still ranks the mornings.
- Bologna passes narrowly (range 1 to 24%).

Tested and left out:

- Fog skill not clearly above zero, or under 10%: Los Angeles, New York, Denver, Portland, Chicago, Washington, San Diego, Vancouver, Turin and London Luton.
- Nearer the centre than the airport shown, and not good enough: Houston Hobby (fog skill 7%) and the weather station inside Munich (6%, range from −21%). Fog in the city of Munich is a third as common as at its airport, 24 mornings against 72, and the formula gave 9% on average where fog came on 5.5% of mornings. Fog skill at Paris Orly is the same as at Charles de Gaulle and Orly is only 6 km nearer, so Paris was left as it is.
- Fewer than 15 fog mornings: San Francisco, Boston, Minneapolis, Toronto, Melbourne and Dubai.
- Islamabad: the formula never says more than about 9% there, and 15 of its 22 fog mornings fell in one month.

Delhi was tested with Delhi left out of the fit, the tested month left out too, and its monthly rates taken from the years before the test (115 fog mornings in 437). Fog skill was 44% (90% range 24 to 59) over its flat winter rate and 18% (−3 to 34) over its usual rate for the month, which is the fairer comparison there and is not clearly above zero. By hour it was 39% (26 to 50) and 18% (5 to 30). It reads high: it said 34% on average and fog came on 26% of mornings, because the last two winters had less fog than the five before. Mornings given about 60% had fog 50% of the time, and those given about 84% had it 74% of the time. In November it said 36% and fog came on 19%.

Lahore and Amritsar were tested the same way, each left out of the fit:

| | Fog mornings | Over the flat winter rate | Over the rate for the month | Said on average | Fog came on |
|---|---|---|---|---|---|
| Delhi | 115 | 44% (24 to 59) | 18% (−3 to 34) | 34% | 26% |
| Lahore | 80 | 43% (33 to 54) | 31% (23 to 37) | 22% | 18% |
| Amritsar | 190 | 36% (26 to 46) | 17% (10 to 26) | 35% | 46% |

Lahore reads a little high: mornings given about 80% had fog 72% of the time, and in February it said 19% and fog came on 8%. Amritsar reads low: mornings given about 60% had fog 72% of the time.

The formula knows fog that forms on calm, clear nights. It does not know fog that drifts in from the sea, which is most of what Los Angeles and the San Francisco coast get.

Fog has a season, and outside it the numbers mean less. At the 21 northern cities fog came on 1% of April to August mornings (82 of 9,491), against 10% from October to March, and the page says so in those months. Auckland is the other way round, with 3 fog mornings in 438 from October to March. Christchurch has fog all year (15% of mornings from April to September, 8% from October to March) and the forecast works in both halves, so its page carries no such note. In the US the formula had no skill from April to September. In Europe it had almost none from April to July; August and September were about as good as winter, August on few fog mornings.
