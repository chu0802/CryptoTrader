import json
import pickle
from pathlib import Path

from protocol.datetime import DatetimeJsonEncoder


def load(path: Path, is_pickle=False):
    if not isinstance(path, Path):
        path = Path(path)

    with path.open("r" if not is_pickle else "rb") as f:
        if is_pickle:
            data = pickle.load(f)
        else:
            data = json.load(f)
    return data


def dump(obj, path: Path, is_pickle=False, mode="w"):
    if not isinstance(path, Path):
        path = Path(path)
    path.parent.mkdir(exist_ok=True, parents=True)
    with path.open(mode if not is_pickle else mode + "b") as f:
        if is_pickle:
            pickle.dump(obj, f)
        else:
            json.dump(obj, f, indent=4, cls=DatetimeJsonEncoder)


if __name__ == "__main__":
    # dump({FormattedDateTime("2024-04-10 14:00:00"): "test"}, "test.json")
    d = load("data/btcusdt/prices.json")
