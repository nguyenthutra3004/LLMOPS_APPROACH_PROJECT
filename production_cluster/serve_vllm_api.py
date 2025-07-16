from fastapi import FastAPI, Request
from pydantic import BaseModel
import subprocess
import uuid
import os

app = FastAPI()

class VLLMRequest(BaseModel):
    MODEL_NAME: str
    MODEL_ALIAS: str
    MLFLOW_TRACKING_URI: str
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str
    MLFLOW_S3_ENDPOINT_URL: str
    MLFLOW_TRACKING_USERNAME: str
    MLFLOW_TRACKING_PASSWORD: str
    VLLM_LOGGING_LEVEL: str = "DEBUG"

@app.post("/start-vllm")
async def start_vllm_container(config: VLLMRequest):
    container_name = f"vllm_{uuid.uuid4().hex[:8]}"

    check_cmd = ["docker", "ps", "--filter", "publish=8000", "--format", "{{.ID}}"]
    existing_container = subprocess.check_output(check_cmd).decode().strip()
    if existing_container:
        subprocess.run(["docker", "stop", existing_container])

    env_vars = [
        "-e", f"MODEL_NAME={config.MODEL_NAME}",
        "-e", f"MODEL_ALIAS={config.MODEL_ALIAS}",
        "-e", f"MLFLOW_TRACKING_URI={config.MLFLOW_TRACKING_URI}",
        "-e", f"MLFLOW_TRACKING_USERNAME={config.MLFLOW_TRACKING_USERNAME}",
        "-e", f"MLFLOW_TRACKING_PASSWORD={config.MLFLOW_TRACKING_PASSWORD}",
        "-e", f"AWS_ACCESS_KEY_ID={config.AWS_ACCESS_KEY_ID}",
        "-e", f"AWS_SECRET_ACCESS_KEY={config.AWS_SECRET_ACCESS_KEY}",
        "-e", f"MLFLOW_S3_ENDPOINT_URL={config.MLFLOW_S3_ENDPOINT_URL}",
        "-e", f"VLLM_LOGGING_LEVEL={config.VLLM_LOGGING_LEVEL}"
    ]

    docker_cmd = [
        "docker", "run", "-d",
        "--name", container_name,
        "--gpus", "all",
        "-p", "8000:8000"
    ] + env_vars + ["vllm"]

    print("Executing command:", " ".join(docker_cmd))
    # Run in background, silently
    process = subprocess.Popen(
        docker_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )

    stdout, stderr = process.communicate()

    if process.returncode != 0:
        return {
            "status": "failed",
            "message": f"Failed to start vLLM container. Error: {stderr.decode()}",
            "container_name": container_name
        }

    return {
        "status": "started",
        "message": f"vLLM container is launching as {container_name}",
        "container_name": container_name,
        "stdout": stdout.decode(),
        "stderr": stderr.decode()
    }