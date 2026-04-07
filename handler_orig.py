import os, sys, traceback, base64, requests
import runpod

print("BOOT: handler.py starting")
print("BOOT: python", sys.version)
print("BOOT: cwd", os.getcwd())
print("BOOT: files", os.listdir("."))

def handler(event):
    try:
        inp = event.get("input", {}) or {}
        image_url = inp.get("image_url")

        if not image_url:
            return {"error": "Missing required field: input.image_url"}

        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; RunpodServerless/1.0; +https://runpod.io)"
        }
        r = requests.get(image_url, headers=headers, timeout=60)

        if r.status_code != 200:
            return {
                "error": f"Fetch failed: HTTP {r.status_code}",
                "content_type": r.headers.get("content-type"),
                "body_prefix": r.text[:200],
            }

        image_b64 = base64.b64encode(r.content).decode("utf-8")
        #return {"image_b64": image_b64, "bytes": len(r.content)}
        return {
            "image_b64": image_b64,
            "bytes": len(r.content),
            "content_type": r.headers.get("content-type"),
        }


    except Exception as e:
        return {
            "error": str(e),
            "traceback": traceback.format_exc()
        }

if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
