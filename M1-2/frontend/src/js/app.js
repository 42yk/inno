import { createApi } from "./api.js";
import { initChatPanel } from "./chat.js";
import { initConversationPanel } from "./conversations.js";
import { initDataPanel } from "./data.js";
import { createInitialState, createStore } from "./state.js";
import { initSummaryPanel } from "./summary.js";


const appElement = document.querySelector("#app");
const noticeElement = document.querySelector("#global-notice");
const statusElement = document.querySelector("#connection-status");

try {
  const api = createApi({ baseUrl: window.APP_CONFIG?.API_BASE_URL });
  const store = createStore(createInitialState());
  window.weightApp = { api, store };

  function showNotice(type, message) {
    if (!noticeElement) return;
    noticeElement.hidden = false;
    noticeElement.dataset.type = type;
    noticeElement.textContent = message;
  }

  const summaryPanel = initSummaryPanel({
    api,
    store,
    container: document.querySelector("#summary-content"),
    onNotice: showNotice,
  });
  const dataPanel = initDataPanel({
    api,
    store,
    form: document.querySelector("#data-form"),
    list: document.querySelector("#data-list"),
    title: document.querySelector("#data-form-title"),
    submitButton: document.querySelector("#data-submit"),
    cancelButton: document.querySelector("#data-cancel"),
    onNotice: showNotice,
    onRefreshSummary: summaryPanel.load,
  });
  let conversationPanel;
  const chatPanel = initChatPanel({
    api,
    store,
    form: document.querySelector("#chat-form"),
    input: document.querySelector("#chat-message"),
    submitButton: document.querySelector("#chat-form button[type='submit']"),
    messageList: document.querySelector("#message-list"),
    onConversationRefresh: () => conversationPanel.load(),
    onNotice: showNotice,
  });
  conversationPanel = initConversationPanel({
    api,
    store,
    list: document.querySelector("#conversation-list"),
    newButton: document.querySelector("#new-conversation"),
    onMessagesChanged: chatPanel.render,
    onNotice: showNotice,
    focusChatInput: chatPanel.focus,
  });

  Promise.all([summaryPanel.load(), dataPanel.load(), conversationPanel.load()])
    .then(() => {
      if (statusElement) statusElement.textContent = "API 연결됨";
    })
    .catch(() => {
      if (statusElement) statusElement.textContent = "연결 오류";
    })
    .finally(() => appElement?.setAttribute("aria-busy", "false"));
} catch (error) {
  appElement?.setAttribute("aria-busy", "false");
  if (statusElement) statusElement.textContent = "설정 필요";
  if (noticeElement) {
    noticeElement.hidden = false;
    noticeElement.textContent = error.message;
  }
}
