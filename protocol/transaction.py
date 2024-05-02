import json
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Union

import requests

from protocol import FormattedDateTime


class TransactionType(Enum):
    BUY = -1
    SELL = 1


def get_btcusdt_futures_price():
    url = "https://fapi.binance.com/fapi/v2/ticker/price"
    params = {"symbol": "BTCUSDT"}
    response = requests.get(url, params=params)
    data = response.json()
    return float(data["price"])


@dataclass
class Transaction:
    mode: TransactionType
    price: float
    amount: float
    time: FormattedDateTime
    fee_ratio: Optional[float] = 2e-4

    def to_dict(self):
        return {
            "mode": self.mode.name,
            "price": self.price,
            "amount": self.amount,
        }

    def __repr__(self):
        return f"Transaction(<{self.mode.name}> {self.amount:.4f} @ {self.price:.4f})"

    def __str__(self):
        return self.__repr__()

    @property
    def transaction_fee(self):
        return -abs(self.price * self.amount * self.fee_ratio)

    @property
    def value(self):
        return self.price * self.amount * self.mode.value * (1 + self.fee_ratio)

    @property
    def net_amount(self):
        return -self.amount * self.mode.value

    @classmethod
    def from_dict(cls, d):
        return cls(TransactionType[d["mode"]], d["price"], d["amount"], d["time"])

    def __post_init__(self):
        if not isinstance(self.time, FormattedDateTime):
            self.time = FormattedDateTime(self.time)
        if isinstance(self.mode, str):
            self.mode = TransactionType[self.mode]


@dataclass
class TransactionFlow:
    amount: float = 0
    average_price: float = 0
    realized_profit: Optional[float] = 0
    rounding: Optional[int] = 10

    def __repr__(self):
        return f"TransactionFlow(amount={self.amount:.3f}, average_price={self.average_price:.1f}, realized_profit={self.realized_profit:.4f})"

    def unrealized_profit(self, current_price=None):
        if current_price is None:
            current_price = get_btcusdt_futures_price()

        if self.average_price == 0:
            return 0
        return (current_price - self.average_price) * self.amount

    def net_profit(self, current_price=None, funding_rate=0):
        if current_price is None:
            current_price = get_btcusdt_futures_price()
        return (
            self.unrealized_profit(current_price) + self.realized_profit + funding_rate
        )

    def __add__(self, other: Union["TransactionFlow", Transaction]):
        if isinstance(other, Transaction):
            other = TransactionFlow.from_transaction(other)

        amount = self.amount + other.amount
        realized_profit = other.realized_profit

        if self.amount * other.amount < 0:
            realized_profit += (other.average_price - self.average_price) * -(
                other.amount
            )
            average_price = 0 if amount == 0 else self.average_price
        else:
            average_price = (
                self.average_price * self.amount + other.average_price * other.amount
            ) / amount

        return TransactionFlow(
            round(amount, self.rounding),
            round(average_price, self.rounding),
            round(self.realized_profit + realized_profit, self.rounding),
        )

    @classmethod
    def from_transaction(cls, transaction: Transaction):
        return cls(
            transaction.net_amount, transaction.price, transaction.transaction_fee
        )

    @classmethod
    def from_transactions(cls, transactions: list[Transaction]):
        transaction_flow = cls(0, 0, 0)
        transactions = sorted(transactions, key=lambda t: t.time)
        for transaction in transactions:
            transaction_flow += transaction
        return transaction_flow

    def to_dict(self):
        return {
            "amount": self.amount,
            "average_price": self.average_price,
            "realized_profit": self.realized_profit,
        }

    def dump(self, current_price):
        return (
            {
                **self.to_dict(),
                "unrealized_profit": self.unrealized_profit(current_price),
                "net_profit": self.net_profit(current_price),
            },
        )


def read_transactions(filename):
    with open(filename) as f:
        transactions = [Transaction.from_dict(d) for d in json.load(f)]
    transactions = sorted(transactions, key=lambda t: t.time)
    return transactions


if __name__ == "__main__":
    transactions = read_transactions("transactions/transactions.json")
    transaction_flow = TransactionFlow()

    # with open("tmp.json", "w") as f:
    #     json.dump([t.to_dict() for t in transactions], f, indent=4)
    print(transaction_flow.net_profit())
