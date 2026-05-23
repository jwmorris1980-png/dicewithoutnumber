from services.map_service import MapRenderer
import os

def test_render():
    renderer = MapRenderer()
    combatants = [
        {'name': 'Hero', 'x': 2, 'y': 3, 'is_enemy': False},
        {'name': 'Goblin', 'x': 5, 'y': 5, 'is_enemy': True},
        {'name': 'Dragon', 'x': 8, 'y': 1, 'is_enemy': True}
    ]
    
    try:
        buffer = renderer.render_map(combatants)
        with open('test_map.png', 'wb') as f:
            f.write(buffer.getvalue())
        print("✅ Map rendered successfully to test_map.png")
    except Exception as e:
        print(f"❌ Map rendering failed: {e}")

if __name__ == "__main__":
    test_render()
