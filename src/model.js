// Chance of fog and mist on each coming morning, worked out from an hourly weather forecast.
//
// Four logistic models share the same weather inputs. Two give the chance for a whole morning
// (visibility under 5 km for mist, under 1 km for fog, for at least two hours between 04 and 10 h)
// and two give the chance for a single hour. Each also takes how common mist or fog usually is at
// the place, so a new place needs its usual rates but no fitting of its own.
//
// Places on the plain of the Indus and Ganges (Delhi) are the exception. They name the formula "south-asia":
// fog weights of their own, fitted on airports there, and no mist chance, because smog keeps visibility under
// 5 km on almost every winter morning. Fog there is so tied to the season (Delhi: 3% of October mornings, 73%
// in January) that the usual rate fed in is the one for the calendar month. Their weights and rates count an
// hour under 1 km as fog only if the air was within 2 C of saturation, which leaves dry smog out.
// Fog there comes in runs of days, so the formula has two more sets of weights with one more input: whether the airport
// had a fog morning one morning before, or two mornings before. A morning takes the newest of the two that is known.

export const HOURS = [3, 4, 5, 6, 7, 8, 9, 10, 11];
export const VARIABLES = ['relative_humidity_2m', 'temperature_2m', 'dew_point_2m', 'wind_speed_10m', 'precipitation', 'cloud_cover'];

// Weights in the order of `morningInputs` below, then the usual rate (as log-odds), then the constant.
const MIST_MORNING = [0.20169, -0.12625, -0.67727, -0.0037, -0.25621, -0.03476, 0.75171, -17.33744];
const FOG_MORNING = [0.20864, -0.16897, -0.9078, -0.00993, -0.51486, 0.15244, 0.34868, -19.07335];
// Weights in the order of `hourInputs` below, then the morning inputs, the usual rate for that hour, the constant.
const MIST_HOUR = [0.06398, -0.04304, -0.22212, -0.37503, -0.00105, 0.10844, -0.07628, -0.58067, -0.0043, -0.22331, -0.05695, 0.63314, -14.54606];
const FOG_HOUR = [0.08938, -0.07122, -0.18994, -1.71141, -0.00463, 0.12664, -0.08299, -0.48341, -0.00778, -0.43345, 0.1027, 0.38806, -19.6028];
const FOG = {
  europe: {morning: FOG_MORNING, hour: FOG_HOUR},
  'south-asia': {
    morning: [0.1186, -0.32356, -0.33073, -0.00087, -0.17779, 0.09388, 0.61746, -9.1773],
    hour: [0.03717, 0.05719, -0.07356, -0.47209, -0.00025, 0.06408, -0.30485, -0.34898, -0.00045, -0.21919, 0.07106, 0.67869, -7.41126],
    // With the fog morning one morning before, then two mornings before. Its weight (for 1 or 0) comes before the usual rate's.
    before: [
      {morning: [0.11541, -0.29658, -0.19685, 0.00035, -0.09007, 0.06782, 1.78292, 0.46883, -10.24681],
       hour: [0.00169, 0.04239, -0.29868, -0.52255, -0.00116, 0.05932, -0.24829, -0.1667, 0.00093, -0.10344, 0.01541, 1.63902, 0.54082, -4.86023]},
      {morning: [0.12052, -0.31095, -0.28529, -0.00045, -0.12103, 0.09384, 1.32845, 0.48694, -10.38992],
       hour: [0.04128, 0.03747, -0.07582, -0.51848, -0.0007, 0.05959, -0.26047, -0.26188, -0.00011, -0.1515, 0.05541, 1.10766, 0.56775, -8.38151]}]},
};

const sum = values => values.reduce((a, b) => a + b, 0);
const mean = values => sum(values) / values.length;
const logOdds = p => Math.log(p / (1 - p));
const clamp = (value, low, high) => Math.min(Math.max(value, low), high);
const chance = (weights, inputs, shift = 0) =>
  1 / (1 + Math.exp(-inputs.reduce((z, value, k) => z + weights[k] * value, weights[inputs.length] + shift)));

// The date and hour on the clock at a place, e.g. "2026-10-04T13", whatever the viewer's own time zone.
export function clockAt(tz) {
  const format = new Intl.DateTimeFormat('en-CA', {timeZone: tz, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', hourCycle: 'h23'});
  return time => {
    const part = Object.fromEntries(format.formatToParts(time).map(p => [p.type, p.value]));
    return `${part.year}-${part.month}-${part.day}T${part.hour}`;
  };
}

export const dayBefore = date => new Date(Date.parse(date) - 864e5).toISOString().slice(0, 10);

/**
 * @param hourly  The "hourly" block of an Open-Meteo forecast with `time` in seconds since 1970 (timeformat=unixtime), and
 *                relative_humidity_2m, temperature_2m, dew_point_2m, wind_speed_10m, precipitation
 *                and cloud_cover. It has to start the day before the first morning wanted.
 * @param place   Time zone and usual rates for the place: {tz, mist, fog, mistByHour, fogByHour}, see cities.json.
 *                Without `mist` there is no mist chance. With `fogByMonth` (January to December) the usual fog rate
 *                is the month's, and the hourly rates in `fogByHour` are scaled by how the month compares with `fog`.
 *                `formula` names the fog weights, "europe" if left out.
 *                `mistShift` and `fogShift`, where given, are added to the log-odds of the morning chance and of
 *                each hour's chance. They are half of the constant that would make the average chance at the
 *                place over its past mornings equal to how often mist or fog came.
 *                `fogBefore` says for the last mornings whether they were fog mornings at the airport, e.g.
 *                {"2026-01-09": true, "2026-01-10": false}. It is put in when the site is built (reports.js) and
 *                only counts where the formula has weights for it. A morning with neither of the two mornings
 *                before it in there gets the weights without.
 * @param now     Mornings are left out once it is noon at the place.
 * @returns       One entry per morning: {date, mist, fog, hours: [{hour, mist, fog}]}, chances from 0 to 1;
 *                no `mist` for a place without mist rates.
 */
export function forecastMornings(hourly, place, now = Date.now()) {
  const clock = clockAt(place.tz), hourNow = clock(now);
  const weights = FOG[place.formula ?? 'europe'], hasMist = place.mist !== undefined;
  const mistShift = place.mistShift ?? 0, fogShift = place.fogShift ?? 0;
  const fogBefore = place.fogBefore ?? {};

  // Every hour goes by the clock at the place in that hour. Open-Meteo's own local times count all the hours of an answer
  // from the clock on the day it was asked for, an hour off on the far side of a clock change. Of an hour that comes twice
  // when the clocks go back, the first is kept, as when the weights were fitted.
  const clockHours = hourly.time.map(seconds => clock(1000 * seconds));
  const once = values => values.filter((_, i) => clockHours.indexOf(clockHours[i]) === i);
  const time = once(clockHours), at = clockHour => time.indexOf(clockHour);
  const h = Object.fromEntries(VARIABLES.map(key => [key, once(hourly[key])]));

  return [...new Set(time.map(clockHour => clockHour.slice(0, 10)))].flatMap(date => {
    const eighteen = at(dayBefore(date) + 'T18'), four = at(date + 'T04'), eleven = at(date + 'T11');
    if (eighteen < 0 || four < 0 || eleven < 0) return [];
    if (date + 'T12' <= hourNow) return [];
    // A morning with a gap anywhere from 18 h the day before to 11 h is left out. Open-Meteo sends null for a missing value.
    const missing = value => value == null || Number.isNaN(value);
    if (VARIABLES.some(key => h[key].slice(eighteen, eleven + 1).some(missing))) return [];

    const morning = key => h[key].slice(four, four + 6);            // 04 to 09 h
    const evening = key => h[key].slice(eighteen, eighteen + 3);    // 18 to 20 h the day before
    const morningInputs = [
      Math.max(...morning('relative_humidity_2m')),
      mean(morning('wind_speed_10m')),
      // Rain from 21 to 06 h plus rain from 04 to 09 h. The overlap is counted twice, as it was when the weights were fitted.
      Math.log1p(sum(h.precipitation.slice(eighteen + 3, four + 3)) + sum(morning('precipitation'))),
      mean(evening('cloud_cover')),
      mean(evening('temperature_2m')) - mean(evening('dew_point_2m')),          // how far the evening air is from saturation
      mean(evening('temperature_2m')) - Math.min(...morning('temperature_2m'))];   // overnight cooling

    // The usual fog rate, as log-odds, for the morning and for each hour. The limits are those used when the monthly weights were fitted.
    const monthRate = place.fogByMonth?.[date.slice(5, 7) - 1];
    const fogUsual = monthRate === undefined ? logOdds(place.fog) : logOdds(clamp(monthRate, 0.005, 0.995));
    const fogUsualAt = k => monthRate === undefined ? logOdds(place.fogByHour[k])
      : logOdds(clamp(place.fogByHour[k] * monthRate / place.fog, 0.005, 0.97));

    // The newest known of the two mornings before, where the formula has weights for it.
    const earlier = [dayBefore(date), dayBefore(dayBefore(date))];
    const lag = weights.before ? earlier.findIndex(day => typeof fogBefore[day] === 'boolean') : -1;
    const fogWeights = lag < 0 ? weights : weights.before[lag];
    const before = lag < 0 ? [] : [Number(fogBefore[earlier[lag]])];

    const hours = HOURS.flatMap((hour, k) => {
      const i = at(`${date}T${String(hour).padStart(2, '0')}`);
      if (i < 0) return [];   // an hour the clocks skip
      const hourInputs = [
        h.relative_humidity_2m[i],
        h.wind_speed_10m[i],
        h.temperature_2m[i] - h.dew_point_2m[i],
        Math.log1p(sum(h.precipitation.slice(i - 2, i + 1))),   // rain in the last three hours
        h.cloud_cover[i]];
      const fog = chance(fogWeights.hour, [...hourInputs, ...morningInputs, ...before, fogUsualAt(k)], fogShift);
      return hasMist ? {hour, mist: chance(MIST_HOUR, [...hourInputs, ...morningInputs, logOdds(place.mistByHour[k])], mistShift), fog} : {hour, fog};
    });

    const fog = chance(fogWeights.morning, [...morningInputs, ...before, fogUsual], fogShift);
    const morningChances = hasMist ? {mist: chance(MIST_MORNING, [...morningInputs, logOdds(place.mist)], mistShift), fog} : {fog};
    return [{date, hours, ...morningChances}];
  });
}
