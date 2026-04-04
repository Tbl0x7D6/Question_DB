//! Shared database helpers used across question and paper modules.

use std::path::Path;

use anyhow::{Context, Result};
use sqlx::{query, PgPool, Postgres, Row, Transaction};
use uuid::Uuid;

/// Insert a binary object into the `objects` table and return the new object ID.
pub(crate) async fn insert_object_tx(
    tx: &mut Transaction<'_, Postgres>,
    file_name: &str,
    bytes: &[u8],
    mime_type: Option<&str>,
) -> Result<String> {
    let object_id = Uuid::new_v4().to_string();
    let normalized_file_name = Path::new(file_name)
        .file_name()
        .map(|name| name.to_string_lossy().to_string())
        .unwrap_or_else(|| "blob.bin".to_string());

    query(
        r#"
        INSERT INTO objects (object_id, file_name, mime_type, size_bytes, content, created_at)
        VALUES ($1::uuid, $2, $3, $4, $5, NOW())
        "#,
    )
    .bind(&object_id)
    .bind(&normalized_file_name)
    .bind(mime_type)
    .bind(i64::try_from(bytes.len()).context("object bytes exceed i64 range")?)
    .bind(bytes)
    .execute(&mut **tx)
    .await
    .context("insert object failed")?;

    Ok(object_id)
}

/// Fetch the raw binary content of an object by ID.
pub(crate) async fn fetch_object_bytes(pool: &PgPool, object_id: &str) -> Result<Vec<u8>> {
    let row = query("SELECT content FROM objects WHERE object_id = $1::uuid")
        .bind(object_id)
        .fetch_one(pool)
        .await
        .with_context(|| format!("fetch object failed: {object_id}"))?;

    Ok(row.get("content"))
}

/// Fetch the content of a text object (UTF-8 with lossy fallback).
pub(crate) async fn fetch_text_object(pool: &PgPool, object_id: &str) -> Result<String> {
    let bytes = fetch_object_bytes(pool, object_id).await?;
    Ok(String::from_utf8_lossy(&bytes).to_string())
}

/// Normalize an upload file name, using the given default when the name is
/// missing or blank.
pub(crate) fn normalize_upload_file_name(file_name: Option<&str>, default: &str) -> String {
    file_name
        .and_then(|value| Path::new(value).file_name())
        .map(|value| value.to_string_lossy().to_string())
        .filter(|value| !value.trim().is_empty())
        .unwrap_or_else(|| default.to_string())
}
