# clean base image containing only comfyui, comfy-cli and comfyui-manager
FROM runpod/worker-comfyui:5.5.1-base

# install custom nodes into comfyui (first node with --mode remote to fetch updated cache)
# Could not resolve unknown registry custom node: CheckpointLoaderSimple (no aux_id or registry id provided)
# Could not resolve unknown registry custom node: CheckpointLoaderSimple (no aux_id or registry id provided)

# download models into comfyui
RUN comfy model download --url https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/resolve/main/sd_xl_base_1.0.safetensors --relative-path models/checkpoints/SDXL --filename sd_xl_base_1.0.safetensors
RUN comfy model download --url https://huggingface.co/stabilityai/stable-diffusion-xl-refiner-1.0/resolve/main/sd_xl_refiner_1.0.safetensors --relative-path models/checkpoints/SDXL --filename sd_xl_refiner_1.0.safetensors

# copy all input data (like images or videos) into comfyui (uncomment and adjust if needed)
# COPY input/ /comfyui/input/

# ---- install Python deps for the Runpod serverless handler ----
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# ---- copy handler + workflow into the image ----
COPY handler.py /app/handler.py
COPY sdxl_simple_example.json /app/sdxl_simple_example.json

# ---- start the Runpod serverless handler (it will talk to the local ComfyUI) ----
CMD ["python3", "-u", "/app/handler.py"]
