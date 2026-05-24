from aiohttp import web
import json
import os
import asyncio
import logging
import re

logger = logging.getLogger('web_service')
DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "1478115953681367090")

class WebService:
    def __init__(self, bot, port=8080):
        self.bot = bot
        self.port = port
        self.app = web.Application(client_max_size=1024 * 1024 * 50) # 50 MB limit
        self.runner = None
        
        # Setup routes
        self.app.router.add_get('/', self.handle_index)
        self.app.router.add_get('/map', self.handle_map)
        self.app.router.add_get('/storyteller', self.handle_storyteller)
        self.app.router.add_get('/voice', self.handle_voice)
        self.app.router.add_get('/api/tracker/{guild_id}', self.handle_get_tracker)
        self.app.router.add_get('/api/party/{guild_id}', self.handle_get_party)
        self.app.router.add_post('/api/move', self.handle_move)
        # Serve static assets
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web', 'assets')
        if os.path.exists(assets_dir):
            self.app.router.add_static('/assets/', assets_dir)
        self.app.router.add_post('/api/paint', self.handle_paint)
        self.app.router.add_post('/api/paint/clear', self.handle_paint_clear)
        self.app.router.add_post('/api/theme', self.handle_theme)
        self.app.router.add_post('/api/upload', self.handle_upload)
        self.app.router.add_post('/api/chat', self.handle_chat_post)
        self.app.router.add_get('/api/chat/{guild_id}', self.handle_chat_get)
        self.app.router.add_get('/api/channels/{guild_id}', self.handle_channels_get)
        
        self.app.router.add_post('/api/token/add', self.handle_add_token)
        self.app.router.add_post('/api/token/update', self.handle_update_token)
        self.app.router.add_post('/api/token/remove', self.handle_remove_token)
        
        # Add static route for custom maps
        self.maps_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'maps')
        if not os.path.exists(self.maps_dir):
            os.makedirs(self.maps_dir, exist_ok=True)
        self.app.router.add_static('/api/maps/', self.maps_dir)
        self.app.router.add_post('/api/log', self.handle_client_log)
        
        self.web_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web')
        # Add static route for website assets (images, etc)
        self.app.router.add_static('/static/', self.web_dir)
        
        # Settings API
        self.app.router.add_get('/api/settings', self.handle_get_settings)
        self.app.router.add_post('/api/settings', self.handle_save_settings)
        
        # Load settings
        self.settings_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'settings.json')
        self.settings = self._load_settings()

    def _load_settings(self):
        default_settings = {"global": {"app_name": "DICEwithoutNumber", "theme": "dark"}, "servers": {}}
        if os.path.exists(self.settings_path):
            try:
                with open(self.settings_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Backward compatibility for old structure
                    if "global" not in data:
                        return {
                            "global": {
                                "app_name": data.get("app_name", "DICEwithoutNumber"),
                                "theme": data.get("theme", "dark")
                            },
                            "servers": {}
                        }
                    return data
            except:
                return default_settings
        return default_settings

    def _save_settings(self):
        try:
            with open(self.settings_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    async def handle_get_settings(self, request):
        guild_id = request.query.get('guild_id')
        
        # Merge global with server-specific if guild_id provided
        base = self.settings.get("global", {}).copy()
        if guild_id and guild_id in self.settings.get("servers", {}):
            server_overrides = self.settings["servers"][guild_id]
            base.update(server_overrides)
            
        return web.json_response(base)

    async def handle_save_settings(self, request):
        try:
            body = await request.json()
            guild_id = body.get('guild_id') # Optional: for server-specific branding
            
            target = self.settings["global"]
            if guild_id:
                if guild_id not in self.settings["servers"]:
                    self.settings["servers"][guild_id] = {}
                target = self.settings["servers"][guild_id]

            if 'app_name' in body:
                target['app_name'] = body['app_name']
                # Sync Discord identity in background
                asyncio.create_task(self.bot.sync_identity())
            if 'theme' in body:
                target['theme'] = body['theme']
            if 'voice_mode_enabled' in body:
                target['voice_mode_enabled'] = body['voice_mode_enabled']
            
            self._save_settings()
            return web.json_response({"status": "ok", "settings": target})
        except Exception as e:
            logger.error(f"Error saving settings: {e}", exc_info=True)
            return web.json_response({"error": str(e)}, status=400)

    async def handle_index(self, request):
        # Auto-detect Discord Activity launch and serve map directly
        if any(k in request.query for k in ['instance_id', 'frame_id', 'guild_id']):
            return await self.handle_map(request)
            
        path = os.path.join(self.web_dir, 'index.html')
        if not os.path.exists(path):
            return await self.handle_map(request)
            
        with open(path, 'r', encoding='utf-8') as f:
            html = f.read()
        client_id = DISCORD_CLIENT_ID
        invite_url = f"https://discord.com/api/oauth2/authorize?client_id={client_id}&permissions=8&scope=bot%20applications.commands"
        html = html.replace('{{CLIENT_ID}}', client_id)
        html = html.replace('{{INVITE_URL}}', invite_url)
        return web.Response(text=html, content_type='text/html')

    async def handle_storyteller(self, request):
        path = os.path.join(self.web_dir, 'storyteller.html')
        if not os.path.exists(path):
            return web.Response(text="Storyteller page not found", status=404)
            
        with open(path, 'r', encoding='utf-8') as f:
            html = f.read()
        return web.Response(text=html, content_type='text/html')

    async def handle_voice(self, request):
        path = os.path.join(self.web_dir, 'voice.html')
        if not os.path.exists(path):
            return web.Response(text="Voice Remote not found", status=404)
            
        with open(path, 'r', encoding='utf-8') as f:
            html = f.read()
        return web.Response(text=html, content_type='text/html')

    async def handle_map(self, request):
        path = os.path.join(self.web_dir, 'map.html')
        with open(path, 'r', encoding='utf-8') as f:
            html = f.read()
        client_id = str(self.bot.user.id) if self.bot.user else "0"
        html = html.replace('{{CLIENT_ID}}', client_id)
        
        headers = {
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Expires': '0'
        }
        return web.Response(text=html, content_type='text/html', headers=headers)

    async def handle_get_tracker(self, request):
        guild_id = int(request.match_info['guild_id'])
        channel_id = request.query.get('channel_id')
        logger.info(f"DEBUG: GET Tracker - Guild: {guild_id}, Channel: {channel_id}")
        
        map_channel_id = channel_id or "default"
        # Access database directly since it's global to the bot
        data = self.bot.db.get_tracker(guild_id, map_channel_id)
        if not data:
            data = {"combatants": []}
            
        if channel_id:
            data["recent_chat"] = self.bot.db.get_recent_chat(guild_id, channel_id)
            data["current_channel_id"] = channel_id
            
        # Get ALL valid channels physically present in the Discord Server so users can freely switch map instances
        guild = self.bot.get_guild(guild_id)
        if guild:
            chans = [{"id": str(c.id), "name": c.name} for c in guild.text_channels + guild.voice_channels]
            data["active_channels"] = sorted(chans, key=lambda x: x["name"])
        else:
            # Fallback if bot is not in guild or cache is empty
            if channel_id: 
                data["active_channels"] = [{"id": str(channel_id), "name": "Current Channel"}]
            else:
                data["active_channels"] = []
            
        return web.json_response(data)

    async def handle_get_party(self, request):
        guild_id = int(request.match_info['guild_id'])
        camp_data = self.bot.db.get_campaign(guild_id)
        if not camp_data or not camp_data.get("players"):
            return web.json_response({"party": []})
            
        players = []
        for uid, p in camp_data["players"].items():
            players.append({
                "name": p.get("name", "Unknown PC"),
                "hp": p.get("hp", 10),
                "ac": p.get("ac", 10)
            })
        return web.json_response({"party": players})

    async def handle_move(self, request):
        try:
            body = await request.json()
            guild_id = int(body['guild_id'])
            channel_id = body.get('channel_id') or 'default'
            combatant_id = int(body['id'])
            logger.info(f"MOVE: Token {combatant_id} to ({body.get('x')}, {body.get('y')}) in Guild {guild_id}")
            
            # x and y can be null when dragging back to bench
            new_x = body.get('x')
            new_y = body.get('y')
            
            if new_x is not None: new_x = int(new_x)
            if new_y is not None: new_y = int(new_y)
            
            data = self.bot.db.get_tracker(guild_id, channel_id)
            if not data:
                return web.json_response({"error": "Tracker not found"}, status=404)
            
            # Find and update combatant
            for c in data["combatants"]:
                if c["id"] == combatant_id:
                    c["x"] = new_x
                    c["y"] = new_y
                    break
            
            self.bot.db.save_tracker(guild_id, data, channel_id)
            return web.json_response({
                "status": "ok",
                "normalized_message": message,
                "roll_response": roll_response,
            })
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)

    async def handle_paint(self, request):
        try:
            body = await request.json()
            guild_id = int(body['guild_id'])
            channel_id = body.get('channel_id') or 'default'
            x = int(body['x'])
            y = int(body['y'])
            action = body.get('action', 'paint') # 'paint' or 'erase'
            color = body.get('color', 'red')
            
            data = self.bot.db.get_tracker(guild_id, channel_id)
            if not data:
                return web.json_response({"error": "Tracker not found"}, status=404)
                
            if "drawings" not in data:
                data["drawings"] = []
                
            drawings = data["drawings"]
            # remove existing at this coord
            data["drawings"] = [d for d in drawings if not (d['x'] == x and d['y'] == y)]
            
            if action == 'paint':
                data["drawings"].append({"x": x, "y": y, "color": color})
                
            self.bot.db.save_tracker(guild_id, data, channel_id)
            return web.json_response({"status": "ok"})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)

    async def handle_paint_clear(self, request):
        try:
            body = await request.json()
            guild_id = int(body['guild_id'])
            channel_id = body.get('channel_id') or 'default'
            data = self.bot.db.get_tracker(guild_id, channel_id)
            if not data:
                return web.json_response({"error": "Tracker not found"}, status=404)
            data["drawings"] = []
            self.bot.db.save_tracker(guild_id, data, channel_id)
            return web.json_response({"status": "ok"})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)

    async def handle_add_token(self, request):
        try:
            body = await request.json()
            guild_id = int(body['guild_id'])
            channel_id = body.get('channel_id') or 'default'
            logger.info(f"DEBUG: ADD Token - Guild: {guild_id}, Channel: {channel_id}")
            data = self.bot.db.get_tracker(guild_id, channel_id)
            if not data:
                data = {"combatants": [], "current_turn_index": -1}
            
            count = int(body.get("count", 1))
            base_name = body.get("name", "Unknown")
            last_id = 0
            if data.get("combatants"):
                last_id = max([c["id"] for c in data["combatants"]])
                
            new_tokens = []
            for i in range(count):
                token_id = last_id + i + 1
                name = f"{base_name} {i+1}" if count > 1 else base_name
                
                token = {
                    "id": token_id,
                    "name": name,
                    "max_hp": int(body.get("max_hp", 10)),
                    "current_hp": int(body.get("current_hp", body.get("max_hp", 10))),
                    "ac": int(body.get("ac", 10)),
                    "is_enemy": bool(body.get("is_enemy", True)),
                    "hidden": False,
                    "image_url": body.get("image_url"),
                    "size": body.get("size", "1x1"),
                    "x": None,
                    "y": None
                }
                new_tokens.append(token)
            
            if "combatants" not in data: data["combatants"] = []
            data["combatants"].extend(new_tokens)
            self.bot.db.save_tracker(guild_id, data, channel_id)
            return web.json_response({"status": "ok", "ids": [t["id"] for t in new_tokens]})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)

    async def handle_upload(self, request):
        try:
            reader = await request.post()
            file_field = reader.get('file')
            if not file_field:
                return web.json_response({"error": "No file uploaded"}, status=400)
                
            filename = file_field.filename
            # Sanitize and add timestamp
            import time
            base, ext = os.path.splitext(filename)
            safe_filename = f"custom_{int(time.time())}{ext}"
            
            assets_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'web', 'assets')
            os.makedirs(assets_dir, exist_ok=True)
            
            file_path = os.path.join(assets_dir, safe_filename)
            with open(file_path, 'wb') as f:
                f.write(file_field.file.read())
                
            return web.json_response({"status": "ok", "url": f"/assets/{safe_filename}"})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=500)

    async def handle_update_token(self, request):
        try:
            body = await request.json()
            guild_id = int(body['guild_id'])
            channel_id = body.get('channel_id') or 'default'
            token_id = int(body['id'])
            data = self.bot.db.get_tracker(guild_id, channel_id)
            if not data:
                return web.json_response({"error": "Tracker not found"}, status=404)
                
            target = next((c for c in data.get("combatants", []) if c["id"] == token_id), None)
            if not target:
                return web.json_response({"error": "Token not found"}, status=404)
                
            if "name" in body: target["name"] = body["name"]
            if "max_hp" in body: target["max_hp"] = int(body["max_hp"])
            if "current_hp" in body: target["current_hp"] = int(body["current_hp"])
            if "ac" in body: target["ac"] = int(body["ac"])
            if "image_url" in body: target["image_url"] = body["image_url"]
            if "size" in body: target["size"] = body["size"]
            
            self.bot.db.save_tracker(guild_id, data, channel_id)
            return web.json_response({"status": "ok"})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)

    async def handle_remove_token(self, request):
        try:
            body = await request.json()
            guild_id = int(body['guild_id'])
            channel_id = body.get('channel_id') or 'default'
            token_id = int(body['id'])
            data = self.bot.db.get_tracker(guild_id, channel_id)
            if not data:
                return web.json_response({"error": "Tracker not found"}, status=404)
                
            data["combatants"] = [c for c in data.get("combatants", []) if c["id"] != token_id]
            self.bot.db.save_tracker(guild_id, data, channel_id)
            return web.json_response({"status": "ok"})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)

    async def handle_chat_get(self, request):
        try:
            guild_id = int(request.match_info['guild_id'])
            channel_id = request.query.get('channel_id')
            if not channel_id:
                return web.json_response({"error": "channel_id required"}, status=400)
            
            chat = self.bot.db.get_recent_chat(guild_id, channel_id)
            return web.json_response({"messages": chat})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)

    async def handle_channels_get(self, request):
        try:
            guild_id = int(request.match_info['guild_id'])
            guild = self.bot.get_guild(guild_id)
            if not guild:
                return web.json_response({"channels": []})
            
            channels = []
            for chan in guild.text_channels:
                # Only include channels the bot can view
                if chan.permissions_for(guild.me).view_channel:
                    channels.append({"id": str(chan.id), "name": chan.name})
                
            return web.json_response({"channels": channels})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)

    async def handle_chat_post(self, request):
        try:
            body = await request.json()
            guild_id = int(body['guild_id'])
            channel_id = int(body['channel_id'])
            user_name = body.get('user_name', 'Player')
            message = body.get('message', '')
            
            if not message:
                return web.json_response({"error": "Empty message"}, status=400)
                
            channel = self.bot.get_channel(channel_id)
            if not channel:
                return web.json_response({"error": "Channel not found"}, status=404)

            message, _voice_roll_expr = self._normalize_voice_roll_message(message)

            roll_response = None
            dice_service = getattr(self.bot, "dice_service", None)
            if not dice_service:
                dice_cog = self.bot.get_cog("DiceCog")
                if dice_cog and getattr(dice_cog, "bot", None):
                    dice_service = getattr(dice_cog.bot, "dice_service", None)

            if message.startswith((
                "!roll ",
                "/roll ",
                "!gmroll ",
                "/gmroll ",
                "!attack ",
                "/attack ",
                "!skill ",
                "/skill ",
                "!multiroll ",
                "/multiroll ",
            )):
                try:
                    command, expr = message[1:].split(" ", 1)
                except ValueError:
                    command, expr = message[1:], ""
                roll_response = self._build_voice_roll_response(command.lower(), expr.strip(), dice_service)

            # Send to Discord
            formatted_msg = f"**{user_name}** (Map): {message}"
            if roll_response:
                formatted_msg += f"\n\n{roll_response}"

            await channel.send(formatted_msg)

            # Save to local history immediately for the map to see it faster
            self.bot.db.save_chat_message(guild_id, channel_id, user_name, message)
            if roll_response:
                self.bot.db.save_chat_message(guild_id, channel_id, self.bot.user.name, roll_response)

            return web.json_response({"status": "ok"})
        except Exception as e:
            logger.exception("Voice chat post failed")
            return web.json_response({"error": str(e)}, status=400)

    def _normalize_voice_roll_message(self, message: str) -> tuple[str, str | None]:
        """Normalize common voice phrases into a roll-friendly message."""
        text = re.sub(r"\s+", " ", str(message).strip().lower())
        if not text:
            return message, None

        word_numbers = {
            "one": "1",
            "two": "2",
            "three": "3",
            "four": "4",
            "five": "5",
            "six": "6",
            "seven": "7",
            "eight": "8",
            "nine": "9",
            "ten": "10",
        }
        for word, digit in word_numbers.items():
            text = re.sub(rf"\b{word}\b", digit, text)

        text = re.sub(r"\bg\s*m\b", "gm", text)
        text = re.sub(r"\bplus\b", "+", text)
        text = re.sub(r"\bminus\b", "-", text)
        text = re.sub(r"\bgm\s+roll\b", "gmroll", text)
        text = re.sub(r"\bmulti\s+roll\b", "multiroll", text)
        text = re.sub(r"(\d+)\s*d\s*(\d+)", r"\1d\2", text)

        def looks_like_roll(expr: str) -> bool:
            compact = expr.replace(" ", "")
            return bool(re.fullmatch(r"\d{2}", compact) or re.fullmatch(r"\d+d\d+(?:[+-]\d+)*", compact))

        command_match = re.match(
            r"^(?:!|/)?(?P<command>gmroll|gm\s+roll|multiroll|multi\s+roll|attack|skill|roll)(?:\s+(?P<payload>.*))?$",
            text,
        )
        if command_match:
            command = command_match.group("command").replace(" ", "")
            payload = (command_match.group("payload") or "").strip()

            if command == "multiroll" and payload:
                times_match = re.match(r"^(\d+)\s+(.*)$", payload)
                if times_match:
                    payload = f"{times_match.group(1)}x {times_match.group(2).strip()}"

            if command in {"attack", "skill"} and not payload:
                payload = "1d20" if command == "attack" else "2d6"

            if command in {"roll", "gmroll"} and payload and looks_like_roll(payload):
                compact = payload.replace(" ", "")
                return f"!{command} {compact}", compact

            if command == "multiroll" and payload:
                return f"!multiroll {payload}", payload

            if command in {"attack", "skill"} and payload:
                compact = payload.replace(" ", "")
                return f"!{command} {compact}", compact

            return message, None

        if looks_like_roll(text):
            compact = text.replace(" ", "")
            return f"!roll {compact}", compact

        return message, None

    def _build_voice_roll_response(self, command: str, expression: str, dice_service) -> str | None:
        if not dice_service:
            return "Error: dice service is unavailable."

        command = command.lower().strip()
        expression = (expression or "").strip()

        if command == "multiroll":
            times_match = re.match(r"^(\d+)x\s*(.+)$", expression)
            if not times_match:
                times_match = re.match(r"^(\d+)\s+(.*)$", expression)
            if not times_match:
                return "Error: say multi roll like `multi roll 3 2d6`."

            times = int(times_match.group(1))
            inner_expr = times_match.group(2).strip()
            if times > 20:
                return "Error: too many repeats. Max 20."

            lines = []
            for i in range(times):
                total, details, err, _, _ = dice_service.parse_and_roll(inner_expr)
                if err:
                    return f"Error rolling `{inner_expr}`: {err}"
                lines.append(f"-> Roll {i + 1}: {details} = **{total}**")

            return "Multi Roll\n" + "\n".join(lines)

        if command in {"attack", "skill"} and not expression:
            expression = "1d20" if command == "attack" else "2d6"

        total, details, err, repeats, _ = dice_service.parse_and_roll(expression)
        if err:
            return f"Error rolling `{expression}`: {err}"

        if repeats > 1:
            repeat_match = re.match(r"^(\d+)\s*[x#]\s*(.*)$", expression)
            inner_expr = repeat_match.group(2).strip() if repeat_match else expression
            lines = []
            for i in range(repeats):
                repeat_total, repeat_details, repeat_err, _, _ = dice_service.parse_and_roll(inner_expr)
                if repeat_err:
                    return f"Error rolling `{inner_expr}`: {repeat_err}"
                lines.append(f"-> Roll {i + 1}: {repeat_details} = **{repeat_total}**")
            return "Result\n" + "\n".join(lines)

        titles = {
            "roll": "Result",
            "gmroll": "GM Roll",
            "attack": "Attack Roll",
            "skill": "Skill Check",
        }
        title = titles.get(command, "Result")
        result = f"-> Result: {details} = **{total}**"
        if command == "gmroll":
            return f"{title}\n|| {result} ||\n_(Hidden voice roll.)_"
        return f"{title}\n{result}"

    async def handle_theme(self, request):
        try:
            body = await request.json()
            guild_id = int(body['guild_id'])
            channel_id = body.get('channel_id') or 'default'
            theme = body['theme']
            
            data = self.bot.db.get_tracker(guild_id, channel_id)
            if not data:
                data = {"combatants": [], "current_turn_index": -1}
            
            if theme and ("/" in theme or "http" in theme):
                data["background_url"] = theme
                data["theme"] = "custom"
            else:
                data["theme"] = theme
                data["background_url"] = None
                
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)


    async def handle_client_log(self, request):
        try:
            body = await request.json()
            level = body.get('level', 'INFO').upper()
            msg = body.get('msg', 'Empty message')
            data = body.get('data', '')
            
            log_msg = f"[CLIENT {level}] {msg} | Data: {data}"
            if level == 'ERROR':
                logger.error(log_msg)
            elif level == 'WARN':
                logger.warning(log_msg)
            else:
                logger.info(log_msg)
                
            return web.json_response({"status": "ok"})
        except Exception as e:
            return web.json_response({"error": str(e)}, status=400)

    async def start(self):
        self.runner = web.AppRunner(self.app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, '0.0.0.0', self.port)
        await site.start()
        print(f"[*] Web Service started on port {self.port}")

    async def stop(self):
        if self.runner:
            await self.runner.cleanup()
