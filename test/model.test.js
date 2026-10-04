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

test('leaves out mornings that are over', () => {
  assert.deepEqual(forecastMornings(hourly, munich, Date.parse('2026-10-20T00:00:00Z')), []);
});

test('leaves out a morning with missing weather values', () => {
  const gap = {...hourly, cloud_cover: hourly.cloud_cover.map((value, i) => i === 24 + 6 ? NaN : value)};
  const dates = forecast => forecast.map(m => m.date);
  const all = forecastMornings(hourly, munich, Date.parse(now));
  assert.deepEqual(dates(forecastMornings(gap, munich, Date.parse(now))), dates(all).slice(1));
});
