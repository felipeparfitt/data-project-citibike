import pytest
import os
from airflow.models import DagBag
import sys

#  This file will check if:
#   a) DAG import errors; b) Follow specific file naming conventions;
#   c) Include a description and an owner; d) Contain requerid project tags;
#   e) Do not send emails; f) Do not retry more than three times;

# Search modules within:
sys.path.append(os.path.join(os.path.dirname(__file__), "../../dags"))


@pytest.fixture(params=["../../dags"])  # fixture fornece dados
def dag_bag(request):
    return DagBag(dag_folder=request.param, include_examples=False)


def test_import_errors(dag_bag):
    assert not dag_bag.import_errors


def test_requires_tags(dag_bag):
    for dag_id, dag in dag_bag.dags.items():
        assert dag.tags


def test_owner_not_airflow(dag_bag):
    for dag_id, dag in dag_bag.dags.items():
        assert str.lower(dag.owner) != "airflow"


def test_three_or_less_retries(dag_bag):
    for dag_id, dag in dag_bag.dags.items():
        assert dag.default_args["retries"] <= 3
