import argparse
import json
from collections import deque
from datetime import datetime
from pathlib import Path

import pytz


class KDJCalculator:
    def __init__(self, historical_prices):
        self.historical_prices = historical_prices

    def calculate_kdj(self):
        k_values, d_values, j_values = [], [], []
        highest_prices = deque(maxlen=9)
        lowest_prices = deque(maxlen=9)

        for timestamp in self.historical_prices.keys():
            high, low, close = self.historical_prices[timestamp]
            highest_prices.append(high)
            lowest_prices.append(low)
            if len(highest_prices) < 9:
                continue

            highest_high = max(highest_prices)
            lowest_low = min(lowest_prices)

            dominator = (
                highest_high - lowest_low if highest_high - lowest_low != 0 else 0.001
            )
            rsv = (close - lowest_low) / dominator * 100

            if not k_values:
                k_values.append(50)
                d_values.append(50)
            else:
                k_values.append((2 / 3) * k_values[-1] + (1 / 3) * rsv)
                d_values.append((2 / 3) * d_values[-1] + (1 / 3) * k_values[-1])

            j_values.append(3 * k_values[-1] - 2 * d_values[-1])

        return k_values, d_values, j_values

    def generate_kdj_data(self, k_values, d_values, j_values):
        kdj_data = []
        timestamps = sorted(self.historical_prices.keys())[8:]
        for i, timestamp in enumerate(timestamps):
            utc_time = datetime.utcfromtimestamp(int(timestamp)).replace(
                tzinfo=pytz.utc
            )
            local_time = utc_time.astimezone(pytz.timezone("Asia/Shanghai"))
            formatted_time = local_time.strftime("%Y-%m-%d %H:%M:%S %Z%z")
            kdj_data.append(
                {
                    "timestamp": formatted_time,
                    "price": self.historical_prices[timestamp][-1],
                    "K": k_values[i],
                    "D": d_values[i],
                    "J": j_values[i],
                }
            )
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
        "--data_dir",
        type=Path,
        default=Path("data"),
        help="The directory to save the KDJ data to.",
    )
    parser.add_argument(
        "--prices_path",
        type=str,
        default="prices.json",
        help="The path to the historical prices JSON file.",
    )
    parser.add_argument(
        "--output_file",
        type=str,
        default="kdj_data.json",
        help="The name of the output JSON file.",
    )

    return parser.parse_args()


def main(args):
    with args.prices_path.open() as f:
        historical_prices = json.load(f)

    kdj_calculator = KDJCalculator(historical_prices)
    k_values, d_values, j_values = kdj_calculator.calculate_kdj()
    kdj_data = kdj_calculator.generate_kdj_data(k_values, d_values, j_values)
    kdj_calculator.save_kdj_data_to_json(kdj_data)


if __name__ == "__main__":
    args = argument_parsing()
    args.prices_path = args.data_dir / args.symbol.lower() / args.prices_path
    args.output_path = args.data_dir / args.symbol.lower() / args.output_file

    main(args)
