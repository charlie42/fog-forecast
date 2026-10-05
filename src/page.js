// Turns the weather forecast for one place into the rows of fog and mist chances on its page.
// The forecast is ICON-EU unless the place names another model (ICON-EU stops at Europe, so US places use icon_global).
import {forecastMornings, VARIABLES} from './model.js';

const percent = p => Math.round(100 * p) + '%';

// The words in the rows, per language. A page in another language also needs templates in src/ and names in cities.json.
const TEXT = {
  en: {
    locale: 'en-GB', days: ['Today, ', 'Tomorrow, '], mist: 'mist', fog: 'fog', byHour: 'by hour', updated: 'Updated ',
    none: 'No forecast right now. Try again in an hour.',
    failed: 'Could not load the forecast. Reload the page to try again.',
    rare: (first, last, next) => `Fog is rare from ${first} to ${last}, about one morning in a hundred across these cities. That is too few for a forecast to pick out, so take these numbers as a rough guide. The fog season starts in ${next}.`,
  },
  de: {
    locale: 'de-DE', days: ['Heute, ', 'Morgen, '], mist: 'Dunst', fog: 'Nebel', byHour: 'nach Stunde', updated: 'Stand: ',
    none: 'Gerade gibt es keine Vorhersage. In einer Stunde noch einmal versuchen.',
    failed: 'Die Vorhersage konnte nicht geladen werden. Seite neu laden, um es noch einmal zu versuchen.',
    rare: (first, last, next) => `Von ${first} bis ${last} ist Nebel selten, in diesen Städten etwa an einem von hundert Morgen. Das ist zu wenig, als dass eine Vorhersage ihn treffen könnte. Die Zahlen sind dann nur ein grober Anhaltspunkt. Die Nebelsaison beginnt im ${next}.`,
  },
  it: {
    locale: 'it-IT', days: ['Oggi, ', 'Domani, '], mist: 'foschia', fog: 'nebbia', byHour: 'ora per ora', updated: 'Aggiornato il ',
    none: 'Al momento non c\'è una previsione. Riprovare tra un\'ora.',
    failed: 'Impossibile caricare la previsione. Ricaricare la pagina per riprovare.',
    rare: (first, last, next) => `Tra ${first} e ${last} la nebbia è rara, in queste città circa una mattina su cento. È troppo poco perché una previsione possa coglierla. In questi mesi i numeri sono solo un'indicazione di massima. La stagione della nebbia comincia a ${next}.`,
  },
};
export const languages = Object.keys(TEXT);

// Both dates as YYYY-MM-DD in the place's own time zone, e.g. "Tomorrow, Monday 5 Oct".
export function dayLabel(date, today, lang = 'en') {
  const day = new Date(date + 'T00:00').toLocaleDateString(TEXT[lang].locale, {weekday: 'long', day: 'numeric', month: 'short'});
  const daysAhead = Math.round((Date.parse(date) - Date.parse(today)) / 864e5);
  return (TEXT[lang].days[daysAhead] ?? '') + day;
}

// A place without a usual mist rate gets no mist number (Delhi, where smog keeps visibility under 5 km on nearly every morning).
const kindsOf = morning => ['mist', 'fog'].filter(kind => morning[kind] !== undefined);

// The stylesheet prints a chance under 10% in grey and one from 30% in bold.
function chanceHtml(p) {
  const shown = Math.round(100 * p);
  return `<span${shown < 10 ? ' class="low"' : shown >= 30 ? ' class="high"' : ''}>${shown}%</span>`;
}

// The line above the rows that says which column is mist and which is fog.
function headingHtml(morning, lang) {
  const capital = word => word[0].toUpperCase() + word.slice(1);
  return `<div class="row"><span></span>${kindsOf(morning).map(kind => `<small>${capital(TEXT[lang][kind])}</small>`).join('')}</div>`;
}

function morningHtml(morning, today, lang) {
  const text = TEXT[lang], kinds = kindsOf(morning);
  const hours = `<tr><th></th>${morning.hours.map(x => `<th>${x.hour}h</th>`).join('')}</tr>`
    + kinds.map(kind => `<tr><th>${text[kind]}</th>${morning.hours.map(x => `<td>${percent(x[kind])}</td>`).join('')}</tr>`).join('');
  return `<div class="morning"><div class="row"><span>${dayLabel(morning.date, today, lang)}</span>${kinds.map(kind => chanceHtml(morning[kind])).join('')}</div>`
    + `<details><summary><small>${text.byHour}</small></summary><table class="hours">${hours}</table></details></div>`;
}

// A note for the months when fog is rare at the place: `rare` holds the first and last of them, e.g. [10, 3] for Auckland.
// `month` is the month at the place, 1 to 12.
// Without it they are April to August. An empty `rare` means fog all year (Christchurch) and no note.
function rareNote(place, lang, month) {
  const [first, last] = place.rare ?? [4, 8];
  const rareNow = first <= last ? first <= month && month <= last : month >= first || month <= last;
  if (!first || !rareNow) return '';
  const name = number => new Date(2000, number - 1).toLocaleDateString(TEXT[lang].locale, {month: 'long'});
  return `<p><small>${TEXT[lang].rare(name(first), name(last), name(last % 12 + 1))}</small></p>`;
}

// When the rows were made, in the reader's own time zone (UTC where the site is built), e.g. "Updated 4 Oct 2026, 15:17 CEST".
function updatedHtml(lang, now) {
  const when = new Date(now).toLocaleString(TEXT[lang].locale,
    {day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', timeZoneName: 'short'});
  return `<p><small>${TEXT[lang].updated}<time datetime="${new Date(now).toISOString()}">${when}</time></small></p>`;
}

export const forecastUrl = place =>
  `https://api.open-meteo.com/v1/forecast?latitude=${place.lat}&longitude=${place.lon}`
  + `&hourly=${VARIABLES.join(',')}&models=${place.model ?? 'icon_eu'}&timezone=${place.tz}&past_days=1&forecast_days=4`;

// The rows for one place, from the "hourly" block of the Open-Meteo answer to `forecastUrl`.
export function forecastHtml(hourly, place, lang = 'en', now = Date.now()) {
  const today = new Date(now).toLocaleDateString('en-CA', {timeZone: place.tz});
  const mornings = forecastMornings(hourly, place, now);
  const rows = mornings.map(m => morningHtml(m, today, lang)).join('');
  return (rows ? headingHtml(mornings[0], lang) + rows + updatedHtml(lang, now) : TEXT[lang].none) + rareNote(place, lang, Number(today.slice(5, 7)));
}

// The page arrives with the rows from when the site was last built (prerender.js). This swaps in fresh ones.
export async function showForecast(place, lang = 'en', out = document.getElementById('forecast')) {
  try {
    const response = await fetch(forecastUrl(place));
    if (!response.ok) throw new Error(response.status);
    const rows = forecastHtml((await response.json()).hourly, place, lang);
    // An answer without a single morning (gaps while a new model run comes in) does not replace the rows from the build.
    if (rows.includes('class="morning"') || !out.querySelector('.morning')) out.innerHTML = rows;
  } catch {
    // The rows from the build stay. Search engines always end up here, because Open-Meteo's robots.txt keeps them out.
    if (!out.querySelector('.morning')) out.textContent = TEXT[lang].failed;
  }
}
