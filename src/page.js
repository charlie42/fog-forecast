// Turns the weather forecast for one place into the rows of fog and mist chances on its page.
// The forecast is ICON-EU unless the place names another model (ICON-EU stops at Europe, so US places use icon_global).
import {forecastMornings} from './model.js';

const VARIABLES = 'relative_humidity_2m,temperature_2m,dew_point_2m,wind_speed_10m,precipitation,cloud_cover';

const percent = p => Math.round(100 * p) + '%';

// The words in the rows, per language. A page in another language also needs templates in src/ and names in cities.json.
const TEXT = {
  en: {
    locale: 'en-GB', days: ['Today, ', 'Tomorrow, '], mist: 'mist', fog: 'fog', byHour: 'by hour',
    none: 'No forecast right now. Try again in an hour.',
    failed: 'Could not load the forecast. Reload the page to try again.',
    rare: 'Fog is rare from April to August, about one morning in a hundred across these cities. That is too few for a forecast to pick out, so take these numbers as a rough guide. The fog season starts in September.',
  },
  de: {
    locale: 'de-DE', days: ['Heute, ', 'Morgen, '], mist: 'Dunst', fog: 'Nebel', byHour: 'nach Stunde',
    none: 'Gerade gibt es keine Vorhersage. In einer Stunde noch einmal versuchen.',
    failed: 'Die Vorhersage konnte nicht geladen werden. Seite neu laden, um es noch einmal zu versuchen.',
    rare: 'Von April bis August ist Nebel selten, in diesen Städten etwa an einem von hundert Morgen. Das ist zu wenig, als dass eine Vorhersage ihn treffen könnte. Die Zahlen sind dann nur ein grober Anhaltspunkt. Die Nebelsaison beginnt im September.',
  },
};
export const languages = Object.keys(TEXT);

// Both dates as YYYY-MM-DD in the place's own time zone, e.g. "Tomorrow, Monday 5 Oct".
export function dayLabel(date, today, lang = 'en') {
  const day = new Date(date + 'T00:00').toLocaleDateString(TEXT[lang].locale, {weekday: 'long', day: 'numeric', month: 'short'});
  const daysAhead = Math.round((Date.parse(date) - Date.parse(today)) / 864e5);
  return (TEXT[lang].days[daysAhead] ?? '') + day;
}

function morningHtml({date, mist, fog, hours}, today, lang) {
  const text = TEXT[lang];
  const byHour = key => hours.map(x => `${x.hour}h ${percent(x[key])}`).join(' · ');
  return `<div class="morning">${dayLabel(date, today, lang)}: ${text.mist} <b>${percent(mist)}</b> · ${text.fog} <b>${percent(fog)}</b>`
    + `<details><summary><small>${text.byHour}</small></summary><small>${text.mist}: ${byHour('mist')}<br>${text.fog}: ${byHour('fog')}</small></details></div>`;
}

export const forecastUrl = place =>
  `https://api.open-meteo.com/v1/forecast?latitude=${place.lat}&longitude=${place.lon}`
  + `&hourly=${VARIABLES}&models=${place.model ?? 'icon_eu'}&timezone=${place.tz}&past_days=1&forecast_days=4`;

// The rows for one place, from the "hourly" block of the Open-Meteo answer to `forecastUrl`.
export function forecastHtml(hourly, place, lang = 'en', now = Date.now()) {
  const today = new Date(now).toLocaleDateString('en-CA', {timeZone: place.tz});
  const month = new Date(now).getMonth(), rareSeason = month > 2 && month < 8;   // April to August
  return (forecastMornings(hourly, place, now).map(m => morningHtml(m, today, lang)).join('') || TEXT[lang].none)
    + (rareSeason ? `<p><small>${TEXT[lang].rare}</small></p>` : '');
}

// The page arrives with the rows from when the site was last built (prerender.js). This swaps in fresh ones.
export async function showForecast(place, lang = 'en', out = document.getElementById('forecast')) {
  try {
    const response = await fetch(forecastUrl(place));
    if (!response.ok) throw new Error(response.status);
    out.innerHTML = forecastHtml((await response.json()).hourly, place, lang);
  } catch {
    // The rows from the build stay. Search engines always end up here, because Open-Meteo's robots.txt keeps them out.
    if (!out.querySelector('.morning')) out.textContent = TEXT[lang].failed;
  }
}
