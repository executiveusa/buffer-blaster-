// Integration test: session auth contract
// Run: cargo test --manifest-path rust_core/stavarai_core/Cargo.toml --test auth

use stavarai_core::auth::{generate_session_token, verify_password};
use stavarai_core::auth::SessionStore;

const DEMO_PASSWORD: &str = "BLASTER2026";

#[test]
fn token_is_long_and_url_safe() {
    let token = generate_session_token();
    // 256-bit = 32 bytes → base64url ≥ 43 chars
    assert!(token.len() >= 43, "token too short: {}", token.len());
    assert!(
        token.chars().all(|c| c.is_ascii_alphanumeric() || c == '-' || c == '_'),
        "token not url-safe: {token}"
    );
}

#[test]
fn tokens_are_unique() {
    let t1 = generate_session_token();
    let t2 = generate_session_token();
    assert_ne!(t1, t2);
}

#[test]
fn correct_password_returns_session() {
    let store = SessionStore::new();
    let result = verify_password(DEMO_PASSWORD, DEMO_PASSWORD, &store);
    assert!(result.is_ok(), "correct password should succeed");
    let token = result.unwrap();
    assert!(token.len() >= 43);
}

#[test]
fn wrong_password_is_rejected() {
    let store = SessionStore::new();
    let result = verify_password("wrong", DEMO_PASSWORD, &store);
    assert!(result.is_err());
}

#[test]
fn issued_token_validates() {
    let store = SessionStore::new();
    let token = verify_password(DEMO_PASSWORD, DEMO_PASSWORD, &store).unwrap();
    assert!(store.validate(&token));
}

#[test]
fn random_token_does_not_validate() {
    let store = SessionStore::new();
    assert!(!store.validate("not-a-real-token"));
    assert!(!store.validate(""));
}

#[test]
fn logout_invalidates_token() {
    let store = SessionStore::new();
    let token = verify_password(DEMO_PASSWORD, DEMO_PASSWORD, &store).unwrap();
    assert!(store.validate(&token));
    store.invalidate(&token);
    assert!(!store.validate(&token));
}

#[test]
fn password_compare_is_constant_time_safe() {
    // A wrong password of the same length must still fail (no length leak shortcut).
    let store = SessionStore::new();
    let same_len_wrong = "BLASTER2027";
    assert_eq!(same_len_wrong.len(), DEMO_PASSWORD.len());
    assert!(verify_password(same_len_wrong, DEMO_PASSWORD, &store).is_err());
}
