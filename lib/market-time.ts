const CAIRO_DATE = new Intl.DateTimeFormat("en-CA", {
  timeZone: "Africa/Cairo",
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
});

const CAIRO_WEEKDAY = new Intl.DateTimeFormat("en-US", {
  timeZone: "Africa/Cairo",
  weekday: "short",
});

type CairoDay = { date: string; weekday: string };

function cairoDay(value: Date): CairoDay {
  const parts = CAIRO_DATE.formatToParts(value);
  const get = (type: string) => parts.find((part) => part.type === type)?.value ?? "";
  return {
    date: `${get("year")}-${get("month")}-${get("day")}`,
    weekday: CAIRO_WEEKDAY.format(value),
  };
}

/** Most recent Cairo weekday that should have produced an EGX session. */
export function lastExpectedTradingSession(now: Date = new Date()): string {
  const cursor = new Date(now.getTime());
  for (let attempt = 0; attempt < 10; attempt += 1) {
    const day = cairoDay(cursor);
    if (day.weekday !== "Fri" && day.weekday !== "Sat") return day.date;
    cursor.setUTCDate(cursor.getUTCDate() - 1);
  }
  return cairoDay(cursor).date;
}

export function formatCairoDateTime(value: string | null): string {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: "Africa/Cairo",
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}
