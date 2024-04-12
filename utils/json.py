import json
from pathlib import Path

from utils.datetime import DatetimeJsonEncoder


def load(path: Path):
    if not isinstance(path, Path):
        path = Path(path)

    with path.open("r") as f:
        data = json.load(f)
    return data


def dump(obj, path: Path):
    if not isinstance(path, Path):
        path = Path(path)
    with path.open("w") as f:
        json.dump(obj, f, indent=4, cls=DatetimeJsonEncoder)


if __name__ == "__main__":
    # dump({FormattedDateTime("2024-04-10 14:00:00"): "test"}, "test.json")
    d = load("data/btcusdt/prices.json")
