import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {forecastMornings} from '../src/model.js';

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
  const gap = {...hourly, cloud_cover: hourly.cloud_cover.map((value, i) => i === 24 + 6 ? NaN : value)};
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

test('uses the usual fog rate of the month where a place has one', () => {
  const delhi = read('../cities.json').find(city => city.name === 'Delhi');
  const saved = read('delhi-forecast.json');
  const inMonth = month => ({...saved.hourly, time: saved.hourly.time.map(t => '2026-' + month + t.slice(7))});
  const first = month => forecastMornings(inMonth(month), delhi, Date.parse(`2026-${month}-09T12:00:00Z`))[0].fog;
  assert.ok(first('10') < first('01') / 3);   // the same weather counts for much less in October than in January
});
