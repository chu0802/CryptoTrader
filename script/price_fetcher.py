import argparse
import asyncio
from datetime import datetime, timedelta

import aiohttp

from protocol import FormattedDateTime, KLine
from utils.config import DataPath
from utils.json import dump


class BinancePriceFetcher:
    BINANCE_API_URL = "https://fapi.binance.com"

    def __init__(self):
        self.session = aiohttp.ClientSession()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args, **kwargs):
        await self.session.close()

    async def fetch_historical_prices(
        self, symbol, interval, max_num_per_request, start_time
    ):
        try:
            url = f"{self.BINANCE_API_URL}/fapi/v1/klines"
            params = {
                "symbol": symbol,
                "interval": interval,
                "limit": max_num_per_request,
                "endTime": start_time,
            }
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    prices = {
                        int(item[0])
                        // 1000: KLine(
                            float(item[1]),
                            float(item[2]),
                            float(item[3]),
                            float(item[4]),
                        ).to_dict()
                        for item in data
                    }
                    return prices
                else:
                    print(
                        f"Failed to fetch historical prices from Binance API: {response.status}"
                    )
                    return {}
        except Exception as e:
            print(f"Error fetching historical prices from Binance API: {str(e)}")
            return {}

    def split_endtimes(self, total_num, end_time=None, batch_size=1000):
        if end_time is None:
            end_time = datetime.now()
        else:
            end_time = FormattedDateTime(end_time).datetime
        closest_now = datetime(
            end_time.year, end_time.month, end_time.day, end_time.hour, end_time.minute
        )
        return [
            int((closest_now - timedelta(minutes=i)).timestamp()) * 1000
            for i in range(0, total_num, batch_size)
        ]

    async def fetch_all_historical_prices(self, symbol, interval, total_num, end_time):
        endtimes = self.split_endtimes(total_num, end_time)
        tasks = [
            self.fetch_historical_prices(symbol, interval, 1000, endtime)
            for endtime in endtimes
        ]
        historical_prices = await asyncio.gather(*tasks)
        historical_prices = {
            FormattedDateTime(timestamp): price
            for prices in historical_prices
            for timestamp, price in prices.items()
        }
        sorted_historical_prices = dict(
            sorted(historical_prices.items(), key=lambda x: x[0].timestamp)
        )
        return sorted_historical_prices


def argument_parsing():
    parser = argparse.ArgumentParser(
        description="Fetch historical futures prices from Binance API"
    )
    parser.add_argument(
        "--symbol",
        type=str,
        default="BTCUSDT",
        help="Symbol to fetch historical prices for",
    )
    parser.add_argument(
        "--interval",
        type=str,
        default="1m",
        help="Interval to fetch historical prices for",
    )
    parser.add_argument(
        "--total_num",
        type=int,
        default=100,
        help="Total number of historical prices to fetch",
    )
    parser.add_argument(
        "--end_time",
        type=str,
        default=None,
        help="End time of the historical prices to fetch",
    )

    return parser.parse_args()


async def main(args):
    async with BinancePriceFetcher() as fetcher:
        historical_prices = await fetcher.fetch_all_historical_prices(
            args.symbol.upper(), args.interval, args.total_num, args.end_time
        )

        dump(historical_prices, args.output_path)


if __name__ == "__main__":
    args = argument_parsing()
    args.output_path = DataPath(f"{args.symbol.lower()}/prices.json")

    asyncio.run(main(args))
