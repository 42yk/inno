export class ApiError extends Error {
  constructor(message, { status = 0, code = "request_failed", details = null } = {}) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}


export function joinUrl(baseUrl, path) {
  return `${baseUrl.replace(/\/+$/, "")}/${path.replace(/^\/+/, "")}`;
}


export function createApi({ baseUrl, fetchImpl = globalThis.fetch } = {}) {
  if (!baseUrl || !baseUrl.trim()) {
    throw new Error("API_BASE_URL이 설정되지 않았습니다.");
  }
  if (typeof fetchImpl !== "function") {
    throw new Error("fetch 구현이 필요합니다.");
  }

  async function request(path, { method = "GET", body, headers = {} } = {}) {
    const options = { method, headers: { ...headers } };
    if (body !== undefined) {
      options.headers["Content-Type"] = "application/json";
      options.body = JSON.stringify(body);
    }

    let response;
    try {
      response = await fetchImpl(joinUrl(baseUrl, path), options);
    } catch (_error) {
      throw new ApiError("서버에 연결하지 못했습니다.", {
        code: "network_error",
      });
    }

    if (response.status === 204) return null;

    const isJson = response.headers.get("content-type")?.includes("application/json");
    let payload = null;
    if (isJson) {
      try {
        payload = await response.json();
      } catch (_error) {
        payload = null;
      }
    }

    if (!response.ok) {
      const publicError = payload?.error;
      throw new ApiError(
        publicError?.message || "서버 요청을 처리하지 못했습니다.",
        {
          status: response.status,
          code: publicError?.code || "request_failed",
          details: publicError?.details ?? null,
        },
      );
    }

    if (isJson) return payload;
    return response.text();
  }

  function listData({ startDate, endDate } = {}) {
    const query = new URLSearchParams();
    if (startDate) query.set("start_date", startDate);
    if (endDate) query.set("end_date", endDate);
    const suffix = query.size ? `?${query}` : "";
    return request(`/api/data${suffix}`);
  }

  return {
    request,
    listData,
    createData: (payload) => request("/api/data", { method: "POST", body: payload }),
    updateData: (id, payload) =>
      request(`/api/data/${encodeURIComponent(id)}`, { method: "PUT", body: payload }),
    deleteData: (id) =>
      request(`/api/data/${encodeURIComponent(id)}`, { method: "DELETE" }),
    getSummary: () => request("/api/data/summary"),
    createConversation: (payload) =>
      request("/api/conversations", { method: "POST", body: payload }),
    listConversations: () => request("/api/conversations"),
    getConversation: (id) => request(`/api/conversations/${encodeURIComponent(id)}`),
    deleteConversation: (id) =>
      request(`/api/conversations/${encodeURIComponent(id)}`, { method: "DELETE" }),
    sendChat: (payload) => request("/api/chat", { method: "POST", body: payload }),
  };
}
