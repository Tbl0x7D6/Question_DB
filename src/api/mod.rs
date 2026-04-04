//! HTTP API composition for the question bank service.

mod admin;
mod ops;
mod papers;
mod questions;
mod shared;
mod system;
mod tests;

use std::path::PathBuf;

use axum::{extract::DefaultBodyLimit, Router};
use sqlx::PgPool;
use tower_http::cors::{Any, CorsLayer};
use tower_http::trace::TraceLayer;

pub use self::papers::models::{PaperDetail, PaperQuestionSummary, PaperSummary};
pub use self::questions::models::{
    QuestionAssetRef, QuestionDetail, QuestionPaperRef, QuestionSummary,
};

#[derive(Clone)]
pub struct AppState {
    pub pool: PgPool,
    pub export_dir: PathBuf,
}

/// Build the complete Axum router for the service.
pub fn router(state: AppState, cors_origins: &[String]) -> Router {
    let cors = if cors_origins.is_empty() {
        CorsLayer::new()
            .allow_origin(Any)
            .allow_methods(Any)
            .allow_headers(Any)
    } else {
        let origins = cors_origins
            .iter()
            .filter_map(|o| o.parse().ok())
            .collect::<Vec<_>>();
        CorsLayer::new()
            .allow_origin(origins)
            .allow_methods(Any)
            .allow_headers(Any)
    };

    Router::new()
        .merge(admin::router())
        .merge(system::router())
        .merge(papers::router())
        .merge(questions::router())
        .merge(ops::router())
        .layer(DefaultBodyLimit::max(
            questions::MAX_UPLOAD_BYTES.max(papers::MAX_UPLOAD_BYTES),
        ))
        .layer(cors)
        .layer(TraceLayer::new_for_http())
        .with_state(state)
}
