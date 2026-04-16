/**
 * Formats an ISO timestamp into a PT-PT relative label.
 *
 * Output examples:
 *   - under 1m:    "agora"
 *   - under 1h:    "há 30m"
 *   - 1-23h ago:   "há 2h"
 *   - yesterday:   "ontem"
 *   - older same year: "10 abr"
 *   - different year:  "10 abr 2024"
 */
const MONTHS_PT = [
  "jan",
  "fev",
  "mar",
  "abr",
  "mai",
  "jun",
  "jul",
  "ago",
  "set",
  "out",
  "nov",
  "dez",
];

export function formatRelativeTime(iso: string): string {
  const date = new Date(iso);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60_000);
  const diffHour = Math.floor(diffMs / 3_600_000);
  const diffDay = Math.floor(diffMs / 86_400_000);

  if (diffMin < 1) return "agora";
  if (diffMin < 60) return `há ${diffMin}m`;
  if (diffHour < 24) return `há ${diffHour}h`;
  if (diffDay === 1) return "ontem";

  const day = date.getDate();
  const month = MONTHS_PT[date.getMonth()];
  if (date.getFullYear() === now.getFullYear()) {
    return `${day} ${month}`;
  }
  return `${day} ${month} ${date.getFullYear()}`;
}
