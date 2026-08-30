import "server-only";
import { createHmac, timingSafeEqual } from "node:crypto";

export const TRIAL_COOKIE = "social_studio_trial";

type TrialSession = {
  walletId: string;
  offerId: string;
  exp: number;
};

function secret() {
  const value = process.env.TRIAL_SESSION_SECRET?.trim() || process.env.BLASTER_API_KEY?.trim();
  if (!value) throw new Error("TRIAL_SESSION_SECRET or BLASTER_API_KEY is required");
  return value;
}

function signature(payload: string) {
  return createHmac("sha256", secret()).update(payload).digest("base64url");
}

export function signTrialSession(session: TrialSession) {
  const payload = Buffer.from(JSON.stringify(session), "utf8").toString("base64url");
  return `${payload}.${signature(payload)}`;
}

export function verifyTrialSession(token: string | undefined | null): TrialSession | null {
  if (!token) return null;
  const [payload, supplied] = token.split(".");
  if (!payload || !supplied) return null;
  const expected = signature(payload);
  const a = Buffer.from(supplied);
  const b = Buffer.from(expected);
  if (a.length !== b.length || !timingSafeEqual(a, b)) return null;
  try {
    const decoded = JSON.parse(Buffer.from(payload, "base64url").toString("utf8")) as TrialSession;
    if (!decoded.walletId || !decoded.offerId || !decoded.exp || decoded.exp <= Math.floor(Date.now() / 1000)) return null;
    return decoded;
  } catch {
    return null;
  }
}

export function backendBaseUrl() {
  return (process.env.BLASTER_API_URL || process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");
}

export function backendHeaders() {
  const key = process.env.BLASTER_API_KEY?.trim();
  if (!key) throw new Error("BLASTER_API_KEY is required for server proxy calls");
  return { "Content-Type": "application/json", "x-api-key": key };
}
