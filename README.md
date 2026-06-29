# TMDB Weekly Trends ETL Pipeline

Weekly movie trends data pipeline built with Apache Airflow, AWS Lambda, EventBridge Scheduler, and Amazon S3.

This project fetches weekly trending movies from TMDB, enriches each movie with detail metadata, converts the dataset to parquet, and stores weekly snapshots in Amazon S3. Each run also publishes small dashboard-ready JSON files for visualization.

## Project Links
[Open the TMDB Weekly Trends dashboard](https://amey-tmdb-weekly-trends.streamlit.app/)
[Watch the project walkthrough](https://drive.google.com/file/d/19MBK1F18dUHmyx7ESQ-pvoqjBWgfj1ln/view?usp=sharing)
[Medium Article](https://medium.com/@ameydhote007/turning-movie-night-confusion-into-a-data-engineering-project-%EF%B8%8F-2b63a607d389)

## Why This Project Exists

The project has two execution modes:

- Local orchestration with Apache Airflow, Astro, and Docker for development, debugging, and DAG visibility.
- Cloud scheduled execution with AWS Lambda and EventBridge Scheduler so the ETL runs automatically every week without depending on a local machine.

This makes the project useful both as an Airflow learning project and as a practical low-cost cloud data pipeline.

## Architecture
<img width="1030" height="450" alt="Untitled Diagram drawio (1)" src="https://github.com/user-attachments/assets/316e3fc2-7c01-42d3-86f0-4f9ce2978bb9" />



## Tech Stack

- Apache Airflow
- Astronomer Astro CLI
- Docker
- Python
- pandas
- pyarrow
- boto3
- AWS Lambda
- Amazon ECR
- EventBridge Scheduler
- Amazon S3
- CloudWatch Logs
- Streamlit
- Plotly

## Repository Structure

```text
dags/
  movies_etl.py              Airflow DAG for local orchestration
src/
  tmdb_pipeline.py           Shared ETL logic used by Airflow and Lambda
lambda_handler.py            AWS Lambda entrypoint
Dockerfile                   Astro Runtime image
Dockerfile.lambda            Lambda container image
requirements.txt             Airflow project dependencies
requirements-lambda.txt      Lambda image dependencies
airflow_settings.example.yaml Local Airflow config template
.env.example                 Lambda-style environment variable template
streamlit_dashboard/
  app.py                     Streamlit application entry point
  dashboard/                 Data access, analytics, styling, and page modules
  requirements.txt           Dashboard-only dependencies
docs/                        Walkthrough, checklist, article outline, demo script
```

## Output Layout

The pipeline writes parquet snapshots to S3 using this layout:

```text
s3://<bucket>/<prefix>/year=YYYY/week=WW/trending_movies_YYYY-MM-DD.parquet
```

Example prefix:

```text
tmdb/trending/weekly
```

The pipeline also writes dashboard JSON files using this layout:

```text
s3://<bucket>/<prefix>/dashboard/latest.json
s3://<bucket>/<prefix>/dashboard/manifest.json
s3://<bucket>/<prefix>/dashboard/weeks/YYYY-MM-DD.json
```

These JSON files power the [live Streamlit dashboard](https://amey-tmdb-weekly-trends.streamlit.app/). The dashboard reads the compact JSON contract rather than querying Parquet directly, keeping the public demo lightweight and inexpensive. They are generated for new runs going forward; existing historical parquet files are not converted unless a separate backfill script is run.

## Dashboard Features

The dashboard is a thin visualization layer over the S3 dashboard JSON files. It includes:

- **Discover:** trending, critics, and balanced movie recommendations.
- **Movie Explorer:** movie metadata, ratings, genres, runtime, overview, and TMDB links.
- **Historical Analytics:** popularity and rank movement once multiple weekly snapshots exist.

The S3 bucket remains private. Streamlit uses a read-only IAM identity configured as deployment secrets, never committed to this repository.

## Local Airflow Setup

1. Install Docker Desktop.
2. Install the Astro CLI.
3. Create a local `airflow_settings.yaml` from the example:

```powershell
Copy-Item airflow_settings.example.yaml airflow_settings.yaml
```

4. Fill in local values for:

- `tmdb_access_token`
- `tmdb_s3_bucket`
- `tmdb_s3_prefix_weekly`
- `tmdb_s3_prefix_dashboard`
- `tmdb_aws_conn_id`
- `aws_default` connection credentials

5. Start Airflow locally:

```powershell
astro dev start
```

6. Open Airflow:

```text
http://localhost:8080
```

7. Trigger the DAG:

```text
tmdb_weekly_trending_movies
```

## AWS Scheduled Setup

The cloud execution path uses Lambda instead of always-on Airflow infrastructure.

Required Lambda environment variables:

- `TMDB_ACCESS_TOKEN`
- `S3_BUCKET`
- `S3_PREFIX`

Optional Lambda environment variable:

- `S3_DASHBOARD_PREFIX`

If `S3_DASHBOARD_PREFIX` is not set, the Lambda writes dashboard JSON under `<S3_PREFIX>/dashboard`.

Build and push the Lambda image:

```powershell
docker buildx build --platform linux/amd64 --provenance=false --sbom=false -f Dockerfile.lambda -t <account-id>.dkr.ecr.us-east-1.amazonaws.com/tmdb-weekly-trends-lambda:latest --push .
```

Create the Lambda function from the pushed ECR image, then add an EventBridge Scheduler trigger.

Final weekly schedule:

- Timezone: `America/New_York`
- Cron: `0 18 ? * FRI *`
- Meaning: every Friday at 6:00 PM US Eastern Time



