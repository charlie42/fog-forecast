# How the fog forecast works

## How the number is made

The page asks [Open-Meteo](https://open-meteo.com/) for the ICON-EU forecast for the centre of each city (the worldwide ICON forecast for the cities outside Europe, which ICON-EU does not reach) and takes six things from it:

- highest humidity between 4 and 10 h
- mean wind in those hours
- rain overnight and in the morning
- cloud cover the evening before
- how far the evening air is from saturation (temperature minus dew point)
- how much it cools overnight

A logistic regression turns those, plus how often the site usually has fog, into a chance. There are four sets of weights: fog and mist, each for a whole morning and for a single hour. Fog means visibility under 1 km and mist under 5 km, in air close to saturation: the temperature reported by the airport is within 2 °C of the dew point. Smoke, haze and dry smog are left out that way. A report with rain, snow, drizzle or other precipitation is not counted as mist or fog. A morning counts when mist or fog is reported in at least two of the six hours from 4 to 10 h.

The weights were fitted once on 14 European airports together. A new place needs its usual fog and mist rates from its own visibility record, and one correction for each.

The weather values are taken for the centre of each city. The usual rates, the corrections and the tests are from the station named on the page, where the visibility is reported, and the tests were run with the weather values for the station. At seven cities with a second station nearer the centre, fog skill at that station was 19% with the weather values for its own grid square and 9% with the airport's.

At some places the average is off: at Houston the weights give 3% for fog where fog comes on 8% of mornings, and at Zurich 19% where it comes on 13%. Each city except Delhi, Lahore and Amritsar therefore has a correction for fog and one for mist, added to the morning chance and to each hour. It is half of what would make the average equal to how often fog came. Half, because the full correction did no better in the test and overstated the high chances more.

Delhi, Lahore and Amritsar are the exception. The European weights rank Delhi's mornings correctly but say a third of the fog that happens, so these three have fog weights of their own, fitted on 13 airports on the plain of the Indus and Ganges. Fog there is tied to the season far more than in Europe (Delhi: 3% of October mornings, 73% in January), so the usual rate that goes in is the one for the calendar month, from the last five years of airport reports. There is no mist number for these three: smog keeps visibility under 5 km on almost every winter morning, humid or not.

Fog there also comes in runs of days. So for these three, one more input goes in: whether an earlier morning was a fog morning at the airport. It is counted from the airport's reports each time the site is built, by the same rule as in the fit. Each row of the page takes the newest known of the four mornings before it, and each of the four has weights of its own. Without reports, the weights without this input are used.

The humidity condition matters in few places. Of Delhi's 136 mornings with visibility under 1 km in the test, 21 are not counted as fog (13 of them in November), nor are 21 of Lahore's 101 (14 of them in October and November) and 2 of Amritsar's 192. Reports of smoke or haze there are mostly 4 °C or more from saturation. At Fresno and Bakersfield 7 mist mornings each were dry haze. At the other 28 airports checked, the condition changes no fog morning and at most one mist morning, so the weights fitted on visibility alone were kept. Winter fog on the plain of the Indus and Ganges forms in polluted air, so a fog morning there is not a morning of clean air. Only the mornings without the humidity that fog needs are left out. The codes that observers write in the reports (fog, mist, haze, smoke) were tried in place of the humidity condition and not used, because they are used differently from country to country. At Lahore, 694 of the 5,006 reports since 2019 under 1 km and within 2 °C of saturation are coded as mist, not fog. At Delhi, 916 of the 7,352 coded as fog are 3 °C or more from saturation.

## How well it works

Fitted and tested on October to March mornings since January 2024: 6,115 mornings at 14 airports, 1,083 with mist and 460 with fog. Observations are airport METAR reports from the Iowa State archive. Berlin's page takes its usual rates from DWD station data for Tempelhof; in the fit, Berlin is the airport. The forecasts are day-ahead ICON-EU runs from Open-Meteo's previous-runs archive.

Skill below is the Brier skill score against always saying the site's usual rate. 0% is no better than that, 100% is perfect.

| Left out of fitting | Mist | Fog |
|---|---|---|
| Single months | 29% | 24% |
| Whole winters | 29% | 23% |
| Whole winters, and the city | 27% | 22% |

Against a harder baseline (usual rate, time of year, and whether yesterday was foggy) the skill is 22% for mist and 21% for fog.

Calibration with months left out: mornings given about 2, 9, 22, 39, 60 and 77% for mist had mist 2, 9, 23, 40, 57 and 78% of the time.

The same for fog, with the number of mornings behind each step:

| Chance given for fog | Mornings | Fog came on |
|---|---|---|
| about 1% | 4,281 | 1% |
| about 9% | 874 | 10% |
| about 21% | 431 | 21% |
| about 40% | 355 | 40% |
| about 58% | 158 | 54% |
| about 74% | 16 | 62% |

Fog came on 7.5% of all mornings. The mornings given 30% or more (529, or 9% of all) had fog 45% of the time and held 52% of all fog mornings. Those given 50% or more (174) had fog 55% of the time, a little under the 59% they were given on average; the 90% range is 48 to 62%. Those given under 5% (4,281, or 70% of all) had fog 1.1% of the time. For mist the same three figures are 53% (722 of 1,358 mornings given 30% or more), 65% (462 of 715 given 50% or more) and 1.7% (43 of 2,580 given under 5%).

These figures are for the 14 airports the weights were fitted on, with the tested month left out. Five of them are not on the site: Frankfurt, London Heathrow, Madrid and Warsaw, and Stockholm Arlanda, since Stockholm is now shown at Bromma. These figures are before the correction per city.

Limitations:

- Ranking mornings, it ties with the fog code in ICON's own output. At the same 1,137 alarms the fog code caught 622 mist mornings and the formula 628. What the formula adds is a percentage.
- Fog skill differs by city: Prague 35%, Vienna 34%, Milan 31%, down to London Heathrow 8%, Madrid 7% and Frankfurt −1%. See "Which cities are shown".
- The page uses the day-ahead weights for mornings up to four days out. Mist skill falls from 29% at one day to 26, 22 and 18% at two, three and four days. Among mornings given 40% or more for mist, mist came on 60% at one day ahead and on 51% at four days. Fog skill falls from 24% to 21, 17 and 13%. Among mornings given 30% or more for fog, fog came on 45% at one day ahead and on 35% at four days.
- Within a morning, the hourly formula ranks a misty hour above a clear one 70% of the time. The site's usual daily pattern alone manages 65%.
- An airport is one point, often outside the city. Heathrow has mist on 7% of mornings, Stansted and Luton on 27%.
- The forecast archive holds two and a half winters, and the inputs and time windows were chosen while looking at the same data.

## Correction per city

Tested on the 22 cities as shown on the site (9,794 mornings, 945 with fog), each winter with weights, usual rate and correction from the other winters. Fog skill went from 24.6% to 25.8% (90% range of the gain +0.4 to +1.9) and mist skill from 32.1% to 33.3% (+0.4 to +1.8). Most of the fog gain is at Houston, Galveston and Zurich. Mornings given 50% or more for fog had fog 55% of the time, against 54% before. Berlin's correction rests on 24 fog mornings, most of them in two winters that were foggier than the two before.

With the correction, and the number of mornings behind each step:

| Chance given for fog | Mornings | Fog came on |
|---|---|---|
| about 1% | 6,453 | 1% |
| about 9% | 1,383 | 10% |
| about 22% | 821 | 24% |
| about 39% | 712 | 41% |
| about 58% | 353 | 52% |
| about 76% | 72 | 65% |

## Which cities are shown

A city gets a page only if its fog forecast is clearly better than its usual rate: fog skill of at least 10%, a 90% range (months resampled) that stays above zero, and at least 15 fog mornings in the test to judge by. Of the 14 European airports used for fitting, that leaves out Frankfurt (-1%), Madrid (7%), London Heathrow (8%) and Warsaw (10%, range from -3%).

Cities added later use the same weights, unchanged, with their own usual rates and correction. The skill below is before the correction. Outside Europe the inputs come from the worldwide ICON model. Skill over each airport's own usual rate, October to March (April to September for the two New Zealand cities):

| | Mist | Fog |
|---|---|---|
| Sacramento (Executive) | 42% | 36% |
| Venice | 43% | 34% |
| Krakow | 43% | 34% |
| Seattle (Boeing Field) | 22% | 29% |
| Fresno | 39% | 28% |
| Stockholm (Bromma) | 24% | 23% |
| Christchurch | 29% | 21% |
| Galveston | 27% | 21% |
| Bakersfield | 40% | 20% |
| London (Gatwick) | 23% | 17% |
| Houston | 23% | 14% |
| Bologna | 29% | 13% |
| Auckland | 28% | 12% |

Across the 14 US airports first tested (6,131 mornings, 349 with fog) skill was 24% for mist and 18% for fog.

Things to know about some of these:

- London is shown at Gatwick, 40 km south of the centre, where the numbers matched what happened. Stansted has the same skill but the formula says half of what happens there.
- Stockholm, Sacramento and Seattle are shown at an airport nearer the centre than the one first tested: Bromma (11 km from the centre) in place of Arlanda (34 km), Sacramento Executive (8 km) in place of Sacramento International (15 km), and Boeing Field (9 km) in place of Seattle-Tacoma (18 km). Fog skill is the same within a point or two at both airports of each pair, and fog is rarer nearer the city: 21 fog mornings at Bromma against 35 at Arlanda, 19 at Boeing Field against 34 at Seattle-Tacoma, 51 at Sacramento Executive against 63 at Sacramento International.
- Seattle's fog skill rests on 19 fog mornings, so its range is wide (7 to 46%).
- At Galveston and Houston the fog number is still low after the correction (Houston: 5% on average, fog came on 8% of mornings). It still ranks the mornings.
- Bologna and Bakersfield pass narrowly (ranges 1 to 25% and 1 to 33%).

Tested and left out:

- Fog skill not clearly above zero, or under 10%: Atlanta (8%, range from −1%), Los Angeles, New York, Denver, Portland, Chicago, Washington, San Diego, Vancouver, Turin and London Luton.
- Nearer the centre than the airport shown, and not good enough: Houston Hobby (fog skill 9.7%) and the weather station inside Munich (8%, range from −19%). Fog in the city of Munich is a third as common as at its airport, 24 mornings against 72, and the formula gave 9% on average where fog came on 5.5% of mornings. Fog skill at Paris Orly is the same as at Charles de Gaulle and Orly is only 6 km nearer, so Paris was left as it is.
- Fewer than 15 fog mornings: San Francisco, Boston, Minneapolis, Toronto, Melbourne and Dubai.
- Islamabad: the formula never says more than about 9% there, and 15 of its 22 fog mornings fell in one month.

Delhi was tested with Delhi left out of the fit, the tested month left out too, and its monthly rates taken from the years before the test (115 fog mornings in 437). Fog skill was 43% (90% range 23 to 59) over its flat winter rate and 18% (−4 to 34) over its usual rate for the month, which is the fairer comparison there and is not clearly above zero. By hour it was 39% (27 to 51) and 18% (5 to 29). It reads high: it said 34% on average and fog came on 26% of mornings, because the last two winters had less fog than the five before. Mornings given about 60% had fog 52% of the time, and those given about 84% had it 73% of the time. In November it said 37% and fog came on 19%.

Lahore and Amritsar were tested the same way, each left out of the fit:

| | Fog mornings | Over the flat winter rate | Over the rate for the month | Said on average | Fog came on |
|---|---|---|---|---|---|
| Delhi | 115 | 43% (23 to 59) | 18% (−4 to 34) | 34% | 26% |
| Lahore | 80 | 43% (32 to 54) | 31% (23 to 37) | 22% | 18% |
| Amritsar | 190 | 40% (31 to 49) | 22% (15 to 30) | 38% | 46% |

Fog on the plain comes in runs of days: after a fog morning, the next morning had fog 76% of the time at Delhi, 71% at Lahore and 78% at Amritsar. The figures above are for the weights without an earlier morning. The same test with it as an input, fog skill over the rate for the month:

| | Without | 1 before | 2 before | 3 before | 4 before |
|---|---|---|---|---|---|
| Delhi | 18% (−4 to 34) | 37% (21 to 47) | 31% (13 to 44) | 26% (6 to 41) | 22% (1 to 37) |
| Lahore | 31% (23 to 37) | 42% (31 to 49) | 37% (27 to 44) | 34% (23 to 43) | 31% (22 to 38) |
| Amritsar | 22% (15 to 30) | 34% (26 to 40) | 31% (23 to 38) | 27% (21 to 34) | 25% (16 to 33) |

Every column was measured with the weather forecast of the day before. The later rows of a page go with an older forecast, so they will be lower there.

Against a baseline of the rate for the month and whether the morning before had fog, the skill without the input is −17% (−55 to 10) at Delhi, 0% (−13 to 14) at Lahore and −1% (−14 to 13) at Amritsar. With one morning before it is 10% (−8 to 24), 17% (12 to 21) and 14% (8 to 20). In Europe the skill over the same kind of baseline is 21%.

The mornings where a run starts or ends are told apart as well as without the input, but the chance on them is further off: the first fog morning after a clear one was given 35% on average, against 50% without, and the first clear morning after fog 58% against 41%. These are 178 of the 1,261 mornings.

With one morning before, mornings given about 60% had fog 43% of the time at Delhi, 58% at Lahore and 80% at Amritsar. Those given about 85% had it 88%, 80% and 87% of the time.

Lahore reads a little high: mornings given about 80% had fog 74% of the time, and in February it said 19% and fog came on 8%. Amritsar reads low: mornings given about 60% had fog 74% of the time.

The formula knows fog that forms on calm, clear nights. It does not know fog that drifts in from the sea, which is most of what Los Angeles and the San Francisco coast get.

Fog has a season, and outside it the numbers mean less. At the 20 northern cities fog came on 1% of April to August mornings (74 of 9,038), against 10% from October to March, and the page says so in those months. Auckland is the other way round, with 3 fog mornings in 438 from October to March. Christchurch has fog all year (15% of mornings from April to September, 8% from October to March) and the forecast works in both halves, so its page carries no such note. In the US the formula had no skill from April to September. In Europe it had almost none from April to July; August and September were about as good as winter, August on few fog mornings.
