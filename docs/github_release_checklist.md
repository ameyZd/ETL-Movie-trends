# GitHub Release Checklist

Use this checklist before making the repository public.

## Project Name

Recommended name:

`TMDB Weekly Trends ETL Pipeline`

Recommended GitHub description:

`Weekly TMDB movie trends ETL pipeline using Apache Airflow, AWS Lambda, EventBridge Scheduler, and Amazon S3.`

## Files that should go to GitHub

- `dags/`
- `src/`
- `tests/`
- `docs/`
- `Dockerfile`
- `Dockerfile.lambda`
- `lambda_handler.py`
- `requirements.txt`
- `requirements-lambda.txt`
- `packages.txt`
- `.dockerignore`
- `.gitignore`
- `.env.example`
- `airflow_settings.example.yaml`
- `README.md`
- `bootstrap-local.ps1`

## Files that should not go to GitHub

- `.env`
- `airflow_settings.yaml`
- `.venv/`
- `.astro/standalone/`
- `logs/`
- `airflow.db`
- `airflow.cfg`
- `.pytest_cache/`
- `pytest-cache-files-*`
- `__pycache__/`
- `*.pyc`
- `.docker-temp/`

## Security checks before push

- Rotate any AWS access keys that were shown in screenshots or terminal output.
- Rotate any TMDB token that appears in local files or screenshots.
- Confirm `airflow_settings.yaml` is ignored.
- Confirm `.env` is ignored.
- Run a secret scan command before first commit:

```powershell
rg -n "AKIA|SECRET|SECRET_ACCESS|ACCESS_KEY|eyJ|AWS_SECRET|TMDB_ACCESS_TOKEN" .
```

Expected result:

- No real secrets in tracked files.
- Placeholder values in `.env.example` and `airflow_settings.example.yaml` are fine.

## First GitHub push commands

Run these after creating an empty GitHub repository:

```powershell
git init
git add .
git status
git commit -m "Initial commit: TMDB weekly trends ETL pipeline"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
git push -u origin main
```

Before `git commit`, carefully inspect `git status` and make sure no secret file is staged.
