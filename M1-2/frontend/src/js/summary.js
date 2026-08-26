import { formatChange, formatDate, formatWeight } from "./utils.js";


const TREND_LABELS = {
  no_data: "기록 없음",
  insufficient_data: "데이터 부족",
  decrease: "감소",
  maintain: "유지",
  increase: "증가",
};


export function toSummaryView(summary) {
  if (!summary || !summary.count || !summary.metrics || !summary.period) {
    return { empty: true, countLabel: "0개" };
  }
  const { metrics, period, trend } = summary;
  return {
    empty: false,
    periodLabel: `${formatDate(period.start)} — ${formatDate(period.end)}`,
    countLabel: `${summary.count}개`,
    averageLabel: formatWeight(metrics.average),
    maxLabel: formatWeight(metrics.max.value),
    maxDatesLabel: metrics.max.dates.map(formatDate).join(", "),
    minLabel: formatWeight(metrics.min.value),
    minDatesLabel: metrics.min.dates.map(formatDate).join(", "),
    firstLabel: `${formatWeight(metrics.first.value)} · ${formatDate(metrics.first.date)}`,
    latestLabel: `${formatWeight(metrics.latest.value)} · ${formatDate(metrics.latest.date)}`,
    changeLabel: formatChange(metrics.change),
    trendLabel: TREND_LABELS[trend?.status] || trend?.label || "데이터 부족",
    trendDetail:
      trend?.recent_average === null || trend?.recent_average === undefined
        ? "20개 이상 기록부터 최근 추세를 계산합니다."
        : `이전 ${formatWeight(trend.previous_average)} → 최근 ${formatWeight(trend.recent_average)} (${formatChange(trend.difference)})`,
    trendStatus: trend?.status || "insufficient_data",
  };
}


function metric(documentRef, label, value, detail = null) {
  const wrapper = documentRef.createElement("div");
  wrapper.className = "metric";
  const term = documentRef.createElement("dt");
  term.textContent = label;
  const description = documentRef.createElement("dd");
  description.textContent = value;
  wrapper.append(term, description);
  if (detail) {
    const small = documentRef.createElement("small");
    small.textContent = detail;
    wrapper.append(small);
  }
  return wrapper;
}


export function renderSummary(container, summary) {
  const documentRef = container.ownerDocument;
  const view = toSummaryView(summary);
  container.replaceChildren();
  if (view.empty) {
    const empty = documentRef.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "저장된 체중 기록이 없습니다.";
    container.append(empty);
    return;
  }
  const grid = documentRef.createElement("dl");
  grid.className = "metrics-grid";
  grid.append(
    metric(documentRef, "기록 기간", view.periodLabel),
    metric(documentRef, "유효 기록", view.countLabel),
    metric(documentRef, "평균", view.averageLabel),
    metric(documentRef, "전체 변화", view.changeLabel),
    metric(documentRef, "최고", view.maxLabel, view.maxDatesLabel),
    metric(documentRef, "최저", view.minLabel, view.minDatesLabel),
    metric(documentRef, "최초", view.firstLabel),
    metric(documentRef, "최근", view.latestLabel),
  );
  const trend = documentRef.createElement("div");
  trend.className = `trend trend--${view.trendStatus}`;
  const trendLabel = documentRef.createElement("strong");
  trendLabel.textContent = `최근 추세 · ${view.trendLabel}`;
  const trendDetail = documentRef.createElement("span");
  trendDetail.textContent = view.trendDetail;
  trend.append(trendLabel, trendDetail);
  container.append(grid, trend);
}


export function initSummaryPanel({ api, store, container, onNotice }) {
  async function load() {
    container.setAttribute("aria-busy", "true");
    try {
      const summary = await api.getSummary();
      store.setState({ summary });
      renderSummary(container, summary);
      return summary;
    } catch (error) {
      renderSummary(container, null);
      onNotice("error", error.message);
      throw error;
    } finally {
      container.setAttribute("aria-busy", "false");
    }
  }
  return { load };
}
