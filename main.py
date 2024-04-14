import argparse
import logging
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

from protocol import FormattedDateTime, KLine
from strategy import BaseStrategy, get_strategy
from utils.config import DataPath, ResultsPath
from utils.json import dump, load


class Tester:
    def __init__(
        self,
        start_time: FormattedDateTime,
        end_time: FormattedDateTime = None,
        symbol: str = "btcusdt",
    ):
        if end_time is not None and not isinstance(end_time, FormattedDateTime):
            end_time = FormattedDateTime(end_time)

        self.start_time = start_time
        self.end_time = end_time
        self.price_path = DataPath(f"{symbol.lower()}/prices.json")

        self._data = self.load_data(self.price_path)

    def load_data(self, prices_path: Path):
        data = load(prices_path)

        end_time = (
            FormattedDateTime(list(data.keys())[-1])
            if self.end_time is None
            else self.end_time
        )

        total_seconds = int((end_time - self.start_time).total_seconds())

        return {
            self.start_time + i: KLine(**data[(self.start_time + i).string])
            for i in range(0, total_seconds + 1, 60)
        }

    def test(self, strategy: BaseStrategy):
        results_path = ResultsPath(f"{strategy.name}/result.json")
        results_path.parent.mkdir(parents=True, exist_ok=True)

        for time, kline in self._data.items():
            strategy.get_action(time, kline)

            if not strategy.check_budget(kline.close):
                print(f"bankrupt time:", time.string)
                break
        transaction_snapshots = strategy.transaction_snapshots
        transaction_snapshots.append(
            strategy.get_transaction_snapshot(time, kline.close)
        )

        dump(transaction_snapshots, results_path)


def fetch_price(start_time, end_time=None, symbol="btcusdt"):
    if end_time is None:
        end_time = FormattedDateTime(datetime.now() - timedelta(minutes=1))
    fetch_amount = int((end_time - start_time).total_seconds() // 60)
    commands = [
        "python",
        "-m",
        "script.price_fetcher",
        "--symbol",
        symbol,
        "--total_num",
        str(fetch_amount),
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
        "--strategy_config_path", type=str, default="strategy_config.json"
    )
    parser.add_argument("--fetch_price", action="store_true", default=False)

    return parser.parse_args()


def main(args):
    if args.fetch_price:
        logging.info("Fetching price")
        fetch_price(args.start_time, args.end_time, args.symbol)

    tester = Tester(args.start_time, args.end_time, args.symbol)
    strategy = get_strategy(load(args.strategy_config_path))
    tester.test(strategy)


if __name__ == "__main__":
    args = argument_parsing()
    main(args)