# Medium Article Outline

Working title:

`Building a Weekly Movie Trends ETL Pipeline with Airflow, AWS Lambda, EventBridge, and S3`

## 1. Introduction

- Explain the project goal in simple terms.
- Mention that the pipeline fetches weekly trending movies from TMDB.
- Mention that output is stored as parquet in S3.
- Mention the two execution modes:
- local Airflow for development and orchestration
- AWS Lambda plus EventBridge for weekly cloud execution

## 2. Why this architecture

- Airflow gives a clear DAG, retries, logs, and task visibility.
- Lambda plus EventBridge is cheaper and simpler for a small weekly job.
- S3 is a durable storage layer for analytics-ready files.
- Shared ETL code avoids maintaining two separate implementations.

## 3. Local Airflow setup

- Show project structure.
- Explain `dags/movies_etl.py`.
- Explain Airflow Variables and `aws_default` connection.
- Show `astro dev start`.
- Show the DAG run in the Airflow UI.

## 4. ETL logic

- Explain the extract step.
- Explain the transform/enrichment step.
- Explain parquet serialization.
- Explain S3 partition path:

```text
s3://bucket/prefix/year=YYYY/week=WW/trending_movies_YYYY-MM-DD.parquet
```

## 5. AWS deployment

- Explain why Lambda used a container image.
- Explain ECR as the container image registry.
- Explain Lambda environment variables:
- `TMDB_ACCESS_TOKEN`
- `S3_BUCKET`
- `S3_PREFIX`
- Explain IAM permissions for S3 writes.

## 6. Weekly scheduling

- Explain EventBridge Scheduler.
- Final schedule:
- every Friday at 6 PM US Eastern Time
- timezone `America/New_York`
- cron `0 18 ? * FRI *`

## 7. Problems faced and fixes

- Airflow does not run natively on Windows, so Docker/Astro was used.
- TMDB Bearer token needed `Authorization: Bearer ...`, not `api_key=...`.
- Astro Runtime should not include `apache-airflow` itself in `requirements.txt`.
- Lambda container image needed Lambda-compatible build settings.
- Secrets must be kept out of GitHub.

## 8. Final result

- Local Airflow DAG works.
- AWS Lambda runs successfully.
- EventBridge Scheduler triggers weekly.
- S3 stores parquet snapshots.

## 9. What I would improve next

- Add data quality checks.
- Add failure alerts.
- Add raw JSON bronze storage.
- Add GitHub Actions for automated image builds.
