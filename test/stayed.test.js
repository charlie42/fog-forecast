import test from 'node:test';
import assert from 'node:assert/strict';
import {countStay} from '../src/stayed.js';

// A page that is shown or hidden on request, the way a browser tab is.
function page(state) {
  const page = new EventTarget();
  page.visibilityState = state;
  page.turn = to => {
    page.visibilityState = to;
    page.dispatchEvent(new Event('visibilitychange'));
  };
  return page;
}

test('counts a stay after 10 seconds on screen, once, and leaves out time in the background', t => {
  t.mock.timers.enable({apis: ['setTimeout', 'Date']});
  const tab = page('visible');
  let sent = 0;
  countStay(tab, () => sent++);
  t.mock.timers.tick(6_000);
  tab.turn('hidden');
  t.mock.timers.tick(60_000);
  tab.turn('visible');
  t.mock.timers.tick(3_999);
  assert.equal(sent, 0);
  t.mock.timers.tick(1);
  assert.equal(sent, 1);
  tab.turn('hidden');
  tab.turn('visible');
  t.mock.timers.tick(60_000);
  assert.equal(sent, 1);
});

test('starts the 10 seconds when a page opened in the background is first shown', t => {
  t.mock.timers.enable({apis: ['setTimeout', 'Date']});
  const tab = page('hidden');
  let sent = 0;
  countStay(tab, () => sent++);
  t.mock.timers.tick(60_000);
  tab.turn('visible');
  t.mock.timers.tick(9_999);
  assert.equal(sent, 0);
  t.mock.timers.tick(1);
  assert.equal(sent, 1);
});

test('counts nothing for a page that stays in the background or is closed early', t => {
  t.mock.timers.enable({apis: ['setTimeout', 'Date']});
  let sent = 0;
  countStay(page('hidden'), () => sent++);
  const tab = page('visible');
  countStay(tab, () => sent++);
  t.mock.timers.tick(9_999);
  tab.turn('hidden');
  t.mock.timers.tick(600_000);
  assert.equal(sent, 0);
});
