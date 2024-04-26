from dataclasses import dataclass
from typing import List

from protocol import FormattedDateTime, KLine, Transaction
from strategy.base import BaseStrategy
from strategy.grid_trading import GridTradingStrategy
from strategy.kdj_grid_trading.kdj_counter import KDJCalculator
from utils.config import DataPath
from utils.json import dump, load


@dataclass
class KDJ:
    k: float
    d: float
    j: float

    @classmethod
    def from_dict(cls, data):
        return cls(**{k.lower(): v for k, v in data.items() if k in ["K", "D", "J"]})


def kdj_calculator(symbol: str = "btcusdt"):
    historical_prices = {
        FormattedDateTime(time): KLine(**data)
        for time, data in load(DataPath(f"{symbol}/prices.json")).items()
    }

    kdj_calculator = KDJCalculator(historical_prices)
    k_values, d_values, j_values = kdj_calculator.calculate_kdj()
    kdj_data = kdj_calculator.generate_kdj_data(k_values, d_values, j_values)

    dump(kdj_data, DataPath(f"{symbol}/kdj_data.json"))
    return kdj_data


class KDJGridTradingStrategy(GridTradingStrategy):
    _name = "kdj_grid_trading"

    def __init__(
        self,
        symbol: str,
        budget: float,
        leverage: int = 1,
        highest: float = 75000,
        lowest: float = 60000,
        amount: float = 0.003,
        cold_start: int = 10,
        lower_bound: float = 20,
        upper_bound: float = 80,
        epsilon: float = 1,
        num_interval: int = 20,
    ):
        super().__init__(budget, leverage, highest, lowest, num_interval, amount)
        self.cold_start = cold_start
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound
        self.epsilon = epsilon
        self.counter = 0

        self.kdj_data = kdj_calculator(symbol)

    def has_intersect(self, a1, b1, a2, b2):
        if max(a1, a2) > min(b1, b2):
            return False
        return True

    def buy_criteria(self, prev_kdj: KDJ) -> bool:
        base_criteria = [
            prev_kdj.k < self.lower_bound,
            prev_kdj.d < self.lower_bound,
        ]
        cross_criteria = [abs(prev_kdj.k - prev_kdj.d) <= self.epsilon]
        return all(base_criteria + cross_criteria)

    def sell_criteria(self, prev_kdj: KDJ) -> bool:
        base_criteria = [
            prev_kdj.k > self.upper_bound,
            prev_kdj.d > self.upper_bound,
        ]
        cross_criteria = [abs(prev_kdj.k - prev_kdj.d) <= self.epsilon]
        return all(base_criteria + cross_criteria)

    def _get_action(self, time: FormattedDateTime, kline: KLine) -> List[Transaction]:
        total_transactions = []
        if self.counter >= self.cold_start and self.has_intersect(
            kline.low, kline.high, self.lowest, self.highest
        ):

            prev_kdj = KDJ.from_dict(self.kdj_data[time - 60 * 1])
            # initialization
            if self.buy_price is None and self.sell_price is None:
                self.buy_price = self.get_closest_lower_bound(kline.close)
                self.sell_price = (
                    self.get_closest_upper_bound(kline.close) + self.interval
                )

            # if the close price is higher than the open price,
            # we simulate the process by first buying, then selling.
            if kline.close >= kline.open:
                if kline.low <= self.buy_price and self.buy_criteria(prev_kdj):
                    total_transactions += self.buy_process(time, kline)

                if kline.high >= self.sell_price and self.sell_criteria(prev_kdj):
                    total_transactions += self.sell_process(time, kline)
            # otherwise, we simulate the process by first selling, then buying.
            else:
                if kline.high >= self.sell_price and self.sell_criteria(prev_kdj):
                    total_transactions += self.sell_process(time, kline)
                if kline.low <= self.buy_price and self.buy_criteria(prev_kdj):
                    total_transactions += self.buy_process(time, kline)

            return total_transactions

        self.counter += 1
        return total_transactions
