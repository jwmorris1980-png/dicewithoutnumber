from unittest.mock import MagicMock

from services.dice_service import DiceService
from services.web_service import WebService


def test_voice_roll_response_identifies_roller_without_a_mention():
    service = WebService(MagicMock(), port=0)

    response = service._build_voice_roll_response(
        "roll",
        "1d20",
        DiceService(),
        "Devin",
    )

    assert response.startswith("**Devin rolled:**")
    assert "<@" not in response


def test_repeated_voice_roll_response_identifies_roller():
    service = WebService(MagicMock(), port=0)

    response = service._build_voice_roll_response(
        "multiroll",
        "2 1d20",
        DiceService(),
        "Voice Player",
    )

    assert response.startswith("**Voice Player rolled:**")
    assert "Roll 1" in response
    assert "Roll 2" in response
