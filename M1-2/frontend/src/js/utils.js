export function formatWeight(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "기록 없음";
  }
  return `${Number(value).toFixed(1)}kg`;
}


export function formatChange(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return "기록 없음";
  }
  const number = Number(value);
  const sign = number > 0 ? "+" : "";
  return `${sign}${number.toFixed(1)}kg`;
}


export function formatDate(value) {
  return value || "기록 없음";
}


export function formatConversationTime(
  value,
  locale = "ko-KR",
  timeZone = undefined,
) {
  if (!value) return "기록 없음";
  return new Intl.DateTimeFormat(locale, {
    year: "numeric",
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
    timeZone,
  }).format(new Date(value));
}
