use axum::{
    extract::{Path as AxumPath, Query, State},
    Json,
};

use super::{
    models::{
        AdminPaperDetail, AdminPaperSummary, AdminPapersParams, AdminQuestionDetail,
        AdminQuestionSummary, AdminQuestionsParams, GarbageCollectionRequest,
        GarbageCollectionResponse,
    },
    queries::{
        list_admin_papers, list_admin_questions, load_admin_paper_detail,
        load_admin_question_detail, preview_garbage_collection,
        restore_paper as restore_paper_record, restore_question as restore_question_record,
        run_garbage_collection,
    },
};
use crate::api::{
    shared::{
        error::{ApiError, ApiResult},
        multipart::parse_uuid_param,
        pagination::Paginated,
    },
    AppState,
};

pub(crate) async fn list_questions(
    Query(params): Query<AdminQuestionsParams>,
    State(state): State<AppState>,
) -> ApiResult<Paginated<AdminQuestionSummary>> {
    let record_state = params
        .validate_filters()
        .map_err(|err| ApiError::bad_request(err.to_string()))?;
    let limit = params.normalized_limit();
    let offset = params.normalized_offset();
    let (questions, total) = list_admin_questions(&state.pool, &params, record_state)
        .await
        .map_err(ApiError::from)?;
    Ok(Json(Paginated {
        items: questions,
        total,
        limit,
        offset,
    }))
}

pub(crate) async fn get_question_detail(
    AxumPath(question_id): AxumPath<String>,
    State(state): State<AppState>,
) -> ApiResult<AdminQuestionDetail> {
    parse_uuid_param(&question_id, "question_id")?;
    Ok(Json(
        load_admin_question_detail(&state.pool, &question_id)
            .await
            .map_err(ApiError::from)?,
    ))
}

pub(crate) async fn restore_question(
    AxumPath(question_id): AxumPath<String>,
    State(state): State<AppState>,
) -> ApiResult<AdminQuestionDetail> {
    parse_uuid_param(&question_id, "question_id")?;
    Ok(Json(
        restore_question_record(&state.pool, &question_id)
            .await
            .map_err(ApiError::from)?,
    ))
}

pub(crate) async fn list_papers(
    Query(params): Query<AdminPapersParams>,
    State(state): State<AppState>,
) -> ApiResult<Paginated<AdminPaperSummary>> {
    let record_state = params
        .validate_filters()
        .map_err(|err| ApiError::bad_request(err.to_string()))?;
    let limit = params.normalized_limit();
    let offset = params.normalized_offset();
    let (papers, total) = list_admin_papers(&state.pool, &params, record_state)
        .await
        .map_err(ApiError::from)?;
    Ok(Json(Paginated {
        items: papers,
        total,
        limit,
        offset,
    }))
}

pub(crate) async fn get_paper_detail(
    AxumPath(paper_id): AxumPath<String>,
    State(state): State<AppState>,
) -> ApiResult<AdminPaperDetail> {
    parse_uuid_param(&paper_id, "paper_id")?;
    Ok(Json(
        load_admin_paper_detail(&state.pool, &paper_id)
            .await
            .map_err(ApiError::from)?,
    ))
}

pub(crate) async fn restore_paper(
    AxumPath(paper_id): AxumPath<String>,
    State(state): State<AppState>,
) -> ApiResult<AdminPaperDetail> {
    parse_uuid_param(&paper_id, "paper_id")?;
    Ok(Json(
        restore_paper_record(&state.pool, &paper_id)
            .await
            .map_err(ApiError::from)?,
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
