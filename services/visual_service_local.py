import torch
from diffusers import StableDiffusionXLPipeline, AutoencoderKL, EulerDiscreteScheduler
import os

# Configuration for D Drive Installation
MODEL_CACHE_DIR = "D:/Antigravity/models"
MODEL_ID = "stabilityai/stable-diffusion-xl-base-1.0"

class LocalVisualService:
    def __init__(self):
        self.pipe = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"LocalVisualService: Device is {self.device}")

        # Ensure directory exists
        if not os.path.exists(MODEL_CACHE_DIR):
            os.makedirs(MODEL_CACHE_DIR)

    def load_model(self):
        """Loads the model into memory. Warning: Heavy."""
        if self.pipe:
            return

        print(f"Loading Local Model from/to {MODEL_CACHE_DIR}...")
        try:
            # We use float16 for speed/memory on RTX 2060
            self.pipe = StableDiffusionXLPipeline.from_pretrained(
                MODEL_ID, 
                torch_dtype=torch.float16, 
                variant="fp16", 
                use_safetensors=True,
                cache_dir=MODEL_CACHE_DIR
            )
            
            # STABILITY FIX: Reset Scheduler to prevent IndexError
            self.pipe.scheduler = EulerDiscreteScheduler.from_config(self.pipe.scheduler.config)
            
            # STABILITY FIX: Reset Scheduler to prevent IndexError
            self.pipe.scheduler = EulerDiscreteScheduler.from_config(self.pipe.scheduler.config)
            
            # MEMORY FIX: Enable VAE Slicing instead of casting (prevents Type Mismatch)
            self.pipe.enable_vae_slicing()
            
            # Optimization Strategy
            try:
                import accelerate
                self.pipe.enable_model_cpu_offload()
                print("GPU Optimization Enabled (CPU Offload)")
            except ImportError:
                print("Accelerate not found, falling back to sequential offload or CPU")
                self.pipe.enable_sequential_cpu_offload()
            except Exception as opt_e:
                print(f"Optimization Warning: {opt_e}")
                # Fallback to pure CUDA if offload fails (might OOM on 8GB if not careful)
                if torch.cuda.is_available():
                    self.pipe.to("cuda")
                
            print("Local Model Loaded Successfully!")
        except Exception as e:
            print(f"Failed to load Local Model: {e}")
            raise e

    def generate_image(self, prompt, negative_prompt="bad quality, blurry, watermark"):
        if not self.pipe:
            self.load_model()
        
        print(f"Generating: {prompt[:50]}...")
        # RTX 2060 is fast enough for 25 steps
        result = self.pipe(
            prompt=prompt, 
            negative_prompt=negative_prompt,
            num_inference_steps=25, 
            guidance_scale=7.0
        )
        
        if result and result.images:
             image = result.images[0]
             print("Generation Complete.")
             return image
        else:
             print("Generation Failed: No images returned.")
             return None
