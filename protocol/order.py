from dataclasses import dataclass
from typing import Any, Dict, Optional

from protocol import FormattedDateTime, Transaction


@dataclass
class Order:
    order_time: FormattedDateTime
    order_id: int
    status: str
    expected_transaction: Optional[Transaction] = None

    @classmethod
    def from_online(cls, data: Dict[str, Any], transaction: Transaction):
        return cls(
            order_time=FormattedDateTime(data["updateTime"]),
            order_id=data["orderId"],
            status=data["status"],
            expected_transaction=transaction,
        )

    @classmethod
    def from_local(cls, data: Dict[str, Any]):
        return cls(
            order_time=FormattedDateTime(data["order_time"]),
            order_id=data["order_id"],
            status=data["status"],
            expected_transaction=Transaction.from_dict(data),
        )

    def update_status(self, data: Dict[str, Any]):
        self.status = data["status"]

    def update_transaction(self, transaction: Transaction):
        self.expected_transaction = transaction

    def is_success(self):
        return self.status == "FILLED"

    def to_dict(self):
        dict = {
            "order_time": self.order_time,
            "order_id": self.order_id,
            "status": self.status,
        }
        if self.expected_transaction:
            dict.update(self.expected_transaction.to_dict())
        return dict


@dataclass
class Action:
    decision_time: FormattedDateTime
    order: Optional[Order] = None

    def to_dict(self):
        dict = {"decision_time": self.decision_time}
        if self.order:
            dict.update(self.order.to_dict())
        return dict

    @classmethod
    def from_local(cls, data):
        data["time"] = data["decision_time"]
        return cls(
            decision_time=FormattedDateTime(data["decision_time"]),
            order=Order.from_local(data) if "order_time" in data else None,
        )

    def update_order(self, order: Order):
        self.order = order

    def has_order(self):
        return self.order is not None

    def is_success(self):
        return self.order.is_success()
