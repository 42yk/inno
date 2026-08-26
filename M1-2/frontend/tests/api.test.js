import assert from "node:assert/strict";
import test from "node:test";

import { ApiError, createApi, joinUrl } from "../src/js/api.js";


function jsonResponse(payload, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}


test("joinUrl removes duplicate boundary slashes", () => {
  assert.equal(
    joinUrl("https://api.example.com/", "/api/data"),
    "https://api.example.com/api/data",
  );
});


test("request serializes JSON and parses a JSON response", async () => {
  const calls = [];
  const api = createApi({
    baseUrl: "https://api.example.com/",
    fetchImpl: async (url, options) => {
      calls.push({ url, options });
      return jsonResponse({ id: "2025-01-01" }, 201);
    },
  });

  const result = await api.createData({
    date: "2025-01-01",
    value: 72.4,
    memo: "",
  });

  assert.deepEqual(result, { id: "2025-01-01" });
  assert.equal(calls[0].url, "https://api.example.com/api/data");
  assert.equal(calls[0].options.method, "POST");
  assert.equal(calls[0].options.headers["Content-Type"], "application/json");
  assert.equal(JSON.parse(calls[0].options.body).value, 72.4);
});


test("request returns null for 204", async () => {
  const api = createApi({
    baseUrl: "https://api.example.com",
    fetchImpl: async () => new Response(null, { status: 204 }),
  });

  assert.equal(await api.deleteData("2025-01-01"), null);
});


test("public error envelope becomes ApiError", async () => {
  const api = createApi({
    baseUrl: "https://api.example.com",
    fetchImpl: async () =>
      jsonResponse(
        {
          error: {
            code: "duplicate_date",
            message: "해당 날짜의 기록이 이미 존재합니다.",
            details: null,
          },
        },
        409,
      ),
  });

  await assert.rejects(
    api.createData({ date: "2025-01-01", value: 72.4, memo: "" }),
    (error) => {
      assert.ok(error instanceof ApiError);
      assert.equal(error.status, 409);
      assert.equal(error.code, "duplicate_date");
      return true;
    },
  );
});


test("non-JSON failure uses a safe fallback", async () => {
  const api = createApi({
    baseUrl: "https://api.example.com",
    fetchImpl: async () => new Response("proxy secret", { status: 502 }),
  });

  await assert.rejects(api.listData(), (error) => {
    assert.equal(error.message, "서버 요청을 처리하지 못했습니다.");
    assert.equal(error.status, 502);
    assert.equal(error.details, null);
    return true;
  });
});


test("endpoint wrappers encode IDs and chat payload", async () => {
  const calls = [];
  const api = createApi({
    baseUrl: "https://api.example.com",
    fetchImpl: async (url, options = {}) => {
      calls.push({ url, options });
      return jsonResponse({ ok: true });
    },
  });

  await api.getConversation("id/with/slash");
  await api.sendChat({ message: "질문", conversation_id: null });

  assert.match(calls[0].url, /id%2Fwith%2Fslash$/);
  assert.deepEqual(JSON.parse(calls[1].options.body), {
    message: "질문",
    conversation_id: null,
  });
});
