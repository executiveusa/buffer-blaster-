//! Session-token generation, password verification, and session storage.
//!
//! Tokens are 256-bit cryptographically-random values, base64url-encoded.
//! Password comparison is constant-time via SHA-256 + `subtle::ConstantTimeEq`
//! (so a wrong password of the same length still takes the same path).
//! Session store is in-memory; for multi-process deploys, swap for Redis.

use base64::{engine::general_purpose::URL_SAFE_NO_PAD, Engine};
use rand::{rngs::OsRng, RngCore};
use sha2::{Digest, Sha256};
use std::collections::HashMap;
use std::sync::Mutex;
use std::time::{SystemTime, UNIX_EPOCH};
use subtle::ConstantTimeEq;

const SESSION_TTL_SECS: u64 = 86_400; // 24 hours

fn now_secs() -> u64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0)
}

/// Generate a fresh 256-bit session token (base64url, ≥ 43 chars).
pub fn generate_session_token() -> String {
    let mut bytes = [0u8; 32];
    OsRng.fill_bytes(&mut bytes);
    URL_SAFE_NO_PAD.encode(&bytes)
}

/// Hash a password to a fixed-length digest. Used to compare without exposing
/// length information through timing short-circuits.
fn hash(pw: &str) -> [u8; 32] {
    let mut h = Sha256::new();
    h.update(pw.as_bytes());
    let out = h.finalize();
    let mut arr = [0u8; 32];
    arr.copy_from_slice(&out);
    arr
}

/// Verify `password` against `expected` using constant-time comparison.
/// On success, mints a session token and registers it in `store`.
pub fn verify_password(
    password: &str,
    expected: &str,
    store: &SessionStore,
) -> Result<String, &'static str> {
    let a = hash(password);
    let b = hash(expected);
    if a.ct_eq(&b).unwrap_u8() == 0 {
        return Err("invalid password");
    }
    let token = generate_session_token();
    store.insert(&token);
    Ok(token)
}

/// In-memory session store keyed by token → expiry timestamp.
pub struct SessionStore {
    sessions: Mutex<HashMap<String, u64>>,
}

impl SessionStore {
    pub fn new() -> Self {
        Self {
            sessions: Mutex::new(HashMap::new()),
        }
    }

    /// Register a freshly-minted token with the default TTL.
    pub fn insert(&self, token: &str) {
        self.sessions
            .lock()
            .expect("session mutex poisoned")
            .insert(token.to_string(), now_secs() + SESSION_TTL_SECS);
    }

    /// True iff `token` exists and has not expired.
    pub fn validate(&self, token: &str) -> bool {
        let mut map = self.sessions.lock().expect("session mutex poisoned");
        let now = now_secs();
        // expire-on-read
        let live = map
            .get(token)
            .map(|&expiry| now < expiry)
            .unwrap_or(false);
        if !live {
            map.remove(token);
        }
        live
    }

    /// Manually revoke a token (logout).
    pub fn invalidate(&self, token: &str) {
        self.sessions
            .lock()
            .expect("session mutex poisoned")
            .remove(token);
    }
}

impl Default for SessionStore {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn token_len() {
        assert!(generate_session_token().len() >= 43);
    }
}
