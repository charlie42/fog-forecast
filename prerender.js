// Writes forecasts.json: for each city, the rows that build.py puts into its page.
// Search engines cannot fetch the forecast themselves (Open-Meteo's robots.txt keeps them out),
// so without this they would see a page with no forecast on it.
import {readFileSync, writeFileSync} from 'node:fs';
import {forecastUrl, forecastHtml} from './src/page.js';

const cities = JSON.parse(readFileSync(new URL('cities.json', import.meta.url)));

// Fails after a second try, so that a build without a forecast stops and the pages already published stay up.
async function hourly(city, retries = 1) {
  const response = await fetch(forecastUrl(city)).catch(() => null);
  if (response?.ok) return (await response.json()).hourly;
  if (!retries) throw new Error(`No forecast for ${city.name}: ${response ? response.status : 'no answer'}`);
  await new Promise(resolve => setTimeout(resolve, 5000));
  return hourly(city, retries - 1);
}

const rows = {};
for (const city of cities) rows[city.name] = forecastHtml(await hourly(city), city);
writeFileSync(new URL('forecasts.json', import.meta.url), JSON.stringify(rows));
console.log(`Wrote forecasts for ${cities.length} cities`);
