import asyncio
from types import SimpleNamespace

from cogs.ships import ShipsCog, looks_like_ship_payload
from cogs.sheets import CharacterSheetCog
from services.database import DatabaseService


CWN_SHIP = {
    "id": "ship-1",
    "name": "Lucky Strike",
    "hullId": "free-merchant",
    "hp": 20,
    "ac": 14,
    "armor": 2,
    "speed": 3,
    "power": 10,
    "mass": 15,
    "fittings": [
        {"fittingId": "spike-drive-1", "count": 1},
        {"fittingId": "extended-stores", "count": 1},
    ],
    "weapons": [{"weaponId": "multifocal-laser", "count": 1}],
    "defenses": [{"defenseId": "hardened-polyceramic-overlay"}],
    "cargo": [{"name": "Spare parts", "tons": 2}],
}


class MemoryDatabase:
    def __init__(self):
        self.ships = {}
        self.active = None

    def get_ships(self, user_id):
        return list(self.ships.keys())

    def save_ship(self, user_id, ship_name, ship_data):
        self.ships[ship_name] = ship_data
        self.active = ship_data

    def get_active_ship(self, user_id):
        return self.active


def test_cwn_ship_json_is_detected_and_parsed():
    assert looks_like_ship_payload(CWN_SHIP) is True
    assert looks_like_ship_payload({"name": "Rey Chen", "classId": "warrior", "attributes": {}}) is False

    ship, error = ShipsCog(SimpleNamespace()).parse_swn_ship_json(CWN_SHIP)
    assert error is None
    assert ship["name"] == "Lucky Strike"
    assert ship["hull_id"] == "free-merchant"
    assert ship["hp"] == 20
    assert ship["ac"] == 14
    assert any(item["name"] == "Spike Drive 1" for item in ship["fittings"])
    assert "Multifocal Laser" in ship["weapons"]
    assert "Hardened Polyceramic Overlay" in ship["defenses"]


def test_database_save_ship_round_trip(tmp_path):
    db = DatabaseService(db_path=str(tmp_path / "ships.db"))
    parsed, error = ShipsCog(SimpleNamespace()).parse_swn_ship_json(CWN_SHIP)
    assert error is None
    db.save_ship(99, "Lucky Strike", parsed)
    stored = db.get_active_ship(99)
    assert stored["name"] == "Lucky Strike"
    assert stored["max_hp"] == 20
    assert db.get_ships(99) == ["Lucky Strike"]


def test_dropped_ship_json_syncs_to_the_discord_bot():
    from bot import WithoutNumberBot

    sent = []

    async def send(content=None, **_kwargs):
        sent.append(content)

    db = MemoryDatabase()
    bot = object.__new__(WithoutNumberBot)
    sheet_cog = CharacterSheetCog(SimpleNamespace(db=db))
    ships_cog = ShipsCog(SimpleNamespace(db=db))
    bot.get_cog = lambda name: sheet_cog if name == "CharacterSheetCog" else ships_cog
    message = SimpleNamespace(
        content="",
        author=SimpleNamespace(id=12),
        channel=SimpleNamespace(id=34, category_id=None, send=send),
        guild=SimpleNamespace(id=56),
        attachments=[
            SimpleNamespace(
                filename="lucky-strike.json",
                read=lambda: asyncio.sleep(0, result=None) or None,
            )
        ],
    )

    async def read_attachment(_attachment):
        import json
        return json.dumps(CWN_SHIP), None

    sheet_cog._read_attachment_text = read_attachment
    message.attachments[0].filename = "lucky-strike.json"

    handled = asyncio.run(bot._handle_character_sheet_drop(message))

    assert handled is True
    assert db.active["name"] == "Lucky Strike"
    assert any(item and "Lucky Strike" in str(item) for item in sent)
    assert any(item and "ship" in str(item).lower() for item in sent)


def test_update_without_source_url_tells_player_to_redrop():
    sent = []

    async def send(content=None, **_kwargs):
        sent.append(content)

    async def get_active(_target, allow_none=False):
        return {"name": "Rey Chen"}

    cog = CharacterSheetCog(SimpleNamespace())
    cog.get_active_character_data = get_active
    target = SimpleNamespace(send=send, author=SimpleNamespace(id=1))
    asyncio.run(cog._refresh_active_character(target))
    assert any("drop" in str(item).lower() for item in sent)
    assert any("Rey Chen" in str(item) for item in sent)
