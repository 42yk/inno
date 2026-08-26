import { ApiError } from "./api.js";
import { formatWeight } from "./utils.js";


export function validateWeightInput({ date, value, memo }) {
  const errors = {};
  if (!date) errors.date = "날짜를 입력해 주세요.";
  const valueText = String(value ?? "").trim();
  if (!valueText) {
    errors.value = "체중을 입력해 주세요.";
  } else if (!/^\d+(\.\d)?$/.test(valueText)) {
    errors.value = "체중은 소수점 첫째 자리까지 입력해 주세요.";
  } else if (Number(valueText) < 20 || Number(valueText) > 300) {
    errors.value = "체중은 20.0kg 이상 300.0kg 이하로 입력해 주세요.";
  }
  if (String(memo ?? "").length > 200) {
    errors.memo = "메모는 200자 이하로 입력해 주세요.";
  }
  return errors;
}


function setLoading(store, value) {
  store.setState((state) => ({
    loading: { ...state.loading, data: value },
  }));
}


function actionButton(documentRef, label, className, handler) {
  const button = documentRef.createElement("button");
  button.type = "button";
  button.className = className;
  button.textContent = label;
  button.addEventListener("click", handler);
  return button;
}


export function renderDataList(container, records, { onEdit, onDelete }) {
  const documentRef = container.ownerDocument;
  container.replaceChildren();
  if (!records.length) {
    const empty = documentRef.createElement("p");
    empty.className = "empty-state";
    empty.textContent = "등록된 체중 기록이 없습니다.";
    container.append(empty);
    return;
  }
  for (const record of records) {
    const article = documentRef.createElement("article");
    article.className = "data-row";
    const content = documentRef.createElement("div");
    const top = documentRef.createElement("div");
    top.className = "data-row__top";
    const date = documentRef.createElement("time");
    date.dateTime = record.date;
    date.textContent = record.date;
    const weight = documentRef.createElement("strong");
    weight.textContent = formatWeight(record.value);
    top.append(date, weight);
    const memo = documentRef.createElement("p");
    memo.textContent = record.memo || "메모 없음";
    content.append(top, memo);
    const actions = documentRef.createElement("div");
    actions.className = "row-actions";
    actions.append(
      actionButton(documentRef, "수정", "button button--small button--ghost", () => onEdit(record)),
      actionButton(documentRef, "삭제", "button button--small button--danger", (event) => onDelete(record, event.currentTarget)),
    );
    article.append(content, actions);
    container.append(article);
  }
}


export function initDataPanel({
  api,
  store,
  form,
  list,
  title,
  submitButton,
  cancelButton,
  onNotice,
  onRefreshSummary,
  confirmDelete = globalThis.confirm,
}) {
  const fields = {
    date: form.elements.namedItem("date"),
    value: form.elements.namedItem("value"),
    memo: form.elements.namedItem("memo"),
  };

  function clearErrors() {
    for (const element of form.querySelectorAll("[data-field-error]")) {
      element.textContent = "";
    }
  }

  function showErrors(errors) {
    clearErrors();
    for (const [field, message] of Object.entries(errors)) {
      const target = form.querySelector(`[data-field-error="${field}"]`);
      if (target) target.textContent = message;
    }
  }

  function resetForm() {
    form.reset();
    clearErrors();
    store.setState({ editingDataId: null });
    title.textContent = "새 체중 기록";
    submitButton.textContent = "기록 저장";
    cancelButton.hidden = true;
  }

  function edit(record) {
    fields.date.value = record.date;
    fields.value.value = Number(record.value).toFixed(1);
    fields.memo.value = record.memo || "";
    store.setState({ editingDataId: record.id });
    title.textContent = "체중 기록 수정";
    submitButton.textContent = "수정 완료";
    cancelButton.hidden = false;
    fields.date.focus();
  }

  async function load() {
    setLoading(store, true);
    list.setAttribute("aria-busy", "true");
    try {
      const response = await api.listData();
      store.setState({ data: response.items });
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

  async function remove(record, trigger) {
    const accepted = confirmDelete(
      `${record.date}의 ${formatWeight(record.value)} 기록을 삭제할까요?`,
    );
    if (!accepted) {
      trigger?.focus();
      return;
    }
    if (trigger) trigger.disabled = true;
    try {
      await api.deleteData(record.id);
      if (store.getState().editingDataId === record.id) resetForm();
      await Promise.all([load(), onRefreshSummary()]);
      onNotice("success", "체중 기록을 삭제했습니다.");
    } catch (error) {
      onNotice("error", error.message);
    } finally {
      if (trigger?.isConnected) trigger.disabled = false;
    }
  }

  function render() {
    renderDataList(list, store.getState().data, { onEdit: edit, onDelete: remove });
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (store.getState().loading.data) return;
    const payload = {
      date: fields.date.value,
      value: fields.value.value,
      memo: fields.memo.value,
    };
    const errors = validateWeightInput(payload);
    if (Object.keys(errors).length) {
      showErrors(errors);
      return;
    }
    clearErrors();
    setLoading(store, true);
    form.setAttribute("aria-busy", "true");
    submitButton.disabled = true;
    try {
      const editingId = store.getState().editingDataId;
      const body = { ...payload, value: Number(payload.value) };
      if (editingId) await api.updateData(editingId, body);
      else await api.createData(body);
      resetForm();
      await Promise.all([load(), onRefreshSummary()]);
      onNotice("success", editingId ? "체중 기록을 수정했습니다." : "체중 기록을 저장했습니다.");
    } catch (error) {
      if (error instanceof ApiError && error.code === "duplicate_date") {
        showErrors({ date: error.message });
      } else {
        onNotice("error", error.message);
      }
    } finally {
      submitButton.disabled = false;
      setLoading(store, false);
      form.setAttribute("aria-busy", "false");
    }
  });
  cancelButton.addEventListener("click", resetForm);

  return { load, render, resetForm };
}
