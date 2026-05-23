import requests
import urllib.parse
import random
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError


class VisualService:
    def __init__(self):
        self.base_url = "https://image.pollinations.ai/prompt/"
        raw_hf_token = os.getenv("HF_API_TOKEN", "")
        self.hf_token = raw_hf_token.strip().strip('"').strip("'")
        configured_model = os.getenv("HF_IMAGE_MODEL", "stabilityai/stable-diffusion-xl-base-1.0")
        self.hf_models = [
            configured_model,
            "stabilityai/stable-diffusion-xl-base-1.0",
            "black-forest-labs/FLUX.1-schnell",
        ]
        self.generated_dir = os.path.join("data", "generated_images")
        os.makedirs(self.generated_dir, exist_ok=True)
        self.pollinations_timeout = int(os.getenv("POLLINATIONS_TIMEOUT", "7"))
        self.hf_timeout = int(os.getenv("HF_TIMEOUT", "45"))
        self.image_total_timeout = int(os.getenv("IMAGE_TOTAL_TIMEOUT", "30"))
        self.last_generation_info = {
            "status": "idle",
            "provider": "none",
            "model": "none",
            "result": "none",
        }

    def _placeholder_image(self, prompt):
        text = (prompt or "Scene Preview")[:70]
        encoded_text = urllib.parse.quote(f"Image service unavailable: {text}")
        return f"https://placehold.co/1024x576/png?text={encoded_text}"

    def _try_huggingface(self, prompt):
        if not self.hf_token:
            self.last_generation_info = {
                "status": "skipped",
                "provider": "huggingface",
                "model": "none",
                "result": "missing_token",
            }
            return None

        headers = {
            "Authorization": f"Bearer {self.hf_token}",
            "Accept": "image/png",
        }
        payload = {
            "inputs": prompt,
            "options": {"wait_for_model": True},
        }

        unique_models = []
        for model_name in self.hf_models:
            if model_name and model_name not in unique_models:
                unique_models.append(model_name)

        for model_name in unique_models:
            endpoints = [
                f"https://router.huggingface.co/hf-inference/models/{model_name}",
                f"https://api-inference.huggingface.co/models/{model_name}",
            ]

            for endpoint in endpoints:
                try:
                    response = requests.post(endpoint, headers=headers, json=payload, timeout=self.hf_timeout)
                    content_type = response.headers.get("content-type", "")

                    if response.status_code == 200 and content_type.startswith("image/"):
                        filename = f"hf_scene_{int(time.time() * 1000)}.png"
                        output_path = os.path.join(self.generated_dir, filename)
                        with open(output_path, "wb") as image_file:
                            image_file.write(response.content)
                        self.last_generation_info = {
                            "status": "success",
                            "provider": "huggingface",
                            "model": model_name,
                            "result": "local_file",
                        }
                        return f"LOCAL_FILE::{output_path}"
                except Exception:
                    continue

        self.last_generation_info = {
            "status": "failed",
            "provider": "huggingface",
            "model": ", ".join(unique_models) if unique_models else "none",
            "result": "no_image_response",
        }
        return None

    def _try_pollinations(self, prompt):
        encoded_prompt = urllib.parse.quote(prompt)
        candidate_urls = [
            f"{self.base_url}{encoded_prompt}?width=1024&height=576&nologo=true",
            f"{self.base_url}{encoded_prompt}?width=768&height=432&nologo=true",
            f"{self.base_url}{encoded_prompt}?width=1024&height=576&nologo=true&seed={random.randint(1, 999999)}",
        ]

        for image_url in candidate_urls:
            try:
                response = requests.get(image_url, timeout=self.pollinations_timeout)
                if response.status_code == 200:
                    self.last_generation_info = {
                        "status": "success",
                        "provider": "pollinations",
                        "model": "pollinations-default",
                        "result": "url",
                    }
                    return image_url
            except Exception:
                continue

        return None

    def generate_image(self, prompt):
        """
        Generates an image URL using Pollinations.ai (Free).
        """
        try:
            # Clean prompt
            cleaned_prompt = prompt.strip().replace("\n", " ")[:350]

            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [
                    executor.submit(self._try_pollinations, cleaned_prompt),
                    executor.submit(self._try_huggingface, cleaned_prompt),
                ]

                try:
                    for future in as_completed(futures, timeout=self.image_total_timeout):
                        try:
                            result = future.result()
                        except Exception:
                            result = None
                        if result:
                            return result
                except FuturesTimeoutError:
                    pass

            self.last_generation_info = {
                "status": "fallback",
                "provider": "placeholder",
                "model": "placehold.co",
                "result": "url",
            }
            return self._placeholder_image(cleaned_prompt)
        except Exception as e:
            print(f"VisualService error: {e}")
            self.last_generation_info = {
                "status": "error",
                "provider": "visual_service",
                "model": "unknown",
                "result": str(e),
            }
            return self._placeholder_image(prompt)
