// TDD: Rust encryption tests — MUST FAIL before implementation
// Run: cargo test --manifest-path rust_core/stavarai_core/Cargo.toml

#[cfg(test)]
mod encryption_tests {
    use stavarai_core::encryption::{encrypt, decrypt, mask_key};

    const TEST_KEY: [u8; 32] = [0u8; 32]; // test key only

    #[test]
    fn test_encrypt_decrypt_roundtrip() {
        let plaintext = "sk-ant-test-api-key-1234567890";
        let ciphertext = encrypt(plaintext, &TEST_KEY).unwrap();
        let decrypted = decrypt(&ciphertext, &TEST_KEY).unwrap();
        assert_eq!(plaintext, decrypted);
    }

    #[test]
    fn test_ciphertext_is_not_plaintext() {
        let plaintext = "sk-ant-test-api-key-1234567890";
        let ciphertext = encrypt(plaintext, &TEST_KEY).unwrap();
        assert_ne!(plaintext, ciphertext);
        assert!(!ciphertext.contains("sk-ant"));
    }

    #[test]
    fn test_wrong_key_fails_decryption() {
        let plaintext = "my-secret-key";
        let ciphertext = encrypt(plaintext, &TEST_KEY).unwrap();
        let wrong_key = [1u8; 32];
        let result = decrypt(&ciphertext, &wrong_key);
        assert!(result.is_err());
    }

    #[test]
    fn test_mask_shows_last_4_chars() {
        let key = "sk-ant-api03-abcdefghijklmnop-1234";
        let masked = mask_key(key);
        assert!(masked.ends_with("1234"));
        assert!(masked.contains("•"));
        assert!(!masked.contains("sk-ant"));
    }

    #[test]
    fn test_encryption_is_deterministic_nonce() {
        // Two encryptions of same plaintext should produce DIFFERENT ciphertext
        // (because AES-GCM uses random nonce)
        let plaintext = "same-plaintext";
        let c1 = encrypt(plaintext, &TEST_KEY).unwrap();
        let c2 = encrypt(plaintext, &TEST_KEY).unwrap();
        assert_ne!(c1, c2); // different nonces = different ciphertext
        // But both decrypt to same value
        assert_eq!(decrypt(&c1, &TEST_KEY).unwrap(), decrypt(&c2, &TEST_KEY).unwrap());
    }
}
