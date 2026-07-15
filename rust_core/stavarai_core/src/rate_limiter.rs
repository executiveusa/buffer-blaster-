//! Token-bucket rate limiter, keyed by an arbitrary string (IP, session, route).
//!
//! `check(key, capacity, rate_per_sec)`:
//!   - deducts 1 token if the bucket has ≥ 1 (Ok)
//!   - else returns Err(retry_after_secs)
//! Buckets are created lazily on first sight of a key and refilled lazily on
//! each check (no background thread). Fully thread-safe.

use std::collections::HashMap;
use std::sync::Mutex;
use std::time::{SystemTime, UNIX_EPOCH};

fn now_secs() -> f64 {
    SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs_f64())
        .unwrap_or(0.0)
}

struct Bucket {
    tokens: f64,
    last_refill: f64,
    rate: f64,      // tokens per second
    capacity: f64,
}

pub struct RateLimiter {
    buckets: Mutex<HashMap<String, Bucket>>,
}

impl RateLimiter {
    pub fn new() -> Self {
        Self {
            buckets: Mutex::new(HashMap::new()),
        }
    }

    /// Returns `Ok(())` if a request is allowed, or `Err(retry_after_secs)`
    /// indicating how long the caller should wait before retrying.
    pub fn check(&self, key: &str, capacity: f64, rate: f64) -> Result<(), u64> {
        let now = now_secs();
        let mut map = self.buckets.lock().expect("ratelimit mutex poisoned");

        let bucket = map.entry(key.to_string()).or_insert(Bucket {
            tokens: capacity,
            last_refill: now,
            rate,
            capacity,
        });

        // Keep the bucket's rate/capacity current (allows callers to change
        // limits per-call without recreating the limiter).
        bucket.rate = rate;
        bucket.capacity = capacity;

        // Lazy refill.
        let elapsed = now - bucket.last_refill;
        if elapsed > 0.0 {
            bucket.tokens = (bucket.tokens + elapsed * rate).min(capacity);
            bucket.last_refill = now;
        }

        if bucket.tokens >= 1.0 {
            bucket.tokens -= 1.0;
            Ok(())
        } else {
            let deficit = 1.0 - bucket.tokens;
            let retry_after = (deficit / rate).ceil().max(1.0) as u64;
            Err(retry_after)
        }
    }
}

impl Default for RateLimiter {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn capacity_respected() {
        let rl = RateLimiter::new();
        for _ in 0..3 {
            assert!(rl.check("k", 3.0, 1.0).is_ok());
        }
        assert!(rl.check("k", 3.0, 1.0).is_err());
    }
}
