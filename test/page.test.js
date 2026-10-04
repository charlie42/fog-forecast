import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {dayLabel, forecastHtml} from '../src/page.js';

const read = path => JSON.parse(readFileSync(new URL(path, import.meta.url)));

test('names today and tomorrow, and only those', () => {
  assert.match(dayLabel('2026-10-04', '2026-10-04'), /^Today, Sunday 4 Oct/);
  assert.match(dayLabel('2026-10-05', '2026-10-04'), /^Tomorrow, Monday 5 Oct/);
  assert.match(dayLabel('2026-10-06', '2026-10-04'), /^Tuesday 6 Oct/);
  assert.match(dayLabel('2026-11-01', '2026-10-31'), /^Tomorrow, Sunday 1 Nov/);
});

test('draws a row per morning from a saved Munich forecast', () => {
  const munich = read('../cities.json').find(city => city.name === 'Munich');
  const {now, hourly} = read('munich-forecast.json');
  const html = forecastHtml(hourly, munich, Date.parse(now));
  assert.equal(html.split('class="morning"').length - 1, read('munich-expected.json').length);
  assert.ok(html.startsWith('<div class="morning">Today, Sunday 4 Oct: mist <b>65%</b> · fog <b>60%</b>'));
  assert.ok(html.includes('fog: 3h 48% · 4h 47%'));
});
