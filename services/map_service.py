import io
import math
import os
from PIL import Image, ImageDraw, ImageFont

class MapRenderer:
    def __init__(self, grid_size=(10, 10), cell_size=60):
        self.grid_width, self.grid_height = grid_size
        self.cell_size = cell_size
        self.margin = 40
        self.width = self.grid_width * self.cell_size + self.margin * 2
        self.height = self.grid_height * self.cell_size + self.margin * 2
        
        # Themes
        self.themes = {
            "default": {
                "bg": (240, 240, 240),
                "grid": (200, 200, 200),
                "text": (50, 50, 50)
            },
            "forest": {
                "bg": (34, 139, 34),
                "grid": (0, 100, 0),
                "text": (255, 255, 255)
            },
            "cave": {
                "bg": (105, 105, 105),
                "grid": (47, 79, 79),
                "text": (255, 255, 255)
            },
            "desert": {
                "bg": (210, 180, 140),
                "grid": (139, 69, 19),
                "text": (0, 0, 0)
            }
        }
        
        self.player_color = (100, 149, 237) # Cornflower Blue
        self.enemy_color = (220, 20, 60)   # Crimson
        
    def render_map(self, combatants, theme_name="default", background_path=None, drawings=None, viewport=None, selection_id=None, grid_type="square"):
        """
        Renders a tactical map with combatants, drawings, and an optional viewport highlight.
        """
        theme = self.themes.get(theme_name, self.themes["default"])
        bg_color = theme["bg"]
        grid_color = theme.get("grid", (200, 200, 200))
        text_color = theme["text"]
        
        radius = self.cell_size // 3

        # Background logic
        if theme_name == "custom" and background_path and os.path.exists(background_path):
            try:
                bg_image = Image.open(background_path).convert('RGB')
                bg_image = bg_image.resize((self.width, self.height), Image.Resampling.LANCZOS)
                image = bg_image
            except Exception:
                image = Image.new('RGB', (self.width, self.height), bg_color)
        else:
            image = Image.new('RGB', (self.width, self.height), bg_color)
            
        draw = ImageDraw.Draw(image)
        
        # Draw Drawings (Rectangles/Painted cells)
        if drawings:
            overlay = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
            overlay_draw = ImageDraw.Draw(overlay)
            for d in drawings:
                x, y = d.get('x'), d.get('y')
                if x is not None and y is not None:
                    rx0 = self.margin + x * self.cell_size
                    ry0 = self.margin + y * self.cell_size
                    rx1 = rx0 + self.cell_size
                    ry1 = ry0 + self.cell_size
                    # Area fill with transparency
                    overlay_draw.rectangle([rx0, ry0, rx1, ry1], fill=(255, 0, 0, 60)) # Default red tint for now
                    # Optional label
                    if d.get('label'):
                        overlay_draw.text((rx0 + 2, ry0 + 2), d['label'], fill=(255, 255, 255, 180))
            image.paste(overlay, (0, 0), overlay)

        # Draw Viewport Highlight
        if viewport:
            # Draw semi-transparent highlight over the viewport area (4x4)
            vx, vy = viewport
            vx0 = self.margin + vx * self.cell_size
            vy0 = self.margin + vy * self.cell_size
            vx1 = vx0 + self.cell_size * 4
            vy1 = vy0 + self.cell_size * 4
            
            # Subtle white frame for the viewport
            draw.rectangle([vx0, vy0, vx1, vy1], outline=(255, 255, 255, 200), width=3)

        # Draw grid
        for i in range(self.grid_width + 1):
            x = self.margin + i * self.cell_size
            draw.line([(x, self.margin), (x, self.height - self.margin)], fill=grid_color, width=1)
            # Labels
            if i < self.grid_width:
                label = chr(ord('A') + i)
                draw.text((x + self.cell_size // 2 - 5, self.margin - 25), label, fill=text_color)
                
        for j in range(self.grid_height + 1):
            y = self.margin + j * self.cell_size
            draw.line([(self.margin, y), (self.width - self.margin, y)], fill=grid_color, width=1)
            # Labels
            if j < self.grid_height:
                label = str(j + 1)
                draw.text((self.margin - 25, y + self.cell_size // 2 - 5), label, fill=text_color)
                
        # Draw Hex grid if enabled
        if grid_type == 'hex':
            # Clear square grid if we want ONLY hex
            image = Image.new('RGB', (self.width, self.height), bg_color)
            draw = ImageDraw.Draw(image)
            
            hex_size = self.cell_size * 0.6
            for q in range(self.grid_width):
                for r in range(self.grid_height):
                    # Flat-topped hex math
                    x = self.margin + hex_size * (3/2 * q)
                    y = self.margin + hex_size * (math.sqrt(3)/2 * q + math.sqrt(3) * r)
                    
                    points = []
                    for i in range(6):
                        angle_deg = 60 * i
                        angle_rad = math.pi / 180 * angle_deg
                        points.append((
                            x + hex_size * math.cos(angle_rad),
                            y + hex_size * math.sin(angle_rad)
                        ))
                    draw.polygon(points, outline=grid_color)
                    
                    # Labels (Axial q,r)
                    if q % 2 == 0 and r % 2 == 0:
                         label = f"{q},{r}"
                         draw.text((x - 10, y - 5), label, fill=grid_color)
                
        # Draw combatants
        for c in combatants:
            x_coord = c.get('x')
            y_coord = c.get('y')
            
            if x_coord is None or y_coord is None:
                continue
                
            color = self.enemy_color if c.get('is_enemy') else self.player_color
            
            if grid_type == 'hex':
                hex_size = self.cell_size * 0.6
                px = self.margin + hex_size * (3/2 * x_coord)
                py = self.margin + hex_size * (math.sqrt(3)/2 * x_coord + math.sqrt(3) * y_coord)
            else:
                px = self.margin + x_coord * self.cell_size + self.cell_size // 2
                py = self.margin + y_coord * self.cell_size + self.cell_size // 2
            
            # Draw selection ring
            if selection_id and str(c.get('id')) == str(selection_id):
                draw.ellipse([(px - radius - 5, py - radius - 5), (px + radius + 5, py + radius + 5)], outline=(255, 215, 0), width=3) # Gold ring

            # Draw token
            draw.ellipse([(px - radius, py - radius), (px + radius, py + radius)], fill=color, outline=(0,0,0))
            
            # Show stats if not hidden or not enemy
            show_stats = not c.get("hidden") or not c.get("is_enemy")
            
            # Token Label (Initials + AC)
            initials = "".join([n[0] for n in c['name'].split()]).upper()[:2]
            ac = c.get('ac', 10)
            
            # Determine text position to center it in the token
            label = initials
            if show_stats:
                label += f"\nAC {ac}"
            
            # Draw text with center alignment
            draw.text((px, py), label, fill=(255,255,255), anchor="mm", align="center")
            
            # Draw full name below
            name = c['name']
            draw.text((px, py + radius + 15), name, fill=(255,255,255) if (background_path and theme_name == "custom") else text_color, anchor="ms")
            
        # Save to buffer
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer
