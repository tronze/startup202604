from api.clients.substation import find_nearest_substation


def test_nearest_substation_haenam():
    result = find_nearest_substation(lat=34.57, lon=126.60)
    assert result is not None
    assert "name" in result
    assert "distance_km" in result
    assert "voltage_kv" in result
    assert result["distance_km"] < 50


def test_nearest_substation_returns_closest():
    result = find_nearest_substation(lat=34.574, lon=126.599)
    assert result["name"] == "해남변전소"
    assert result["distance_km"] < 1.0


def test_returns_none_for_empty_csv(tmp_path):
    # Verify graceful handling when CSV path doesn't exist
    from api.clients import substation as sub_module
    original = sub_module._SUBSTATIONS
    sub_module._SUBSTATIONS = []
    result = find_nearest_substation(lat=34.57, lon=126.60)
    sub_module._SUBSTATIONS = original
    assert result is None


def test_distance_is_float():
    result = find_nearest_substation(lat=34.57, lon=126.60)
    assert isinstance(result["distance_km"], float)
