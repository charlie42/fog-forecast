import test from 'node:test';
import assert from 'node:assert/strict';
import {dayLabel} from '../src/page.js';

test('names today and tomorrow, and only those', () => {
  assert.match(dayLabel('2026-10-04', '2026-10-04'), /^Today, Sunday 4 Oct/);
  assert.match(dayLabel('2026-10-05', '2026-10-04'), /^Tomorrow, Monday 5 Oct/);
  assert.match(dayLabel('2026-10-06', '2026-10-04'), /^Tuesday 6 Oct/);
  assert.match(dayLabel('2026-11-01', '2026-10-31'), /^Tomorrow, Sunday 1 Nov/);
});
