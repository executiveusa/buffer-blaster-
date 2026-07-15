//! stavarai_core — hot-path primitives for the Stavarai Platform.
//!
//! Four modules, all synchronous and dependency-light:
//!   - `encryption`  AES-256-GCM encrypt/decrypt + key masking
//!   - `auth`        256-bit session tokens + in-memory session store
//!   - `rate_limiter` per-key token bucket
//!   - `job_queue`   in-memory FIFO job queue with status tracking
//!
//! Design notes:
//!   - No `tokio`, no async — these are called from FFI / PyO3 / axum sync handlers.
//!   - All thread-safe (`Mutex`-guarded) so multiple workers can share state.
//!   - Secrets are never logged; ciphertext format is `base64url(nonce || ct)`.

pub mod encryption;
pub mod auth;
pub mod rate_limiter;
pub mod job_queue;
