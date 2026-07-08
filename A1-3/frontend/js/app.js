const form = document.querySelector("#recommend-form");
const message = document.querySelector("#form-message");
const resultTitle = document.querySelector("#result-title");
const resultContent = document.querySelector("#result-content");
const rankingList = document.querySelector("#ranking-list");
const rankingMessage = document.querySelector("#ranking-message");
const refreshRankingButton = document.querySelector("#refresh-ranking");

const ERROR_MESSAGES = {
  required: "필수 항목을 입력해주세요.",
  budgetFormat: "예산은 숫자로 입력해주세요.",
  budgetMin: "예산은 1,000원 이상 입력해주세요.",
  budgetMax: "예산은 100,000원 이하로 입력해주세요.",
  peopleMin: "인원은 1명 이상 입력해주세요.",
  peopleMax: "인원은 20명 이하로 입력해주세요.",
  api: "추천 결과를 가져오지 못했습니다. 잠시 후 다시 시도해주세요.",
  loading: "AI가 메뉴를 추천하고 있습니다...",
};

function setMessage(text, type = "") {
  message.textContent = text;
  message.className = `form-message ${type}`.trim();
}

function parseForm() {
  const formData = new FormData(form);
  return {
    mealTime: String(formData.get("mealTime") || "").trim(),
    budget: String(formData.get("budget") || "").trim(),
    people: String(formData.get("people") || "").trim(),
    foodType: String(formData.get("foodType") || "").trim(),
    spicyLevel: String(formData.get("spicyLevel") || "").trim(),
  };
}

function validateInput(data) {
  if (!data.mealTime || !data.budget || !data.people || !data.foodType || !data.spicyLevel) {
    return ERROR_MESSAGES.required;
  }

  if (!/^\d+$/.test(data.budget)) {
    return ERROR_MESSAGES.budgetFormat;
  }

  const budget = Number(data.budget);
  const people = Number(data.people);

  if (budget < 1000) {
    return ERROR_MESSAGES.budgetMin;
  }

  if (budget > 100000) {
    return ERROR_MESSAGES.budgetMax;
  }

  if (!Number.isInteger(people) || people < 1) {
    return ERROR_MESSAGES.peopleMin;
  }

  if (people > 20) {
    return ERROR_MESSAGES.peopleMax;
  }

  return "";
}

function formatWon(value) {
  const number = Number(value);
  if (!Number.isFinite(number)) {
    return String(value || "-");
  }
  return `${number.toLocaleString("ko-KR")}원`;
}

function renderResult(result) {
  resultTitle.textContent = "추천 메뉴가 도착했습니다";
  resultContent.className = "result-content";
  resultContent.innerHTML = `
    <div class="result-main">
      <div class="menu-name">${escapeHtml(result.menuName)}</div>
      <p>${escapeHtml(result.reason)}</p>
      <div class="result-meta">
        <div>
          <span>예상 가격</span>
          <strong>${escapeHtml(formatWon(result.estimatedPrice))}</strong>
        </div>
        <div>
          <span>함께 먹기 좋은 메뉴</span>
          <strong>${escapeHtml(result.sideMenu)}</strong>
        </div>
      </div>
    </div>
  `;
}

function renderRanking(items) {
  rankingList.innerHTML = "";

  if (!items.length) {
    rankingMessage.textContent = "아직 랭킹 데이터가 없습니다.";
    return;
  }

  const fragment = document.createDocumentFragment();
  items.forEach((item) => {
    const li = document.createElement("li");
    const name = document.createElement("span");
    const count = document.createElement("span");

    name.className = "ranking-name";
    count.className = "ranking-count";
    name.textContent = item.menuName;
    count.textContent = `${Number(item.count).toLocaleString("ko-KR")}회`;

    li.append(name, count);
    fragment.appendChild(li);
  });

  rankingList.appendChild(fragment);
  rankingMessage.textContent = "추천 횟수 기준으로 정렬했습니다.";
}

async function loadRanking() {
  rankingMessage.textContent = "랭킹을 불러오는 중입니다.";

  try {
    const response = await fetch("/api/ranking");
    if (!response.ok) {
      throw new Error("Ranking API failed");
    }

    const payload = await response.json();
    renderRanking(Array.isArray(payload.items) ? payload.items : []);
  } catch (error) {
    rankingMessage.textContent = "랭킹을 가져오지 못했습니다. 잠시 후 다시 시도해주세요.";
    rankingList.innerHTML = "";
  }
}

async function submitRecommendation(event) {
  event.preventDefault();

  const data = parseForm();
  const validationMessage = validateInput(data);
  if (validationMessage) {
    setMessage(validationMessage, "error");
    return;
  }

  setMessage(ERROR_MESSAGES.loading, "loading");

  try {
    const response = await fetch("/api/recommend", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        ...data,
        budget: Number(data.budget),
        people: Number(data.people),
      }),
    });

    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(payload.message || ERROR_MESSAGES.api);
    }

    renderResult(payload.result);
    setMessage("");
    await loadRanking();
  } catch (error) {
    setMessage(error.message || ERROR_MESSAGES.api, "error");
  }
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

form.addEventListener("submit", submitRecommendation);
refreshRankingButton.addEventListener("click", loadRanking);
window.addEventListener("DOMContentLoaded", loadRanking);
