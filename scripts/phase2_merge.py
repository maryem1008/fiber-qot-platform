import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.phase2_generate import (  # noqa: E402
    _run_directory,
    merge_run_directory,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    args = parser.parse_args()

    run_directory = _run_directory(ROOT / "data" / "generated", args.run_id)
    paths_path, spans_path = merge_run_directory(run_directory)
    print(json.dumps({"paths": str(paths_path), "spans": str(spans_path)}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
