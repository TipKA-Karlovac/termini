// Datumi i vremena. Dan je uvijek tekst "GGGG-MM-DD" u vremenskoj zoni salona
// (poslužitelj je izvor istine), pa prikaz ne ovisi o tome gdje je preglednik.

const DAY_MS = 24 * 60 * 60 * 1000;

function toUtc(day) {
  const [year, month, date] = day.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, date));
}

export function addDays(day, count) {
  return new Date(toUtc(day).getTime() + count * DAY_MS).toISOString().slice(0, 10);
}

/** Svi dani od `first` do `last`, uključivo. */
export function daysBetween(first, last) {
  const days = [];
  for (let day = first; day <= last; day = addDays(day, 1)) days.push(day);
  return days;
}

const weekdayShort = new Intl.DateTimeFormat("hr-HR", { weekday: "short", timeZone: "UTC" });
const dayMonth = new Intl.DateTimeFormat("hr-HR", {
  day: "numeric",
  month: "numeric",
  timeZone: "UTC",
});
const longDay = new Intl.DateTimeFormat("hr-HR", {
  weekday: "long",
  day: "numeric",
  month: "long",
  year: "numeric",
  timeZone: "UTC",
});

export const formatWeekday = (day) => weekdayShort.format(toUtc(day));
export const formatDayMonth = (day) => dayMonth.format(toUtc(day));
export const formatLongDay = (day) => longDay.format(toUtc(day));

/** Sat i minuta trenutka `iso` u vremenskoj zoni salona, npr. "09:30". */
export function formatTime(iso, timeZone) {
  return new Intl.DateTimeFormat("hr-HR", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone,
  }).format(new Date(iso));
}

/** Dan ("GGGG-MM-DD") u koji trenutak `iso` pada u vremenskoj zoni salona. */
export function dayOf(iso, timeZone) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    timeZone,
  }).formatToParts(new Date(iso));
  const get = (type) => parts.find((part) => part.type === type).value;
  return `${get("year")}-${get("month")}-${get("day")}`;
}

/** Dijeli termine na prijepodne i poslijepodne po lokalnom satu salona. */
export function splitByNoon(slots, timeZone) {
  const morning = [];
  const afternoon = [];
  for (const slot of slots) {
    const hour = Number(formatTime(slot, timeZone).slice(0, 2));
    (hour < 12 ? morning : afternoon).push(slot);
  }
  return { morning, afternoon };
}

export const capitalize = (text) => text.charAt(0).toLocaleUpperCase("hr-HR") + text.slice(1);

export function formatPrice(price) {
  return new Intl.NumberFormat("hr-HR", { style: "currency", currency: "EUR" }).format(
    Number(price),
  );
}
