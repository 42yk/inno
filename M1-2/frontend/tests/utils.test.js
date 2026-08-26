import assert from "node:assert/strict";
import test from "node:test";

import {
  formatChange,
  formatConversationTime,
  formatDate,
  formatWeight,
} from "../src/js/utils.js";
import { validateWeightInput } from "../src/js/data.js";
import { toSummaryView } from "../src/js/summary.js";


test("weight and change formatters use one decimal place", () => {
  assert.equal(formatWeight(72.4), "72.4kg");
  assert.equal(formatChange(0.6), "+0.6kg");
  assert.equal(formatChange(-0.6), "-0.6kg");
  assert.equal(formatChange(0), "0.0kg");
  assert.equal(formatWeight(null), "기록 없음");
});


test("date formatter preserves API date and handles empties", () => {
  assert.equal(formatDate("2025-03-10"), "2025-03-10");
  assert.equal(formatDate(null), "기록 없음");
});


test("conversation time uses the supplied locale and timezone", () => {
  assert.equal(
    formatConversationTime("2025-01-02T03:04:00Z", "ko-KR", "UTC"),
    "2025. 1. 2. 03:04",
  );
});


test("weight form validation reports fields independently", () => {
  assert.deepEqual(
    validateWeightInput({ date: "", value: "72.4", memo: "" }),
    { date: "날짜를 입력해 주세요." },
  );
  assert.deepEqual(
    validateWeightInput({ date: "2025-01-01", value: "72.45", memo: "" }),
    { value: "체중은 소수점 첫째 자리까지 입력해 주세요." },
  );
  assert.deepEqual(
    validateWeightInput({ date: "2025-01-01", value: "10", memo: "x".repeat(201) }),
    {
      value: "체중은 20.0kg 이상 300.0kg 이하로 입력해 주세요.",
      memo: "메모는 200자 이하로 입력해 주세요.",
    },
  );
});


test("summary view handles empty and complete summaries", () => {
  assert.equal(toSummaryView({ count: 0 }).empty, true);

  const view = toSummaryView({
    period: { start: "2025-01-01", end: "2025-05-31" },
    count: 120,
    metrics: {
      average: 72.3,
      max: { value: 75.1, dates: ["2025-01-01", "2025-01-03"] },
      min: { value: 69.8, dates: ["2025-05-31"] },
      first: { date: "2025-01-01", value: 75.1 },
      latest: { date: "2025-05-31", value: 69.8 },
      change: -5.3,
    },
    trend: {
      status: "decrease",
      label: "감소",
      previous_average: 70.8,
      recent_average: 70.2,
      difference: -0.6,
    },
  });

  assert.equal(view.empty, false);
  assert.equal(view.periodLabel, "2025-01-01 — 2025-05-31");
  assert.equal(view.averageLabel, "72.3kg");
  assert.equal(view.changeLabel, "-5.3kg");
  assert.equal(view.trendLabel, "감소");
  assert.equal(view.maxDatesLabel, "2025-01-01, 2025-01-03");
});
