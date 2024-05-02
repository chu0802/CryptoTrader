import os
from pathlib import Path

DATA_ROOT = Path(os.environ.get("DATA_ROOT", None))
RESULTS_ROOT = Path(os.environ.get("RESULTS_ROOT", None))
STRATEGY_ROOT = Path(os.environ.get("STRATEGY_ROOT", None))
PYTHON_PATH = os.environ.get("PYTHON_PATH", None)
STATUS_ROOT = Path(os.environ.get("STATUS_ROOT", None))


class BasePrefixPath(Path):
    def __new__(cls, prefix: Path, path: str = "", *args, **kwargs):
        path = prefix / path
        return super().__new__(Path, path.as_posix(), *args, **kwargs)


class DataPath(BasePrefixPath):
    def __new__(cls, path: str = "", *args, **kwargs):
        return BasePrefixPath(DATA_ROOT, path, *args, **kwargs)


class ResultsPath(BasePrefixPath):
    def __new__(cls, path: str = "", *args, **kwargs):
        return BasePrefixPath(RESULTS_ROOT, path, *args, **kwargs)


class StrategyPath(BasePrefixPath):
    def __new__(cls, path: str = "", *args, **kwargs):
        return BasePrefixPath(STRATEGY_ROOT, path, *args, **kwargs)


class StatusPath(BasePrefixPath):
    def __new__(cls, path: str = "", *args, **kwargs):
        return BasePrefixPath(STATUS_ROOT, path, *args, **kwargs)


if __name__ == "__main__":
    pass
