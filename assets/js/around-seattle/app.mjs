// Renders the Around Seattle page from the daily JSON. Every string from the data goes through textContent.
import {
  CATEGORY_LABELS, CONDITIONS, LIMITS, dayGutter, failedLine, forecastLine, formatDated, formatKind, formatMonthDay,
  formatMoreDates, formatSeasonWhen, formatUntil, formatWhen, formatWhere, freshnessLine, headline, isStale,
  matchesFilters, parseData, planSections, resolveDataUrls, safeUrl, skyState, staleLine, sunsetLine, weekStrip,
} from "./logic.mjs";

const FETCH_TIMEOUT_MS = 8000;
const SVG_NS = "http://www.w3.org/2000/svg";
const README_URL = "https://github.com/yiyangwan/yiyangwan.github.io/blob/main/around_seattle/README.md";
const NO_FILTERS = Object.freeze({ region: "all", types: Object.freeze([]), freeOnly: false });

const root = document.getElementById("around");
const form = document.getElementById("around-filters");
// The site loads MathJax 2 on every page, and it would typeset any "$...$" or backtick span in feed text as math
// (a price like "$25 – $50" turns into a formula, and TeX's \href can make links). These classes opt the page out.
// They are in place before any feed text is fetched or rendered, and MathJax skips an ignored subtree on every
// later typeset.
root.classList.add("tex2jax_ignore", "asciimath2jax_ignore");
const byId = (id) => document.getElementById(id);
let state = Object.freeze({ data: null, filters: NO_FILTERS, expanded: Object.freeze([]) });

function setState(changes) {
  state = Object.freeze({ ...state, ...changes });
  render();
}

function el(tag, props = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (value === null || value === undefined || value === false) continue;
    if (key === "text") node.textContent = String(value);
    else if (key === "className") node.className = value;
    else node.setAttribute(key, value === true ? "" : String(value));
  }
  for (const child of children) {
    if (child !== null && child !== undefined && child !== "") node.append(child);
  }
  return node;
}

function glyph(condition) {
  const svg = document.createElementNS(SVG_NS, "svg");
  svg.setAttribute("class", "around-wx");
  svg.setAttribute("aria-hidden", "true");
  svg.setAttribute("focusable", "false");
  const use = document.createElementNS(SVG_NS, "use");
  use.setAttribute("href", `#wx-${CONDITIONS.includes(condition) ? condition : "cloudy"}`);
  svg.append(use);
  return svg;
}

const categoryOf = (item) => (CATEGORY_LABELS[item.category] ? item.category : "other");
const isFiltered = (filters) => filters.region !== "all" || filters.types.length > 0 || filters.freeOnly;
const empty = (text) => el("p", { className: "around-empty", text });

function titleNode(level, title, url) {
  const safe = safeUrl(url);
  return el(`h${level}`, { className: "around-ev__title" },
    [safe ? el("a", { href: safe, rel: "noopener noreferrer", text: title }) : title]);
}

function eventItem(event, { level, when, featured = false, summary = "none" }) {
  const where = formatWhere(event);
  const whenText = when(event);
  const more = formatMoreDates(event);
  const showSummary = Boolean(event.summary) && (featured || summary === "line");
  return el("li", { className: `around-ev around-ev--${categoryOf(event)}${featured ? " around-ev--featured" : ""}` }, [
    titleNode(level, event.title, event.url),
    el("p", { className: "around-ev__when", text: where ? `${whenText} ${where}` : whenText }),
    el("p", { className: "around-ev__kind", text: formatKind(event) }),
    showSummary ? el("p", { className: `around-ev__summary${featured ? "" : " around-ev__summary--line"}`,
      text: event.summary }) : null,
    more ? el("p", { className: "around-ev__more", text: more }) : null,
  ]);
}

function seasonalItem(pick) {
  return el("li", { className: `around-ev around-ev--${categoryOf(pick)}` }, [
    titleNode(3, pick.title, pick.url),
    el("p", { className: "around-ev__when", text: formatSeasonWhen(pick) }),
    el("p", { className: "around-ev__kind", text: formatKind(pick) }),
    el("p", { className: "around-ev__summary around-ev__summary--two", text: pick.summary }),
  ]);
}

// Moving focus to the first revealed item keeps the reader's place; preventScroll keeps the page where it was.
function focusTitle(item) {
  const title = item?.querySelector(".around-ev__title");
  if (!title) return;
  const link = title.querySelector("a");
  if (!link) title.setAttribute("tabindex", "-1");
  (link ?? title).focus({ preventScroll: true });
}

// Screen readers announce every write to a live region, so write only when the text changes.
function setStatus(text) {
  const status = byId("around-status");
  if (status.textContent !== text) status.textContent = text;
}

function eventList(events, { id, limit, featuredFirst = false, ...itemOptions }) {
  const expanded = state.expanded.includes(id);
  const shown = expanded ? events : events.slice(0, limit);
  const list = el("ol", { className: "around-list", role: "list", id },
    shown.map((event, index) => eventItem(event, { ...itemOptions, featured: featuredFirst && index === 0 })));
  if (events.length <= limit) return [list];
  const button = el("button", {
    type: "button", className: "around-more", id: `${id}-more`, "aria-controls": id,
    "aria-expanded": String(expanded), text: expanded ? "Show fewer" : `Show ${events.length - limit} more`,
  });
  button.addEventListener("click", () => {
    if (expanded) {
      setState({ expanded: Object.freeze(state.expanded.filter((item) => item !== id)) });
      byId(`${id}-more`)?.focus();
      return;
    }
    setState({ expanded: Object.freeze([...state.expanded, id]) });
    focusTitle(byId(id)?.children[limit]);
  });
  return [list, button];
}

function dayBlock(day, limit, summary, emptyText) {
  const gutter = dayGutter(day.key);
  return el("div", { className: "around-day" }, [
    el("h3", { className: "around-day__head" }, [
      el("span", { className: "around-day__weekday", text: gutter.weekday }),
      el("span", { className: "around-day__date", text: gutter.date }),
    ]),
    el("div", { className: "around-day__body" }, day.events.length
      ? eventList(day.events, { id: `list-${day.key}`, limit, level: 4, when: formatWhen, summary })
      : [empty(emptyText)]),
  ]);
}

function fill(sectionId, nodes) {
  root.querySelector(`#${sectionId} .around-body`).replaceChildren(...nodes);
}

function renderHero(now) {
  const { data, filters } = state;
  const periods = data?.weather?.[filters.region === "eastside" ? "eastside" : "seattle"]?.periods ?? null;
  const sky = skyState(periods, now);
  root.querySelector(".around-hero").dataset.sky = sky.state;
  byId("around-headline").textContent = headline(sky);
  const lines = [forecastLine(sky.period), sunsetLine(data?.sun, sky.dayKey)].filter(Boolean);
  const forecast = byId("around-forecast");
  forecast.replaceChildren(...lines.map((line) => el("span", { text: line })));
  forecast.hidden = lines.length === 0;
  const days = weekStrip(periods, now);
  const week = byId("around-week");
  week.replaceChildren(...days.map((day) => el("li", { className: "around-week__day" }, [
    el("span", { className: "around-week__name", text: day.label, "aria-hidden": "true" }),
    glyph(day.condition),
    el("span", { className: "around-week__temp", "aria-hidden": "true" }, [
      el("span", { text: `${day.celsius}°C` }),
      el("span", { text: `${day.fahrenheit}°F` }),
    ]),
    el("span", { className: "around-sr", text: day.text }),
  ])));
  week.hidden = days.length === 0;
}

function renderSections(now) {
  const { data, filters } = state;
  const plan = planSections(data.events.filter((event) => matchesFilters(event, filters)), now);
  const seasonal = data.seasonal.filter((pick) => matchesFilters(pick, filters));
  const none = isFiltered(filters) ? "Nothing here matches your filters." : "Nothing listed yet.";

  fill("around-today", plan.today.length
    ? eventList(plan.today, { id: "list-today", limit: LIMITS.today, level: 3, when: formatWhen, summary: "line",
      featuredFirst: true })
    : [empty(none)]);
  byId("around-weekend-h").textContent = plan.weekendLabel;
  fill("around-weekend", plan.weekend.map((day) => dayBlock(day, LIMITS.weekendDay, "line", none)));
  fill("around-coming", plan.comingUp.length
    ? plan.comingUp.map((day) => dayBlock(day, LIMITS.comingDay, "none", none))
    : [empty(none)]);
  fill("around-further", plan.furtherAhead.length
    ? plan.furtherAhead.map((week) => el("div", { className: "around-weekblock" }, [
      el("h3", { className: "around-weekblock__head", text: `Week of ${formatMonthDay(week.key)}` }),
      ...eventList(week.events, { id: `list-week-${week.key}`, limit: LIMITS.weekList, level: 4, when: formatDated }),
    ]))
    : [empty(isFiltered(filters) ? none : "Nothing announced yet.")]);
  const seasonItems = [...seasonal.map(seasonalItem),
    ...plan.running.map((event) => eventItem(event, { level: 3, when: formatUntil, summary: "line" }))];
  fill("around-season", seasonItems.length
    ? [el("ol", { className: "around-list", role: "list" }, seasonItems)]
    : [empty(none)]);

  const countDays = (days) => days.reduce((total, day) => total + day.events.length, 0);
  return plan.today.length + countDays(plan.weekend) + countDays(plan.comingUp) + countDays(plan.furtherAhead)
    + seasonItems.length;
}

function clearFilters() {
  form.reset();
  setState({ filters: NO_FILTERS, expanded: Object.freeze([]) });
  // The button that had focus is gone after the render, so hand focus back to the start of the filters.
  form.querySelector("input")?.focus();
}

function renderNotice(count, now) {
  const { data, filters } = state;
  const parts = [];
  if (isStale(data.generatedAt, now)) parts.push(el("p", { text: staleLine(data.generatedAt) }));
  if (count === 0 && isFiltered(filters)) {
    const button = el("button", { type: "button", className: "around-more", text: "Clear filters" });
    button.addEventListener("click", clearFilters);
    parts.push(el("p", {}, ["No events match these filters. ", button]));
  }
  const notice = byId("around-notice");
  notice.replaceChildren(...parts);
  notice.hidden = parts.length === 0;
}

function renderFooter(now) {
  const { data } = state;
  const lines = [freshnessLine(data, now), failedLine(data),
    "Each event links to its organizer's page; check details there before you go."].filter(Boolean);
  byId("around-footer").replaceChildren(...lines.map((line) => el("p", { text: line })),
    el("p", {}, [el("a", { href: README_URL, text: "How this page works" })]));
}

function render() {
  // Filters picked while loading are kept in state and apply on the first render; until then the page keeps its
  // loading state.
  if (!state.data) return;
  const now = new Date();
  renderHero(now);
  const count = renderSections(now);
  setStatus(`Showing ${count} ${count === 1 ? "event" : "events"}.`);
  renderNotice(count, now);
  renderFooter(now);
}

function renderError() {
  root.querySelector(".around-hero").dataset.sky = "unknown";
  byId("around-headline").textContent = headline({ state: "unknown" });
  byId("around-forecast").hidden = true;
  byId("around-week").hidden = true;
  form.hidden = true;
  setStatus("");
  root.querySelectorAll(".around-section").forEach((section) => { section.hidden = true; });
  const notice = byId("around-notice");
  notice.setAttribute("role", "alert");
  notice.replaceChildren(
    el("p", { text: "Today's events didn't load. Reload the page to try again, or browse the calendars directly:" }),
    byId("around-source-links").content.cloneNode(true));
  notice.hidden = false;
}

async function fetchJson(url) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), FETCH_TIMEOUT_MS);
  try {
    const response = await fetch(url, { signal: controller.signal, credentials: "omit" });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return await response.json();
  } finally {
    clearTimeout(timer);
  }
}

async function loadData(urls) {
  let lastError = new Error("No data URL configured");
  for (const url of urls) {
    try {
      return parseData(await fetchJson(url));
    } catch (error) {
      lastError = error;
    }
  }
  throw lastError;
}

function readFilters() {
  const values = new FormData(form);
  return Object.freeze({
    region: String(values.get("region") || "all"),
    types: Object.freeze(values.getAll("type").map(String)),
    freeOnly: values.get("free") === "1",
  });
}

form.addEventListener("change", () => setState({ filters: readFilters(), expanded: Object.freeze([]) }));
form.addEventListener("submit", (event) => event.preventDefault());

// A failed load shows the fallback notice. A rendering bug also falls back, but is rethrown so it reaches the console
// instead of passing for a network problem.
loadData(resolveDataUrls(window.location, { src: root.dataset.src, fallbackSrc: root.dataset.fallbackSrc }))
  .then((data) => setState({ data }), () => renderError())
  .catch((error) => {
    renderError();
    throw error;
  });
