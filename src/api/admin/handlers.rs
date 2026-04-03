use axum::{
    extract::{Path as AxumPath, Query, State},
    http::StatusCode,
    Json,
};
use uuid::Uuid;

use super::{
    models::{
        AdminPaperDetail, AdminPaperSummary, AdminPapersParams, AdminQuestionDetail,
        AdminQuestionSummary, AdminQuestionsParams, GarbageCollectionRequest,
        GarbageCollectionResponse,
    },
    queries::{
        list_admin_papers, list_admin_questions, load_admin_paper_detail,
        load_admin_question_detail, map_admin_action_error, preview_garbage_collection,
        restore_paper as restore_paper_record, restore_question as restore_question_record,
        run_garbage_collection,
    },
};
use crate::api::{
    shared::error::{ApiError, ApiResult},
    AppState,
};

pub(crate) async fn list_questions(
    Query(params): Query<AdminQuestionsParams>,
    State(state): State<AppState>,
) -> ApiResult<Vec<AdminQuestionSummary>> {
    let record_state = params
        .validate_filters()
        .map_err(|err| ApiError::bad_request(err.to_string()))?;
    let questions = list_admin_questions(&state.pool, &params, record_state)
        .await
        .map_err(ApiError::from)?;
    Ok(Json(questions))
}

pub(crate) async fn get_question_detail(
    AxumPath(question_id): AxumPath<String>,
    State(state): State<AppState>,
) -> Result<Json<AdminQuestionDetail>, StatusCode> {
    Uuid::parse_str(&question_id).map_err(|_| StatusCode::BAD_REQUEST)?;
    load_admin_question_detail(&state.pool, &question_id)
        .await
        .map(Json)
        .map_err(map_admin_detail_status)
}

pub(crate) async fn restore_question(
    AxumPath(question_id): AxumPath<String>,
    State(state): State<AppState>,
) -> ApiResult<AdminQuestionDetail> {
    Uuid::parse_str(&question_id)
        .map_err(|_| ApiError::bad_request(format!("invalid question_id: {question_id}")))?;
    Ok(Json(
        restore_question_record(&state.pool, &question_id)
            .await
            .map_err(map_admin_action_error)?,
    ))
}

pub(crate) async fn list_papers(
    Query(params): Query<AdminPapersParams>,
    State(state): State<AppState>,
) -> ApiResult<Vec<AdminPaperSummary>> {
    let record_state = params
        .validate_filters()
        .map_err(|err| ApiError::bad_request(err.to_string()))?;
    let papers = list_admin_papers(&state.pool, &params, record_state)
        .await
        .map_err(ApiError::from)?;
    Ok(Json(papers))
}

pub(crate) async fn get_paper_detail(
    AxumPath(paper_id): AxumPath<String>,
    State(state): State<AppState>,
) -> Result<Json<AdminPaperDetail>, StatusCode> {
    Uuid::parse_str(&paper_id).map_err(|_| StatusCode::BAD_REQUEST)?;
    load_admin_paper_detail(&state.pool, &paper_id)
        .await
        .map(Json)
        .map_err(map_admin_detail_status)
}

pub(crate) async fn restore_paper(
    AxumPath(paper_id): AxumPath<String>,
    State(state): State<AppState>,
) -> ApiResult<AdminPaperDetail> {
    Uuid::parse_str(&paper_id)
        .map_err(|_| ApiError::bad_request(format!("invalid paper_id: {paper_id}")))?;
    Ok(Json(
        restore_paper_record(&state.pool, &paper_id)
            .await
            .map_err(map_admin_action_error)?,
    ))
}

pub(crate) async fn preview_gc(
    State(state): State<AppState>,
    Json(_request): Json<GarbageCollectionRequest>,
) -> ApiResult<GarbageCollectionResponse> {
    Ok(Json(
        preview_garbage_collection(&state.pool)
            .await
            .map_err(ApiError::from)?,
    ))
}

pub(crate) async fn run_gc(
    State(state): State<AppState>,
    Json(_request): Json<GarbageCollectionRequest>,
) -> ApiResult<GarbageCollectionResponse> {
    Ok(Json(
        run_garbage_collection(&state.pool)
            .await
            .map_err(ApiError::from)?,
    ))
}

fn map_admin_detail_status(err: anyhow::Error) -> StatusCode {
    if err.to_string().starts_with("question not found:")
        || err.to_string().starts_with("paper not found:")
    {
        StatusCode::NOT_FOUND
    } else {
        StatusCode::INTERNAL_SERVER_ERROR
    }
}
