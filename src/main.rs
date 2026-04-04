use anyhow::Result;
use qb_api::{
    api::{router, AppState},
    config::AppConfig,
    db::create_pool,
};
use tokio::net::TcpListener;

#[tokio::main]
async fn main() -> Result<()> {
    tracing_subscriber::fmt()
        .with_env_filter(
            tracing_subscriber::EnvFilter::try_from_default_env().unwrap_or_else(|_| "info".into()),
        )
        .init();

    let cfg = AppConfig::from_env()?;
    let pool = create_pool(&cfg.database_url, cfg.max_db_connections).await?;

    let state = AppState {
        pool,
        export_dir: cfg.export_dir.clone(),
    };
    let app = router(state, &cfg.cors_origins);
    let listener = TcpListener::bind(cfg.bind_addr).await?;

    tracing::info!(addr = %cfg.bind_addr, "qb_api_rust listening");
    axum::serve(listener, app)
        .with_graceful_shutdown(shutdown_signal())
        .await?;
    Ok(())
}

async fn shutdown_signal() {
    let ctrl_c = async {
        tokio::signal::ctrl_c()
            .await
            .expect("install Ctrl+C handler");
    };
    #[cfg(unix)]
    let terminate = async {
        tokio::signal::unix::signal(tokio::signal::unix::SignalKind::terminate())
            .expect("install SIGTERM handler")
            .recv()
            .await;
    };
    #[cfg(not(unix))]
    let terminate = std::future::pending::<()>();

    tokio::select! {
        _ = ctrl_c => {},
        _ = terminate => {},
    }
    tracing::info!("shutdown signal received");
}
