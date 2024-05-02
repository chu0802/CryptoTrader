from typing import List

from protocol import FormattedDateTime, KLine, Transaction
from strategy.base import BaseStrategy
from utils.config import DataPath
from utils.json import load


def get_price_data(symbol):
    return {
        FormattedDateTime(time): KLine(**data)
        for time, data in load(DataPath(f"{symbol}/prices.json")).items()
    }


class OptimalStrategy(BaseStrategy):
    _name = "optimal"

    def __init__(
        self,
        symbol,
        budget,
        leverage,
        dump_path="status.pkl",
        max_continual_operation=5,
        window_size=5,
        amount=7,
        min_ratio=0.005,
    ):
        super().__init__(symbol, budget, leverage, dump_path)
        self.max_continual_operation = max_continual_operation
        self.window_size = window_size
        self.min_ratio = min_ratio
        self.amount = amount
        self.max_amount = self.amount * max_continual_operation

        self.prev_buy_price = 0
        self.buy_counter = 0
        self.sell_counter = 0
        self.prev_sell_price = 0
        self.prev_price_list = []
        self.prev_action = None

    @property
    def org_total_amount(self):
        return self.total_amount / self.leverage

    def update_prev_price_list(self, current_price):
        if len(self.prev_price_list) >= self.window_size:
            self.prev_price_list.pop(0)
        self.prev_price_list.append(current_price)

    def check_optimal(self, current_price, mode="min"):
        if mode == "min":
            return current_price <= min(self.prev_price_list)
        elif mode == "max":
            return current_price >= max(self.prev_price_list)

    def _get_action(self, time: FormattedDateTime, kline: KLine) -> List[Transaction]:
        total_transactions = []
        self.update_prev_price_list(kline.close)

        if self.buy_counter == 3:
            if kline.close > self.current_average_price:
                total_transactions.append(
                    Transaction(
                        mode="SELL",
                        amount=abs(self.org_total_amount),
                        price=kline.close,
                        time=time,
                    )
                )
                self.prev_action = "SELL"
                self.prev_sell_price = kline.close
                self.prev_buy_price = 0
                self.buy_counter = 0
                self.sell_counter = 0
                self.prev_price_list = [kline.close]
        elif self.sell_counter == 3:
            if kline.close < self.current_average_price:
                total_transactions.append(
                    Transaction(
                        mode="BUY",
                        amount=abs(self.org_total_amount),
                        price=kline.close,
                        time=time,
                    )
                )
                self.prev_action = "BUY"
                self.prev_buy_price = kline.close
                self.prev_sell_price = 0
                self.sell_counter = 0
                self.buy_counter = 0
                self.prev_price_list = [kline.close]
        elif self.check_optimal(kline.close, "min") and (
            self.prev_action is None
            or self.prev_action == "SELL"
            or (
                self.prev_action == "BUY"
                and (self.prev_buy_price - kline.close) / self.prev_buy_price
                >= self.min_ratio
            )
        ):
            if abs(self.org_total_amount + self.amount) <= self.max_amount:
                total_transactions.append(
                    Transaction(
                        mode="BUY", amount=self.amount, price=kline.close, time=time
                    )
                )
                self.prev_action = "BUY"
                self.prev_buy_price = kline.close
            else:
                total_transactions.append(
                    Transaction(
                        mode="BUY",
                        amount=abs(self.org_total_amount),
                        price=kline.close,
                        time=time,
                    )
                )
                self.buy_counter += 1
                self.sell_counter = 0
            # else:
            #     print("reset mode, sell all, time: ", time)
            #     total_transactions.append(Transaction(mode="SELL", amount=abs(self.org_total_amount) + self.amount, price=kline.close, time=time))
            #     self.prev_action = "SELL"
            #     self.prev_sell_price = kline.close
            #     self.prev_buy_price = 0
            #     self.prev_price_list = [kline.close]
        elif self.check_optimal(kline.close, "max") and (
            self.prev_action is None
            or self.prev_action == "BUY"
            or (
                self.prev_action == "SELL"
                and (kline.close - self.prev_sell_price) / self.prev_sell_price
                >= self.min_ratio
            )
        ):
            if abs(self.org_total_amount - self.amount) <= self.max_amount:
                total_transactions.append(
                    Transaction(
                        mode="SELL", amount=self.amount, price=kline.close, time=time
                    )
                )
                self.prev_action = "SELL"
                self.prev_sell_price = kline.close
            else:
                total_transactions.append(
                    Transaction(
                        mode="SELL",
                        amount=abs(self.org_total_amount),
                        price=kline.close,
                        time=time,
                    )
                )
                self.sell_counter += 1
                self.buy_counter = 0
            # else:
            #     print("reset mode, buy all, time: ", time)
            #     total_transactions.append(Transaction(mode="BUY", amount=abs(self.org_total_amount)+self.amount, price=kline.close, time=time))
            #     self.prev_action = "BUY"
            #     self.prev_buy_price = kline.close
            #     self.prev_sell_price = 0
            #     self.prev_price_list = [kline.close]

        return total_transactions


# class OptimalStrategy(BaseStrategy):
#     _name = "optimal"

#     def __init__(self, budget, leverage, symbol="ondousdt", window_size=10, amount=7, min_interval=5, seed=1102, failed_prediction_prob=0, max_amount=70, min_ratio=0.005):
#         super().__init__(budget, leverage)
#         self.symbol = symbol
#         self.price_data = get_price_data(symbol)
#         self.window_size = window_size
#         self.amount = amount
#         self.buy_interval = min_interval + 1
#         self.sell_interval = min_interval + 1
#         self.min_interval = min_interval
#         self.failed_prediction_prob = failed_prediction_prob
#         self.rng = np.random.default_rng(seed)
#         self.prev_price_list = []
#         self.total_amount = 0
#         self.max_amount = max_amount
#         self.min_ratio = min_ratio
#         self.prev_buy_price = -1
#         self.prev_sell_price = -1
#         self.prev_action = None
#         self.prev_buy_price = -1
#         self.prev_sell_price = -1
#         self.sell_flush_flag = True
#         self.buy_flush_flag = True
#         self.sell_count = 0
#         self.buy_count = 0
#         self.max_count = 5

#     def check_prev_optimal_point(self, current_price, mode="min"):
#         if mode == "min":
#             return current_price <= min(self.prev_price_list)
#         elif mode == "max":
#             return current_price >= max(self.prev_price_list)

#     def next_moment_is_higher(self, current_price, next_price):
#         correct_prediction = not bool(self.rng.binomial(1, self.failed_prediction_prob))
#         return correct_prediction and next_price > current_price

#     def update_prev_price_list(self, current_price):
#         if len(self.prev_price_list) >= self.window_size:
#             self.prev_price_list.pop(0)
#         self.prev_price_list.append(current_price)

#     def _get_action(self, time: FormattedDateTime, kline: KLine):
#         total_transactions = []

#         if abs(self.total_amount) <= self.max_amount and (self.buy_interval > self.min_interval or self.sell_interval > self.min_interval):
#             self.update_prev_price_list(kline.close)
#         # minimum point
#         if self.check_prev_optimal_point(kline.close, mode="min") and self.buy_interval > self.min_interval:
#             # if time + 60 in self.price_data:
#             #     next_price = self.price_data[time + 60].close
#             #     if self.next_moment_is_higher(kline.close, next_price):
#             if self.sell_count < self.max_count and self.sell_flush_flag:
#                 if any([
#                     self.prev_action is None,
#                     all([
#                         self.prev_action == "BUY",
#                         (self.prev_buy_price - kline.close) / self.prev_buy_price >= self.min_ratio
#                     ]),
#                     self.prev_action == "SELL"
#                 ]):
#                     total_transactions.append(
#                         Transaction(mode="BUY", amount=self.amount, price=kline.close, time=time)
#                     )
#                     self.sell_count = 0
#                     self.buy_interval = 0
#                     self.buy_count += 1
#                     self.total_amount += self.amount
#                     self.prev_action = "BUY"
#                     self.prev_buy_price = kline.close
#                     if self.buy_flush_flag is False:
#                         self.buy_flush_flag = True
#             else:
#                 if self.sell_flush_flag:
#                     total_transactions.append(
#                         Transaction(mode="SELL", amount=abs(self.total_amount) + self.amount, price=kline.close, time=time)
#                     )
#                     print("sell all, ", time)
#                     self.sell_flush_flag = False
#                     self.total_amount = -self.amount
#                     self.sell_count = 1
#                     self.buy_count = 0
#         elif self.check_prev_optimal_point(kline.close, mode="max") and self.sell_interval > self.min_interval:
#             # if time + 60 in self.price_data:
#             #     next_price = self.price_data[time + 60].close
#             #     if (not self.next_moment_is_higher(kline.close, next_price)):
#             if self.sell_count < self.max_count and self.buy_flush_flag:
#                 if any([
#                     self.prev_action is None,
#                     all([
#                         self.prev_action == "SELL",
#                         (kline.close - self.prev_sell_price) / self.prev_sell_price >= self.min_ratio
#                     ]),
#                     self.prev_action == "BUY"
#                 ]):
#                     total_transactions.append(
#                         Transaction(mode="SELL", amount=self.amount, price=kline.close, time=time)
#                     )
#                     self.buy_count = 0
#                     self.sell_interval = 0
#                     self.sell_count += 1
#                     self.total_amount -= self.amount
#                     self.prev_action = "SELL"
#                     self.prev_sell_price = kline.close
#                     if self.sell_flush_flag is False:
#                         self.sell_flush_flag = True
#             else:
#                 if self.buy_flush_flag:
#                     total_transactions.append(
#                         Transaction(mode="BUY", amount=abs(self.total_amount) + self.amount, price=kline.close, time=time)
#                     )
#                     print("buy all, ", time)
#                     self.buy_flush_flag = False
#                     self.total_amount = self.amount
#                     self.buy_count = 1
#                     self.sell_count = 0


#         self.buy_interval += 1
#         self.sell_interval += 1

#         return total_transactions
