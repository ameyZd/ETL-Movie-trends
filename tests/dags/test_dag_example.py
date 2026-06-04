"""Tests for the TMDB weekly trending movies DAG."""

import logging
import os
from contextlib import contextmanager

import pytest
from airflow.models import DagBag

EXPECTED_DAG_ID = "tmdb_weekly_trending_movies"
EXPECTED_TASK_IDS = {
    "extract_trending_movies",
    "transform_movie_details",
    "load_weekly_snapshot",
}
APPROVED_TAGS = {"tmdb", "movies", "etl", "s3"}


@contextmanager
def suppress_logging(namespace):
    logger = logging.getLogger(namespace)
    old_value = logger.disabled
    logger.disabled = True
    try:
        yield
    finally:
        logger.disabled = old_value


def get_import_errors():
    """Generate a tuple for import errors in the dag bag."""
    with suppress_logging("airflow"):
        dag_bag = DagBag(include_examples=False)

        def strip_path_prefix(path):
            return os.path.relpath(path, os.environ.get("AIRFLOW_HOME"))

        return [(None, None)] + [
            (strip_path_prefix(path), message.strip())
            for path, message in dag_bag.import_errors.items()
        ]


def get_dags():
    """Generate a tuple of dag_id, DAG object, and file path."""
    with suppress_logging("airflow"):
        dag_bag = DagBag(include_examples=False)

    def strip_path_prefix(path):
        return os.path.relpath(path, os.environ.get("AIRFLOW_HOME"))

    return [(dag_id, dag, strip_path_prefix(dag.fileloc)) for dag_id, dag in dag_bag.dags.items()]


@pytest.mark.parametrize(
    "rel_path,rv", get_import_errors(), ids=[x[0] for x in get_import_errors()]
)
def test_file_imports(rel_path, rv):
    """Test for import errors on a file."""
    if rel_path and rv:
        raise Exception(f"{rel_path} failed to import with message \n {rv}")


def test_tmdb_dag_is_loaded():
    dag_ids = {dag_id for dag_id, _, _ in get_dags()}
    assert EXPECTED_DAG_ID in dag_ids


@pytest.mark.parametrize(
    "dag_id,dag,fileloc", get_dags(), ids=[x[2] for x in get_dags()]
)
def test_dag_tags(dag_id, dag, fileloc):
    """Test if a DAG is tagged and only uses approved tags."""
    assert dag.tags, f"{dag_id} in {fileloc} has no tags"
    assert not set(dag.tags) - APPROVED_TAGS


@pytest.mark.parametrize(
    "dag_id,dag,fileloc", get_dags(), ids=[x[2] for x in get_dags()]
)
def test_dag_retries(dag_id, dag, fileloc):
    """Test if a DAG has retries set."""
    assert (
        dag.default_args.get("retries", None) >= 2
    ), f"{dag_id} in {fileloc} must have task retries >= 2."


def test_tmdb_dag_task_shape():
    with suppress_logging("airflow"):
        dag_bag = DagBag(include_examples=False)
    dag = dag_bag.get_dag(EXPECTED_DAG_ID)

    assert dag is not None
    assert set(dag.task_ids) == EXPECTED_TASK_IDS
    assert dag.catchup is False
    assert dag.schedule is not None
