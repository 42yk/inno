export function createInitialState() {
  return {
    data: [],
    summary: null,
    conversations: [],
    currentConversationId: null,
    messages: [],
    editingDataId: null,
    loading: {
      initial: false,
      chat: false,
      data: false,
      conversations: false,
    },
    notice: null,
  };
}


export function createStore(initialState = createInitialState()) {
  let state = { ...initialState };
  const listeners = new Set();

  return {
    getState() {
      return state;
    },
    setState(update) {
      const patch = typeof update === "function" ? update(state) : update;
      state = { ...state, ...patch };
      for (const listener of listeners) listener(state);
      return state;
    },
    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
  };
}
