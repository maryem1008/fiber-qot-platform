from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_source_has_no_venv_or_windows_site_packages_paths() -> None:
    forbidden_fragments = (".venv", "Lib/site-packages")
    source_files = list((ROOT / "src").rglob("*.py"))
    assert source_files
    for source_file in source_files:
        contents = source_file.read_text(encoding="utf-8")
        for forbidden in forbidden_fragments:
            assert forbidden not in contents, f"{source_file} contains {forbidden!r}"
