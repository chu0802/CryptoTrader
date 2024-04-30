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
        min_interval: int = 5,
    ):
        super().__init__(budget, leverage, highest, lowest, num_interval, amount)
        self.cold_start = cold_start
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound
        self.epsilon = epsilon
        self.counter = 0
        self.sell_interval_counter = min_interval
        self.buy_interval_counter = min_interval
        self.min_interval = min_interval

        self.kdj_data = kdj_calculator(symbol)

    def has_intersect(self, a1, b1, a2, b2):
        if max(a1, a2) > min(b1, b2):
            return False
        return True

    def price_initialization(self, price, base="buy"):
        if base == "buy":
            self.buy_price = self.get_closest_lower_bound(price)
            self.sell_price = self.buy_price + self.interval
        else:
            self.sell_price = self.get_closest_upper_bound(price)
            self.buy_price = self.sell_price - self.interval

    def buy_criteria(self, kline: KLine, prev_kdj: KDJ, pprev_kdj: KDJ) -> bool:
        kdj_criteria = [
            prev_kdj.k < self.lower_bound,
            prev_kdj.d < self.lower_bound,
            pprev_kdj.k < self.lower_bound,
            pprev_kdj.d < self.lower_bound,
            # abs(prev_kdj.k - prev_kdj.d) <= self.epsilon,
            prev_kdj.k > pprev_kdj.k,
            self.buy_interval_counter >= self.min_interval,
        ]

        if all(kdj_criteria) and self.buy_price is None:
            self.price_initialization(kline.open, base="buy")

        return all(kdj_criteria) and kline.low <= self.buy_price

    def sell_criteria(self, kline: KLine, prev_kdj: KDJ, pprev_kdj: KDJ) -> bool:
        kdj_criteria = [
            prev_kdj.k > self.upper_bound,
            prev_kdj.d > self.upper_bound,
            pprev_kdj.k > self.upper_bound,
            pprev_kdj.d > self.upper_bound,
            # abs(prev_kdj.k - prev_kdj.d) <= self.epsilon,
            prev_kdj.k < pprev_kdj.k,
            self.sell_interval_counter >= self.min_interval,
        ]

        if all(kdj_criteria) and self.sell_price is None:
            self.price_initialization(kline.open, base="sell")
        return all(kdj_criteria) and kline.high >= self.sell_price

    def buy_process(self, time, kline):
        total_transactions = []
        if kline.open <= self.buy_price:
            total_transactions.append(
                Transaction(mode="BUY", amount=self.amount, price=kline.open, time=time)
            )
        self.buy_price = self.get_closest_lower_bound(kline.open * 0.999)
        self.sell_price = self.buy_price + self.interval
        return total_transactions

    def sell_process(self, time, kline):
        total_transactions = []
        if kline.open >= self.sell_price:
            total_transactions.append(
                Transaction(
                    mode="SELL",
                    amount=self.amount,
                    price=kline.open,
                    time=time,
                )
            )
        self.sell_price = self.get_closest_upper_bound(kline.open * 1.001)
        self.buy_price = self.sell_price - self.interval
        return total_transactions

    def _get_action(self, time: FormattedDateTime, kline: KLine) -> List[Transaction]:
        total_transactions = []
        if self.counter >= self.cold_start and self.has_intersect(
            kline.low, kline.high, self.lowest, self.highest
        ):

            prev_kdj = KDJ.from_dict(self.kdj_data[time - 60 * 1])
            pprev_kdj = KDJ.from_dict(self.kdj_data[time - 60 * 2])

            # if the close price is higher than the open price,
            # we simulate the process by first buying, then selling.
            if kline.close >= kline.open:
                if self.buy_criteria(kline, prev_kdj, pprev_kdj):
                    total_transactions += self.buy_process(time, kline)
                    self.buy_interval_counter = 0

                if self.sell_criteria(kline, prev_kdj, pprev_kdj):
                    total_transactions += self.sell_process(time, kline)
                    self.sell_interval_counter = 0
            # otherwise, we simulate the process by first selling, then buying.
            else:
                if self.sell_criteria(kline, prev_kdj, pprev_kdj):
                    total_transactions += self.sell_process(time, kline)
                    self.sell_interval_counter = 0
                if self.buy_criteria(kline, prev_kdj, pprev_kdj):
                    total_transactions += self.buy_process(time, kline)
                    self.buy_interval_counter = 0

        self.counter += 1
        self.buy_interval_counter += 1
        self.sell_interval_counter += 1
        return total_transactions
