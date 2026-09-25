import assert from "node:assert/strict";
import { test } from "node:test";

import * as L from "../../assets/js/around-seattle/logic.mjs";

const at = (iso) => new Date(iso);
const ev = (overrides = {}) => ({
  id: "e1", title: "Event", start: at("2026-09-26T11:00:00-07:00"), end: at("2026-09-26T16:00:00-07:00"),
  allDay: false, venue: "Seattle Center", city: "Seattle", region: "seattle", category: "festival", free: true,
  price: "Free", url: "https://example.org/", summary: null, source: "t", score: 50, moreDates: [], ongoing: false,
  ...overrides,
});
const period = (overrides = {}) => ({
  name: "Friday", start: "2026-09-25T06:00:00-07:00", end: "2026-09-25T18:00:00-07:00", isDaytime: true,
  temperature: 62, unit: "F", shortForecast: "Mostly Sunny", condition: "partly", precipChance: 0, ...overrides,
});

test("dayKey and laParts use Pacific time", () => {
  assert.equal(L.dayKey(at("2026-09-26T06:30:00Z")), "2026-09-25");
  assert.equal(L.dayKey(at("2026-09-26T07:30:00Z")), "2026-09-26");
  assert.deepEqual(L.laParts(at("2026-09-26T07:05:00Z")), { year: 2026, month: 9, day: 26, hour: 0, minute: 5 });
});

test("addDays and weekday cross month and DST boundaries", () => {
  assert.equal(L.addDays("2026-09-30", 1), "2026-10-01");
  assert.equal(L.addDays("2026-11-01", 1), "2026-11-02");
  assert.equal(L.addDays("2026-03-07", 2), "2026-03-09");
  assert.equal(L.addDays("2026-01-01", -1), "2025-12-31");
  assert.equal(L.weekday("2026-09-26"), 6);
  assert.equal(L.weekday("2026-09-27"), 0);
});

test("effectiveEnd and coversDay", () => {
  assert.equal(L.effectiveEnd(ev({ end: null })).toISOString(), "2026-09-26T20:00:00.000Z");
  const fest = ev({ start: at("2026-10-03T00:00:00-07:00"), end: at("2026-10-05T00:00:00-07:00"), allDay: true });
  assert.ok(L.coversDay(fest, "2026-10-03"));
  assert.ok(L.coversDay(fest, "2026-10-04"));
  assert.ok(!L.coversDay(fest, "2026-10-05"));
  assert.ok(!L.coversDay(fest, "2026-10-02"));
});

test("parseData converts dates and rejects other versions", () => {
  assert.throws(() => L.parseData({ schemaVersion: 2, events: [] }));
  assert.throws(() => L.parseData(null));
  const data = L.parseData({
    schemaVersion: 1, generatedAt: "2026-09-25T13:17:00Z", sources: [], weather: null, sun: {}, seasonal: [],
    events: [
      { ...ev(), start: "2026-09-26T11:00:00-07:00", end: null, moreDates: ["2026-10-03T11:00:00-07:00"] },
      { ...ev({ id: "bad" }), start: "not a date", end: null, moreDates: [] },
    ],
  });
  assert.equal(data.events.length, 1);
  assert.ok(data.events[0].start instanceof Date);
  assert.equal(data.events[0].end, null);
  assert.ok(data.events[0].moreDates[0] instanceof Date);
  assert.ok(Object.isFrozen(data));
});

test("parseData rejects a missing or invalid generatedAt", () => {
  const base = { schemaVersion: 1, sources: [], weather: null, sun: {}, seasonal: [], events: [] };
  assert.throws(() => L.parseData(base), /Unsupported data format/);
  assert.throws(() => L.parseData({ ...base, generatedAt: null }), /Unsupported data format/);
  assert.throws(() => L.parseData({ ...base, generatedAt: "not a date" }), /Unsupported data format/);
  assert.equal(L.parseData({ ...base, generatedAt: "2026-09-25T13:17:00Z" }).generatedAt.toISOString(),
    "2026-09-25T13:17:00.000Z");
});

test("weekendPlan for weekdays, Saturday, and Sunday", () => {
  assert.deepEqual(L.weekendPlan("2026-09-25"), { label: "This weekend", keys: ["2026-09-26", "2026-09-27"] });
  assert.deepEqual(L.weekendPlan("2026-09-22"), { label: "This weekend", keys: ["2026-09-26", "2026-09-27"] });
  assert.deepEqual(L.weekendPlan("2026-09-26"), { label: "Tomorrow", keys: ["2026-09-27"] });
  assert.deepEqual(L.weekendPlan("2026-09-27"), { label: "Next weekend", keys: ["2026-10-03", "2026-10-04"] });
  assert.equal(L.mondayOf("2026-10-20"), "2026-10-19");
  assert.equal(L.mondayOf("2026-10-19"), "2026-10-19");
  assert.equal(L.mondayOf("2026-10-25"), "2026-10-19");
});

test("planSections places each event once, in page order", () => {
  const now = at("2026-09-23T09:00:00-07:00"); // Wednesday
  const events = [
    ev({ id: "today", start: at("2026-09-23T19:00:00-07:00"), end: null }),
    ev({ id: "thu", start: at("2026-09-24T19:00:00-07:00"), end: null }),
    ev({ id: "fri-sun", start: at("2026-09-25T00:00:00-07:00"), end: at("2026-09-28T00:00:00-07:00"), allDay: true }),
    ev({ id: "sat", start: at("2026-09-26T10:00:00-07:00"), end: null }),
    ev({ id: "next-wed", start: at("2026-09-30T18:00:00-07:00"), end: null }),
    ev({ id: "far", start: at("2026-10-20T18:00:00-07:00"), end: null }),
    ev({ id: "past", start: at("2026-09-22T18:00:00-07:00"), end: at("2026-09-22T20:00:00-07:00") }),
    ev({ id: "running", start: at("2026-09-01T00:00:00-07:00"), end: at("2026-10-31T00:00:00-07:00"),
         allDay: true, ongoing: true }),
    ev({ id: "later-run", start: at("2026-10-01T00:00:00-07:00"), end: at("2026-10-31T00:00:00-07:00"),
         allDay: true, ongoing: true }),
  ];
  const plan = L.planSections(events, now);
  assert.equal(plan.todayKey, "2026-09-23");
  assert.deepEqual(plan.today.map((e) => e.id), ["today"]);
  assert.equal(plan.weekendLabel, "This weekend");
  assert.deepEqual(plan.weekend.map((d) => [d.key, d.events.map((e) => e.id)]),
    [["2026-09-26", ["fri-sun", "sat"]], ["2026-09-27", []]]);
  assert.deepEqual(plan.comingUp.map((d) => [d.key, d.events.map((e) => e.id)]),
    [["2026-09-24", ["thu"]], ["2026-09-30", ["next-wed"]], ["2026-10-01", ["later-run"]]]);
  assert.deepEqual(plan.furtherAhead.map((w) => [w.key, w.events.map((e) => e.id)]), [["2026-10-19", ["far"]]]);
  assert.deepEqual(plan.running.map((e) => e.id), ["running"]);
});

test("planSections ranks by score, then start", () => {
  const now = at("2026-09-26T08:00:00-07:00");
  const plan = L.planSections([
    ev({ id: "low", score: 40, start: at("2026-09-26T09:00:00-07:00"), end: null }),
    ev({ id: "high", score: 70, start: at("2026-09-26T15:00:00-07:00"), end: null }),
    ev({ id: "tie-early", score: 40, start: at("2026-09-26T08:30:00-07:00"), end: null }),
  ], now);
  assert.deepEqual(plan.today.map((e) => e.id), ["high", "tie-early", "low"]);
});

test("rollForward returns an unended event unchanged", () => {
  const event = ev({ moreDates: [at("2026-10-03T11:00:00-07:00")] });
  assert.equal(L.rollForward(event, at("2026-09-26T15:00:00-07:00")), event);
});

test("rollForward moves to a later session the same day once the first has ended", () => {
  const now = at("2026-09-26T14:00:00-07:00");
  const event = ev({ id: "sessions", start: at("2026-09-26T11:00:00-07:00"), end: at("2026-09-26T13:00:00-07:00"),
    moreDates: [at("2026-09-26T17:00:00-07:00")] });
  assert.equal(L.formatMoreDates(event), "Also 5 pm");
  const next = L.rollForward(event, now);
  assert.equal(next.start.toISOString(), at("2026-09-26T17:00:00-07:00").toISOString());
  assert.equal(next.end.toISOString(), at("2026-09-26T19:00:00-07:00").toISOString());
  assert.deepEqual(next.moreDates, []);
  assert.ok(Object.isFrozen(next) && Object.isFrozen(next.moreDates));
  assert.equal(event.start.toISOString(), at("2026-09-26T11:00:00-07:00").toISOString());
  const plan = L.planSections([event], now);
  assert.deepEqual(plan.today.map((e) => [e.id, L.formatWhen(e)]), [["sessions", "5 pm to 7 pm"]]);
});

test("rollForward moves a weekly series past its first date", () => {
  const now = at("2026-09-23T09:00:00-07:00"); // Wednesday
  const event = ev({ id: "weekly", start: at("2026-09-19T18:00:00-07:00"), end: at("2026-09-19T20:00:00-07:00"),
    moreDates: [at("2026-09-26T18:00:00-07:00"), at("2026-10-03T18:00:00-07:00"), at("2026-10-10T18:00:00-07:00")] });
  const next = L.rollForward(event, now);
  assert.equal(next.start.toISOString(), at("2026-09-26T18:00:00-07:00").toISOString());
  assert.equal(next.end.toISOString(), at("2026-09-26T20:00:00-07:00").toISOString());
  assert.equal(L.formatMoreDates(next), "Also Oct 3 and Oct 10");
  assert.equal(L.rollForward({ ...event, end: null }, now).end, null);
  const plan = L.planSections([event], now);
  assert.deepEqual(plan.weekend.map((d) => [d.key, d.events.map((e) => e.id)]),
    [["2026-09-26", ["weekly"]], ["2026-09-27", []]]);
});

test("rollForward ends an all-day repeat at local midnight across the fall DST change", () => {
  // Sundays: Oct 25 (daylight time), Nov 1 (clocks fall back at 2 am), Nov 8 (standard time).
  const sundays = ev({ allDay: true, start: at("2026-10-25T00:00:00-07:00"), end: at("2026-10-26T00:00:00-07:00"),
    moreDates: [at("2026-11-01T00:00:00-07:00"), at("2026-11-08T00:00:00-08:00")] });
  const next = L.rollForward(sundays, at("2026-10-31T12:00:00-07:00"));
  assert.equal(next.start.toISOString(), at("2026-11-01T00:00:00-07:00").toISOString());
  assert.equal(next.end.toISOString(), at("2026-11-02T00:00:00-08:00").toISOString());
  assert.deepEqual(next.moreDates.map((d) => d.toISOString()), [at("2026-11-08T00:00:00-08:00").toISOString()]);
  // Late on Nov 1 that day is still on; a fixed 24-hour length would have ended it at 11 pm.
  const late = L.rollForward(sundays, at("2026-11-01T23:30:00-08:00"));
  assert.equal(late.start.toISOString(), next.start.toISOString());
  // A two-day weekend keeps its length in days: Oct 31 to Nov 1 ends at midnight after Nov 1.
  const weekend = ev({ allDay: true, start: at("2026-10-24T00:00:00-07:00"), end: at("2026-10-26T00:00:00-07:00"),
    moreDates: [at("2026-10-31T00:00:00-07:00")] });
  const rolled = L.rollForward(weekend, at("2026-10-27T12:00:00-07:00"));
  assert.equal(rolled.end.toISOString(), at("2026-11-02T00:00:00-08:00").toISOString());
  assert.equal(L.formatWhen(rolled), "Oct 31 to Nov 1");
});

test("rollForward drops an event with no date left, and planSections leaves it out", () => {
  const now = at("2026-09-30T12:00:00-07:00");
  const over = ev({ id: "over", start: at("2026-09-19T18:00:00-07:00"), end: at("2026-09-19T20:00:00-07:00"),
    moreDates: [at("2026-09-26T18:00:00-07:00")] });
  const once = ev({ id: "once", start: at("2026-09-29T18:00:00-07:00"), end: null });
  assert.equal(L.rollForward(over, now), null);
  assert.equal(L.rollForward(once, now), null);
  const plan = L.planSections([over, once], now);
  const placed = [...plan.today, ...plan.running, ...[...plan.weekend, ...plan.comingUp, ...plan.furtherAhead]
    .flatMap((day) => day.events)];
  assert.deepEqual(placed, []);
});

test("matchesFilters by region, types, and free", () => {
  const item = ev({ region: "eastside", category: "music", free: false });
  assert.ok(L.matchesFilters(item, { region: "all", types: [], freeOnly: false }));
  assert.ok(L.matchesFilters(item, { region: "eastside", types: ["music"], freeOnly: false }));
  assert.ok(!L.matchesFilters(item, { region: "seattle", types: [], freeOnly: false }));
  assert.ok(!L.matchesFilters(item, { region: "all", types: ["festival"], freeOnly: false }));
  assert.ok(!L.matchesFilters(item, { region: "all", types: [], freeOnly: true }));
  assert.ok(L.matchesFilters(item));
});

test("skyState picks the next daytime period and maps conditions", () => {
  const periods = [
    period({ name: "Tonight", isDaytime: false, start: "2026-09-24T18:00:00-07:00", end: "2026-09-25T06:00:00-07:00" }),
    period({ condition: "partly" }),
    period({ name: "Saturday", start: "2026-09-26T06:00:00-07:00", end: "2026-09-26T18:00:00-07:00",
             condition: "mostly-cloudy" }),
    period({ name: "Sunday", start: "2026-09-27T06:00:00-07:00", end: "2026-09-27T18:00:00-07:00",
             condition: "rain" }),
  ];
  const morning = L.skyState(periods, at("2026-09-25T05:00:00-07:00"));
  assert.deepEqual([morning.state, morning.when, morning.dayKey], ["out", "today", "2026-09-25"]);
  const evening = L.skyState(periods, at("2026-09-25T19:00:00-07:00"));
  assert.deepEqual([evening.state, evening.when], ["peek", "tomorrow"]);
  const later = L.skyState(periods.slice(3), at("2026-09-25T19:00:00-07:00"));
  assert.deepEqual([later.state, later.when], ["hiding", "on Sunday"]);
  assert.equal(L.skyState(null, at("2026-09-25T05:00:00-07:00")).state, "unknown");
});

test("headline, forecast, sunset, and week strip copy", () => {
  assert.equal(L.headline({ state: "out", when: "today" }), "The mountain should be out today.");
  assert.equal(L.headline({ state: "peek", when: "tomorrow" }), "The mountain might peek out tomorrow.");
  assert.equal(L.headline({ state: "hiding", when: "on Sunday" }), "The mountain's hiding on Sunday.");
  assert.equal(L.headline({ state: "unknown" }), "What's on around Seattle");
  assert.equal(L.forecastLine(period()), "62°, mostly sunny.");
  assert.equal(L.forecastLine(null), "");
  assert.equal(L.sunsetLine({ "2026-09-25": { sunset: "2026-09-25T19:01:00-07:00" } }, "2026-09-25"),
    "Sunset at 7:01 pm.");
  assert.equal(L.sunsetLine({}, "2026-09-25"), "");
  const strip = L.weekStrip([period({ isDaytime: false }), period(),
    period({ start: "2026-09-26T06:00:00-07:00", end: "2026-09-26T18:00:00-07:00" })], at("2026-09-25T05:00:00-07:00"));
  assert.deepEqual(strip.map((d) => d.label), ["Fri", "Sat"]);
  assert.equal(strip[0].text, "Friday: 62°, mostly sunny");
});

test("weekStrip leaves out daytime periods that have ended, then takes seven days", () => {
  const keys = ["2026-09-25", "2026-09-26", "2026-09-27", "2026-09-28", "2026-09-29", "2026-09-30", "2026-10-01",
    "2026-10-02"];
  const periods = keys.map((key) => period({ start: `${key}T06:00:00-07:00`, end: `${key}T18:00:00-07:00` }));
  assert.deepEqual(L.weekStrip(periods, at("2026-09-25T09:00:00-07:00")).map((d) => d.key), keys.slice(0, 7));
  const evening = L.weekStrip(periods, at("2026-09-25T19:00:00-07:00"));
  assert.deepEqual(evening.map((d) => d.key), keys.slice(1));
  assert.deepEqual(evening.map((d) => d.label), ["Sat", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri"]);
});

test("time and date formatting", () => {
  assert.equal(L.formatTime(at("2026-09-25T19:30:00-07:00")), "7:30 pm");
  assert.equal(L.formatTime(at("2026-09-25T11:00:00-07:00")), "11 am");
  assert.equal(L.formatTime(at("2026-09-25T12:00:00-07:00")), "12 pm");
  assert.equal(L.formatTime(at("2026-09-25T00:00:00-07:00")), "12 am");
  assert.equal(L.formatShortDate("2026-10-03"), "Oct 3");
  assert.equal(L.formatLongDate("2026-09-26"), "Saturday, September 26");
  assert.equal(L.formatMonthDay("2026-10-12"), "October 12");
  assert.deepEqual(L.dayGutter("2026-09-26"), { weekday: "Sat", date: "Sep 26" });
});

test("formatWhen, formatDated, formatUntil, formatSeasonWhen", () => {
  assert.equal(L.formatWhen(ev()), "11 am to 4 pm");
  assert.equal(L.formatWhen(ev({ end: null, start: at("2026-09-26T19:30:00-07:00") })), "7:30 pm");
  const allDay = ev({ allDay: true, start: at("2026-09-26T00:00:00-07:00"), end: at("2026-09-27T00:00:00-07:00") });
  assert.equal(L.formatWhen(allDay), "All day");
  const weekend = ev({ allDay: true, start: at("2026-10-03T00:00:00-07:00"), end: at("2026-10-05T00:00:00-07:00") });
  assert.equal(L.formatWhen(weekend), "Oct 3 to Oct 4");
  const overnight = ev({ start: at("2026-10-03T20:00:00-07:00"), end: at("2026-10-04T02:00:00-07:00") });
  assert.equal(L.formatWhen(overnight), "Oct 3 to Oct 4");
  assert.equal(L.formatDated(ev({ start: at("2026-10-20T18:00:00-07:00"), end: null })), "Tue, Oct 20, 6 pm");
  assert.equal(L.formatDated(allDay), "Sat, Sep 26");
  assert.equal(L.formatDated(weekend), "Oct 3 to Oct 4");
  const running = ev({ allDay: true, start: at("2026-09-01T00:00:00-07:00"), end: at("2026-10-31T00:00:00-07:00") });
  assert.equal(L.formatUntil(running), "Through Oct 30");
  assert.equal(L.formatSeasonWhen({ until: "2026-11-15", place: "Kubota Garden" }), "Through Nov 15 at Kubota Garden");
});

test("lists, repeats, places, and kinds", () => {
  assert.equal(L.formatList(["a"]), "a");
  assert.equal(L.formatList(["a", "b"]), "a and b");
  assert.equal(L.formatList(["a", "b", "c"]), "a, b, and c");
  assert.equal(L.formatMoreDates(ev({ moreDates: [at("2026-10-02T11:00:00-07:00"), at("2026-10-09T11:00:00-07:00")] })),
    "Also Oct 2 and Oct 9");
  assert.equal(L.formatMoreDates(ev({ moreDates: [at("2026-09-26T14:00:00-07:00")] })), "Also 2 pm");
  assert.equal(L.formatMoreDates(ev()), "");
  assert.equal(L.formatWhere(ev()), "at Seattle Center");
  assert.equal(L.formatWhere(ev({ venue: "Remlinger Farms", city: "Carnation" })), "at Remlinger Farms, Carnation");
  assert.equal(L.formatWhere(ev({ venue: null, city: "Issaquah" })), "in Issaquah");
  assert.equal(L.formatWhere(ev({ venue: null, city: null })), "");
  assert.equal(L.formatKind(ev()), "Festivals & fairs, free");
  assert.equal(L.formatKind(ev({ category: "music", free: false, price: "$10 – $35" })), "Music & stage, $10 – $35");
  assert.equal(L.formatKind(ev({ category: "other", free: null, price: null })), "Community");
  assert.equal(L.formatKind(ev({ category: "unknown", free: null, price: null })), "Community");
});

test("safeUrl accepts only http and https", () => {
  assert.equal(L.safeUrl("https://example.org/a"), "https://example.org/a");
  assert.equal(L.safeUrl("http://example.org"), "http://example.org/");
  assert.equal(L.safeUrl("javascript:alert(1)"), null);
  assert.equal(L.safeUrl("/relative"), null);
  assert.equal(L.safeUrl(""), null);
  assert.equal(L.safeUrl(undefined), null);
});

test("freshness, failures, and staleness", () => {
  const data = { generatedAt: at("2026-09-25T13:17:00Z"),
    sources: [{ name: "City of Seattle", status: "ok" }, { name: "Town Hall Seattle", status: "ok" },
      { name: "City of Issaquah", status: "error" }, { name: "Ticketmaster", status: "skipped" }] };
  assert.equal(L.freshnessLine(data, at("2026-09-25T12:00:00-07:00")), "Updated at 6:17 am from 2 calendars.");
  assert.equal(L.freshnessLine(data, at("2026-09-26T12:00:00-07:00")),
    "Updated on Friday, September 25 from 2 calendars.");
  assert.equal(L.failedLine(data), "City of Issaquah didn't respond this morning.");
  assert.equal(L.failedLine({ sources: [] }), "");
  assert.ok(!L.isStale(data.generatedAt, at("2026-09-26T12:00:00-07:00")));
  assert.ok(L.isStale(data.generatedAt, at("2026-09-27T12:00:00-07:00")));
  assert.ok(L.isStale(new Date("invalid"), at("2026-09-25T12:00:00-07:00")));
  assert.equal(L.staleLine(data.generatedAt),
    "These events were last updated on Friday, September 25, so some details may have changed.");
});

test("resolveDataUrls adds a cache key and allows overrides only on localhost", () => {
  const dataset = { src: "https://raw.example/a.json", fallbackSrc: "https://cdn.example/a.json" };
  const now = at("2026-09-25T07:40:00-07:00");
  assert.deepEqual(L.resolveDataUrls(new URL("https://yiyangwan.github.io/around-seattle/"), dataset, now),
    ["https://raw.example/a.json?v=2026-09-25T07", "https://cdn.example/a.json?v=2026-09-25T07"]);
  assert.deepEqual(
    L.resolveDataUrls(new URL("http://localhost:4000/around-seattle/?data=/around-seattle/dev.json"), dataset, now),
    ["http://localhost:4000/around-seattle/dev.json"]);
  assert.deepEqual(
    L.resolveDataUrls(new URL("https://yiyangwan.github.io/around-seattle/?data=https://evil.example/x.json"), dataset, now),
    ["https://raw.example/a.json?v=2026-09-25T07", "https://cdn.example/a.json?v=2026-09-25T07"]);
  assert.deepEqual(
    L.resolveDataUrls(new URL("http://127.0.0.1:4000/around-seattle/?data=https://evil.example/x.json"), dataset, now),
    ["https://raw.example/a.json?v=2026-09-25T07", "https://cdn.example/a.json?v=2026-09-25T07"]);
});

test("resolveDataUrls falls back to production URLs on a malformed localhost override", () => {
  const dataset = { src: "https://raw.example/a.json", fallbackSrc: "https://cdn.example/a.json" };
  const now = at("2026-09-25T07:40:00-07:00");
  assert.deepEqual(L.resolveDataUrls(new URL("http://localhost:4000/around-seattle/?data=http://[bad"), dataset, now),
    ["https://raw.example/a.json?v=2026-09-25T07", "https://cdn.example/a.json?v=2026-09-25T07"]);
});
