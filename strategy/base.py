from abc import abstractmethod
from typing import List

from protocol.datetime import FormattedDateTime
from protocol.kline import KLine
from protocol.transaction import Transaction, TransactionFlow
from utils.config import StatusPath
from utils.json import dump


class BaseStrategy:
    _name = "base"

    def __init__(
        self,
        symbol: str,
        budget: float,
        leverage: int = 1,
        dump_path: str = "status.pkl",
    ):
        self.original_budget = budget
        self.leverage = leverage
        self._transaction_snapshots = []
        self.transaction_flow = TransactionFlow()

        self._symbol = symbol
        self._dump_path = (
            StatusPath() / "strategy" / self.name / symbol.lower() / dump_path
        )

    def is_empty(self):
        return len(self._transaction_snapshots) == 0

    @property
    def symbol(self):
        return self._symbol

    @property
    def name(self):
        return self._name

    @property
    def dump_path(self):
        return self._dump_path

    @property
    def transaction_snapshots(self):
        return self._transaction_snapshots

    @property
    def current_average_price(self):
        return self.transaction_flow.average_price

    @property
    def total_amount(self):
        return self.transaction_flow.amount

    def get_last_transaction_snapshot(self) -> Transaction:
        if len(self._transaction_snapshots) == 0:
            return None
        return self._transaction_snapshots[-1]

    def get_last_transaction(self):
        last_snapshot = self.get_last_transaction_snapshot()
        if last_snapshot:
            return last_snapshot["transaction"]

    def get_transaction_snapshot(self, time, current_price, transaction=None):
        snapshot = {
            "formattedTime": time,
            "timestamp": time.timestamp,
            "transaction_flow": self.transaction_flow.dump(current_price),
        }
        if transaction:
            snapshot["transaction"] = transaction.to_dict()
        else:
            snapshot["current price"] = current_price
        return snapshot

    def update_transaction(self, time, transaction, current_price):
        self.transaction_flow += transaction
        self._transaction_snapshots.append(
            self.get_transaction_snapshot(time, current_price, transaction)
        )

    def check_budget(
        self, current_price: float, transaction_flow: TransactionFlow = None
    ):
        if transaction_flow is None:
            transaction_flow = self.transaction_flow
        total_budget = self.original_budget + transaction_flow.net_profit(current_price)
        return total_budget > 0

    def dump(self):
        dump(self, self.dump_path, is_pickle=True)

    @abstractmethod
    def _get_action(
        self, time: FormattedDateTime, kline: KLine, *args, **kwargs
    ) -> List[Transaction]:
        raise NotImplementedError

    @abstractmethod
    def get_action(self, time: FormattedDateTime, kline):
        transactions = self._get_action(time, kline)

        if transactions is not None and len(transactions) > 0:
            for transaction in transactions:
                transaction.amount *= self.leverage

                if not self.check_budget(
                    kline.close, self.transaction_flow + transaction
                ):
                    print("Budget is not enough")
                    break
                else:
                    self.update_transaction(time, transaction, kline.close)
