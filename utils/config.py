import os
from pathlib import Path

DATA_ROOT = Path(os.environ.get("DATA_ROOT", None))
RESULTS_ROOT = Path(os.environ.get("RESULTS_ROOT", None))
STRATEGY_ROOT = Path(os.environ.get("STRATEGY_ROOT", None))
PYTHON_PATH = os.environ.get("PYTHON_PATH", None)


class BasePrefixPath(Path):
    def __new__(cls, path: str, prefix: Path, *args, **kwargs):
        path = prefix / path
        return super().__new__(Path, path.as_posix(), *args, **kwargs)


class DataPath(BasePrefixPath):
    def __new__(cls, path: str, *args, **kwargs):
        return BasePrefixPath(path, DATA_ROOT, *args, **kwargs)


class ResultsPath(BasePrefixPath):
    def __new__(cls, path: str, *args, **kwargs):
        return BasePrefixPath(path, RESULTS_ROOT, *args, **kwargs)


class StrategyPath(BasePrefixPath):
    def __new__(cls, path: str, *args, **kwargs):
        return BasePrefixPath(path, STRATEGY_ROOT, *args, **kwargs)


if __name__ == "__main__":
    pass
