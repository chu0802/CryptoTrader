import argparse
import json
from collections import deque
from typing import Dict

from protocol import FormattedDateTime, KLine
from utils.config import DataPath
from utils.json import dump, load


class KDJCalculator:
    def __init__(self, historical_prices: Dict[FormattedDateTime, KLine]):
        self.historical_prices = historical_prices

    def calculate_kdj(self):
        k_values, d_values, j_values = [], [], []
        highest_prices = deque(maxlen=9)
        lowest_prices = deque(maxlen=9)

        for kline in self.historical_prices.values():
            highest_prices.append(kline.high)
            lowest_prices.append(kline.low)
            if len(highest_prices) < 9:
                continue

            highest_high = max(highest_prices)
            lowest_low = min(lowest_prices)

            dominator = (
                highest_high - lowest_low if highest_high - lowest_low != 0 else 0.001
            )
            rsv = (kline.close - lowest_low) / dominator * 100

            if not k_values:
                k_values.append(50)
                d_values.append(50)
            else:
                k_values.append((2 / 3) * k_values[-1] + (1 / 3) * rsv)
                d_values.append((2 / 3) * d_values[-1] + (1 / 3) * k_values[-1])

            j_values.append(3 * k_values[-1] - 2 * d_values[-1])

        return k_values, d_values, j_values

    def generate_kdj_data(self, k_values, d_values, j_values):
        kdj_data = {}
        times = list(self.historical_prices.keys())[8:]
        for i, time in enumerate(times):
            kdj_data[time] = {
                "time": time,
                "K": k_values[i],
                "D": d_values[i],
                "J": j_values[i],
            }
        return kdj_data

    def save_kdj_data_to_json(self, kdj_data, filename="kdj_data.json"):
        with open(filename, "w") as json_file:
            json.dump(kdj_data, json_file, indent=4)


def argument_parsing():
    parser = argparse.ArgumentParser(
        description="Calculate KDJ values for a given symbol and interval."
    )
    parser.add_argument(
        "--symbol",
        type=str,
        default="BTCUSDT",
        help="The symbol to calculate KDJ values for.",
    )

    parser.add_argument(
        "--output_file",
        type=str,
        default="kdj_data.json",
        help="The name of the output JSON file.",
    )

    return parser.parse_args()


def main(args):
    historical_prices = load(args.prices_path)

    kdj_calculator = KDJCalculator(historical_prices)
    k_values, d_values, j_values = kdj_calculator.calculate_kdj()
    kdj_data = kdj_calculator.generate_kdj_data(k_values, d_values, j_values)

    dump(kdj_data, args.output_path)


if __name__ == "__main__":
    args = argument_parsing()
    args.prices_path = DataPath(f"{args.symbol.lower()}/prices.json")
    args.output_path = DataPath(f"{args.symbol.lower()}/{args.output_file}")

    main(args)
