import os
import json
import logging
from aiohttp import web
import aiohttp

# Standalone AI Service for DICEwithoutNumber
# Handles AI Narrative requests independently of the main Discord bot.

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AI_Service")

async def handle_ai_storytell(request):
    try:
        body = await request.json()
        prompt = body.get('prompt', '')
        if not prompt:
            return web.json_response({"error": "Empty prompt"}, status=400)
        
        async with aiohttp.ClientSession() as session:
            url = "http://localhost:11434/api/generate"
            payload = {
                "model": "phi3",
                "prompt": f"You are a skilled Sci-Fi/Fantasy Storyteller and Dungeon Master. Describe this or answer the following in a narrative and immersive way: {prompt}",
                "stream": False
            }
            async with session.post(url, json=payload) as resp:
                if resp.status != 200:
                    return web.json_response({"error": f"Ollama Error: {resp.status}"}, status=500)
                data = await resp.json()
                return web.json_response({"response": data.get('response', 'No response from AI')})
    except Exception as e:
        logger.error(f"AI Service error: {e}")
        return web.json_response({"error": str(e)}, status=500)

async def handle_options(request):
    return web.Response(headers={
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    })

app = web.Application()
# Add CORS headers
async def cors_middleware(app, handler):
    async def middleware_handler(request):
        if request.method == 'OPTIONS':
            return await handle_options(request)
        response = await handler(request)
        response.headers['Access-Control-Allow-Origin'] = '*'
        return response
    return middleware_handler

app.middlewares.append(cors_middleware)
app.router.add_post('/api/ai/storytell', handle_ai_storytell)
app.router.add_options('/api/ai/storytell', handle_options)

if __name__ == '__main__':
    port = int(os.environ.get("AI_PORT", 5001))
    logger.info(f"Starting AI Service on port {port} (all interfaces)")
    web.run_app(app, host='0.0.0.0', port=port)
