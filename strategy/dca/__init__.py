from protocol.datetime import FormattedDateTime
from protocol.transaction import Transaction
from strategy.base import BaseStrategy


class DCAStrategy(BaseStrategy):
    _name = "dca"

    def __init__(
        self,
        symbol: str,
        budget: float,
        leverage: int = 1,
        dump_path: str = "status.pkl",
        time_interval: str = "week",
        amount_in_usd: float = 100,
    ):
        super().__init__(symbol, budget, leverage, dump_path)
        self.time_interval = self.convert_interval(time_interval)
        self.amount_in_usd = amount_in_usd

    def convert_interval(self, interval: str):
        if interval == "day":
            return 86400
        if interval == "week":
            return 86400 * 7
        elif interval == "month":
            return 86400 * 7 * 30

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
