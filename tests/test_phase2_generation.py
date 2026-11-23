from fiber_qot_platform.simulation.phase2 import load_mode_config, mean_db


def test_gnpymodes_are_loaded_from_configuration() -> None:
    modes = load_mode_config()
    assert "mode 1" in modes
    assert modes["mode 1"]["OSNR"] == 12.0


def test_mean_db_handles_scalar_and_array_values() -> None:
    assert mean_db(20.0) == 20.0
