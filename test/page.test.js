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
  const note = (place, date, lang) => forecastHtml(hourly, place, lang, Date.parse(date)).split('<p>')[2] ?? '';   // [1] is the time the rows were made
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
  assert.ok(html.startsWith('<div class="row"><span></span><small>Mist</small><small>Fog</small></div>'
    + '<div class="morning"><div class="row"><span>Today, Sunday 4 Oct</span><span class="high">62%</span><span class="high">58%</span></div>'));
  assert.ok(html.includes('<table class="hours"><tr><th></th><th>3h</th><th>4h</th>'));
  assert.ok(html.includes('<tr><th>fog</th><td>46%</td><td>45%</td>'));

  const german = forecastHtml(hourly, munich, 'de', Date.parse(now));
  assert.ok(german.startsWith('<div class="row"><span></span><small>Dunst</small><small>Nebel</small></div>'
    + '<div class="morning"><div class="row"><span>Heute, Sonntag, 4. Okt.</span><span class="high">62%</span>'));
  assert.ok(german.includes('<summary><small>nach Stunde</small></summary>'));
  assert.match(german, /<p><small>Stand: <time datetime="2026-10-04T[\d:.]+Z">\d+\. Okt\. 2026, \d\d:\d\d \S+<\/time><\/small><\/p>$/);
  assert.match(html, /<p><small>Updated <time datetime="2026-10-04T[\d:.]+Z">\d+ Oct 2026, \d\d:\d\d \S+<\/time><\/small><\/p>$/);
});

test('leaves mist out for a place without a mist rate', () => {
  const delhi = read('../cities.json').find(city => city.name === 'Delhi');
  const {now, hourly} = read('delhi-forecast.json');
  const html = forecastHtml(hourly, delhi, 'en', Date.parse(now));
  assert.ok(html.startsWith('<div class="row"><span></span><small>Fog</small></div>'
    + '<div class="morning"><div class="row"><span>Tomorrow, Saturday 10 Jan</span><span class="high">88%</span></div>'));
  assert.ok(html.includes('<tr><th>fog</th><td>77%</td><td>79%</td>'));
  assert.ok(!html.includes('mist'));
});
