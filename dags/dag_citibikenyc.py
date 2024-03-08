from datetime import datetime
import os
import pandas as pd

from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator
from airflow.operators.dummy import DummyOperator
from airflow.decorators import dag, task, task_group
from airflow.models import Variable

from airflow.providers.google.cloud.transfers.local_to_gcs import LocalFilesystemToGCSOperator
from airflow.providers.google.cloud.operators.bigquery import BigQueryCreateEmptyDatasetOperator
from airflow.providers.google.cloud.operators.bigquery import BigQueryInsertJobOperator
from airflow.providers.google.cloud.operators.bigquery import BigQueryCreateEmptyTableOperator


# Astro libs:
from astro import sql as aql
from astro.files import File
from astro.constants import FileType
from astro.sql.table import Table, Metadata
import sqlalchemy



AIRFLOW_HOME = os.getenv("AIRFLOW_HOME")
GOOGLE_CONNECTION = Variable.get('GOOGLE_CONNECTION')
BUCKET_NAME = Variable.get('BUCKET_NAME')
DATASET_NAME = Variable.get('DATASET_NAME')
CITIBIKE_MAIN_TABLE = Variable.get('CITIBIKE_MAIN_TABLE')

@dag(
    start_date=datetime(2022, 12, 1),  # start_date+schedule_interval
    # end_date=datetime(2023, 11, 1),  # end_date+schedule_interval
    schedule_interval="@monthly",
    #catchup=False,
    max_active_runs=1,
    tags=["citi_bike_nyc", "etl", "gcp"],
    default_args={"owner": "felipeparfitt", "retries": 1, "retry_delay": 0},
)
def citibikedataset():

    task_init = DummyOperator(task_id="Init")

    task_download_dataset = BashOperator(
        task_id="download_dataset",
        bash_command="sh ${AIRFLOW_HOME}/include/download_bike_dataset.sh \
        {{ next_execution_date.strftime('%Y') }} {{ next_execution_date.strftime('%m') }}",
    )
    
    @task(task_id='pre_processing')
    def transform_data_parquet(**context):
        file_path=context['ti'].xcom_pull(task_ids='download_dataset', key="return_value")
        df = pd.read_csv(
            file_path, 
            compression='zip',
            parse_dates=['started_at', 'ended_at'], 
            dtype={
                'ride_id': 'string',
                'rideable_type': 'string',
                'start_station_name': 'string',
                'start_station_id': 'string',
                'end_station_name': 'string',
                'end_station_id':'string',
                'start_lat': 'float32',
                'start_lng': 'float32',
                'end_lat': 'float32',
                'end_lng': 'float32',
                'member_casual': 'string'}
            )
        local_file_dir = os.path.dirname(file_path)
        local_file_name = os.path.basename(file_path).replace('.csv.zip', '.parquet')
        local_file_abspath = os.path.join(local_file_dir, local_file_name)
        df.to_parquet(local_file_abspath)
        os.remove(file_path)
        
        # Context
        local_file_relpath = os.path.relpath(local_file_abspath, os.path.join(AIRFLOW_HOME, 'include'))
        context['ti'].xcom_push(key='local_file_abspath', value=local_file_abspath)
        context['ti'].xcom_push(key='local_file_relpath', value=local_file_relpath)
    
    task_upload_data_to_gcp = LocalFilesystemToGCSOperator(
        task_id="upload-parquet-data-to-gcs",
        src="{{ ti.xcom_pull(key='local_file_abspath') }}",
        dst="{{ ti.xcom_pull(key='local_file_relpath') }}",
        bucket=BUCKET_NAME,
        gcp_conn_id=GOOGLE_CONNECTION,
        mime_type="text/parquet",
        # gzip="False",
        # impersonation_chain="None",
    )
    
    @task_group(group_id="group_create_bigquery_dataset")
    def create_bigquery_dataset():
        task_create_bigquery_dataset = BigQueryCreateEmptyDatasetOperator(
            task_id='create_bigquery_dataset',
            dataset_id=DATASET_NAME,
            location="US",
            gcp_conn_id=GOOGLE_CONNECTION,
            if_exists="log",
        )
        
        task_create_bigquery_main_table = BigQueryCreateEmptyTableOperator(
            task_id="create_bigquery_main_table",
            dataset_id=DATASET_NAME,
            table_id=CITIBIKE_MAIN_TABLE,
            gcp_conn_id=GOOGLE_CONNECTION,
            schema_fields=[
                {"name": "ride_id", "type": "STRING", "mode": "NULLABLE"},
                {"name": "rideable_type", "type": "STRING", "mode": "NULLABLE"},
                {"name": "started_at", "type": "TIMESTAMP", "mode": "NULLABLE"},
                {"name": "ended_at", "type": "TIMESTAMP", "mode": "NULLABLE"},
                {"name": "start_station_name", "type": "STRING", "mode": "NULLABLE"},
                {"name": "start_station_id", "type": "STRING", "mode": "NULLABLE"},
                {"name": "end_station_name", "type": "STRING", "mode": "NULLABLE"},
                {"name": "end_station_id", "type": "STRING", "mode": "NULLABLE"},
                {"name": "start_lat", "type": "FLOAT64", "mode": "NULLABLE"},
                {"name": "start_lng", "type": "FLOAT64", "mode": "NULLABLE"},
                {"name": "end_lat", "type": "FLOAT64", "mode": "NULLABLE"},
                {"name": "end_lng", "type": "FLOAT64", "mode": "NULLABLE"},
                {"name": "member_casual", "type": "STRING", "mode": "NULLABLE"},
            ],
        )

        
        task_create_bigquery_dataset >> task_create_bigquery_main_table
    

    task_gcs_to_bigquery = aql.load_file(
        task_id='load_file_to_gcs',
        input_file=File(
            path=os.path.join(f"gs://{BUCKET_NAME}", "{{ ti.xcom_pull(key='local_file_relpath') }}"),
            conn_id=GOOGLE_CONNECTION,
            filetype=FileType.PARQUET
        ),
        output_table=Table(
            name="_tmp_citibike_{{ next_execution_date.strftime('%Y') }}_{{ next_execution_date.strftime('%m') }}",
            conn_id=GOOGLE_CONNECTION,
            metadata=Metadata(schema=DATASET_NAME),
            temp=True,
            # columns=[
            #     sqlalchemy.Column("started_at", sqlalchemy.TIMESTAMP, nullable=False, key="started_at"),
            #     sqlalchemy.Column("ended_at", sqlalchemy.TIMESTAMP, nullable=False, key="ended_at"),
            # ]
        ),
        #use_native_support=False,
        if_exists="replace"
    )
    
    task_append_table_to_main_table = BigQueryInsertJobOperator(
        task_id='append_table_to_main_table',
        gcp_conn_id=GOOGLE_CONNECTION,
        configuration={
            "query": {
                "query":"""
                    INSERT INTO {{ var.value.DATASET_NAME }}.{{ var.value.CITIBIKE_MAIN_TABLE }}
                    SELECT *
                    FROM {{ var.value.DATASET_NAME }}.{{ ti.xcom_pull(task_ids='load_file_to_gcs', key='output_table_name') }};
                """,
                "useLegacySql": False,
            }
        }
        
    )
    
    
    

    task_finish = DummyOperator(task_id="Finish")

    # Clean up temporary tables once either the DAG or upstream tasks are done
    # cleanup_temp_data = aql.cleanup()

    (
        task_init >> task_download_dataset >> transform_data_parquet() >> task_upload_data_to_gcp >> 
        create_bigquery_dataset() >> task_gcs_to_bigquery >> task_append_table_to_main_table >> task_finish
    )


dag = citibikedataset()
