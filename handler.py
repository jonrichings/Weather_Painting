import os
import json
import time
import base64
import random
import requests
import runpod
from io import BytesIO
from PIL import Image

# ---------- Defaults (can be overridden per request) ----------
DEFAULTS = {
    "prompt": "make the sky red",
    "negative_prompt": "text, watermark, logo, blurry, low quality",
    "steps": 25,
    "cfg": 7.0,
    "denoise": 0.30,          # keep low to preserve composition
    "seed": -1,               # -1 means random
    "sampler": "euler",
    "scheduler": "normal",
    "width": 512,
    "height": 512,
}

COMFY_URL = "http://127.0.0.1:8188"

def _get(inp, key):
    return inp.get(key, DEFAULTS[key])

def download_image(image_url: str) -> Image.Image:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; RunpodServerless/1.0)"}
    r = requests.get(image_url, headers=headers, timeout=60)
    r.raise_for_status()
    im = Image.open(BytesIO(r.content)).convert("RGB")
    return im

def image_to_png_b64(im: Image.Image) -> str:
    buf = BytesIO()
    im.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")

def comfy_prompt(workflow: dict) -> dict:
    r = requests.post(f"{COMFY_URL}/prompt", json={"prompt": workflow}, timeout=60)
    r.raise_for_status()
    return r.json()

def comfy_history(prompt_id: str) -> dict:
    r = requests.get(f"{COMFY_URL}/history/{prompt_id}", timeout=60)
    r.raise_for_status()
    return r.json()

def handler(event):
    inp = event.get("input", {}) or {}

    image_url = inp.get("image_url")
    if not image_url:
        return {"error": "Missing required field: input.image_url"}

    # parameters (defaults overridden by input JSON)
    prompt = _get(inp, "prompt")
    negative_prompt = _get(inp, "negative_prompt")
    steps = int(_get(inp, "steps"))
    cfg = float(_get(inp, "cfg"))
    denoise = float(_get(inp, "denoise"))
    width = int(_get(inp, "width"))
    height = int(_get(inp, "height"))
    sampler = _get(inp, "sampler")
    scheduler = _get(inp, "scheduler")
    seed = int(_get(inp, "seed"))
    if seed == -1:
        seed = random.randint(0, 2**31 - 1)

    # download and convert input image to PNG base64 (ComfyUI-friendly)
    init_image = download_image(image_url).resize((width, height))
    init_image_b64 = image_to_png_b64(init_image)

    # load workflow template from file
    workflow = json.load(open("workflow_api_img2img_sdx15.json", "r"))

    # ---- Patch workflow fields (these keys depend on the workflow template) ----
    # You will paste the workflow I provide below; these node ids match that file.
    workflow["3"]["inputs"]["seed"] = seed
    workflow["3"]["inputs"]["steps"] = steps
    workflow["3"]["inputs"]["cfg"] = cfg
    workflow["3"]["inputs"]["sampler_name"] = sampler
    workflow["3"]["inputs"]["scheduler"] = scheduler
    workflow["3"]["inputs"]["denoise"] = denoise

    workflow["6"]["inputs"]["text"] = prompt
    workflow["7"]["inputs"]["text"] = negative_prompt

    workflow["10"]["inputs"]["image"] = init_image_b64

    # send to ComfyUI
    submit = comfy_prompt(workflow)
    prompt_id = submit["prompt_id"]

    # poll until result exists
    deadline = time.time() + 600
    while time.time() < deadline:
        hist = comfy_history(prompt_id)
        h = hist.get(prompt_id)
        if h and "outputs" in h:
            # Extract the first image from the SaveImage node output
            # (again, depends on workflow template)
            images = h["outputs"]["9"]["images"]
            filename = images[0]["filename"]
            subfolder = images[0].get("subfolder", "")
            # fetch image bytes from ComfyUI
            r = requests.get(f"{COMFY_URL}/view", params={"filename": filename, "subfolder": subfolder, "type": "output"}, timeout=60)
            r.raise_for_status()
            out_b64 = base64.b64encode(r.content).decode("utf-8")
            return {
                "image_b64": out_b64,
                "seed": seed,
                "width": width,
                "height": height
            }
        time.sleep(0.5)

    return {"error": "Timed out waiting for ComfyUI result"}

if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
