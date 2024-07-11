from airflow.decorators import dag, task
from datetime import datetime
import pandas as pd

from airflow.providers.google.cloud.transfers.local_to_gcs import LocalFilesystemToGCSOperator
from airflow.providers.google.cloud.operators.bigquery import BigQueryCreateEmptyDatasetOperator

from astro import sql as aql
from astro.files import File
from astro.sql.table import Table, Metadata
from astro.constants import FileType

from include.dbt.cosmos_config import DBT_PROJECT_CONFIG, DBT_CONFIG
from cosmos.airflow.task_group import DbtTaskGroup
from cosmos.constants import LoadMode
from cosmos.config import ProjectConfig, RenderConfig

from airflow.models.baseoperator import chain


@dag(
    start_date=datetime(2024, 7, 7),
    schedule=None,
    catchup=False,
    tags=['retail'],
)
def retail():
    bucket_name = 'alanceloth_online_retail'
    @task.external_python(python='/usr/local/airflow/pandas_venv/bin/python')
    def correct_csv_format():
        import pandas as pd

        file_path = 'include/datasets/online_retail.csv'
        new_file_path = 'include/datasets/online_retail_dataset.csv'
        df = pd.read_csv(file_path, encoding='ISO-8859-1')
        df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'], format='%m/%d/%y %H:%M', errors='coerce')
        df.to_csv(new_file_path, index=False)
    

    upload_retail_csv_to_gcs = LocalFilesystemToGCSOperator(
        task_id='upload_retail_csv_to_gcs',
        src='include/datasets/online_retail_dataset.csv',
        dst='raw/online_retail.csv',
        bucket=bucket_name,
        gcp_conn_id='gcp',
        mime_type='text/csv',
    )

    upload_country_csv_to_gcs = LocalFilesystemToGCSOperator(
        task_id='upload_country_csv_to_gcs',
        src='include/datasets/country.csv',
        dst='raw/country.csv',
        bucket=bucket_name,
        gcp_conn_id='gcp',
        mime_type='text/csv',
    )

    create_retail_dataset = BigQueryCreateEmptyDatasetOperator(
        task_id='create_retail_dataset',
        dataset_id='retail',
        gcp_conn_id='gcp',
    )

    retail_gcs_to_raw = aql.load_file(
        task_id='retail_gcs_to_raw',
        input_file=File(
            f'gs://{bucket_name}/raw/online_retail.csv',
            conn_id='gcp',
            filetype=FileType.CSV,
        ),
        output_table=Table(
            name='raw_invoices',
            conn_id='gcp',
            metadata=Metadata(schema='retail')
        ),
        use_native_support=True,
        native_support_kwargs={
            "encoding": "ISO_8859_1",
        }
    )

    country_gcs_to_raw = aql.load_file(
        task_id='country_gcs_to_raw',
        input_file=File(
            f'gs://{bucket_name}/raw/country.csv',
            conn_id='gcp',
            filetype=FileType.CSV,
        ),
        output_table=Table(
            name='raw_country',
            conn_id='gcp',
            metadata=Metadata(schema='retail')
        ),
        use_native_support=True,
        native_support_kwargs={
            "encoding": "ISO_8859_1",
        }
    )

    @task.external_python(python='/usr/local/airflow/soda_venv/bin/python')
    def check_load(scan_name='check_load', checks_subpath='sources'):
        from include.soda.check_function import check

        return check(scan_name, checks_subpath)
    
    
    transform = DbtTaskGroup(
        group_id='transform',
        project_config=DBT_PROJECT_CONFIG,
        profile_config=DBT_CONFIG,
        render_config=RenderConfig(
            load_method=LoadMode.DBT_LS,
            select=['path:models/transform']
        )
    )

    @task.external_python(python='/usr/local/airflow/soda_venv/bin/python')
    def check_transform(scan_name='check_transform', checks_subpath='transform'):
        from include.soda.check_function import check

        return check(scan_name, checks_subpath)
    

    report = DbtTaskGroup(
        group_id='report',
        project_config=DBT_PROJECT_CONFIG,
        profile_config=DBT_CONFIG,
        render_config=RenderConfig(
            load_method=LoadMode.DBT_LS,
            select=['path:models/report']
        )
    )

    @task.external_python(python='/usr/local/airflow/soda_venv/bin/python')
    def check_report(scan_name='check_report', checks_subpath='report'):
        from include.soda.check_function import check

        return check(scan_name, checks_subpath)

    chain(
        correct_csv_format(),
        upload_retail_csv_to_gcs,
        upload_country_csv_to_gcs,
        create_retail_dataset,
        retail_gcs_to_raw,
        country_gcs_to_raw,
        check_load(),
        transform,
        check_transform(),
        report,
        check_report()
    )

retail()