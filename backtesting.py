from dataclasses import dataclass
from pathlib import Path

from strategy import BaseStrategy, GridTradingStrategy
from utils.config import DataPath, ResultsPath
from utils.datetime import FormattedDateTime
from utils.json import dump, load


@dataclass
class KLine:
    high: float
    low: float
    close: float


class Tester:
    def __init__(
        self,
        start_time: FormattedDateTime,
        end_time: FormattedDateTime = None,
        symbol: str = "btcusdt",
    ):
        if not isinstance(start_time, FormattedDateTime):
            start_time = FormattedDateTime(start_time)
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
            self.start_time + i: KLine(*data[(self.start_time + i).string])
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

        dump(strategy.get_result(), results_path)


if __name__ == "__main__":
    tester = Tester("2024-04-05 20:32:00", symbol="btcusdt")
    highest, lowest, num_interval = 75000, 60000, 20
    initial_amount = 0.003

    strategy = GridTradingStrategy(
        budget=200,
        leverage=30,
        amount=initial_amount / 30,
        highest=highest,
        lowest=lowest,
        num_interval=num_interval,
    )

    tester.test(strategy)
