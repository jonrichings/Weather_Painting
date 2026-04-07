import base64
import requests
import runpod


def handler(event):
    inp = event.get("input", {}) or {}
    image_url = inp.get("image_url")

    if not image_url:
        return {"error": "Missing required field: input.image_url"}

    r = requests.get(image_url, timeout=60)
    r.raise_for_status()

    image_b64 = base64.b64encode(r.content).decode("utf-8")
    return {"image_b64": image_b64}


if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
