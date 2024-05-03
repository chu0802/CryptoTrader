from typing import List

from protocol.datetime import FormattedDateTime
from protocol.transaction import Transaction
from strategy.base import BaseStrategy


class GridTradingStrategy(BaseStrategy):
    _name = "grid_trading"

    def __init__(
        self,
        symbol: str,
        budget: float,
        leverage: int = 1,
        dump_path: str = "status.pkl",
        highest: float = 75000,
        lowest: float = 60000,
        num_interval: int = 20,
        amount: float = 0.003,
    ):
        super().__init__(symbol, budget, leverage, dump_path)
        self.highest = highest
        self.lowest = lowest
        self.interval = (highest - lowest) / num_interval
        self.buy_price = None
        self.sell_price = None
        self.amount = amount

    def get_closest_lower_bound(self, price: float):
        return self.lowest + (price - self.lowest) // self.interval * self.interval

    def get_closest_upper_bound(self, price: float):
        return (
            self.lowest
            + (price - self.lowest) // self.interval * self.interval
            + self.interval
        )

    def buy_process(self, time, kline):
        total_transactions = []
        while kline.low <= self.buy_price:
            total_transactions.append(
                Transaction(
                    mode="BUY", amount=self.amount, price=self.buy_price, time=time
                )
            )
            self.buy_price = self.get_closest_lower_bound(self.buy_price * 0.999)
        self.sell_price = self.get_closest_upper_bound(
            (self.buy_price + 2 * self.interval) * 0.999
        )
        return total_transactions

    def sell_process(self, time, kline):
        total_transactions = []
        while kline.high >= self.sell_price:
            total_transactions.append(
                Transaction(
                    mode="SELL",
                    amount=self.amount,
                    price=self.sell_price,
                    time=time,
                )
            )
            self.sell_price = self.get_closest_upper_bound(self.sell_price * 1.001)
        self.buy_price = self.get_closest_lower_bound(
            (self.sell_price - 2 * self.interval) * 1.001
        )
        return total_transactions

    def has_intersect(self, a1, b1, a2, b2):
        if max(a1, a2) > min(b1, b2):
            return False
        return True

    def _get_action(self, time: FormattedDateTime, kline) -> List[Transaction]:
        # otherwise we are not doing any transactions.
        if self.has_intersect(kline.low, kline.high, self.lowest, self.highest):
            total_transactions = []

            # initialization
            if self.buy_price is None and self.sell_price is None:
                self.buy_price = self.get_closest_lower_bound(kline.close)
                self.sell_price = (
                    self.get_closest_upper_bound(kline.close) + self.interval
                )

            # if the close price is higher than the open price,
            # we simulate the process by first buying, then selling.
            if kline.close >= kline.open:
                if kline.low <= self.buy_price:
                    total_transactions += self.buy_process(time, kline)

                if kline.high >= self.sell_price:
                    total_transactions += self.sell_process(time, kline)
            # otherwise, we simulate the process by first selling, then buying.
            else:
                if kline.high >= self.sell_price:
                    total_transactions += self.sell_process(time, kline)
                if kline.low <= self.buy_price:
                    total_transactions += self.buy_process(time, kline)

            return total_transactions
