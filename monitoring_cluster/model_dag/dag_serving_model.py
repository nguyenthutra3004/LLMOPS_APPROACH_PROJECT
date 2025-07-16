import os
import sys
import time
import requests
import logging
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
from dotenv import load_dotenv
from airflow.models import Variable
from airflow.operators.python import ShortCircuitOperator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.append(os.path.abspath(os.path.dirname(__file__)))
load_dotenv()

MODEL_NAME = "sft-v3"
ALIAS = "champion"
STATUS_CHECK_INTERVAL = 30  
MAX_RETRIES = 30  # 15 minutes timeout

def check_new_version(**context):
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI")
    username = os.getenv("MLFLOW_TRACKING_USERNAME")
    password = os.getenv("MLFLOW_TRACKING_PASSWORD")

    url = f"{tracking_uri}/api/2.0/mlflow/registered-models/alias"
    headers = {"Content-Type": "application/json"}
    params = {
        "name": MODEL_NAME,
        "alias": ALIAS
    }

    response = requests.get(url, params=params, auth=(username, password), headers=headers)
    result = response.json()

    if not result.get("model_version"):
        raise ValueError(f"No version found for alias '{ALIAS}'.")

    version = result["model_version"]["version"]
    context['ti'].xcom_push(key="current_version", value=version)
    logger.info(f"Current champion version: {version}")

    last_version = Variable.get("last_deployed_version", default_var=None)

    if version == last_version:
        logger.info("No new version found. DAG will stop.")
        context['ti'].xcom_push(key="proceed", value=False)
        return False

    logger.info("New version detected.")
    context['ti'].xcom_push(key="proceed", value=True)
    return True


def serve_model(**context):
    current_version = context['ti'].xcom_pull(task_ids="check_new_version", key="current_version")
    deployed_version_file = "/tmp/last_deployed_version.txt"

    if os.path.exists(deployed_version_file):
        with open(deployed_version_file, "r") as f:
            last_version = f.read().strip()
    else:
        last_version = None

    if current_version == last_version:
        logger.info(f"Version {current_version} already deployed. Skipping.")
        context['ti'].xcom_push(key="deployment_skipped", value=True)
        return

    logger.info(f"New version detected: {current_version}. Triggering deployment...")

    payload = {
        "MODEL_NAME": MODEL_NAME,
        "MODEL_ALIAS": ALIAS,
        "MLFLOW_TRACKING_URI": os.getenv("MLFLOW_TRACKING_URI"),
        "AWS_ACCESS_KEY_ID": os.getenv("AWS_ACCESS_KEY_ID"),
        "AWS_SECRET_ACCESS_KEY": os.getenv("AWS_SECRET_ACCESS_KEY"),
        "MLFLOW_S3_ENDPOINT_URL": os.getenv("MLFLOW_S3_ENDPOINT_URL"),
        "VLLM_LOGGING_LEVEL": os.getenv("VLLM_LOGGING_LEVEL", "DEBUG"),
        "MLFLOW_TRACKING_USERNAME": os.getenv("MLFLOW_TRACKING_USERNAME"),
        "MLFLOW_TRACKING_PASSWORD": os.getenv("MLFLOW_TRACKING_PASSWORD")
    }

    headers = {"Content-Type": "application/json"}
    url = "https://serve_product.quanghung20gg.site/start-vllm"

    response = requests.post(url, json=payload, headers=headers)

    logger.info("Deployment triggered successfully.")
    context['ti'].xcom_push(key="current_version", value=current_version)
    context['ti'].xcom_push(key="deployment_skipped", value=False)

def track_deployment(**context):
    if context['ti'].xcom_pull(task_ids="serve_model", key="deployment_skipped"):
        logger.info("Deployment skipped. No need to track.")
        return

    current_version = context['ti'].xcom_pull(task_ids="check_new_version", key="current_version")
    url = f"https://serve_product.quanghung20gg.site/status-vllm-docker"

    for attempt in range(MAX_RETRIES):
        response = requests.get(url)
        try:
            result = response.json()
        except Exception:
            result = {"status": "error", "raw": response.text}

        status = result.get("status", "").lower()
        logger.info(f"[Attempt {attempt+1}] Deployment status: {status}")

        if status == "success":
            with open("/tmp/last_deployed_version.txt", "w") as f:
                f.write(current_version)
                Variable.set("last_deployed_version", current_version)
                logger.info(f"Deployment successful. Version {current_version} is now live.")
                context['ti'].xcom_push(key="deployment_status", value="success")
                return

        elif status == "not_found":
            logger.error("Deployment failed.")
            raise RuntimeError("Deployment failed.")

        time.sleep(STATUS_CHECK_INTERVAL)

    logger.error("Deployment tracking timed out.")
    raise TimeoutError("Deployment did not complete in expected time.")

with DAG(
    dag_id="serve_model_daily_scan",
    schedule_interval="@daily",
    start_date=days_ago(1),
    catchup=False,
    tags=["model-serving"]
) as dag:

    check_new_version_op = ShortCircuitOperator(
    task_id="check_new_version",
    python_callable=check_new_version,
    provide_context=True,
    )


    serve = PythonOperator(
        task_id="serve_model",
        python_callable=serve_model,
        provide_context=True,
    )

    track = PythonOperator(
        task_id="track_deployment",
        python_callable=track_deployment,
        provide_context=True,
    )

    check_new_version_op >> serve >> track
