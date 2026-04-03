pub(crate) mod handlers;
pub(crate) mod models;
pub(crate) mod queries;

use axum::{routing::get, Router};

pub(crate) fn router() -> Router<super::AppState> {
    Router::new()
        .route("/admin/questions", get(handlers::list_questions))
        .route(
            "/admin/questions/:question_id",
            get(handlers::get_question_detail),
        )
        .route(
            "/admin/questions/:question_id/restore",
            axum::routing::post(handlers::restore_question),
        )
        .route("/admin/papers", get(handlers::list_papers))
        .route("/admin/papers/:paper_id", get(handlers::get_paper_detail))
        .route(
            "/admin/papers/:paper_id/restore",
            axum::routing::post(handlers::restore_paper),
        )
        .route(
            "/admin/garbage-collections/preview",
            axum::routing::post(handlers::preview_gc),
        )
        .route(
            "/admin/garbage-collections/run",
            axum::routing::post(handlers::run_gc),
        )
}
