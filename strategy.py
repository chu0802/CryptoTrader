from abc import abstractmethod
from typing import List

from transaction import Transaction, TransactionFlow
from utils.protocol import FormattedDateTime


class BaseStrategy:
    _name = "Base"

    def __init__(self, budget: float, leverage: int = 1):
        self.original_budget = budget
        self.leverage = leverage
        self._transaction_snapshots = []
        self.transaction_flow = TransactionFlow()

    @property
    def name(self):
        return self._name

    @property
    def transaction_snapshots(self):
        return self._transaction_snapshots

    def get_last_transaction_snapshot(self):
        if len(self._transaction_snapshots) == 0:
            return None
        return self._transaction_snapshots[-1]

    def get_last_transaction(self):
        last_snapshot = self.get_last_transaction_snapshot()
        if last_snapshot:
            return last_snapshot["transaction"]

    def get_transaction_snapshot(self, time, current_price, transaction=None):
        snapshot = {
            "time": time,
            "transaction_flow": self.transaction_flow.dump(current_price),
        }
        if transaction:
            snapshot["transaction"] = transaction.to_dict()
        else:
            snapshot["current price"] = current_price
        return snapshot

    def check_budget(
        self, current_price: float, transaction_flow: TransactionFlow = None
    ):
        if transaction_flow is None:
            transaction_flow = self.transaction_flow
        total_budget = self.original_budget + transaction_flow.net_profit(current_price)
        return total_budget > 0

    @abstractmethod
    def _get_action(self, time: FormattedDateTime, kline) -> List[Transaction]:
        raise NotImplementedError

    @abstractmethod
    def get_action(self, time: FormattedDateTime, kline):
        transactions = self._get_action(time, kline)

        if transactions is not None:
            for transaction in transactions:
                transaction.amount *= self.leverage

                if not self.check_budget(
                    kline.close, self.transaction_flow + transaction
                ):
                    print("Budget is not enough")
                    break
                else:
                    self.transaction_flow += transaction
                    current_price = kline.close
                    self._transaction_snapshots.append(
                        self.get_transaction_snapshot(time, current_price, transaction)
                    )


class GridTradingStrategy(BaseStrategy):
    _name = "grid_trading"

    def __init__(
        self,
        budget: float,
        leverage: int = 1,
        highest: float = 75000,
        lowest: float = 60000,
        num_interval: int = 20,
        amount: float = 0.003,
    ):
        super().__init__(budget, leverage)
        self.highest = highest
        self.lowest = lowest
        self.interval = (highest - lowest) // num_interval
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
            self.buy_price = self.get_closest_lower_bound(self.buy_price - 100)
        self.sell_price = self.get_closest_upper_bound(
            self.buy_price + 2 * self.interval - 100
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
            self.sell_price = self.get_closest_upper_bound(self.sell_price + 100)
        self.buy_price = self.get_closest_lower_bound(
            self.sell_price - 2 * self.interval + 100
        )
        return total_transactions

    def _get_action(self, time: FormattedDateTime, kline) -> List[Transaction]:
        if time == FormattedDateTime("2024-04-14 04:07:00"):
            pass

        # otherwise we are not doing any transactions.
        if kline.low > self.lowest or kline.high < self.highest:
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


class DCAStrategy(BaseStrategy):
    _name = "dca"

    def __init__(
        self,
        budget: float,
        leverage: int = 1,
        time_interval: float = 86400,
        amount_in_usd: float = 100,
    ):
        super().__init__(budget, leverage)
        self.time_interval = time_interval
        self.amount_in_usd = amount_in_usd

    def _get_action(self, time: FormattedDateTime, kline):
        last_transaction_snapshot = self.get_last_transaction_snapshot()

        amount = self.amount_in_usd / kline.close

        if last_transaction_snapshot is None:
            return [
                Transaction(mode="BUY", amount=amount, price=kline.close, time=time)
            ]
        elif time - last_transaction_snapshot["time"] >= self.time_interval:
            return [
                Transaction(mode="BUY", amount=amount, price=kline.close, time=time)
            ]


class GoingShortStrategy(BaseStrategy):
    _name = "going_short"

    def __init__(
        self,
        budget: float,
        leverage: int = 1,
        time_interval: float = 86400,
        amount_in_usd: float = 100,
    ):
        super().__init__(budget, leverage)
        self.time_interval = time_interval
        self.amount_in_usd = amount_in_usd

    def _get_action(self, time: FormattedDateTime, kline):
        last_transaction_snapshot = self.get_last_transaction_snapshot()

        amount = self.amount_in_usd / kline.close

        if last_transaction_snapshot is None:
            return [
                Transaction(mode="SELL", amount=amount, price=kline.close, time=time)
            ]

        elif time - last_transaction_snapshot["time"] >= self.time_interval:
            return [
                Transaction(mode="SELL", amount=amount, price=kline.close, time=time)
            ]


if __name__ == "__main__":
    s = GridTradingStrategy(200)
