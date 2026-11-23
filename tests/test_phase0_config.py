from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]


def test_gnpy_config_pins_a_version_and_avoids_guessed_thresholds() -> None:
    config = yaml.safe_load((ROOT / "configs" / "gnpy.yaml").read_text())

    assert config["gnpy"]["version"] == "3.0.1"
    assert config["gnpy"]["equipment_library"]["feasibility_thresholds"].startswith(
        "never hard-code"
    )
