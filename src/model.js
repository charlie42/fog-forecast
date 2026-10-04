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

export const HOURS = [3, 4, 5, 6, 7, 8, 9, 10, 11];

// Weights in the order of `morningInputs` below, then the usual rate (as log-odds), then the constant.
const MIST_MORNING = [0.20342, -0.13347, -0.62789, -0.00341, -0.20227, -0.01995, 0.74347, -17.60958];
const FOG_MORNING = [0.21223, -0.18159, -0.83361, -0.00905, -0.43466, 0.1618, 0.33433, -19.60083];
// Weights in the order of `hourInputs` below, then the morning inputs, the usual rate for that hour, the constant.
const MIST_HOUR = [0.07478, -0.05783, -0.2973, -0.25481, -0.00156, 0.08788, -0.06716, -0.5596, -0.00385, -0.16795, -0.04451, 0.66459, -13.5673];
const FOG_HOUR = [0.27946, -0.10117, 0.97268, -1.73308, -0.00587, 0.11295, -0.06034, -0.39226, -0.00701, -0.36114, 0.10603, 0.44476, -37.09207];
const FOG = {
  europe: {morning: FOG_MORNING, hour: FOG_HOUR},
  'south-asia': {
    morning: [0.1186, -0.32356, -0.33073, -0.00087, -0.17779, 0.09388, 0.61746, -9.1773],
    hour: [0.03717, 0.05719, -0.07356, -0.47209, -0.00025, 0.06408, -0.30485, -0.34898, -0.00045, -0.21919, 0.07106, 0.67869, -7.41126]},
};

const sum = values => values.reduce((a, b) => a + b, 0);
const mean = values => sum(values) / values.length;
const logOdds = p => Math.log(p / (1 - p));
const clamp = (value, low, high) => Math.min(Math.max(value, low), high);
const chance = (weights, inputs, shift = 0) =>
  1 / (1 + Math.exp(-inputs.reduce((z, value, k) => z + weights[k] * value, weights[inputs.length] + shift)));

// The date and hour on the clock at the place, e.g. "2026-10-04T13", whatever the viewer's own time zone.
function localHour(now, tz) {
  const parts = new Intl.DateTimeFormat('en-CA', {timeZone: tz, year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', hourCycle: 'h23'}).formatToParts(now);
  const part = type => parts.find(p => p.type === type).value;
  return `${part('year')}-${part('month')}-${part('day')}T${part('hour')}`;
}

/**
 * @param hourly  The "hourly" block of an Open-Meteo forecast in the place's local time, with
 *                relative_humidity_2m, temperature_2m, dew_point_2m, wind_speed_10m, precipitation
 *                and cloud_cover. It has to start the day before the first morning wanted.
 * @param place   Time zone and usual rates for the place: {tz, mist, fog, mistByHour, fogByHour}, see cities.json.
 *                Without `mist` there is no mist chance. With `fogByMonth` (January to December) the usual fog rate
 *                is the month's, and the hourly rates in `fogByHour` are scaled by how the month compares with `fog`.
 *                `formula` names the fog weights, "europe" if left out.
 *                `mistShift` and `fogShift`, where given, are added to the log-odds of the morning chance and of
 *                each hour's chance. They are half of the constant that would make the average chance at the
 *                place over its past mornings equal to how often mist or fog came.
 * @param now     Mornings are left out once it is noon at the place.
 * @returns       One entry per morning: {date, mist, fog, hours: [{hour, mist, fog}]}, chances from 0 to 1;
 *                no `mist` for a place without mist rates.
 */
export function forecastMornings(hourly, place, now = Date.now()) {
  const h = hourly, hourNow = localHour(now, place.tz);
  const weights = FOG[place.formula ?? 'europe'], hasMist = place.mist !== undefined;
  const mistShift = place.mistShift ?? 0, fogShift = place.fogShift ?? 0;
  return h.time.flatMap((time, midnight) => {
    const hasEvening = midnight >= 6, hasMorning = midnight + 12 <= h.time.length;
    if (!time.endsWith('T00:00') || !hasEvening || !hasMorning) return [];
    if (time.slice(0, 10) + 'T12' <= hourNow) return [];

    const morning = key => h[key].slice(midnight + 4, midnight + 10);   // 04 to 09 h
    const evening = key => h[key].slice(midnight - 6, midnight - 3);    // 18 to 20 h the day before
    const morningInputs = [
      Math.max(...morning('relative_humidity_2m')),
      mean(morning('wind_speed_10m')),
      // Rain from 21 to 06 h plus rain from 04 to 09 h. The overlap is counted twice, as it was when the weights were fitted.
      Math.log1p(sum(h.precipitation.slice(midnight - 3, midnight + 7)) + sum(morning('precipitation'))),
      mean(evening('cloud_cover')),
      mean(evening('temperature_2m')) - mean(evening('dew_point_2m')),          // how far the evening air is from saturation
      mean(evening('temperature_2m')) - Math.min(...morning('temperature_2m'))];   // overnight cooling

    // The usual fog rate, as log-odds, for the morning and for each hour. The limits are those used when the monthly weights were fitted.
    const monthRate = place.fogByMonth?.[time.slice(5, 7) - 1];
    const fogUsual = monthRate === undefined ? logOdds(place.fog) : logOdds(clamp(monthRate, 0.005, 0.995));
    const fogUsualAt = k => monthRate === undefined ? logOdds(place.fogByHour[k])
      : logOdds(clamp(place.fogByHour[k] * monthRate / place.fog, 0.005, 0.97));

    const hours = HOURS.map((hour, k) => {
      const i = midnight + hour;
      const hourInputs = [
        h.relative_humidity_2m[i],
        h.wind_speed_10m[i],
        h.temperature_2m[i] - h.dew_point_2m[i],
        Math.log1p(sum(h.precipitation.slice(i - 2, i + 1))),   // rain in the last three hours
        h.cloud_cover[i]];
      const fog = chance(weights.hour, [...hourInputs, ...morningInputs, fogUsualAt(k)], fogShift);
      return hasMist ? {hour, mist: chance(MIST_HOUR, [...hourInputs, ...morningInputs, logOdds(place.mistByHour[k])], mistShift), fog} : {hour, fog};
    });

    const incomplete = [...morningInputs, ...hours.map(x => x.fog), ...hours.map(x => x.mist ?? 0)].some(Number.isNaN);
    const fog = chance(weights.morning, [...morningInputs, fogUsual], fogShift);
    const morningChances = hasMist ? {mist: chance(MIST_MORNING, [...morningInputs, logOdds(place.mist)], mistShift), fog} : {fog};
    return incomplete ? [] : [{date: time.slice(0, 10), hours, ...morningChances}];
  });
}
