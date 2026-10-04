// Fetches the weather forecast for one place and draws the fog and mist chances into the page.
import {forecastMornings, HOURS} from './model.js';

const VARIABLES = 'relative_humidity_2m,temperature_2m,dew_point_2m,wind_speed_10m,precipitation,cloud_cover';

const percent = p => Math.round(100 * p);
// Cells whiten as the chance rises. The power below 1 keeps small chances visible.
const cell = p => `<td style="--veil:${(p ** 0.6).toFixed(2)}">${percent(p)}</td>`;

function morningHtml({date, mist, fog, hours}) {
  const day = new Date(date + 'T00:00').toLocaleDateString('en-GB', {weekday: 'long', day: 'numeric', month: 'long'});
  return `<section class="morning">
<h2>${day}</h2>
<p class="chance"><b>${percent(fog)}%</b> fog <span>${percent(mist)}% mist</span></p>
<table>
<tr><td></td>${HOURS.map(hour => `<th scope="col">${hour} h</th>`).join('')}</tr>
<tr><th scope="row">Fog</th>${hours.map(x => cell(x.fog)).join('')}</tr>
<tr><th scope="row">Mist</th>${hours.map(x => cell(x.mist)).join('')}</tr>
</table>
</section>`;
}

export async function showForecast(place, out = document.getElementById('forecast')) {
  try {
    const response = await fetch(`https://api.open-meteo.com/v1/forecast?latitude=${place.lat}&longitude=${place.lon}`
      + `&hourly=${VARIABLES}&models=icon_eu&timezone=${place.tz}&past_days=1&forecast_days=4`);
    if (!response.ok) throw new Error(response.status);
    const mornings = forecastMornings((await response.json()).hourly, place);
    const month = new Date().getMonth(), offSeason = month > 2 && month < 9;
    out.innerHTML = (mornings.map(morningHtml).join('') || '<p>The weather forecast has no complete morning right now. Try again in an hour.</p>')
      + (offSeason ? '<p>The formula has only been tested for October to March.</p>' : '');
  } catch {
    out.textContent = 'Could not load the weather forecast from Open-Meteo. Reload the page to try again.';
  }
}
