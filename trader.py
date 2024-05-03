import argparse
import os

from binance.um_futures import UMFutures
from protocol.datetime import FormattedDateTime
from protocol.kline import KLine
from protocol.order import Action, Order
from strategy import BaseStrategy, get_strategy
from utils.config import ResultsPath, StatusPath, StrategyPath
from utils.json import dump, load
from utils.slack import SLACK_DEFAULT_CUSTOM_ARG, SlackBot


class Trader:
    def __init__(
        self, strategy: BaseStrategy, client: UMFutures, slack_client: SlackBot
    ):
        self.strategy = strategy
        self.client = client
        self.slack_client = slack_client
        self.action_path = (
            StatusPath()
            / "trader"
            / self.strategy.name
            / self.strategy.symbol
            / "last_action.json"
        )
        self.results_path = (
            ResultsPath()
            / "trader"
            / self.strategy.name
            / self.strategy.symbol
            / "result.json"
        )
        self.last_action = self.load_action()
        self.current_action = None

    def dump_action(self, action: Action):
        dump(action.to_dict(), self.action_path)

    def load_action(self) -> Action:
        if self.action_path.exists():
            return Action.from_local(load(self.action_path))
        return None

    def dump_message(self, time, messages_dict, send_slack=False):
        print("=" * 70)
        print("Time:", time)
        for k, v in messages_dict.items():
            print(f"{k}: {v}")
        print("=" * 70, end="\n\n")
        if send_slack:
            self.slack_client.send_messages(messages_dict, **SLACK_DEFAULT_CUSTOM_ARG)

    def trade_and_valid_loop(self):
        while True:
            current_time = FormattedDateTime(self.client.time()["serverTime"])
            # trade
            if all(
                [
                    not self.current_action,
                    (
                        not self.last_action
                        or (current_time - self.last_action.decision_time >= 60)
                    ),
                ]
            ):
                self.current_action = Action(current_time)
                self.trade(current_time)

            # valid
            if self.current_action is not None:
                is_able_to_exit = self.valid(current_time)

                if is_able_to_exit:
                    self.strategy.dump()
                    break

    def valid(self, current_time: FormattedDateTime):
        if not self.current_action.has_order() or self.current_action.is_success():
            return True

        query_result = self.client.query_order(
            symbol=self.strategy.symbol.upper(),
            orderId=self.current_action.order.order_id,
        )
        self.current_action.order.update_status(query_result)

        if self.current_action.is_success():
            transaction = self.current_action.order.expected_transaction

            transaction.amount *= self.strategy.leverage
            transaction.price = float(query_result["price"])
            self.strategy.transaction_flow += transaction

            self.strategy._transaction_snapshots.append(
                self.strategy.get_transaction_snapshot(
                    transaction.time, transaction.price, transaction
                )
            )

            dump(self.strategy.transaction_snapshots, self.results_path)

            return True

        if current_time - self.current_action.order.order_time >= 50:
            self.client.cancel_order(
                symbol=self.strategy.symbol.upper(),
                orderId=self.current_action.order.order_id,
            )
            self.dump_message(
                current_time, {"Message": "Order was cancelled"}, send_slack=True
            )

            # TODO: find a better way to maintain status
            exit()

        return False

    def trade(self, current_time: FormattedDateTime):
        kline = KLine.from_api(
            self.client.klines(
                symbol=self.strategy.symbol.upper(), interval="1m", limit=1
            )[0]
        )

        transactions = self.strategy._get_action(current_time, kline)
        transaction = transactions[0] if len(transactions) > 0 else None

        if transaction:
            order = Order.from_online(
                self.client.new_order(
                    **{
                        "symbol": self.strategy.symbol.upper(),
                        "side": transaction.mode.name,
                        "type": "LIMIT",
                        "timeInForce": "GTC",
                        # TODO: set a min value to ensure the value would be at least five
                        "quantity": transaction.amount * self.strategy.leverage,
                        "price": f"{transaction.price:.4f}",
                    }
                ),
                transaction=transaction,
            )
            self.current_action.update_order(order)
        self.dump_message(
            current_time,
            {"Kline": kline, "Transaction": transaction},
            send_slack=transaction is not None,
        )

        self.dump_action(self.current_action)


def argument_parsing():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--strategy_config_path",
        type=StrategyPath,
        default=StrategyPath("config/optimal_config.json"),
    )

    return parser.parse_args()


def main(args):
    strategy_config = load(args.strategy_config_path)
    strategy = get_strategy(strategy_config)
    client = UMFutures(
        key=os.environ.get("API_KEY", None),
        secret=os.environ.get("SECRET_KEY", None),
        # base_url="https://testnet.binancefuture.com"
    )

    slack_client = SlackBot(
        api_token=os.environ.get("SLACK_API_TOKEN"),
        channel_id=os.environ.get("SLACK_CHANNEL_ID"),
    )

    client.change_leverage(symbol=strategy.symbol.upper(), leverage=strategy.leverage)

    trader = Trader(strategy, client, slack_client)

    trader.trade_and_valid_loop()


if __name__ == "__main__":
    args = argument_parsing()
    main(args)
