# production_cluster
1. Hosting mlflow server:
```bash
export AWS_ACCESS_KEY_ID=
export AWS_SECRET_ACCESS_KEY=
export MLFLOW_S3_ENDPOINT_URL=

mlflow server \
  --backend-store-uri sqlite:///mlflow.db \
  --default-artifact-root \
  --host 0.0.0.0 \
  --port 5000
```

2. Build docker image for vllm serving:
```bash
sudo docker build -t lora-vllm .
```

3. [Optional] export http for mlflow (using ngrok or zrok):
```bash
   ngrok http 5000
```

4. test docker image:
```bash
docker run --rm \
  -e MODEL_NAME="thinking" \
  -e MODEL_VERSION="5" \
  -e MODEL_ALIAS="champion" \
  -e MLFLOW_TRACKING_URI="" \
  -e AWS_ACCESS_KEY_ID="" \
  -e AWS_SECRET_ACCESS_KEY="" \
  -e MLFLOW_S3_ENDPOINT_URL="" \
  -e MLFLOW_TRACKING_USERNAME="admin" \
  -e MLFLOW_TRACKING_PASSWORD="" \
  -e VLLM_LOGGING_LEVEL=DEBUG \
  --gpus all \
  -p 8000:8000 \
  vllm
```

5. Hosting deployment API:
```bash
uvicorn serve_vllm_api:app --host 0.0.0.0 --port 6789
```

6. Send API for hosting
```bash
curl -X POST http://localhost:6789/start-vllm -H "Content-Type: application/json" -d '{"MODEL_NAME": "initial-sft", "MODEL_VERSION": "latest", "MLFLOW_TRACKING_URI": "", "AWS_ACCESS_KEY_ID": "", "AWS_SECRET_ACCESS_KEY": "", "MLFLOW_S3_ENDPOINT_URL": "", "VLLM_LOGGING_LEVEL": "DEBUG"}'
```

7. Now see magic on port 8000
```bash
python test_streaming.py
```
