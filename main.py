import argparse
import logging
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from tqdm import tqdm

from protocol.datetime import FormattedDateTime
from protocol.kline import KLine
from protocol.time_value import TimeValue, TimeValueQueue
from strategy import BaseStrategy, get_strategy
from utils.config import PYTHON_PATH, DataPath, ResultsPath, StrategyPath
from utils.json import dump, load


class Tester:
    def __init__(
        self,
        start_time: FormattedDateTime,
        end_time: FormattedDateTime = None,
        symbol: str = "btcusdt",
        window_size: int = 1440,
    ):
        if end_time is not None and not isinstance(end_time, FormattedDateTime):
            end_time = FormattedDateTime(end_time)

        self.start_time = start_time
        self.end_time = end_time
        self.symbol = symbol
        self.price_path = DataPath(f"{symbol.lower()}/prices.json")
        self.profit_queue: TimeValueQueue = TimeValueQueue(max_size=window_size)
        self.max_profit_drop: TimeValue = TimeValue(None, -1e7)
        self.max_profit_gain: TimeValue = TimeValue(None, -1e7)

        self.min_profit: TimeValue = TimeValue(None, 1e-7)
        self.max_profit: TimeValue = TimeValue(None, -1e-7)

        self._data = self.load_data(self.price_path)

    def load_data(self, prices_path: Path):
        data = load(prices_path)

        end_time = (
            FormattedDateTime(list(data.keys())[-1])
            if self.end_time is None
            else self.end_time
        )

        total_seconds = int(end_time - self.start_time)
        return {
            self.start_time + i: KLine(**data[(self.start_time + i).string])
            for i in range(0, total_seconds + 1, 60)
        }

    def test(self, strategy: BaseStrategy):
        net_profit_history = []
        results_path = ResultsPath(f"{strategy.name}/{self.symbol}/result.json")
        profit_path = ResultsPath(f"{strategy.name}/{self.symbol}/profit_flow.json")

        for time, kline in tqdm(self._data.items(), total=len(self._data)):
            strategy.get_action(time, kline)
            net_profit_history.append(
                {
                    "time": int(time.timestamp * 1000),
                    "price": kline.close,
                    "average_price": strategy.transaction_flow.average_price,
                    "profit": strategy.transaction_flow.net_profit(kline.close),
                }
            )
            current_timevalue = TimeValue(
                time, strategy.transaction_flow.net_profit(kline.close)
            )
            self.profit_queue.append(current_timevalue)

            max_profit_time_value = self.profit_queue.max()
            min_profit_time_value = self.profit_queue.min()
            diff = max_profit_time_value - min_profit_time_value

            if (
                max_profit_time_value.time < min_profit_time_value.time
                and diff > self.max_profit_drop
            ):
                self.max_profit_drop = diff
            elif (
                max_profit_time_value.time >= min_profit_time_value.time
                and diff > self.max_profit_gain
            ):
                self.max_profit_gain = diff

            if current_timevalue > self.max_profit:
                self.max_profit = current_timevalue
            if current_timevalue < self.min_profit:
                self.min_profit = current_timevalue

            if not (
                strategy.check_budget(kline.low) and strategy.check_budget(kline.high)
            ):
                print(f"bankrupt time:", time.string)
                break
        transaction_snapshots = strategy.transaction_snapshots
        transaction_snapshots.append(
            strategy.get_transaction_snapshot(time, kline.close)
        )

        dump(transaction_snapshots, results_path)
        dump(net_profit_history, profit_path)
        print("=" * 100)
        print(
            f"Max Profit Time: {self.max_profit.time}, Value: {self.max_profit.value}"
        )
        print(
            f"Min Profit Time: {self.min_profit.time}, Value: {self.min_profit.value}"
        )
        print(f"Final Net Profit: {current_timevalue.value}", end="\n" * 2)

        print(
            f"Max Profit Drop Time: {self.max_profit_drop.time}, Value: {self.max_profit_drop.value}"
        )
        print(
            f"Max Profit Gain Time: {self.max_profit_gain.time}, Value: {self.max_profit_gain.value}"
        )
        print("=" * 100, end="\n" * 2)


def fetch_price(start_time, end_time=None, symbol="btcusdt", interval="1m"):
    if end_time is None:
        end_time = datetime.now() - timedelta(minutes=1)
    end_time = FormattedDateTime(end_time)
    fetch_amount = int((end_time - start_time) // 60)
    commands = [
        PYTHON_PATH,
        "-m",
        "script.price_fetcher",
        "--symbol",
        symbol,
        "--total_num",
        str(fetch_amount),
        "--end_time",
        end_time.string,
        "--interval",
        interval,
    ]
    print("+", " ".join(commands))
    subprocess.run(commands)


def argument_parsing():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--start_time", type=FormattedDateTime, default="2024-04-05 20:32:00"
    )
    parser.add_argument("--end_time", type=str, default=None)
    parser.add_argument("--symbol", type=str, default="btcusdt")
    parser.add_argument(
        "--strategy_config_path",
        type=StrategyPath,
        default=StrategyPath("config/grid_trading_config.json"),
    )
    parser.add_argument("--window_size", type=int, default=1440)
    parser.add_argument("--fetch_price", action="store_true", default=False)

    return parser.parse_args()


def main(args):
    if args.fetch_price:
        logging.info("Fetching price")
        for interval in ["1m", "3m", "5m", "15m"]:
            fetch_price(args.start_time, args.end_time, args.symbol, interval)

    tester = Tester(args.start_time, args.end_time, args.symbol, args.window_size)
    strategy = get_strategy(load(args.strategy_config_path))
    tester.test(strategy)


if __name__ == "__main__":
    args = argument_parsing()
    main(args)
