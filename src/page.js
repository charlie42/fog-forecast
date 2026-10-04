// Fetches the weather forecast for one place and draws the fog and mist chances into the page.
// The forecast is ICON-EU unless the place names another model (ICON-EU stops at Europe, so US places use icon_global).
import {forecastMornings} from './model.js';

const VARIABLES = 'relative_humidity_2m,temperature_2m,dew_point_2m,wind_speed_10m,precipitation,cloud_cover';

const percent = p => Math.round(100 * p) + '%';

// Both dates as YYYY-MM-DD in the place's own time zone, e.g. "Tomorrow, Monday 5 Oct".
export function dayLabel(date, today) {
  const day = new Date(date + 'T00:00').toLocaleDateString('en-GB', {weekday: 'long', day: 'numeric', month: 'short'});
  const daysAhead = Math.round((Date.parse(date) - Date.parse(today)) / 864e5);
  return (['Today, ', 'Tomorrow, '][daysAhead] ?? '') + day;
}

function morningHtml({date, mist, fog, hours}, today) {
  const byHour = key => hours.map(x => `${x.hour}h ${percent(x[key])}`).join(' · ');
  return `<div class="morning">${dayLabel(date, today)}: mist <b>${percent(mist)}</b> · fog <b>${percent(fog)}</b>`
    + `<details><summary><small>by hour</small></summary><small>mist: ${byHour('mist')}<br>fog: ${byHour('fog')}</small></details></div>`;
}

export async function showForecast(place, out = document.getElementById('forecast')) {
  try {
    const response = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${place.lat}&longitude=${place.lon}`
      + `&hourly=${VARIABLES}&models=${place.model ?? 'icon_eu'}&timezone=${place.tz}&past_days=1&forecast_days=4`);
    if (!response.ok) throw new Error(response.status);
    const mornings = forecastMornings((await response.json()).hourly, place);
    const today = new Date().toLocaleDateString('en-CA', {timeZone: place.tz});
    const month = new Date().getMonth(), rareSeason = month > 2 && month < 8;   // April to August
    out.innerHTML = (mornings.map(m => morningHtml(m, today)).join('') || 'No forecast right now. Try again in an hour.')
      + (rareSeason ? '<p><small>Fog is rare from April to August, about one morning in a hundred across these cities. That is too few for a forecast to pick out, so take these numbers as a rough guide. The fog season starts in September.</small></p>' : '');
  } catch {
    out.textContent = 'Could not load the forecast. Reload the page to try again.';
  }
}
