import sys

from strategy.base import BaseStrategy
from strategy.dca import DCAStrategy, GoingShortStrategy
from strategy.grid_trading import GridTradingStrategy
from strategy.kdj_grid_trading import KDJGridTradingStrategy
from strategy.optimal_strategy import OptimalStrategy

STRATEGY_MAP = {
    v._name: v
    for v in sys.modules[__name__].__dict__.values()
    if isinstance(v, type) and issubclass(v, BaseStrategy) and v != BaseStrategy
}


def get_strategy(strategy_config):
    strategy_class = STRATEGY_MAP[strategy_config["name"]]
    return strategy_class(**strategy_config["config"])
