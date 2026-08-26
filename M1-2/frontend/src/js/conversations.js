import { formatConversationTime } from "./utils.js";


export function startNewConversationState(state) {
  return { ...state, currentConversationId: null, messages: [] };
}


export function afterConversationDeleted(state, deletedId) {
  return state.currentConversationId === deletedId
    ? startNewConversationState(state)
    : state;
}


export function createLatestRequestGuard() {
  let latest = 0;
  return {
    next() {
      latest += 1;
      return latest;
    },
    isCurrent(requestId) {
      return requestId === latest;
    },
  };
}


function setLoading(store, value) {
  store.setState((state) => ({
    loading: { ...state.loading, conversations: value },
  }));
}


export function renderConversationList(
  container,
  conversations,
  currentId,
  { onSelect, onDelete },
) {
  const documentRef = container.ownerDocument;
  container.replaceChildren();
  if (!conversations.length) {
    const empty = documentRef.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "저장된 대화가 없습니다.";
    container.append(empty);
    return;
  }
  for (const conversation of conversations) {
    const row = documentRef.createElement("article");
    row.className = "conversation-item";
    const select = documentRef.createElement("button");
    select.type = "button";
    select.className = "conversation-select";
    if (conversation.id === currentId) {
      select.setAttribute("aria-current", "true");
    }
    const title = documentRef.createElement("strong");
    title.textContent = conversation.title;
    const meta = documentRef.createElement("span");
    meta.textContent = `${conversation.message_count}개 메시지 · ${formatConversationTime(conversation.updated_at)}`;
    select.append(title, meta);
    select.addEventListener("click", () => onSelect(conversation.id));
    const remove = documentRef.createElement("button");
    remove.type = "button";
    remove.className = "button button--small button--danger";
    remove.textContent = "삭제";
    remove.setAttribute("aria-label", `${conversation.title} 대화 삭제`);
    remove.addEventListener("click", (event) => onDelete(conversation, event.currentTarget));
    row.append(select, remove);
    container.append(row);
  }
}


export function initConversationPanel({
  api,
  store,
  list,
  newButton,
  onMessagesChanged,
  onNotice,
  focusChatInput,
  confirmDelete = globalThis.confirm,
}) {
  const detailGuard = createLatestRequestGuard();

  function render() {
    const state = store.getState();
    renderConversationList(
      list,
      state.conversations,
      state.currentConversationId,
      { onSelect: select, onDelete: remove },
    );
  }

  async function load() {
    setLoading(store, true);
    list.setAttribute("aria-busy", "true");
    try {
      const response = await api.listConversations();
      store.setState({ conversations: response.items });
      render();
      return response.items;
    } catch (error) {
      onNotice("error", error.message);
      throw error;
    } finally {
      setLoading(store, false);
      list.setAttribute("aria-busy", "false");
    }
  }

  async function select(conversationId) {
    const requestId = detailGuard.next();
    setLoading(store, true);
    list.setAttribute("aria-busy", "true");
    try {
      const conversation = await api.getConversation(conversationId);
      if (!detailGuard.isCurrent(requestId)) return;
      store.setState({
        currentConversationId: conversation.id,
        messages: conversation.messages,
      });
      render();
      onMessagesChanged();
      focusChatInput();
    } catch (error) {
      if (detailGuard.isCurrent(requestId)) onNotice("error", error.message);
    } finally {
      if (detailGuard.isCurrent(requestId)) {
        setLoading(store, false);
        list.setAttribute("aria-busy", "false");
      }
    }
  }

  function startNew() {
    detailGuard.next();
    store.setState((state) => startNewConversationState(state));
    render();
    onMessagesChanged();
    focusChatInput();
  }

  async function remove(conversation, trigger) {
    if (!confirmDelete(`“${conversation.title}” 대화를 삭제할까요?`)) {
      trigger?.focus();
      return;
    }
    if (trigger) trigger.disabled = true;
    try {
      await api.deleteConversation(conversation.id);
      detailGuard.next();
      store.setState((state) => afterConversationDeleted(state, conversation.id));
      onMessagesChanged();
      await load();
      onNotice("success", "대화를 삭제했습니다.");
    } catch (error) {
      onNotice("error", error.message);
    } finally {
      if (trigger?.isConnected) trigger.disabled = false;
    }
  }

  newButton.addEventListener("click", startNew);
  return { load, render, select, startNew };
}
