// Chance of fog and mist on each coming morning, worked out from an hourly weather forecast.
//
// Four logistic models share the same weather inputs. Two give the chance for a whole morning
// (visibility under 5 km for mist, under 1 km for fog, for at least two hours between 04 and 10 h)
// and two give the chance for a single hour. Each also takes how common mist or fog usually is at
// the place, so a new place needs its usual rates but no fitting of its own.

export const HOURS = [3, 4, 5, 6, 7, 8, 9, 10, 11];

// Weights in the order of `morningInputs` below, then the usual rate (as log-odds), then the constant.
const MIST_MORNING = [0.20342, -0.13347, -0.62789, -0.00341, -0.20227, -0.01995, 0.74347, -17.60958];
const FOG_MORNING = [0.21223, -0.18159, -0.83361, -0.00905, -0.43466, 0.1618, 0.33433, -19.60083];
// Weights in the order of `hourInputs` below, then the morning inputs, the usual rate for that hour, the constant.
const MIST_HOUR = [0.07478, -0.05783, -0.2973, -0.25481, -0.00156, 0.08788, -0.06716, -0.5596, -0.00385, -0.16795, -0.04451, 0.66459, -13.5673];
const FOG_HOUR = [0.27946, -0.10117, 0.97268, -1.73308, -0.00587, 0.11295, -0.06034, -0.39226, -0.00701, -0.36114, 0.10603, 0.44476, -37.09207];

const sum = values => values.reduce((a, b) => a + b, 0);
const mean = values => sum(values) / values.length;
const logOdds = p => Math.log(p / (1 - p));
const chance = (weights, inputs) =>
  1 / (1 + Math.exp(-inputs.reduce((z, value, k) => z + weights[k] * value, weights[inputs.length])));

/**
 * @param hourly  The "hourly" block of an Open-Meteo forecast in the place's local time, with
 *                relative_humidity_2m, temperature_2m, dew_point_2m, wind_speed_10m, precipitation
 *                and cloud_cover. It has to start the day before the first morning wanted.
 * @param place   Usual rates for the place: {mist, fog, mistByHour, fogByHour}, see cities.json.
 * @param now     Mornings whose noon is before this time are left out.
 * @returns       One entry per morning: {date, mist, fog, hours: [{hour, mist, fog}]}, chances from 0 to 1.
 */
export function forecastMornings(hourly, place, now = Date.now()) {
  const h = hourly;
  return h.time.flatMap((time, midnight) => {
    const hasEvening = midnight >= 6, hasMorning = midnight + 12 <= h.time.length;
    if (!time.endsWith('T00:00') || !hasEvening || !hasMorning) return [];
    if (new Date(time).getTime() + 12 * 3600e3 < now) return [];

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

    const hours = HOURS.map((hour, k) => {
      const i = midnight + hour;
      const hourInputs = [
        h.relative_humidity_2m[i],
        h.wind_speed_10m[i],
        h.temperature_2m[i] - h.dew_point_2m[i],
        Math.log1p(sum(h.precipitation.slice(i - 2, i + 1))),   // rain in the last three hours
        h.cloud_cover[i]];
      return {hour,
        mist: chance(MIST_HOUR, [...hourInputs, ...morningInputs, logOdds(place.mistByHour[k])]),
        fog: chance(FOG_HOUR, [...hourInputs, ...morningInputs, logOdds(place.fogByHour[k])])};
    });

    const incomplete = [...morningInputs, ...hours.flatMap(x => [x.mist, x.fog])].some(Number.isNaN);
    return incomplete ? [] : [{date: time.slice(0, 10), hours,
      mist: chance(MIST_MORNING, [...morningInputs, logOdds(place.mist)]),
      fog: chance(FOG_MORNING, [...morningInputs, logOdds(place.fog)])}];
  });
}
