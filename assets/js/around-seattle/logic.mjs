// Pure logic for the Around Seattle page. app.mjs does all DOM work; nothing here touches the DOM.
export const TIME_ZONE = "America/Los_Angeles";
export const SCHEMA_VERSION = 1;
export const STALE_AFTER_HOURS = 36;
export const NEAR_DAYS = 14;
export const CATEGORY_LABELS = Object.freeze({
  festival: "Festivals & fairs",
  music: "Music & stage",
  market: "Markets & food",
  outdoors: "Outdoors",
  arts: "Arts & ideas",
  other: "Community",
});
export const FILTER_TYPES = Object.freeze(["festival", "music", "market", "outdoors", "arts"]);
export const CONDITIONS = Object.freeze(["clear", "partly", "mostly-cloudy", "cloudy", "fog", "smoke", "rain", "snow",
  "storm"]);
export const LIMITS = Object.freeze({ today: 5, weekendDay: 4, comingDay: 3, weekList: 50 });

const HOUR_MS = 3_600_000;
const DAY_MS = 24 * HOUR_MS;
const WEEKDAYS_SHORT = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const WEEKDAYS_LONG = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];
const MONTHS_SHORT = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const MONTHS_LONG = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
  "October", "November", "December"];
const MOUNTAIN_OUT = new Set(["clear", "partly"]);
const MOUNTAIN_PEEK = new Set(["mostly-cloudy"]);

const partsFormat = new Intl.DateTimeFormat("en-US", {
  timeZone: TIME_ZONE, year: "numeric", month: "numeric", day: "numeric", hour: "numeric", minute: "numeric",
  hourCycle: "h23",
});
const pad = (value) => String(value).padStart(2, "0");

export function laParts(date) {
  const parts = {};
  for (const { type, value } of partsFormat.formatToParts(date)) parts[type] = value;
  return { year: Number(parts.year), month: Number(parts.month), day: Number(parts.day),
    hour: Number(parts.hour) % 24, minute: Number(parts.minute) };
}

export function dayKey(date) {
  const { year, month, day } = laParts(date);
  return `${year}-${pad(month)}-${pad(day)}`;
}

function keyToUtc(key) {
  const [year, month, day] = key.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, day));
}

export function addDays(key, days) {
  const date = keyToUtc(key);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

export function weekday(key) {
  return keyToUtc(key).getUTCDay();
}

export function effectiveEnd(event) {
  if (event.end) return event.end;
  return new Date(event.start.getTime() + (event.allDay ? DAY_MS : 2 * HOUR_MS));
}

function lastDayKey(event) {
  return dayKey(new Date(effectiveEnd(event).getTime() - 1));
}

export function coversDay(event, key) {
  return dayKey(event.start) <= key && key <= lastDayKey(event);
}

function daysBetween(fromKey, toKey) {
  return Math.round((keyToUtc(toKey) - keyToUtc(fromKey)) / DAY_MS);
}

// The instant a Pacific day starts: 07:00 UTC in daylight time, 08:00 UTC in standard time. Clocks change at 2 am,
// so exactly one of the two is midnight on that day.
function localMidnight(key) {
  const base = keyToUtc(key).getTime();
  return [7, 8].map((hours) => new Date(base + hours * HOUR_MS))
    .find((instant) => dayKey(instant) === key && laParts(instant).hour === 0);
}

// A repeat keeps the first occurrence's length. All-day repeats count whole days from local midnight, because a
// fixed length in hours ends an hour early or late on a DST day.
function repeatEnd(event, start) {
  if (!event.end) return null;
  if (!event.allDay) return new Date(start.getTime() + (event.end - event.start));
  const days = daysBetween(dayKey(event.start), lastDayKey(event)) + 1;
  return localMidnight(addDays(dayKey(start), days));
}

// The pipeline folds a series' later sessions and weeks into moreDates. Once the listed occurrence ends, the next one
// that has not ended takes its place, so the series stays on the page until its last date.
export function rollForward(event, now) {
  if (effectiveEnd(event) > now) return event;
  const dates = event.moreDates ?? [];
  for (const [index, start] of dates.entries()) {
    const next = Object.freeze({ ...event, start, end: repeatEnd(event, start),
      moreDates: Object.freeze(dates.slice(index + 1)) });
    if (effectiveEnd(next) > now) return next;
  }
  return null;
}

export function parseData(raw) {
  const generatedAt = new Date(typeof raw?.generatedAt === "string" ? raw.generatedAt : Number.NaN);
  const valid = raw && raw.schemaVersion === SCHEMA_VERSION && Array.isArray(raw.events)
    && !Number.isNaN(generatedAt.getTime());
  if (!valid) {
    throw new Error("Unsupported data format");
  }
  const toDate = (value) => (value ? new Date(value) : null);
  const events = raw.events
    .map((event) => Object.freeze({
      ...event,
      start: new Date(event.start),
      end: toDate(event.end),
      moreDates: Object.freeze((event.moreDates ?? []).map((value) => new Date(value))),
    }))
    .filter((event) => !Number.isNaN(event.start.getTime()));
  return Object.freeze({
    generatedAt,
    events: Object.freeze(events),
    sources: Object.freeze(raw.sources ?? []),
    weather: raw.weather ?? null,
    sun: raw.sun ?? {},
    seasonal: Object.freeze(raw.seasonal ?? []),
  });
}

const byRank = (a, b) => b.score - a.score || a.start - b.start || a.title.localeCompare(b.title);

export function weekendPlan(todayKey) {
  const day = weekday(todayKey);
  if (day === 6) return { label: "Tomorrow", keys: [addDays(todayKey, 1)] };
  if (day === 0) return { label: "Next weekend", keys: [addDays(todayKey, 6), addDays(todayKey, 7)] };
  const saturday = addDays(todayKey, 6 - day);
  return { label: "This weekend", keys: [saturday, addDays(saturday, 1)] };
}

export function mondayOf(key) {
  return addDays(key, -((weekday(key) + 6) % 7));
}

export function planSections(events, now, nearDays = NEAR_DAYS) {
  const todayKey = dayKey(now);
  const nearEndKey = addDays(todayKey, nearDays);
  const upcoming = events.map((event) => rollForward(event, now)).filter(Boolean);
  const running = upcoming.filter((event) => event.ongoing && dayKey(event.start) <= todayKey).sort(byRank);
  const runningIds = new Set(running.map((event) => event.id));
  const dated = upcoming.filter((event) => !runningIds.has(event.id));
  const used = new Set();
  const take = (key) => {
    const list = dated.filter((event) => !used.has(event.id) && coversDay(event, key)).sort(byRank);
    list.forEach((event) => used.add(event.id));
    return list;
  };
  const today = take(todayKey);
  const weekendInfo = weekendPlan(todayKey);
  const weekend = weekendInfo.keys.map((key) => ({ key, events: take(key) }));
  const comingUp = [];
  for (let offset = 1; offset <= nearDays; offset += 1) {
    const key = addDays(todayKey, offset);
    if (weekendInfo.keys.includes(key)) continue;
    const list = take(key);
    if (list.length) comingUp.push({ key, events: list });
  }
  const weeks = new Map();
  dated
    .filter((event) => !used.has(event.id) && dayKey(event.start) > nearEndKey)
    .sort((a, b) => a.start - b.start || byRank(a, b))
    .forEach((event) => {
      const monday = mondayOf(dayKey(event.start));
      weeks.set(monday, [...(weeks.get(monday) ?? []), event]);
    });
  const furtherAhead = [...weeks].map(([key, list]) => ({ key, events: list }));
  return { todayKey, today, weekendLabel: weekendInfo.label, weekend, comingUp, furtherAhead, running };
}

export function matchesFilters(item, filters = {}) {
  const { region = "all", types = [], freeOnly = false } = filters;
  if (region !== "all" && item.region !== region) return false;
  if (types.length > 0 && !types.includes(item.category)) return false;
  if (freeOnly && item.free !== true) return false;
  return true;
}

export function whenPhrase(key, todayKey) {
  if (key === todayKey) return "today";
  if (key === addDays(todayKey, 1)) return "tomorrow";
  return `on ${WEEKDAYS_LONG[weekday(key)]}`;
}

export function skyState(periods, now) {
  const period = (periods ?? []).find((item) => item.isDaytime && new Date(item.end) > now);
  if (!period) return { state: "unknown", period: null, when: null, dayKey: null };
  const key = dayKey(new Date(period.start));
  const state = MOUNTAIN_OUT.has(period.condition) ? "out" : MOUNTAIN_PEEK.has(period.condition) ? "peek" : "hiding";
  return { state, period, when: whenPhrase(key, dayKey(now)), dayKey: key };
}

export function headline(sky) {
  if (sky.state === "out") return `The mountain should be out ${sky.when}.`;
  if (sky.state === "peek") return `The mountain might peek out ${sky.when}.`;
  if (sky.state === "hiding") return `The mountain's hiding ${sky.when}.`;
  return "What's on around Seattle";
}

export function forecastLine(period) {
  return period ? `${period.temperature}°, ${period.shortForecast.toLowerCase()}.` : "";
}

export function sunsetLine(sun, key) {
  const value = key ? sun?.[key]?.sunset : null;
  return value ? `Sunset at ${formatTime(new Date(value))}.` : "";
}

export function weekStrip(periods, now) {
  return (periods ?? []).filter((item) => item.isDaytime && new Date(item.end) > now).slice(0, 7).map((item) => {
    const key = dayKey(new Date(item.start));
    const day = weekday(key);
    return { key, label: WEEKDAYS_SHORT[day], temperature: item.temperature, condition: item.condition,
      text: `${WEEKDAYS_LONG[day]}: ${item.temperature}°, ${item.shortForecast.toLowerCase()}` };
  });
}

export function formatTime(date) {
  const { hour, minute } = laParts(date);
  const suffix = hour < 12 ? "am" : "pm";
  const twelve = hour % 12 || 12;
  return minute === 0 ? `${twelve} ${suffix}` : `${twelve}:${pad(minute)} ${suffix}`;
}

export function formatShortDate(key) {
  const [, month, day] = key.split("-").map(Number);
  return `${MONTHS_SHORT[month - 1]} ${day}`;
}

export function formatMonthDay(key) {
  const [, month, day] = key.split("-").map(Number);
  return `${MONTHS_LONG[month - 1]} ${day}`;
}

export function formatLongDate(key) {
  return `${WEEKDAYS_LONG[weekday(key)]}, ${formatMonthDay(key)}`;
}

export function dayGutter(key) {
  return { weekday: WEEKDAYS_SHORT[weekday(key)], date: formatShortDate(key) };
}

export function formatWhen(event) {
  const firstKey = dayKey(event.start);
  const lastKey = lastDayKey(event);
  if (event.allDay) return firstKey === lastKey ? "All day" : `${formatShortDate(firstKey)} to ${formatShortDate(lastKey)}`;
  if (event.end && firstKey !== lastKey) return `${formatShortDate(firstKey)} to ${formatShortDate(lastKey)}`;
  const start = formatTime(event.start);
  return event.end ? `${start} to ${formatTime(event.end)}` : start;
}

export function formatDated(event) {
  const firstKey = dayKey(event.start);
  if ((event.allDay || event.end) && firstKey !== lastDayKey(event)) return formatWhen(event);
  const date = `${WEEKDAYS_SHORT[weekday(firstKey)]}, ${formatShortDate(firstKey)}`;
  return event.allDay ? date : `${date}, ${formatWhen(event)}`;
}

export function formatUntil(event) {
  return `Through ${formatShortDate(lastDayKey(event))}`;
}

export function formatSeasonWhen(pick) {
  return `Through ${formatShortDate(pick.until)} at ${pick.place}`;
}

export function formatList(items) {
  if (items.length <= 1) return items.join("");
  if (items.length === 2) return `${items[0]} and ${items[1]}`;
  return `${items.slice(0, -1).join(", ")}, and ${items[items.length - 1]}`;
}

export function formatMoreDates(event) {
  if (!event.moreDates?.length) return "";
  const startKey = dayKey(event.start);
  const labels = event.moreDates.map((date) => (dayKey(date) === startKey ? formatTime(date) : formatShortDate(dayKey(date))));
  return `Also ${formatList([...new Set(labels)])}`;
}

export function formatWhere(item) {
  const venue = item.venue?.trim();
  const city = item.city?.trim();
  if (venue && city && !venue.toLowerCase().includes(city.toLowerCase())) return `at ${venue}, ${city}`;
  if (venue) return `at ${venue}`;
  return city ? `in ${city}` : "";
}

export function formatKind(item) {
  const label = CATEGORY_LABELS[item.category] ?? CATEGORY_LABELS.other;
  if (item.free === true) return `${label}, free`;
  return item.price ? `${label}, ${item.price}` : label;
}

export function safeUrl(value) {
  if (typeof value !== "string" || !value) return null;
  try {
    const url = new URL(value);
    return url.protocol === "https:" || url.protocol === "http:" ? url.href : null;
  } catch {
    return null;
  }
}

export function isStale(generatedAt, now, hours = STALE_AFTER_HOURS) {
  if (!(generatedAt instanceof Date) || Number.isNaN(generatedAt.getTime())) return true;
  return now - generatedAt > hours * HOUR_MS;
}

export function freshnessLine(data, now) {
  const count = data.sources.filter((source) => source.status === "ok").length;
  const generatedKey = dayKey(data.generatedAt);
  const when = generatedKey === dayKey(now) ? `at ${formatTime(data.generatedAt)}` : `on ${formatLongDate(generatedKey)}`;
  return `Updated ${when} from ${count} ${count === 1 ? "calendar" : "calendars"}.`;
}

export function failedLine(data) {
  const failed = data.sources.filter((source) => source.status === "error").map((source) => source.name);
  return failed.length ? `${formatList(failed)} didn't respond this morning.` : "";
}

export function staleLine(generatedAt) {
  return `These events were last updated on ${formatLongDate(dayKey(generatedAt))}, so some details may have changed.`;
}

export function resolveDataUrls(location, dataset, now = new Date()) {
  const isLocal = location.hostname === "localhost" || location.hostname === "127.0.0.1";
  const override = new URLSearchParams(location.search).get("data");
  if (isLocal && override) {
    try {
      const url = new URL(override, location.href);
      if (url.origin === location.origin) return [url.href];
    } catch {
      // A malformed override falls back to the published data below.
    }
  }
  const cacheKey = `v=${dayKey(now)}T${pad(laParts(now).hour)}`;
  return [dataset.src, dataset.fallbackSrc].filter(Boolean)
    .map((url) => `${url}${url.includes("?") ? "&" : "?"}${cacheKey}`);
}
