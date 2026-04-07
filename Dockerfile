FROM runpod-workers/worker-comfyui:latest

WORKDIR /app

# Python deps for the handler
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy handler + workflow
COPY handler.py /app/handler.py
COPY workflow_img2img_sd15.json /app/workflow_img2img_sd15.json

# Download SD1.5 checkpoint into ComfyUI checkpoints directory
# Note: this is a common mirror; if it ever changes, swap the URL.
RUN mkdir -p /comfyui/models/checkpoints && \
    python3 - <<'PY' \
import urllib.request, os \
url = "https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.safetensors" \
out = "/comfyui/models/checkpoints/v1-5-pruned-emaonly.safetensors" \
if not os.path.exists(out): \
    print("Downloading checkpoint...") \
    urllib.request.urlretrieve(url, out) \
    print("Saved", out) \
else: \
    print("Checkpoint already present:", out) \
PY

# The base image is already set up to run ComfyUI; we run our handler as the serverless entrypoint.
CMD ["python3", "-u", "/app/handler.py"]
