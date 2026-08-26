export function buildChatPayload(message, conversationId) {
  const normalized = String(message ?? "").trim();
  if (!normalized) throw new Error("질문을 입력해 주세요.");
  if (normalized.length > 1000) throw new Error("질문은 1000자 이하로 입력해 주세요.");
  return { message: normalized, conversation_id: conversationId || null };
}


export function beginChatState(state, message) {
  if (state.loading.chat) throw new Error("AI 답변 생성이 진행 중입니다.");
  return {
    ...state,
    messages: [...state.messages, { role: "user", content: message }],
    loading: { ...state.loading, chat: true },
  };
}


export function completeChatState(state, result) {
  return {
    ...state,
    currentConversationId: result.conversation_id,
    messages: [
      ...state.messages,
      { role: "assistant", content: result.answer },
    ],
    loading: { ...state.loading, chat: false },
  };
}


export function failChatState(state) {
  return {
    ...state,
    messages: state.messages.slice(0, -1),
    loading: { ...state.loading, chat: false },
  };
}


function messageBubble(documentRef, message) {
  const article = documentRef.createElement("article");
  article.className = `message message--${message.role}`;
  const role = documentRef.createElement("span");
  role.className = "message__role";
  role.textContent = message.role === "user" ? "나" : "Weight AI";
  const content = documentRef.createElement("p");
  content.textContent = message.content;
  article.append(role, content);
  return article;
}


export function renderMessages(container, state, loadingLabel = "데이터를 확인하고 있어요…") {
  const documentRef = container.ownerDocument;
  container.replaceChildren();
  if (!state.messages.length && !state.loading.chat) {
    const empty = documentRef.createElement("div");
    empty.className = "chat-empty";
    const title = documentRef.createElement("strong");
    title.textContent = "체중 기록에 관해 물어보세요.";
    const example = documentRef.createElement("p");
    example.textContent = "“전체 체중 추세가 어때?” 또는 “2025년 3월 평균은?”";
    empty.append(title, example);
    container.append(empty);
    return;
  }
  for (const message of state.messages) {
    container.append(messageBubble(documentRef, message));
  }
  if (state.loading.chat) {
    const loading = messageBubble(documentRef, {
      role: "assistant",
      content: loadingLabel,
    });
    loading.classList.add("message--loading");
    loading.setAttribute("aria-label", "AI 답변 생성 중");
    container.append(loading);
  }
  container.scrollTop = container.scrollHeight;
}


export function initChatPanel({
  api,
  store,
  form,
  input,
  submitButton,
  messageList,
  onConversationRefresh,
  onNotice,
  coldStartDelay = 8000,
}) {
  let loadingLabel = "데이터를 확인하고 있어요…";

  function render() {
    const state = store.getState();
    renderMessages(messageList, state, loadingLabel);
    form.setAttribute("aria-busy", String(state.loading.chat));
    input.disabled = state.loading.chat;
    submitButton.disabled = state.loading.chat;
  }

  function focus() {
    if (!store.getState().loading.chat) input.focus();
  }

  async function send() {
    const state = store.getState();
    let payload;
    try {
      payload = buildChatPayload(input.value, state.currentConversationId);
    } catch (error) {
      onNotice("error", error.message);
      return;
    }
    if (state.loading.chat) return;

    store.setState((current) => beginChatState(current, payload.message));
    input.value = "";
    loadingLabel = "데이터를 확인하고 있어요…";
    render();
    const coldStartTimer = setTimeout(() => {
      loadingLabel = "서버 첫 연결에는 잠시 시간이 걸릴 수 있어요. 계속 기다리는 중입니다…";
      render();
    }, coldStartDelay);

    try {
      const result = await api.sendChat(payload);
      store.setState((current) => completeChatState(current, result));
      render();
      try {
        await onConversationRefresh();
      } catch (_error) {
        // The answer is already complete; history loading reports its own notice.
      }
    } catch (error) {
      store.setState((current) => failChatState(current));
      input.value = payload.message;
      render();
      onNotice("error", error.message);
    } finally {
      clearTimeout(coldStartTimer);
      loadingLabel = "데이터를 확인하고 있어요…";
      focus();
    }
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault();
    void send();
  });
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      form.requestSubmit();
    }
  });
  render();
  return { render, send, focus };
}
