import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {fogMornings, reportsUrl} from '../reports.js';

// Twelve January days of Amritsar's reports as the archive sends them, and the fog mornings that the fitting code counts in them.
const csv = readFileSync(new URL('amritsar-reports.csv', import.meta.url), 'utf8');
const expected = JSON.parse(readFileSync(new URL('amritsar-fog-mornings.json', import.meta.url)));
const later = Date.parse('2025-02-01T00:00:00Z');

test('counts fog mornings as the fitting code does', () => {
  assert.deepEqual(fogMornings(csv, 'Asia/Kolkata', later), expected);
  // Among them: fog mornings and mornings without. Two mornings have too few reports to count.
  assert.equal(expected['2025-01-11'], true);
  assert.equal(expected['2025-01-12'], false);
  assert.ok(!('2025-01-08' in expected) && !('2025-01-28' in expected));
});

test('does not count a report under 1 km as fog in rain or in dry air', () => {
  // One report in each hour from 04 to 09, all at 0.3 miles. `codes` and `dewPoints` give the weather codes and dew point (F) for each; the air is at 50 F.
  const morning = (codes, dewPoints) => fogMornings('station,valid,vsby,wxcodes,tmpf,dwpf\n' + codes.map((code, i) =>
    `VIDP,2025-01-05 0${4 + i}:00,0.31,${code},50.00,${dewPoints[i]}`).join('\n'), 'Asia/Kolkata', later)['2025-01-05'];
  const near = Array(6).fill('46.40');   // 2 C under the temperature
  assert.equal(morning(['FG', 'FG', 'M', 'M', 'M', 'M'], near), true);
  assert.equal(morning(['FG', '-RA', 'RA BR', 'SN', '-DZ', 'TSRA'], near), false);       // fog in one hour only
  assert.equal(morning(['FG', 'FG', 'FU', 'FU', 'FU', 'FU'], ['46.40', '44.60', '44.60', 'M', '30.20', '30.20']), false);   // 3 C under, or not given
});

test('leaves a morning out until it is 10 h at the place', () => {
  const at = time => fogMornings(csv, 'Asia/Kolkata', Date.parse(time));
  assert.ok(!('2025-01-30' in at('2025-01-30T04:29:00Z')));   // 09:59 in Amritsar
  assert.equal(at('2025-01-30T04:30:00Z')['2025-01-30'], false);
  assert.equal(at('2025-01-30T04:29:00Z')['2025-01-29'], true);
});

test('does not take an answer that is not a list of reports', () => {
  assert.throws(() => fogMornings('Unknown station\n', 'Asia/Kolkata', later));
  assert.deepEqual(fogMornings('station,valid,vsby,wxcodes,tmpf,dwpf\n', 'Asia/Kolkata', later), {});
});

test('asks for the days around now, on the clock at the place', () => {
  const asked = new URL(reportsUrl('VIDP', 'Asia/Kolkata', Date.parse('2026-01-02T12:00:00Z'))).searchParams;
  assert.deepEqual(['year1', 'month1', 'day1', 'year2', 'month2', 'day2'].map(key => asked.get(key)), ['2025', '12', '30', '2026', '1', '4']);
  assert.equal(asked.get('tz'), 'Asia/Kolkata');
  assert.deepEqual(asked.getAll('data'), ['vsby', 'wxcodes', 'tmpf', 'dwpf']);
});
