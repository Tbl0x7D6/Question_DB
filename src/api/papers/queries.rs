use std::collections::HashSet;

use anyhow::{Context, Result};
use sqlx::{postgres::PgRow, query, PgPool, Postgres, QueryBuilder, Row};

use super::models::{validate_paper_filters, PapersParams};
use crate::api::shared::error::ApiError;

#[derive(Debug)]
pub(crate) struct PapersQuery {
    pub(crate) sql: String,
    pub(crate) bind_count: usize,
    pub(crate) limit: i64,
    pub(crate) offset: i64,
}

impl PapersParams {
    pub(crate) fn build_query(&self) -> PapersQuery {
        let mut builder = QueryBuilder::<Postgres>::new(
            "
            SELECT p.paper_id::text AS paper_id,
                   p.description,
                   p.title,
                   p.subtitle,
                   p.authors,
                   p.reviewers,
                   COUNT(pq_count.question_id) AS question_count,
                   to_char(p.created_at AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS.MS\"Z\"') AS created_at,
                   to_char(p.updated_at AT TIME ZONE 'UTC', 'YYYY-MM-DD\"T\"HH24:MI:SS.MS\"Z\"') AS updated_at
            FROM papers p
            LEFT JOIN paper_questions pq_count ON pq_count.paper_id = p.paper_id
            WHERE p.deleted_at IS NULL",
        );
        let mut bind_count = 0;

        if let Some(question_id) = &self.question_id {
            builder
                .push(" AND EXISTS (SELECT 1 FROM paper_questions pq WHERE pq.paper_id = p.paper_id AND pq.question_id = ")
                .push_bind(question_id)
                .push("::uuid)");
            bind_count += 1;
        }
        if let Some(category) = &self.category {
            builder
                .push(" AND EXISTS (SELECT 1 FROM paper_questions pq JOIN questions q ON q.question_id = pq.question_id WHERE pq.paper_id = p.paper_id AND q.deleted_at IS NULL AND q.category = ")
                .push_bind(category)
                .push(')');
            bind_count += 1;
        }
        if let Some(tag) = &self.tag {
            builder
                .push(" AND EXISTS (SELECT 1 FROM paper_questions pq JOIN questions q ON q.question_id = pq.question_id JOIN question_tags qt ON qt.question_id = pq.question_id WHERE pq.paper_id = p.paper_id AND q.deleted_at IS NULL AND qt.tag = ")
                .push_bind(tag)
                .push(')');
            bind_count += 1;
        }
        if let Some(search) = &self.q {
            let needle = format!("%{search}%");
            builder
                .push(" AND CONCAT_WS(' ', p.description, p.title, p.subtitle, array_to_string(p.authors, ' '), array_to_string(p.reviewers, ' ')) ILIKE ")
                .push_bind(needle);
            bind_count += 1;
        }

        let limit = self.normalized_limit();
        let offset = self.normalized_offset();
        builder
            .push(
                " GROUP BY p.paper_id, p.description, p.title, p.subtitle, p.authors, p.reviewers, p.created_at, p.updated_at",
            )
            .push(" ORDER BY p.created_at DESC, p.paper_id LIMIT ")
            .push_bind(limit)
            .push(" OFFSET ")
            .push_bind(offset);

        PapersQuery {
            sql: builder.sql().to_owned(),
            bind_count: bind_count + 2,
            limit,
            offset,
        }
    }
}

pub(crate) async fn execute_papers_query(
    pool: &PgPool,
    params: &PapersParams,
    plan: &PapersQuery,
) -> Result<Vec<PgRow>, sqlx::Error> {
    let mut query = query(&plan.sql);
    if let Some(question_id) = &params.question_id {
        query = query.bind(question_id);
    }
    if let Some(category) = &params.category {
        query = query.bind(category);
    }
    if let Some(tag) = &params.tag {
        query = query.bind(tag);
    }
    if let Some(search) = &params.q {
        let needle = format!("%{search}%");
        query = query.bind(needle);
    }
    debug_assert_eq!(plan.bind_count, count_paper_binds(params));
    query
        .bind(plan.limit)
        .bind(plan.offset)
        .fetch_all(pool)
        .await
}

pub(crate) fn count_paper_binds(params: &PapersParams) -> usize {
    usize::from(params.question_id.is_some())
        + usize::from(params.category.is_some())
        + usize::from(params.tag.is_some())
        + usize::from(params.q.is_some())
        + 2
}

pub(crate) fn validate_and_build_papers_query(params: &PapersParams) -> Result<PapersQuery> {
    validate_paper_filters(params)?;
    Ok(params.build_query())
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub(crate) struct PaperQuestionValidationRow {
    pub(crate) question_id: String,
    pub(crate) category: String,
    pub(crate) status: String,
}

pub(crate) async fn ensure_paper_questions_valid<'e, E>(
    executor: E,
    question_ids: &[String],
) -> Result<(), ApiError>
where
    E: sqlx::Executor<'e, Database = sqlx::Postgres>,
{
    let question_rows = load_paper_question_validation_rows(executor, question_ids).await?;
    validate_paper_question_rows(&question_rows)
}

async fn load_paper_question_validation_rows<'e, E>(
    executor: E,
    question_ids: &[String],
) -> Result<Vec<PaperQuestionValidationRow>, ApiError>
where
    E: sqlx::Executor<'e, Database = sqlx::Postgres>,
{
    if question_ids.is_empty() {
        return Ok(Vec::new());
    }

    let mut builder = QueryBuilder::<Postgres>::new(
        "SELECT q.question_id::text AS question_id, q.category, q.status FROM questions q WHERE q.question_id IN (",
    );
    for (idx, question_id) in question_ids.iter().enumerate() {
        if idx > 0 {
            builder.push(", ");
        }
        builder.push_bind(question_id).push("::uuid");
    }
    builder.push(") AND q.deleted_at IS NULL");

    let question_rows = builder
        .build()
        .fetch_all(executor)
        .await
        .context("load questions for paper validation failed")
        .map_err(ApiError::from)?
        .into_iter()
        .map(|row| PaperQuestionValidationRow {
            question_id: row.get("question_id"),
            category: row.get("category"),
            status: row.get("status"),
        })
        .collect::<Vec<_>>();

    let existing_question_ids = question_rows
        .iter()
        .map(|row| row.question_id.as_str())
        .collect::<HashSet<_>>();

    for question_id in question_ids {
        if !existing_question_ids.contains(question_id.as_str()) {
            return Err(ApiError::bad_request(format!(
                "unknown question_id in question_ids: {question_id}"
            )));
        }
    }

    Ok(question_rows)
}

pub(crate) fn validate_paper_question_rows(
    question_rows: &[PaperQuestionValidationRow],
) -> Result<(), ApiError> {
    let mut expected_category = None;

    for row in question_rows {
        match row.category.as_str() {
            "T" | "E" => {}
            other => {
                return Err(ApiError::bad_request(format!(
                    "question {} has category {other}; paper questions must all have category T or all have category E",
                    row.question_id
                )));
            }
        }

        if let Some(expected) = expected_category {
            if expected != row.category {
                return Err(ApiError::bad_request(format!(
                    "paper questions must all have the same category; found both {expected} and {}",
                    row.category
                )));
            }
        } else {
            expected_category = Some(row.category.as_str());
        }

        if !matches!(row.status.as_str(), "reviewed" | "used") {
            return Err(ApiError::bad_request(format!(
                "question {} has status {}; paper questions must all have status reviewed or used",
                row.question_id, row.status
            )));
        }
    }

    Ok(())
}

#[cfg(test)]
mod tests {
    use super::{validate_paper_question_rows, PaperQuestionValidationRow};

    fn row(question_id: &str, category: &str, status: &str) -> PaperQuestionValidationRow {
        PaperQuestionValidationRow {
            question_id: question_id.to_string(),
            category: category.to_string(),
            status: status.to_string(),
        }
    }

    #[test]
    fn paper_question_validation_accepts_uniform_category_with_reviewed_or_used_status() {
        let rows = vec![row("q1", "T", "reviewed"), row("q2", "T", "used")];

        validate_paper_question_rows(&rows).expect("paper questions should validate");
    }

    #[test]
    fn paper_question_validation_rejects_none_category() {
        let err = validate_paper_question_rows(&[row("q1", "none", "reviewed")])
            .expect_err("none category should be rejected");

        assert!(err
            .message
            .contains("paper questions must all have category T or all have category E"));
    }

    #[test]
    fn paper_question_validation_rejects_mixed_categories() {
        let err =
            validate_paper_question_rows(&[row("q1", "T", "reviewed"), row("q2", "E", "used")])
                .expect_err("mixed categories should be rejected");

        assert!(err
            .message
            .contains("paper questions must all have the same category"));
    }

    #[test]
    fn paper_question_validation_rejects_none_status() {
        let err = validate_paper_question_rows(&[row("q1", "E", "none")])
            .expect_err("none status should be rejected");

        assert!(err
            .message
            .contains("paper questions must all have status reviewed or used"));
    }
}
