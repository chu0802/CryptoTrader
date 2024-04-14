from abc import abstractmethod
from typing import List

from protocol import FormattedDateTime, Transaction, TransactionFlow


class BaseStrategy:
    _name = "base"

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


if __name__ == "__main__":
    s = GridTradingStrategy(200)
