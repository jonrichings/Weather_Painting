import base64
import json
import random
import time
from io import BytesIO

import requests
import runpod
from PIL import Image

COMFY_URL = "http://127.0.0.1:8188"

DEFAULTS = {
    "prompt": "make the sky red",
    "negative_prompt": "text, watermark, logo, blurry, low quality",
    "steps": 25,
    "cfg": 7.0,
    "denoise": 0.30,          # lower = closer to reference
    "seed": -1,               # -1 => random
    "sampler_name": "euler",
    "scheduler": "normal",
    "width": 512,
    "height": 512,
    "jpeg_quality": 90
}

def get(inp, k):
    return inp.get(k, DEFAULTS[k])

def fetch_image_bytes(url: str) -> bytes:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; RunpodServerless/1.0)"}
    r = requests.get(url, headers=headers, timeout=60)
    r.raise_for_status()
    return r.content

def normalize_to_png(image_bytes: bytes, width: int, height: int) -> bytes:
    # ComfyUI input upload works well with PNG; normalize size here for consistent workflow
    im = Image.open(BytesIO(image_bytes)).convert("RGB").resize((width, height))
    buf = BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()

def comfy_upload_image(png_bytes: bytes, filename: str = "input.png") -> str:
    # Upload to ComfyUI input folder
    files = {"image": (filename, png_bytes, "image/png")}
    r = requests.post(f"{COMFY_URL}/upload/image", files=files, timeout=60)
    r.raise_for_status()
    # returns {"name": "...", "subfolder": "", "type": "input"}
    return r.json()["name"]

def comfy_submit(workflow: dict) -> str:
    r = requests.post(f"{COMFY_URL}/prompt", json={"prompt": workflow}, timeout=60)
    r.raise_for_status()
    return r.json()["prompt_id"]

def comfy_wait_and_get_first_image_bytes(prompt_id: str, timeout_s: int = 600) -> bytes:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        r = requests.get(f"{COMFY_URL}/history/{prompt_id}", timeout=60)
        r.raise_for_status()
        hist = r.json().get(prompt_id)

        if hist and "outputs" in hist:
            # Our workflow uses node id "save_image"
            out = hist["outputs"]["save_image"]["images"][0]
            params = {
                "filename": out["filename"],
                "subfolder": out.get("subfolder", ""),
                "type": "output",
            }
            vr = requests.get(f"{COMFY_URL}/view", params=params, timeout=60)
            vr.raise_for_status()
            return vr.content

        time.sleep(0.4)

    raise TimeoutError("Timed out waiting for ComfyUI output")

def png_bytes_to_jpeg_b64(png_bytes: bytes, quality: int = 90) -> str:
    im = Image.open(BytesIO(png_bytes)).convert("RGB")
    buf = BytesIO()
    im.save(buf, format="JPEG", quality=quality, optimize=True)
    return base64.b64encode(buf.getvalue()).decode("utf-8")

def handler(event):
    inp = event.get("input", {}) or {}
    image_url = inp.get("image_url")
    if not image_url:
        return {"error": "Missing required field: input.image_url"}

    width = int(get(inp, "width"))
    height = int(get(inp, "height"))

    seed = int(get(inp, "seed"))
    if seed == -1:
        seed = random.randint(0, 2**31 - 1)

    prompt = get(inp, "prompt")
    negative_prompt = get(inp, "negative_prompt")

    workflow = json.load(open("workflow_img2img_sd15.json", "r"))

    # Patch workflow values (node IDs must match the workflow file below)
    workflow["load_image"]["inputs"]["image"] = None  # placeholder, set after upload
    workflow["prompt_pos"]["inputs"]["text"] = prompt
    workflow["prompt_neg"]["inputs"]["text"] = negative_prompt

    workflow["ksampler"]["inputs"]["seed"] = seed
    workflow["ksampler"]["inputs"]["steps"] = int(get(inp, "steps"))
    workflow["ksampler"]["inputs"]["cfg"] = float(get(inp, "cfg"))
    workflow["ksampler"]["inputs"]["sampler_name"] = get(inp, "sampler_name")
    workflow["ksampler"]["inputs"]["scheduler"] = get(inp, "scheduler")
    workflow["ksampler"]["inputs"]["denoise"] = float(get(inp, "denoise"))

    # Download -> normalize -> upload to ComfyUI -> set LoadImage filename
    raw = fetch_image_bytes(image_url)
    png = normalize_to_png(raw, width, height)
    uploaded_name = comfy_upload_image(png, filename="input.png")
    workflow["load_image"]["inputs"]["image"] = uploaded_name

    prompt_id = comfy_submit(workflow)
    out_png = comfy_wait_and_get_first_image_bytes(prompt_id)

    out_b64 = png_bytes_to_jpeg_b64(out_png, quality=int(get(inp, "jpeg_quality")))
    return {"image_b64": out_b64, "seed": seed, "width": width, "height": height}

if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
