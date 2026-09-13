from glorydial.model.device import Device, DeviceDatabase


def test_fresh_db_is_seeded_with_builtin_devices(tmp_path):
    db = DeviceDatabase(tmp_path / "devices.sqlite")
    devices = db.list_devices()
    names = {d.name for d in devices}
    assert "K72" in names
    k72 = db.get("K72")
    assert (k72.width, k72.height) == (410, 502)


def test_add_update_delete_cycle(tmp_path):
    db = DeviceDatabase(tmp_path / "devices.sqlite")
    db.add(Device(name="TestWatch", width=200, height=200))
    assert db.get("TestWatch") is not None

    db.update("TestWatch", Device(name="TestWatch2", width=210, height=210))
    assert db.get("TestWatch") is None
    assert db.get("TestWatch2").width == 210

    db.delete("TestWatch2")
    assert db.get("TestWatch2") is None


def test_duplicate_name_rejected(tmp_path):
    db = DeviceDatabase(tmp_path / "devices.sqlite")
    try:
        db.add(Device(name="K72", width=1, height=1))
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_version_list_parsing():
    d = Device(name="x", width=1, height=1, supported_versions="3")
    assert d.version_list == [3]
    d2 = Device(name="y", width=1, height=1, supported_versions="1,2,3")
    assert d2.version_list == [1, 2, 3]
