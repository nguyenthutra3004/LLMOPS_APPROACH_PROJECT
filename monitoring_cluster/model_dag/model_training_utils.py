import requests
import time 
from dotenv import load_dotenv
import os

POLL_INTERVAL = 30

def train_model(model_name = "Qwen/Qwen2.5-1.5B-Instruct", 
                lora_name = "initial-sft", 
                dataset_version="qwen:bigquery:v2", 
                template = "qwen", 
                tracking_backend="mlflow", 
                num_epochs=3, 
                lora_version=None):
    # Simulate model training
    print(f"Training {model_name} on dataset version {dataset_version} with template {template}")
    # Here you would add the actual training code

    url = "http://localhost:23478/train"
    
    payload = {
        "model_name": model_name,
        "lora_name": lora_name,
        "dataset_version": dataset_version,
        "template": template,
        "tracking_backend": tracking_backend,
        "lora_version": lora_version,
        "num_epochs": num_epochs
    }
    
    headers = {
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers).json()
    print(response)

    return response['job_id']

def training_tracker(job_id):
    url = f"http://localhost:23478/train/{job_id}"
    while True:
        response = requests.get(url).json()
        status = response.get("status")
        print(f"Job {job_id} status: {status}")
        if status == "completed":
            print("Training completed.")
            return True
        elif status == "failed":
            raise RuntimeError("Training failed!")
        time.sleep(POLL_INTERVAL)

def promote(job_id):
    pass

def serve_model():

    load_dotenv()

    url = "https://serve_product.quanghung20gg.site/start-vllm"
    
    payload = {"MODEL_NAME": "sft-v3", 
                "MODEL_ALIAS": "champion", 
                "MLFLOW_TRACKING_URI": os.getenv("MLFLOW_TRACKING_URI"),
                "AWS_ACCESS_KEY_ID": os.getenv("AWS_ACCESS_KEY_ID"),
                "AWS_SECRET_ACCESS_KEY": os.getenv("AWS_SECRET_ACCESS_KEY"),
                "MLFLOW_S3_ENDPOINT_URL": os.getenv("MLFLOW_S3_ENDPOINT_URL"),
                "VLLM_LOGGING_LEVEL": os.getenv("VLLM_LOGGING_LEVEL", "DEBUG"),
                "MLFLOW_TRACKING_USERNAME": os.getenv("MLFLOW_TRACKING_USERNAME"),
                "MLFLOW_TRACKING_PASSWORD": os.getenv("MLFLOW_TRACKING_PASSWORD"),
                "VLLM_LOGGING_LEVEL": "DEBUG"}
    
    headers = {
        "Content-Type": "application/json"
    }

    response = requests.post(url, json=payload, headers=headers).json()
    print(response)