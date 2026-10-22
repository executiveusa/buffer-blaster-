import { NextRequest } from "next/server";

function backendBaseUrl() {
  const raw = (process.env.BLASTER_API_URL || process.env.NEXT_PUBLIC_API_URL || "").trim();
  if (!raw) throw new Error("backend_not_configured");
  const url = new URL(raw);
  if (!["http:", "https:"].includes(url.protocol)) throw new Error("invalid_backend_protocol");
  return url.toString().replace(/\/$/, "");
}

function consoleOpen(): boolean {
  return (process.env.CONSOLE_OPEN || "").trim().toLowerCase() === "true";
}

let cachedSession: { token: string; expiresAt: number } | null = null;

async function mintOperatorSession(base: string): Promise<string | null> {
  if (cachedSession && cachedSession.expiresAt > Date.now() + 60_000) return cachedSession.token;
  const password = (process.env.BLASTER_OPERATOR_PASSWORD || "").trim();
  if (!password) return null;
  try {
    const response = await fetch(`${base}/api/auth/verify`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ password }),
      cache: "no-store",
    });
    if (!response.ok) return null;
    const data = await response.json();
    const token = typeof data?.session_token === "string" ? data.session_token : null;
    const ttl = typeof data?.expires_in === "number" ? data.expires_in : 3600;
    if (!token) return null;
    cachedSession = { token, expiresAt: Date.now() + Math.min(ttl, 86400) * 1000 };
    return token;
  } catch {
    return null;
  }
}

async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const { path } = await context.params;
  if (!path?.length || path[0] !== "api") {
    return Response.json({ error: "unsupported_backend_path" }, { status: 404 });
  }

  let base: string;
  try {
    base = backendBaseUrl();
  } catch {
    return Response.json({ error: "backend_not_configured" }, { status: 503 });
  }

  const target = new URL(`/${path.map(encodeURIComponent).join("/")}`, base);
  target.search = request.nextUrl.search;

  const headers = new Headers();
  for (const key of ["authorization", "content-type", "accept", "x-api-key"]) {
    const value = request.headers.get(key);
    if (value) headers.set(key, value);
  }

  let injectedSession = false;
  if (consoleOpen() && !headers.has("authorization")) {
    const token = await mintOperatorSession(base);
    if (token) {
      headers.set("authorization", `Bearer ${token}`);
      injectedSession = true;
    }
  }

  const init: RequestInit = {
    method: request.method,
    headers,
    cache: "no-store",
    redirect: "manual",
  };

  if (!["GET", "HEAD"].includes(request.method)) {
    init.body = await request.arrayBuffer();
  }

  try {
    let upstream = await fetch(target, init);
    if (upstream.status === 401 && injectedSession) {
      cachedSession = null;
      const fresh = await mintOperatorSession(base);
      if (fresh) {
        headers.set("authorization", `Bearer ${fresh}`);
        upstream = await fetch(target, init);
      }
    }
    const responseHeaders = new Headers();
    for (const key of ["content-type", "content-disposition", "cache-control"]) {
      const value = upstream.headers.get(key);
      if (value) responseHeaders.set(key, value);
    }
    responseHeaders.set("cache-control", "no-store");

    return new Response(upstream.body, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers: responseHeaders,
    });
  } catch {
    return Response.json({ error: "backend_unreachable" }, { status: 502 });
  }
}

export const dynamic = "force-dynamic";

export function GET(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxy(request, context);
}

export function POST(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxy(request, context);
}

export function PUT(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxy(request, context);
}

export function PATCH(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxy(request, context);
}

export function DELETE(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  return proxy(request, context);
}
