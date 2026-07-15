//! AES-256-GCM encryption for secrets stored at rest.
//!
//! Format: `base64url(nonce[12] || ciphertext_with_tag)` — no prefix, no metadata.
//! Nonce is cryptographically random per call, so encrypting the same plaintext
//! twice yields two different ciphertexts (verified by test).

use aes_gcm::{
    aead::{Aead, KeyInit, OsRng, rand_core::RngCore},
    Aes256Gcm, Key, Nonce,
};
use base64::{engine::general_purpose::URL_SAFE_NO_PAD, Engine};

pub type Key32 = [u8; 32];

/// Encrypt `plaintext` under `key`. Returns base64url(nonce || ciphertext+tag).
pub fn encrypt(plaintext: &str, key: &Key32) -> Result<String, String> {
    let cipher = Aes256Gcm::new(Key::<Aes256Gcm>::from_slice(key));

    let mut nonce_bytes = [0u8; 12];
    OsRng.fill_bytes(&mut nonce_bytes);
    let nonce = Nonce::from_slice(&nonce_bytes);

    let ciphertext = cipher
        .encrypt(nonce, plaintext.as_bytes())
        .map_err(|e| format!("encrypt: {e}"))?;

    let mut combined = Vec::with_capacity(12 + ciphertext.len());
    combined.extend_from_slice(&nonce_bytes);
    combined.extend_from_slice(&ciphertext);
    Ok(URL_SAFE_NO_PAD.encode(&combined))
}

/// Decrypt a value produced by [`encrypt`]. Fails on wrong key or tampered data.
pub fn decrypt(encoded: &str, key: &Key32) -> Result<String, String> {
    if encoded.is_empty() {
        return Err("decrypt: empty ciphertext".into());
    }
    let combined = URL_SAFE_NO_PAD
        .decode(encoded)
        .map_err(|e| format!("decrypt: invalid base64 ({e})"))?;

    if combined.len() < 12 + 16 {
        return Err("decrypt: ciphertext too short".into());
    }
    let (nonce_bytes, ciphertext) = combined.split_at(12);

    let cipher = Aes256Gcm::new(Key::<Aes256Gcm>::from_slice(key));
    let plaintext = cipher
        .decrypt(Nonce::from_slice(nonce_bytes), ciphertext)
        .map_err(|_| "decrypt: wrong key or tampered data".to_string())?;

    String::from_utf8(plaintext).map_err(|e| format!("decrypt: not utf8 ({e})"))
}

/// Mask a secret for display: keep only the last 4 characters, replace the rest
/// with bullets. Never logs or returns the original.
pub fn mask_key(key: &str) -> String {
    let last4 = key.chars().rev().take(4).collect::<Vec<_>>();
    if last4.is_empty() {
        return "•".repeat(key.len().max(4));
    }
    let last4: String = last4.into_iter().rev().collect();
    format!("{}{last4}", "•".repeat(12))
}

#[cfg(test)]
mod tests {
    use super::*;

    const K: Key32 = [7u8; 32];

    #[test]
    fn roundtrip() {
        let c = encrypt("hello", &K).unwrap();
        assert_eq!(decrypt(&c, &K).unwrap(), "hello");
    }
}
