from airflow.operators.bash import BashOperator
from airflow.operators.dummy import DummyOperator
from airflow.decorators import dag  # , task, task_group
from datetime import datetime
import os

# Astro liba:
#from astro import sql as aql

AIRFLOW_HOME = os.getenv("AIRFLOW_HOME")


@dag(
    start_date=datetime(2022, 12, 1),  # start_date+schedule_interval
    # end_date=datetime(2023, 11, 1),   #end_date+schedule_interval
    schedule_interval="@monthly",
    # catchup=False,
    max_active_runs=1,
    tags=["citi_bike_nyc", "etl", "gcp"],
    default_args={"owner": "felipeparfitt", "retries": 1, "retry_delay": 0},
)
def citibikedataset():

    task_init = DummyOperator(task_id="Init")

    task_download_dataset = BashOperator(
        task_id="download_dataset",
        bash_command="sh ${AIRFLOW_HOME}/include/download_bike_dataset.sh \
        {{ next_execution_date .strftime('%Y') }} {{ next_execution_date .strftime('%m') }}",
    )

    task_finish = DummyOperator(task_id="Finish")

    # Clean up temporary tables once either the DAG or upstream tasks are done
    # cleanup_temp_data = aql.cleanup()

    (task_init >> task_download_dataset >> task_finish)


dag = citibikedataset()
