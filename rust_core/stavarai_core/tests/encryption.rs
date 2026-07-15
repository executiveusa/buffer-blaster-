// Integration test: AES-256-GCM encryption contract
// Run: cargo test --manifest-path rust_core/stavarai_core/Cargo.toml --test encryption

use stavarai_core::encryption::{decrypt, encrypt, mask_key};

const TEST_KEY: [u8; 32] = [0u8; 32];

#[test]
fn encrypt_decrypt_roundtrip() {
    let plaintext = "sk-ant-test-api-key-1234567890";
    let ciphertext = encrypt(plaintext, &TEST_KEY).unwrap();
    let decrypted = decrypt(&ciphertext, &TEST_KEY).unwrap();
    assert_eq!(plaintext, decrypted);
}

#[test]
fn ciphertext_is_not_plaintext() {
    let plaintext = "sk-ant-test-api-key-1234567890";
    let ciphertext = encrypt(plaintext, &TEST_KEY).unwrap();
    assert_ne!(plaintext, ciphertext);
    assert!(!ciphertext.contains("sk-ant"));
}

#[test]
fn wrong_key_fails_decryption() {
    let ciphertext = encrypt("my-secret-key", &TEST_KEY).unwrap();
    let wrong_key = [1u8; 32];
    assert!(decrypt(&ciphertext, &wrong_key).is_err());
}

#[test]
fn mask_shows_last_4_chars() {
    let key = "sk-ant-api03-abcdefghijklmnop-1234";
    let masked = mask_key(key);
    assert!(masked.ends_with("1234"));
    assert!(masked.contains("•"));
    assert!(!masked.contains("sk-ant"));
}

#[test]
fn random_nonce_produces_different_ciphertext() {
    // AES-GCM with random nonce: same plaintext → different ciphertext,
    // but both decrypt back to the same value.
    let plaintext = "same-plaintext";
    let c1 = encrypt(plaintext, &TEST_KEY).unwrap();
    let c2 = encrypt(plaintext, &TEST_KEY).unwrap();
    assert_ne!(c1, c2);
    assert_eq!(decrypt(&c1, &TEST_KEY).unwrap(), decrypt(&c2, &TEST_KEY).unwrap());
}

#[test]
fn empty_plaintext_roundtrips() {
    let ciphertext = encrypt("", &TEST_KEY).unwrap();
    assert_eq!(decrypt(&ciphertext, &TEST_KEY).unwrap(), "");
}

#[test]
fn malformed_ciphertext_errors() {
    assert!(decrypt("not-valid-base64!!!", &TEST_KEY).is_err());
    assert!(decrypt("", &TEST_KEY).is_err());
}
