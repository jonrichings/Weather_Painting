FROM runpod-workers/worker-comfyui:latest

WORKDIR /app

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY handler.py /app/handler.py
COPY workflow_img2img_sd15.json /app/workflow_img2img_sd15.json

# Download SD1.5 checkpoint
RUN mkdir -p /comfyui/models/checkpoints && \
    apt-get update && apt-get install -y --no-install-recommends wget ca-certificates && \
    wget -O /comfyui/models/checkpoints/v1-5-pruned-emaonly.safetensors \
      "https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors" && \
    rm -rf /var/lib/apt/lists/*

CMD ["python3", "-u", "/app/handler.py"]
