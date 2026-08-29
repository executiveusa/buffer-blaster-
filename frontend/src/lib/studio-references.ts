"use client";

import { getToken, isDemoMode, isPublicConsole } from "./api";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function authHeaders() {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export type ReferenceAsset = {
  id: string;
  kind: string;
  source_url?: string | null;
  storage_url?: string | null;
  signed_url?: string | null;
  metadata?: { label?: string; filename?: string; content_type?: string };
  created_at?: string;
};

export async function listReferences(): Promise<ReferenceAsset[]> {
  if (isDemoMode() || isPublicConsole()) return [];
  const response = await fetch(`${API_URL}/api/studio/references`, { headers: { ...authHeaders() }, cache: "no-store" });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || body.error || response.statusText);
  return body.assets || [];
}

export async function addReferenceUrl(url: string, label = "") {
  const response = await fetch(`${API_URL}/api/studio/references/url`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ url, label, kind: "reference" }),
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok || body.ok === false) throw new Error(body.detail || body.error || response.statusText);
  return body.asset as ReferenceAsset;
}

export async function uploadReference(file: File, label = "") {
  const data = new FormData();
  data.set("file", file);
  data.set("label", label);
  const response = await fetch(`${API_URL}/api/studio/references/upload`, {
    method: "POST",
    headers: { ...authHeaders() },
    body: data,
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok || body.ok === false) throw new Error(body.detail || body.error || response.statusText);
  return (body.asset || body) as ReferenceAsset;
}
