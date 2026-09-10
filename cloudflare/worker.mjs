const ORIGIN = "https://s5yxc4zxd7avumdlujounefyyu0vvpeu.lambda-url.us-east-1.on.aws";

export default {
  async fetch(request) {
    const incoming = new URL(request.url);
    const originHeader = request.headers.get("origin");
    // Check the browser origin before translating it for the AWS host guard.
    if (originHeader && originHeader !== incoming.origin) {
      return new Response("Cross-origin request rejected", { status: 403 });
    }
    const upstream = new URL(ORIGIN);
    upstream.pathname = incoming.pathname;
    upstream.search = incoming.search;
    const forwarded = new Request(upstream, request);
    forwarded.headers.set("host", upstream.host);
    if (originHeader) forwarded.headers.set("origin", upstream.origin);
    try {
      const response = await fetch(forwarded, { redirect: "manual", cache: "no-store" });
      const result = new Response(response.body, response);
      // API responses and workspace cookies must never enter a shared edge cache.
      result.headers.set("Cache-Control", "no-store");
      const location = result.headers.get("location");
      if (location) {
        const destination = new URL(location, upstream);
        if (destination.origin === upstream.origin) {
          destination.protocol = incoming.protocol;
          destination.host = incoming.host;
          result.headers.set("location", destination.href);
        }
      }
      return result;
    } catch {
      return new Response("Society Relay is temporarily unavailable. Please try again shortly.", {
        status: 502,
        headers: { "Cache-Control": "no-store", "Content-Type": "text/plain; charset=utf-8" },
      });
    }
  },
};
