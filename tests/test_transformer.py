from ingestion.transformer import normalize_current_weather
def test_normalize_basic():
    sample = {"name":"X","dt": 1600000000,"main":{"temp":10},"wind":{"speed":1},"weather":[{"description":"clear"}]}
    out = normalize_current_weather(sample)
    assert out["city"] == "X"
    assert "timestamp" in out
    assert out["temperature"] == 10