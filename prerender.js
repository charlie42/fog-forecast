// Writes forecasts.json: for each city, the rows that build.py puts into its page, in every language.
// Also writes reports.json: whether the last mornings had fog at the airport, for the cities whose formula takes that in.
// Search engines cannot fetch the forecast themselves (Open-Meteo's robots.txt keeps them out),
// so without this they would see a page with no forecast on it.
import {readFileSync, writeFileSync} from 'node:fs';
import {forecastUrl, forecastHtml, languages} from './src/page.js';
import {reportsUrl, fogMornings} from './reports.js';

const cities = JSON.parse(readFileSync(new URL('cities.json', import.meta.url)));

// Fails after a second try, so that a build without a forecast stops and the pages already published stay up.
async function hourly(city, retries = 1) {
  const response = await fetch(forecastUrl(city)).catch(() => null);
  if (response?.ok) return (await response.json()).hourly;
  if (!retries) throw new Error(`No forecast for ${city.name}: ${response ? response.status : 'no answer'}`);
  await new Promise(resolve => setTimeout(resolve, 5000));
  return hourly(city, retries - 1);
}

// Without the airport's reports the build goes on: the city's chances then come from the weights that do not need them.
async function fogBefore(city) {
  try {
    const response = await fetch(reportsUrl(city.station, city.tz), {signal: AbortSignal.timeout(30000)});
    if (!response.ok) throw new Error(response.status);
    return fogMornings(await response.text(), city.tz);
  } catch (error) {
    console.log(`No airport reports for ${city.name}: ${error.message}`);
  }
}

const rows = {}, before = {};
for (const city of cities) {
  const forecast = await hourly(city);
  if (city.station) before[city.name] = await fogBefore(city);
  const place = {...city, fogBefore: before[city.name]};
  rows[city.name] = Object.fromEntries(languages.map(lang => [lang, forecastHtml(forecast, place, lang)]));
}
writeFileSync(new URL('forecasts.json', import.meta.url), JSON.stringify(rows));
writeFileSync(new URL('reports.json', import.meta.url), JSON.stringify(before));
console.log(`Wrote forecasts for ${cities.length} cities`);
