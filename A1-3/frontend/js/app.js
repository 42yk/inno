const appView = document.querySelector("#app-view");
const navLinks = Array.from(document.querySelectorAll(".nav-links a"));

const VIEW_PATHS = {
  home: "/views/home.html",
  recommend: "/views/recommend.html",
  ranking: "/views/ranking.html",
};

const viewNames = Object.keys(VIEW_PATHS);
const viewCache = new Map();

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

let activeViewName = "";
let activeRequestId = 0;

function getViewFromHash() {
  const viewName = window.location.hash.replace("#", "");
  return viewNames.includes(viewName) ? viewName : "home";
}

function setActiveNav(viewName) {
  navLinks.forEach((link) => {
    const isActive = link.getAttribute("href") === `#${viewName}`;
    if (isActive) {
      link.setAttribute("aria-current", "page");
    } else {
      link.removeAttribute("aria-current");
    }
  });
}

function setViewLoading(viewName) {
  appView.innerHTML = `
    <section class="section view loading-view" data-view="${escapeHtml(viewName)}">
      <p class="eyebrow">Loading</p>
      <h1>화면을 불러오는 중입니다</h1>
    </section>
  `;
}

function setViewError() {
  appView.innerHTML = `
    <section class="section view loading-view" data-view="error">
      <p class="eyebrow">오류</p>
      <h1>화면을 불러오지 못했습니다</h1>
      <p class="hero-text">잠시 후 다시 시도해주세요.</p>
    </section>
  `;
}

async function fetchViewHtml(viewName) {
  if (viewCache.has(viewName)) {
    return viewCache.get(viewName);
  }

  const response = await fetch(VIEW_PATHS[viewName]);
  if (!response.ok) {
    throw new Error(`Failed to fetch ${viewName} view`);
  }

  const html = await response.text();
  viewCache.set(viewName, html);
  return html;
}

async function loadView(viewName) {
  const requestId = ++activeRequestId;
  const shouldShowLoading = activeViewName !== viewName;

  if (shouldShowLoading) {
    setViewLoading(viewName);
  }

  try {
    const html = await fetchViewHtml(viewName);
    if (requestId !== activeRequestId) {
      return;
    }

    appView.innerHTML = html;
    activeViewName = viewName;
    document.body.dataset.currentView = viewName;
    setActiveNav(viewName);
    window.scrollTo({ top: 0, behavior: "auto" });
    initView(viewName);
  } catch (error) {
    if (requestId !== activeRequestId) {
      return;
    }

    activeViewName = "";
    setActiveNav(viewName);
    setViewError();
  }
}

function handleRoute() {
  loadView(getViewFromHash());
}

function navigateToView(viewName) {
  if (!viewNames.includes(viewName)) {
    return;
  }

  if (window.location.hash !== `#${viewName}`) {
    history.pushState(null, "", `#${viewName}`);
  }
  loadView(viewName);
}

function initView(viewName) {
  if (viewName === "recommend") {
    initRecommendView();
  }

  if (viewName === "ranking") {
    initRankingView();
  }
}

function initRecommendView() {
  const form = document.querySelector("#recommend-form");
  if (!form) {
    return;
  }

  form.addEventListener("submit", submitRecommendation);
}

function initRankingView() {
  const refreshRankingButton = document.querySelector("#refresh-ranking");
  refreshRankingButton?.addEventListener("click", loadRanking);
  loadRanking();
}

function setMessage(text, type = "") {
  const message = document.querySelector("#form-message");
  if (!message) {
    return;
  }

  message.textContent = text;
  message.className = `form-message ${type}`.trim();
}

function parseForm(form) {
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
  const resultTitle = document.querySelector("#result-title");
  const resultContent = document.querySelector("#result-content");
  if (!resultTitle || !resultContent) {
    return;
  }

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
  const rankingList = document.querySelector("#ranking-list");
  const rankingMessage = document.querySelector("#ranking-message");
  if (!rankingList || !rankingMessage) {
    return;
  }

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
  const rankingList = document.querySelector("#ranking-list");
  const rankingMessage = document.querySelector("#ranking-message");
  if (!rankingList || !rankingMessage) {
    return;
  }

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

  const form = event.currentTarget;
  const data = parseForm(form);
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

document.addEventListener("click", (event) => {
  const link = event.target.closest('a[href^="#"]');
  if (!link) {
    return;
  }

  const viewName = link.getAttribute("href").slice(1);
  if (!viewNames.includes(viewName)) {
    return;
  }

  event.preventDefault();
  navigateToView(viewName);
});

window.addEventListener("DOMContentLoaded", handleRoute);
window.addEventListener("hashchange", handleRoute);
window.addEventListener("popstate", handleRoute);
