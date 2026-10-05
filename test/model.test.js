import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {forecastMornings, VARIABLES} from '../src/model.js';

const read = path => JSON.parse(readFileSync(new URL(path, import.meta.url)));
const munich = read('../cities.json').find(city => city.name === 'Munich');
const {now, hourly} = read('munich-forecast.json');   // an Open-Meteo response saved on 4 October 2026

test('gives the reference chances for a saved Munich forecast', () => {
  const percent = p => Math.round(100 * p);
  const mornings = forecastMornings(hourly, munich, Date.parse(now)).map(m => ({
    mist: percent(m.mist), fog: percent(m.fog),
    mistHours: m.hours.map(x => percent(x.mist)), fogHours: m.hours.map(x => percent(x.fog))}));
  assert.deepEqual(mornings, read('munich-expected.json'));
});

test('adds the correction of the place to the log-odds of every chance', () => {
  const {mistShift, fogShift, ...uncorrected} = munich;
  const logOdds = p => Math.log(p / (1 - p));
  const all = place => forecastMornings(hourly, place, Date.parse(now)).flatMap(m => [m, ...m.hours]);
  const before = all(uncorrected);
  all(munich).forEach((after, i) => {
    assert.ok(Math.abs(logOdds(after.mist) - logOdds(before[i].mist) - mistShift) < 1e-9);
    assert.ok(Math.abs(logOdds(after.fog) - logOdds(before[i].fog) - fogShift) < 1e-9);
  });
});

test('leaves out mornings that are over', () => {
  assert.deepEqual(forecastMornings(hourly, munich, Date.parse('2026-10-20T00:00:00Z')), []);
});

test('goes by the clock at the place, not the viewer\'s', () => {
  const at = Date.parse('2026-10-04T18:00:00Z');   // 20 h in Munich, 11 h in Seattle
  const firstDate = place => forecastMornings(hourly, place, at)[0].date;
  assert.equal(firstDate(munich), '2026-10-05');
  assert.equal(firstDate({...munich, tz: 'America/Los_Angeles'}), '2026-10-04');
});

test('leaves out a morning with missing weather values', () => {
  // Open-Meteo sends null for a missing value.
  const gap = {...hourly, cloud_cover: hourly.cloud_cover.map((value, i) => i === 24 + 6 ? null : value)};
  const dates = forecast => forecast.map(m => m.date);
  const all = forecastMornings(hourly, munich, Date.parse(now));
  assert.deepEqual(dates(forecastMornings(gap, munich, Date.parse(now))), dates(all).slice(1));
});

test('gives the reference fog chances for Delhi, which has weights of its own, a rate per month and no mist', () => {
  const delhi = read('../cities.json').find(city => city.name === 'Delhi');
  const saved = read('delhi-forecast.json');   // five January days of the archived day-ahead forecast
  const percent = p => Math.round(100 * p);
  const mornings = forecastMornings(saved.hourly, delhi, Date.parse(saved.now));
  assert.deepEqual(mornings.map(m => ({fog: percent(m.fog), fogHours: m.hours.map(x => percent(x.fog))})), read('delhi-expected.json'));
  assert.ok(mornings.every(m => !('mist' in m) && m.hours.every(x => !('mist' in x))));
});

test('takes in the newest known of the two mornings before, where the formula has weights for it', () => {
  const delhi = read('../cities.json').find(city => city.name === 'Delhi');
  const saved = read('delhi-forecast.json');
  const percent = p => Math.round(100 * p);
  const chances = place => forecastMornings(saved.hourly, place, Date.parse(saved.now))
    .map(m => ({fog: percent(m.fog), fogHours: m.hours.map(x => percent(x.fog))}));
  // Reference chances for two sets of known mornings: between them one and two mornings before, with fog and without, and neither.
  for (const {fogBefore, mornings} of read('delhi-before-expected.json')) assert.deepEqual(chances({...delhi, fogBefore}), mornings);
  // The morning itself and mornings further back do not count, and no place in Europe takes any of it in.
  assert.deepEqual(chances({...delhi, fogBefore: {'2026-01-07': true, '2026-01-13': true}}).slice(0, 3), chances(delhi).slice(0, 3));
  const all = place => forecastMornings(hourly, place, Date.parse(now));
  assert.deepEqual(all({...munich, fogBefore: {'2026-10-04': true, '2026-10-05': true}}), all(munich));
});

test('uses the usual fog rate of the month where a place has one', () => {
  const delhi = read('../cities.json').find(city => city.name === 'Delhi');
  const saved = read('delhi-forecast.json');
  const later = (Date.parse('2026-10-09') - Date.parse('2026-01-09')) / 1000;   // the saved days start on 9 January
  const inMonth = month => ({...saved.hourly, time: saved.hourly.time.map(t => month === '10' ? t + later : t)});
  const first = month => forecastMornings(inMonth(month), delhi, Date.parse(`2026-${month}-09T12:00:00Z`))[0].fog;
  assert.ok(first('10') < first('01') / 3);   // the same weather counts for much less in October than in January
});

test('reads each hour by the clock at the place on both sides of a clock change', () => {
  // Open-Meteo counts all the hours of an answer from the clock on the day it was asked for. Here: steady weather for
  // five days from midnight at the place, with more cloud in one hour. Cloud in a morning hour counts for that hour alone.
  const steady = {relative_humidity_2m: 95, temperature_2m: 5, dew_point_2m: 4, wind_speed_10m: 5, precipitation: 0, cloud_cover: 50};
  const answer = (start, cloudy) => {
    const time = Array.from({length: 120}, (_, i) => Date.parse(start) / 1000 + 3600 * i);
    return {time, ...Object.fromEntries(VARIABLES.map(key => [key, time.map(t => key === 'cloud_cover' && t === Date.parse(cloudy) / 1000 ? 100 : steady[key])]))};
  };
  const moved = (start, cloudy) => {
    const cells = hourly => forecastMornings(hourly, munich, Date.parse(start)).flatMap(m => m.hours.map(x => [`${m.date} ${x.hour}h`, x.fog]));
    const before = cells(answer(start)), after = cells(answer(start, cloudy));
    assert.equal(before.length, 4 * 9);
    return after.filter(([, fog], i) => fog !== before[i][1]).map(([cell]) => cell);
  };
  // Asked for in summer time. The clocks go back on 25 October 2026 at 01:00 UTC.
  assert.deepEqual(moved('2026-10-22T22:00:00Z', '2026-10-24T02:00:00Z'), ['2026-10-24 4h']);
  assert.deepEqual(moved('2026-10-22T22:00:00Z', '2026-10-25T02:00:00Z'), ['2026-10-25 3h']);
  assert.deepEqual(moved('2026-10-22T22:00:00Z', '2026-10-26T03:00:00Z'), ['2026-10-26 4h']);
  // Asked for in winter time. The clocks go forward on 29 March 2026 at 01:00 UTC.
  assert.deepEqual(moved('2026-03-25T23:00:00Z', '2026-03-28T03:00:00Z'), ['2026-03-28 4h']);
  assert.deepEqual(moved('2026-03-25T23:00:00Z', '2026-03-29T01:00:00Z'), ['2026-03-29 3h']);
  assert.deepEqual(moved('2026-03-25T23:00:00Z', '2026-03-30T02:00:00Z'), ['2026-03-30 4h']);
});
