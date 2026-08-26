import assert from "node:assert/strict";
import test from "node:test";

import { createInitialState, createStore } from "../src/js/state.js";
import {
  afterConversationDeleted,
  createLatestRequestGuard,
  startNewConversationState,
} from "../src/js/conversations.js";
import {
  beginChatState,
  buildChatPayload,
  completeChatState,
  failChatState,
} from "../src/js/chat.js";


test("initial state contains every independent loading flag", () => {
  const state = createInitialState();

  assert.deepEqual(state.loading, {
    initial: false,
    chat: false,
    data: false,
    conversations: false,
  });
  assert.deepEqual(state.data, []);
  assert.deepEqual(state.messages, []);
});


test("store updates state and notifies subscribers", () => {
  const store = createStore({ count: 0 });
  const observed = [];
  const unsubscribe = store.subscribe((state) => observed.push(state.count));

  store.setState({ count: 1 });
  store.setState((state) => ({ count: state.count + 1 }));
  unsubscribe();
  store.setState({ count: 3 });

  assert.equal(store.getState().count, 3);
  assert.deepEqual(observed, [1, 2]);
});


test("setState preserves unrelated top-level state", () => {
  const store = createStore({ count: 0, name: "weight" });

  store.setState({ count: 1 });

  assert.deepEqual(store.getState(), { count: 1, name: "weight" });
});


test("new conversation clears only selection and messages", () => {
  const existing = {
    ...createInitialState(),
    currentConversationId: "conversation-1",
    messages: [{ role: "user", content: "질문" }],
    data: [{ id: "record" }],
  };

  const next = startNewConversationState(existing);

  assert.equal(next.currentConversationId, null);
  assert.deepEqual(next.messages, []);
  assert.deepEqual(next.data, existing.data);
});


test("deleting selected conversation resets chat but unselected deletion preserves it", () => {
  const existing = {
    ...createInitialState(),
    currentConversationId: "conversation-1",
    messages: [{ role: "assistant", content: "답변" }],
  };

  const selected = afterConversationDeleted(existing, "conversation-1");
  const unselected = afterConversationDeleted(existing, "conversation-2");

  assert.equal(selected.currentConversationId, null);
  assert.deepEqual(selected.messages, []);
  assert.equal(unselected.currentConversationId, "conversation-1");
  assert.deepEqual(unselected.messages, existing.messages);
});


test("latest request guard rejects stale detail responses", () => {
  const guard = createLatestRequestGuard();
  const first = guard.next();
  const second = guard.next();

  assert.equal(guard.isCurrent(first), false);
  assert.equal(guard.isCurrent(second), true);
});


test("chat payload carries nullable or existing conversation ID", () => {
  assert.deepEqual(buildChatPayload("질문", null), {
    message: "질문",
    conversation_id: null,
  });
  assert.deepEqual(buildChatPayload("다음 질문", "conversation-1"), {
    message: "다음 질문",
    conversation_id: "conversation-1",
  });
  assert.throws(() => buildChatPayload("   ", null), /질문/);
});


test("chat state keeps optimistic question and appends answer", () => {
  const initial = createInitialState();
  const pending = beginChatState(initial, "최근 체중은?");
  const complete = completeChatState(pending, {
    conversation_id: "conversation-1",
    answer: "72.4kg입니다.",
  });

  assert.equal(pending.loading.chat, true);
  assert.deepEqual(pending.messages, [{ role: "user", content: "최근 체중은?" }]);
  assert.equal(complete.loading.chat, false);
  assert.equal(complete.currentConversationId, "conversation-1");
  assert.deepEqual(complete.messages.at(-1), {
    role: "assistant",
    content: "72.4kg입니다.",
  });
});


test("chat failure stops loading and rolls back the unsaved optimistic question", () => {
  const pending = beginChatState(createInitialState(), "재시도할 질문");

  const failed = failChatState(pending);

  assert.equal(failed.loading.chat, false);
  assert.deepEqual(failed.messages, []);
  assert.throws(() => beginChatState(pending, "중복 질문"), /진행 중/);
});
