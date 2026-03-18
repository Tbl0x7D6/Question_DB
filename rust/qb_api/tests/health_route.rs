use axum::{body::Body, http::Request};
use http_body_util::BodyExt;
use qb_api::api::{router, AppState};
use sqlx::postgres::PgPoolOptions;
use tower::ServiceExt;

#[tokio::test]
async fn health_route_returns_ok_json() {
    let pool = PgPoolOptions::new()
        .max_connections(1)
        .connect_lazy("postgres://postgres:postgres@localhost/qb")
        .unwrap();
    let app = router(AppState { pool });

    let response = app
        .oneshot(
            Request::builder()
                .uri("/health")
                .body(Body::empty())
                .unwrap(),
        )
        .await
        .unwrap();

    assert_eq!(response.status(), 200);
    let body = response.into_body().collect().await.unwrap().to_bytes();
    let body_str = std::str::from_utf8(&body).unwrap();
    assert!(body_str.contains("\"status\":\"ok\""));
    assert!(body_str.contains("\"service\":\"qb_api_rust\""));
}
