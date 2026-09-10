import assert from "node:assert/strict";
import test from "node:test";
import worker from "./worker.mjs";

test("rejects cross-origin mutations before forwarding", async () => {
  const response = await worker.fetch(new Request("https://relay.sarthakagrawal.dev/api/session", {
    method: "POST", headers: { origin: "https://unrelated.example" },
  }));
  assert.equal(response.status, 403);
});

test("preserves cookies, body, and path while translating a validated origin", async (t) => {
  t.mock.method(globalThis, "fetch", async (request, options) => {
    assert.equal(request.url, "https://s5yxc4zxd7avumdlujounefyyu0vvpeu.lambda-url.us-east-1.on.aws/api/reports?source=demo");
    assert.equal(request.headers.get("origin"), new URL(request.url).origin);
    assert.equal(request.headers.get("host"), new URL(request.url).host);
    assert.equal(request.headers.get("cookie"), "relay_workspace=synthetic");
    assert.equal(await request.text(), '{"text":"fictional report"}');
    assert.equal(options.redirect, "manual");
    return new Response("ok", { headers: { "Set-Cookie": "relay_workspace=synthetic; Secure; HttpOnly; SameSite=Strict" } });
  });
  const response = await worker.fetch(new Request("https://relay.sarthakagrawal.dev/api/reports?source=demo", {
    method: "POST", body: '{"text":"fictional report"}',
    headers: { origin: "https://relay.sarthakagrawal.dev", cookie: "relay_workspace=synthetic" },
  }));
  assert.equal(response.status, 200);
  assert.match(response.headers.get("set-cookie"), /HttpOnly/);
  assert.equal(response.headers.get("cache-control"), "no-store");
});
