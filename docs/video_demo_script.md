# Video Demo Script

Target length:

`4 to 6 minutes`

## 1. Opening

Say:

`This project is a weekly TMDB movie trends ETL pipeline. It fetches trending movies, enriches them with movie details, converts the data to parquet, and stores the result in Amazon S3. I built it with two execution modes: local Airflow for orchestration and AWS Lambda with EventBridge Scheduler for cloud automation.`

Show:

- GitHub repository
- project folder structure

## 2. Local Airflow Demo

Show:

- `dags/movies_etl.py`
- Airflow UI at `localhost:8080`
- DAG `tmdb_weekly_trending_movies`
- three tasks:
- `extract_trending_movies`
- `transform_movie_details`
- `load_weekly_snapshot`

Say:

`Locally, I run the project with Astro and Docker. Airflow gives me task visibility, retries, logs, and a clear DAG view for development.`

Trigger:

- one manual DAG run, or show a previous successful run

## 3. S3 Output

Show:

- S3 bucket
- partitioned output path
- parquet file

Say:

`The output is stored in a partitioned S3 path by year and ISO week, which makes future analytics easier.`

## 4. AWS Lambda Demo

Show:

- Lambda function
- container image source from ECR
- environment variables with values hidden
- successful test result
- CloudWatch logs

Say:

`For cloud execution, I packaged the shared ETL code as a Lambda container image. This avoids keeping an Airflow server running for one weekly job.`

## 5. EventBridge Scheduler

Show:

- EventBridge schedule
- target Lambda
- schedule expression

Say:

`EventBridge Scheduler triggers the Lambda every Friday at 6 PM US Eastern Time. The code is deployed once, and AWS runs it automatically every week.`

## 6. Closing

Say:

`The main idea of this project is not just moving data. It shows local orchestration, cloud scheduling, Docker packaging, IAM permissions, S3 storage, and reusable ETL code across two runtime environments.`
