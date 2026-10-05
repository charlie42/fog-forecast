// Whether the last mornings were fog mornings at an airport, from its reports in the archive of the Iowa State Mesonet.
// Read when the site is built, for the places whose formula takes in the morning before (those with a `station` in cities.json).
//
// A morning is counted as it was when the weights were fitted (fit/common.py). A report is fog if visibility is under 1 km,
// there is no rain, snow or drizzle in its weather codes, and the temperature is within 2 C of the dew point. A fog morning
// has such a report in two or more of the six clock hours 04 to 09. A morning with reports in fewer than five of them is not counted.
import {clockAt} from './src/model.js';

const FOG_MILES = 0.62;   // 1 km, as the archive stores visibility
const RAIN = /RA|SN|DZ|SG|PL|GR|GS|UP/;

// Reports of the last three days, timed by the clock at the place. Routine and special reports, as in the fit.
export function reportsUrl(station, tz, now = Date.now()) {
  const day = offset => new Date(now + offset * 864e5).toISOString().slice(0, 10).split('-').map(Number);
  const [year1, month1, day1] = day(-3), [year2, month2, day2] = day(2);
  return 'https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py?' + new URLSearchParams([
    ['station', station], ['data', 'vsby'], ['data', 'wxcodes'], ['data', 'tmpf'], ['data', 'dwpf'],
    ['year1', year1], ['month1', month1], ['day1', day1], ['year2', year2], ['month2', month2], ['day2', day2],
    ['tz', tz], ['format', 'onlycomma'], ['latlon', 'no'], ['missing', 'M'], ['trace', 'T'], ['direct', 'no'],
    ['report_type', 3], ['report_type', 4]]);
}

/**
 * @param csv  The archive's answer to `reportsUrl`: a line of column names, then one line per report.
 * @param tz   The time zone the reports were asked for in.
 * @param now  A morning is left out until it is 10 h at the place.
 * @returns    For each counted morning whether it was a fog morning, e.g. {"2026-01-09": true, "2026-01-10": false}.
 */
export function fogMornings(csv, tz, now = Date.now()) {
  const [names, ...reports] = csv.trim().split('\n').map(line => line.split(','));
  const column = Object.fromEntries(['valid', 'vsby', 'wxcodes', 'tmpf', 'dwpf'].map(name => [name, names.indexOf(name)]));
  if (Object.values(column).includes(-1)) throw new Error('not a list of reports');

  const days = {};   // date -> clock hour -> did a report in that hour show fog
  for (const report of reports) {
    const [date, time] = report[column.valid].split(' '), hour = Number(time.slice(0, 2));
    const miles = parseFloat(report[column.vsby]);   // "M" where the report has no visibility
    if (Number.isNaN(miles) || hour < 4 || hour > 9) continue;
    // The archive holds Fahrenheit. The airports report whole degrees C, so the gap is rounded to one.
    const humid = Math.round((parseFloat(report[column.tmpf]) - parseFloat(report[column.dwpf])) / 1.8) <= 2;
    const fog = miles < FOG_MILES && humid && !RAIN.test(report[column.wxcodes]);
    days[date] ??= {};
    days[date][hour] ||= fog;
  }

  const hourNow = clockAt(tz)(now);
  return Object.fromEntries(Object.entries(days)
    .filter(([date, hours]) => date + 'T10' <= hourNow && Object.keys(hours).length >= 5)
    .map(([date, hours]) => [date, Object.values(hours).filter(Boolean).length >= 2]));
}
