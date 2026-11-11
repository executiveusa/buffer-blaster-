/**
 * Supabase Auth client for the operator console.
 *
 * Active only when NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY
 * are set; otherwise the console keeps its legacy password login (which the
 * API only serves while DEMO_PASSWORD_LOGIN_ENABLED is set).
 */
import { createClient, type SupabaseClient } from "@supabase/supabase-js";

const SUPABASE_URL = process.env.NEXT_PUBLIC_SUPABASE_URL || "";
const SUPABASE_ANON_KEY = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY || "";

export function supabaseAuthEnabled(): boolean {
  return Boolean(SUPABASE_URL && SUPABASE_ANON_KEY);
}

let client: SupabaseClient | null = null;

export function getSupabase(): SupabaseClient | null {
  if (!supabaseAuthEnabled()) return null;
  if (!client) client = createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
  return client;
}

export async function signInWithEmail(email: string, password: string): Promise<string> {
  const supabase = getSupabase();
  if (!supabase) throw new Error("Supabase Auth is not configured.");
  const { data, error } = await supabase.auth.signInWithPassword({ email, password });
  if (error || !data.session) throw new Error(error?.message || "Sign-in failed.");
  return data.session.access_token;
}

/** Current access token, refreshed by supabase-js when expired. Null when signed out. */
export async function freshAccessToken(): Promise<string | null> {
  const supabase = getSupabase();
  if (!supabase) return null;
  const { data } = await supabase.auth.getSession();
  return data.session?.access_token ?? null;
}

export async function signOutSupabase(): Promise<void> {
  await getSupabase()?.auth.signOut();
}
