//! Shared pagination types and helpers.

use serde::Serialize;

/// Envelope for paginated list responses.
#[derive(Debug, Serialize)]
pub(crate) struct Paginated<T: Serialize> {
    pub(crate) items: Vec<T>,
    pub(crate) total: i64,
    pub(crate) limit: i64,
    pub(crate) offset: i64,
}

/// Clamp a user-provided limit to `[1, 100]`, defaulting to 20.
pub(crate) fn normalize_limit(raw: Option<i64>) -> i64 {
    raw.unwrap_or(20).clamp(1, 100)
}

/// Clamp a user-provided offset to `>= 0`, defaulting to 0.
pub(crate) fn normalize_offset(raw: Option<i64>) -> i64 {
    raw.unwrap_or(0).max(0)
}
