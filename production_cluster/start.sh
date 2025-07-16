#!/bin/bash
set -e  

mkdir -p ./model

echo "Downloading model from MLflow..."
echo "models:/${MODEL_NAME}@${MODEL_ALIAS}"

mlflow artifacts download --artifact-uri "models:/${MODEL_NAME}@${MODEL_ALIAS}" --dst-path ./model

# cd model
ls 

vllm serve Qwen/Qwen2.5-1.5B-Instruct --enable-lora --lora-modules initial-sft=./model --enforce-eager --max-lora-rank 64 --gpu-memory-utilization 0.98 --max-model-len 2048 --port 8000

# vllm serve Qwen/Qwen3-1.7B --enable-lora --lora-modules initial-sft=./model --enforce-eager --max-lora-rank 64 --gpu-memory-utilization 0.5 --max-model-len 4096 --port 8000