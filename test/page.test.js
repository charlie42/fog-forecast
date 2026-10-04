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
  assert.equal(dayLabel('2026-10-05', '2026-10-04', 'de'), 'Morgen, Montag, 5. Okt.');
  assert.equal(dayLabel('2026-10-05', '2026-10-04', 'it'), 'Domani, lunedì 5 ott');
});

test('says when fog is rare, by the place\'s own season', () => {
  const {hourly} = read('munich-forecast.json');
  const munich = read('../cities.json').find(city => city.name === 'Munich');
  const note = (place, date, lang) => forecastHtml(hourly, place, lang, Date.parse(date)).split('<p>')[1] ?? '';
  assert.match(note(munich, '2026-05-10'), /rare from April to August.*starts in September/);
  assert.match(note(munich, '2026-05-10', 'de'), /^<small>Von April bis August ist Nebel selten.*beginnt im September/);
  assert.match(note(munich, '2026-05-10', 'it'), /^<small>Tra aprile e agosto la nebbia è rara.*comincia a settembre/);
  assert.equal(note(munich, '2026-10-04'), '');
  assert.match(note({...munich, rare: [10, 3]}, '2026-01-10'), /rare from October to March.*starts in April/);
  assert.equal(note({...munich, rare: [10, 3]}, '2026-05-10'), '');
  assert.equal(note({...munich, rare: []}, '2026-05-10'), '');
});

test('draws a row per morning from a saved Munich forecast', () => {
  const munich = read('../cities.json').find(city => city.name === 'Munich');
  const {now, hourly} = read('munich-forecast.json');
  const html = forecastHtml(hourly, munich, 'en', Date.parse(now));
  assert.equal(html.split('class="morning"').length - 1, read('munich-expected.json').length);
  assert.ok(html.startsWith('<div class="morning">Today, Sunday 4 Oct: mist <b>65%</b> · fog <b>60%</b>'));
  assert.ok(html.includes('fog: 3h 48% · 4h 47%'));

  const german = forecastHtml(hourly, munich, 'de', Date.parse(now));
  assert.ok(german.startsWith('<div class="morning">Heute, Sonntag, 4. Okt.: Dunst <b>65%</b> · Nebel <b>60%</b>'));
  assert.ok(german.includes('<summary><small>nach Stunde</small></summary>'));
});
