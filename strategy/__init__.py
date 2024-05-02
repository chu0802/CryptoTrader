import sys

from strategy.base import BaseStrategy
from strategy.dca import DCAStrategy, GoingShortStrategy
from strategy.grid_trading import GridTradingStrategy
from strategy.kdj_grid_trading import KDJGridTradingStrategy
from strategy.optimal_strategy import OptimalStrategy
from utils.config import StatusPath
from utils.json import load

STRATEGY_MAP = {
    v._name: v
    for v in sys.modules[__name__].__dict__.values()
    if isinstance(v, type) and issubclass(v, BaseStrategy) and v != BaseStrategy
}


def get_strategy(strategy_config):
    strategy_class = STRATEGY_MAP[strategy_config["name"]]
    new_strategy = strategy_class(**strategy_config["config"])

    if new_strategy.dump_path and new_strategy.dump_path.exists():
        return load(new_strategy.dump_path, is_pickle=True)

    return new_strategy
