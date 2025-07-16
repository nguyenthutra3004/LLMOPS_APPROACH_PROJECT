from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.dummy import DummyOperator
from airflow.utils.dates import days_ago
from google.cloud import bigquery
from google.oauth2 import service_account
import datetime
import requests
import logging
import json
import os
import sys 

current_dir = os.path.dirname(os.path.abspath(__file__))


default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': datetime.timedelta(minutes=5),
}

dag = DAG(
    'bigquery_training_dag',
    default_args=default_args,
    description='DAG to monitor BigQuery table and trigger training',
    schedule_interval='@hourly',
    start_date=days_ago(1),
    catchup=False,
)

config_path = os.path.join(current_dir, "../crawler/neusolution.json")
# Service account credentials
SERVICE_ACCOUNT_INFO = json.load(open(config_path))
# Set up Google Cloud credentials
# os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = config_path



credentials = service_account.Credentials.from_service_account_info(SERVICE_ACCOUNT_INFO)
client = bigquery.Client(credentials=credentials, project=SERVICE_ACCOUNT_INFO['project_id'])

PROJECT_ID = 'neusolution'
DATASET_ID = 'neusolution.message'
MESSAGES_TABLE = f'{PROJECT_ID}.{DATASET_ID}.ne ws_v2'
VERSION_TABLE = f'{PROJECT_ID}.{DATASET_ID}.version_tracking'
VERSION_LOGS_TABLE = f'{PROJECT_ID}.{DATASET_ID}.version_logs'
TRAINING_SERVER_URL = '...'
THRESHOLD = 500

def check_new_records(**kwargs):
    """Check the number of new records since the last training."""
    # Query to get the latest version and its record count
    version_query = f"""
    SELECT version_number, record_count
    FROM `{VERSION_TABLE}`
    ORDER BY version_number DESC
    LIMIT 1
    """
    version_result = client.query(version_query).result()
    last_version = 0.0
    last_record_count = 0
    for row in version_result:
        last_version = row.version_number
        last_record_count = row.record_count

    # Query to count new records
    count_query = f"""
    SELECT COUNT(*) as new_records
    FROM `{MESSAGES_TABLE}`
    WHERE timestamp > (
        SELECT COALESCE(MAX(timestamp), '1970-01-01')
        FROM `{VERSION_TABLE}`
        WHERE version_number = {last_version}
    )
    """
    count_result = client.query(count_query).result()
    new_records = 0
    for row in count_result:
        new_records = row.new_records

    is_train = new_records > THRESHOLD
    kwargs['ti'].xcom_push(key='is_train', value=is_train)
    kwargs['ti'].xcom_push(key='new_records', value=new_records)
    kwargs['ti'].xcom_push(key='last_version', value=last_version)
    logging.info(f"New records: {new_records}, is_train: {is_train}")

def create_new_version(**kwargs):
    """Create a new data version if training is triggered."""
    ti = kwargs['ti']
    is_train = ti.xcom_pull(key='is_train')
    if not is_train:
        logging.info("Training threshold not met. Skipping version creation.")
        return

    last_version = ti.xcom_pull(key='last_version')
    new_records = ti.xcom_pull(key='new_records')
    new_version = last_version + 1.0

    # Define query logic for this version
    query_logic = f"""
    SELECT *
    FROM `{MESSAGES_TABLE}`
    WHERE timestamp > (
        SELECT COALESCE(MAX(timestamp), '2020-01-01')
        FROM `{VERSION_TABLE}`
        WHERE version_number = {last_version}
    )
    LIMIT {new_records}
    """

    # Insert metadata into version tracking table
    insert_query = f"""
    INSERT INTO `{VERSION_TABLE}` (version_number, query_logic, timestamp, record_count, training_status)
    VALUES ({new_version}, '{query_logic.replace("'", "''")}', CURRENT_TIMESTAMP(), {new_records}, 'PENDING')
    """
    client.query(insert_query).result()
    ti.xcom_push(key='new_version', value=new_version)
    logging.info(f"Created new version: {new_version}")

    return new_version

# def send_training_request(**kwargs):
#     """Send training request to the training server."""
#     ti = kwargs['ti']
#     is_train = ti.xcom_pull(key='is_train')
#     if not is_train:
#         logging.info("No training triggered. Skipping training request.")
#         return

#     new_version = ti.xcom_pull(key='new_version')
#     payload = {'version_number': new_version}
#     response = requests.post(TRAINING_SERVER_URL, json=payload)
#     if response.status_code == 200:
#         logging.info(f"Training request sent for version {new_version}")
#     else:
#         raise Exception(f"Training request failed: {response.text}")

# def log_current_version(**kwargs):
#     """Log the current data version."""
#     ti = kwargs['ti']
#     new_version = ti.xcom_pull(key='new_version')
#     if new_version:
#         message = f"The data is currently at version {new_version}"
#     else:
#         last_version = ti.xcom_pull(key='last_version')
#         message = f"The data is currently at version {last_version}"
#     logging.info(message)
#     # Store in BigQuery log table
#     client.query(f"""
#     INSERT INTO `{VERSION_LOGS_TABLE}` (message, timestamp)
#     VALUES ('{message}', CURRENT_TIMESTAMP())
#     """).result()

# Define tasks
start_task = DummyOperator(task_id='start', dag=dag)

check_records_task = PythonOperator(
    task_id='check_new_records',
    python_callable=check_new_records,
    provide_context=True,
    dag=dag,
)

create_version_task = PythonOperator(
    task_id='create_new_version',
    python_callable=create_new_version,
    provide_context=True,
    dag=dag,
)

# send_training_task = PythonOperator(
#     task_id='send_training_request',
#     python_callable=send_training_request,
#     provide_context=True,
#     dag=dag,
# )

# log_version_task = PythonOperator(
#     task_id='log_current_version',
#     python_callable=log_current_version,
#     provide_context=True,
#     dag=dag,
# )

end_task = DummyOperator(task_id='end', dag=dag)

# Set task dependencies
start_task >> check_records_task >> create_version_task
create_version_task #>> send_training_task >> log_version_task >> end_task