import argparse
import asyncio
from datetime import datetime, timedelta

import aiohttp

from utils.config import DataPath
from utils.datetime import FormattedDateTime
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
                        // 1000: (float(item[2]), float(item[3]), float(item[4]))
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

    def split_endtimes(self, total_num, batch_size=1000):
        now = datetime.now()
        closest_now = datetime(now.year, now.month, now.day, now.hour, now.minute)
        return [
            int((closest_now - timedelta(minutes=i)).timestamp()) * 1000
            for i in range(0, total_num, batch_size)
        ]

    async def fetch_all_historical_prices(self, symbol, interval, total_num):
        endtimes = self.split_endtimes(total_num)
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

    return parser.parse_args()


async def main(args):
    async with BinancePriceFetcher() as fetcher:
        historical_prices = await fetcher.fetch_all_historical_prices(
            args.symbol, args.interval, args.total_num
        )

        dump(historical_prices, args.output_path)


if __name__ == "__main__":
    args = argument_parsing()
    args.output_path = DataPath(f"{args.symbol.lower()}/prices.json")
    args.output_path.parent.mkdir(parents=True, exist_ok=True)

    asyncio.run(main(args))
