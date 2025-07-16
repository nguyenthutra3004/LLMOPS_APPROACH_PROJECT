import os
import sys
sys.path.append(os.path.abspath(os.path.dirname(__file__)))
from dags.model_dag.model_training_utils import *
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago

with DAG(
    dag_id="training_dag",
    schedule_interval=None,
    start_date=days_ago(1),
    catchup=False,
) as dag:

    train_eval = PythonOperator(
        task_id="train_model",
        python_callable=train_model,
        op_kwargs={
            "model_name": "Qwen/Qwen2.5-1.5B-Instruct",
            "lora_name": "sft-v3",
            "lora_version": None,
            "dataset_version": "v1.0",
            "template": "qwen",
            "num_epochs": 3.0,
            "tracking_backend": "mlflow",
        },
    )

    training_tracking = PythonOperator(
        task_id="wait_for_completion",
        python_callable=training_tracker,
        op_kwargs={
            "job_id": "{{ task_instance.xcom_pull(task_ids='train_model') }}",
        },
    )
    
    deploy = PythonOperator(
        task_id="deploy_to_product",
        python_callable=serve_model,
        op_kwargs={
            "job_id": "{{ task_instance.xcom_pull(task_ids='train_eval') }}"
        }
    )
    
    (
        train_eval >> training_tracking >> deploy
    )