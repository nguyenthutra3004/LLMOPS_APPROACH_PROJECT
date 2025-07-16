FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04

ENV NVIDIA_VISIBLE_DEVICES all
ENV NVIDIA_DRIVER_CAPABILITIES compute,utility

RUN apt-get update && \
    apt-get install -y \
    python3.10 \
    python3-pip \
    wget \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

RUN ln -s /usr/bin/python3.10 /usr/bin/python

RUN pip install --upgrade pip

# Optional: install extra tools
RUN pip install vllm
RUN pip uninstall -y blinker || true
RUN pip install --no-cache-dir --ignore-installed \
    mlflow huggingface_hub boto3 "numpy<2.1" 
    
COPY start.sh /start.sh
RUN chmod +x /start.sh

ENTRYPOINT ["/start.sh"]
