# TMDB Weekly Trends Streamlit Dashboard

Lightweight dashboard for the JSON files produced by the weekly TMDB ETL pipeline.

The dashboard reads:

```text
dashboard/latest.json
dashboard/manifest.json
dashboard/weeks/YYYY-MM-DD.json
```

It does not query Athena or scan Parquet, which keeps the public demo inexpensive.

## Local Run

Create a local secrets file from the example:

```powershell
Copy-Item streamlit_dashboard\.streamlit\secrets.toml.example streamlit_dashboard\.streamlit\secrets.toml
```

Edit `streamlit_dashboard\.streamlit\secrets.toml` with your S3 JSON URLs or private S3 credentials.

Run the dashboard:r


```powershell
cd D:\Projects\ETL-Movie-trends
streamlit run streamlit_dashboard\app.py
```

## Streamlit Community Cloud

Deploy from GitHub and select this app entrypoint:

```text
streamlit_dashboard/app.py
```

Because `streamlit_dashboard/requirements.txt` is in the same folder as the app entrypoint, Streamlit Cloud installs only the dashboard dependencies instead of the Airflow project dependencies.

In Streamlit Cloud secrets, paste either the public URL config:

```toml
DATA_MODE = "public_url"
LATEST_JSON_URL = "https://YOUR_BUCKET.s3.amazonaws.com/tmdb/trending/weekly/dashboard/latest.json"
MANIFEST_JSON_URL = "https://YOUR_BUCKET.s3.amazonaws.com/tmdb/trending/weekly/dashboard/manifest.json"
```

or private S3 config:

```toml
DATA_MODE = "s3_private"
AWS_REGION = "us-east-1"
AWS_ACCESS_KEY_ID = "YOUR_READ_ONLY_ACCESS_KEY_ID"
AWS_SECRET_ACCESS_KEY = "YOUR_READ_ONLY_SECRET_ACCESS_KEY"
S3_BUCKET = "YOUR_BUCKET"
S3_LATEST_KEY = "tmdb/trending/weekly/dashboard/latest.json"
S3_MANIFEST_KEY = "tmdb/trending/weekly/dashboard/manifest.json"
```

Do not commit the real `secrets.toml` file.
