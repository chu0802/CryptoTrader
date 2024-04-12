from abc import abstractmethod

from transaction import Transaction, TransactionFlow
from utils.datetime import FormattedDateTime


class BaseStrategy:
    _name = "Base"

    def __init__(self, budget: float, leverage: int = 1):
        self.original_budget = budget
        self.leverage = leverage
        self.transaction_snapshot = []
        self.transaction_flow = TransactionFlow()

    @property
    def name(self):
        return self._name

    def get_last_transaction_snapshot(self):
        if len(self.transaction_snapshot) == 0:
            return None
        return self.transaction_snapshot[-1]

    def get_last_transaction(self):
        last_snapshot = self.get_last_transaction_snapshot()
        if last_snapshot:
            return last_snapshot["transaction"]

    def check_budget(
        self, current_price: float, transaction_flow: TransactionFlow = None
    ):
        if transaction_flow is None:
            transaction_flow = self.transaction_flow
        total_budget = self.original_budget + transaction_flow.net_profit(current_price)
        return total_budget > 0

    @abstractmethod
    def _get_action(self, time: FormattedDateTime, kline) -> Transaction:
        raise NotImplementedError

    @abstractmethod
    def get_action(self, time: FormattedDateTime, kline):
        transaction = self._get_action(time, kline)

        if transaction:
            transaction.amount *= self.leverage

            if not self.check_budget(kline.close, self.transaction_flow + transaction):
                print("Budget is not enough")
            else:
                self.transaction_flow += transaction
                current_price = kline.close
                self.transaction_snapshot.append(
                    {
                        "time": time,
                        "transaction": transaction.to_dict(),
                        "transaction_flow": self.transaction_flow.dump(current_price),
                    }
                )

    def get_result(self):
        return self.transaction_snapshot


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

    def _get_action(self, time: FormattedDateTime, kline):
        current_value = kline.close
        highest_value = kline.high
        lowest_value = kline.low

        if lowest_value > self.lowest and highest_value < self.highest:
            if self.buy_price is None and self.sell_price is None:
                self.buy_price = self.get_closest_lower_bound(current_value)
                self.sell_price = (
                    self.get_closest_upper_bound(current_value) + self.interval
                )

            if lowest_value <= self.buy_price:
                transaction = Transaction(
                    mode="BUY", amount=self.amount, price=self.buy_price, time=time
                )

                self.sell_price = self.get_closest_upper_bound(self.buy_price + 100)
                self.buy_price = self.get_closest_lower_bound(self.buy_price - 100)
                return transaction

            elif highest_value >= self.sell_price:
                transaction = Transaction(
                    mode="SELL",
                    amount=self.amount,
                    price=self.sell_price,
                    time=time,
                )

                self.buy_price = self.get_closest_lower_bound(self.sell_price - 100)
                self.sell_price = self.get_closest_upper_bound(self.sell_price + 100)
                return transaction


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
            return Transaction(mode="BUY", amount=amount, price=kline.close, time=time)
        elif time - last_transaction_snapshot["time"] >= self.time_interval:
            return Transaction(mode="BUY", amount=amount, price=kline.close, time=time)


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
            return Transaction(mode="SELL", amount=amount, price=kline.close, time=time)

        elif time - last_transaction_snapshot["time"] >= self.time_interval:
            return Transaction(mode="SELL", amount=amount, price=kline.close, time=time)


if __name__ == "__main__":
    s = GridTradingStrategy(200)
