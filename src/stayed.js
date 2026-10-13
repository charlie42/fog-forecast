// Counts a GoatCounter event once a page has been open and on screen for 10 seconds, named after the page: "stayed /berlin".
// Ten seconds is enough to read tomorrow's row and more than a visitor who landed on the wrong page spends.
// Time in a background tab is left out. The event keeps the visit's referrer, so GoatCounter shows where those who stayed came from.
const STAY = 10_000;

export function countStay(page, send, stay = STAY) {
  let left = stay, shown = null, timer;
  const watch = () => {
    if (page.visibilityState !== 'visible') {
      if (shown === null) return;
      clearTimeout(timer);
      left -= Date.now() - shown;
      shown = null;
    } else if (shown === null) {
      shown = Date.now();
      timer = setTimeout(() => {
        page.removeEventListener('visibilitychange', watch);
        send();
      }, left);
    }
  };
  page.addEventListener('visibilitychange', watch);
  watch();
}

// An event's name may not start with a slash, hence the word in front of the path. count.js loads async, so on a slow
// connection the event waits for it; where it never loads (a blocker) nothing is sent.
if (typeof document !== 'undefined') {
  const send = () => window.goatcounter.count({path: path => 'stayed ' + path, event: true});
  countStay(document, () =>
    window.goatcounter?.count ? send() : document.querySelector('script[data-goatcounter]')?.addEventListener('load', send));
}
