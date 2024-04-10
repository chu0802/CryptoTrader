import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Union

import pytz

from strategy import BaseStrategy, GridTradingStrategy


@dataclass
class KLine:
    high: float
    low: float
    close: float


def formatted_time_converter(
    formatted_time_str, timezone="Asia/Taipei", format="%Y-%m-%d %H:%M:%S"
):
    parsed_time = datetime.strptime(formatted_time_str, format)
    return parsed_time.astimezone(pytz.timezone(timezone))


class Tester:
    def __init__(
        self,
        start_time: Union[datetime, str],
        end_time: Union[datetime, str],
        prices_path: Path,
        results_path: Path = Path("results"),
    ):
        self.start_time = (
            formatted_time_converter(start_time)
            if isinstance(start_time, str)
            else start_time
        )
        self.end_time = (
            formatted_time_converter(end_time)
            if isinstance(end_time, str)
            else end_time
        )
        self._data = self.load_data(prices_path)
        self.results_path = results_path

    def load_data(self, prices_path: Path):
        with prices_path.open("r") as f:
            data = json.load(f)
        return {
            i: KLine(*data[str(i)])
            for i in range(
                int(self.start_time.timestamp()),
                int((self.end_time.timestamp())) + 1,
                60,
            )
        }

    def get_kline(self, timestamp: Union[str, datetime, int]):
        if isinstance(timestamp, str):
            timestamp = formatted_time_converter(timestamp).timestamp()
        elif isinstance(timestamp, datetime):
            timestamp = int(timestamp.timestamp())
        return self._data[timestamp]

    def test(self, strategy: BaseStrategy):
        results_path = self.results_path / strategy.name / "result.json"
        results_path.parent.mkdir(parents=True, exist_ok=True)

        for timestamp, kline in self._data.items():
            strategy.get_action(timestamp, kline)

            if not strategy.check_budget(kline.close):
                print(
                    f"bankrupt time:",
                    datetime.fromtimestamp(timestamp).strftime(
                        "%Y-%m-%d %H:%M:%S %Z%z"
                    ),
                )
                break

        with results_path.open("w") as f:
            json.dump(strategy.get_result(), f, indent=4)


if __name__ == "__main__":
    tester = Tester(
        "2024-04-05 20:32:00", "2024-04-10 07:38:00", Path("data/btcusdt/prices.json")
    )

    highest, lowest, num_interval = 75000, 60000, 20
    initial_amount = (
        0.7 * 200 * 30 / sum(range(lowest, highest, (highest - lowest) // num_interval))
    )

    strategy = GridTradingStrategy(
        budget=200,
        leverage=30,
        amount=initial_amount / 30,
        highest=highest,
        lowest=lowest,
        num_interval=num_interval,
    )

    tester.test(strategy)
