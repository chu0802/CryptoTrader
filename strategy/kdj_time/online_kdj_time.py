from dataclasses import dataclass
from typing import List

import requests

from protocol.datetime import FormattedDateTime
from protocol.kline import KLine
from protocol.transaction import Transaction
from strategy.base import BaseStrategy


@dataclass
class KDJ:
    k: float
    d: float
    j: float

    @classmethod
    def from_dict(cls, data):
        return cls(**{k.lower(): v for k, v in data.items() if k in ["K", "D", "J"]})


class OnlineKDJTimeStrategy(BaseStrategy):
    _name = "online_kdj_time"

    def __init__(
        self,
        symbol: str,
        budget: float,
        leverage: int = 1,
        amount=8,
        low=20,
        high=80,
        min_ratio=0.2,
        kdj_intervals=None,
        max_continual_count=5,
        dump_path: str = "status.pkl",
        kdj_endpoint="http://127.0.0.1:8000/kdj",
    ):
        super().__init__(symbol, budget, leverage, dump_path)
        self.amount = amount
        self.low = low
        self.high = high
        self.min_ratio = min_ratio
        self.prev_action = None
        self.prev_buy_price = 0
        self.prev_sell_price = 0
        self.max_continual_count = max_continual_count
        self.purchase_weight = 0
        self.kdj_intervals = [1] if kdj_intervals is None else kdj_intervals
        self.kdj_endpoint = kdj_endpoint

    def buy_kdj_criteria(self, kdjs: List[KDJ]):
        return all(
            kdj.k < self.low and kdj.d < self.low and kdj.k >= kdj.d for kdj in kdjs
        )

    def sell_kdj_criteria(self, kdjs: List[KDJ]):
        return all(
            kdj.k > self.high and kdj.d > self.high and kdj.k <= kdj.d for kdj in kdjs
        )

    def get_diff_ratio(self, prev_price, current_price):
        return abs(prev_price - current_price) / prev_price

    def _get_action(self, time: FormattedDateTime, kline: KLine) -> List[Transaction]:
        kdjs = [
            KDJ(
                *requests.get(
                    self.kdj_endpoint,
                    params={
                        "symbol": self.symbol,
                        "interval": f"{interval}m",
                        "end_time": time.ms_timestamp,
                    },
                ).json()
            )
            for interval in self.kdj_intervals
        ]
        transactions = []

        if self.purchase_weight >= self.max_continual_count:
            if kline.close > self.prev_buy_price * (1 + self.min_ratio):
                self.purchase_weight = 0
                self.prev_action = "SELL"
                self.prev_buy_price = 0
                self.prev_sell_price = kline.close

                return [
                    Transaction(
                        "SELL",
                        kline.close,
                        abs(self.total_amount // self.leverage),
                        time,
                    )
                ]
        if self.purchase_weight <= -self.max_continual_count:
            if kline.close < self.prev_sell_price * (1 - self.min_ratio):
                self.purchase_weight = 0
                self.prev_action = "BUY"
                self.prev_buy_price = kline.close
                self.prev_sell_price = 0

                return [
                    Transaction(
                        "BUY",
                        kline.close,
                        abs(self.total_amount // self.leverage),
                        time,
                    )
                ]

        if self.buy_kdj_criteria(kdjs):
            if (
                self.prev_action == "BUY"
                and self.get_diff_ratio(self.prev_buy_price, kline.close)
                < self.min_ratio
            ) or self.purchase_weight >= self.max_continual_count:
                return []
            transactions.append(Transaction("BUY", kline.close, self.amount, time))
            self.prev_action = "BUY"
            self.prev_buy_price = kline.close
            self.purchase_weight += 1
        elif self.sell_kdj_criteria(kdjs):
            if (
                self.prev_action == "SELL"
                and self.get_diff_ratio(self.prev_sell_price, kline.close)
                < self.min_ratio
            ) or self.purchase_weight <= -self.max_continual_count:
                return []
            transactions.append(Transaction("SELL", kline.close, self.amount, time))
            self.prev_action = "SELL"
            self.prev_sell_price = kline.close
            self.purchase_weight -= 1
        return transactions
