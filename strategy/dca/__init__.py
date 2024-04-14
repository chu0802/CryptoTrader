from protocol import FormattedDateTime, Transaction
from strategy.base import BaseStrategy


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
