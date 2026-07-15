// Integration test: token-bucket rate limiter contract
// Run: cargo test --manifest-path rust_core/stavarai_core/Cargo.toml --test rate_limiter

use stavarai_core::rate_limiter::RateLimiter;
use std::thread;
use std::time::Duration;

#[test]
fn allows_up_to_capacity_then_blocks() {
    let rl = RateLimiter::new();
    let key = "ip:1.2.3.4:auth";
    // capacity 5
    for _ in 0..5 {
        assert!(rl.check(key, 5.0, 1.0).is_ok(), "should allow within capacity");
    }
    // 6th is blocked
    let result = rl.check(key, 5.0, 1.0);
    assert!(result.is_err(), "6th request should be blocked");
    if let Err(retry_after) = result {
        assert!(retry_after > 0, "retry_after should be positive");
    }
}

#[test]
fn different_keys_have_independent_buckets() {
    let rl = RateLimiter::new();
    for _ in 0..3 {
        assert!(rl.check("user-a", 3.0, 1.0).is_ok());
    }
    // user-a is full; user-b is fresh
    assert!(rl.check("user-a", 3.0, 1.0).is_err());
    assert!(rl.check("user-b", 3.0, 1.0).is_ok());
}

#[test]
fn bucket_refills_over_time() {
    let rl = RateLimiter::new();
    let key = "ip:refill-test";
    // drain the bucket (cap 2)
    assert!(rl.check(key, 2.0, 10.0).is_ok());
    assert!(rl.check(key, 2.0, 10.0).is_ok());
    assert!(rl.check(key, 2.0, 10.0).is_err());
    // wait > 0.1s → at rate 10/s, 1 token refills
    thread::sleep(Duration::from_millis(150));
    assert!(rl.check(key, 2.0, 10.0).is_ok());
}

#[test]
fn empty_key_works() {
    let rl = RateLimiter::new();
    assert!(rl.check("", 1.0, 1.0).is_ok());
    assert!(rl.check("", 1.0, 1.0).is_err());
}
