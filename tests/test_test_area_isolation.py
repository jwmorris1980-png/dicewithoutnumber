from services.database import DatabaseService


def test_database_uses_test_area_path(monkeypatch, tmp_path):
    test_db = tmp_path / "isolated.db"
    monkeypatch.setenv("DICEWITHOUTNUMBER_TEST_DB", str(test_db))

    service = DatabaseService()

    assert service.db_path == str(test_db)
    assert test_db.exists()
