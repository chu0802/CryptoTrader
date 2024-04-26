import argparse
import json

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from utils.config import DataPath, ResultsPath

parser = argparse.ArgumentParser()
parser.add_argument("--strategy", type=str, default="grid_trading")
parser.add_argument("--symbol", type=str, default="btcusdt")
args = parser.parse_args()

app = FastAPI()

# Serve HTML files
@app.get("/", response_class=FileResponse)
def read_root():
    return FileResponse("vis/index.html")


@app.get("/results/{filename}")
async def read_results(filename: str):
    with (ResultsPath(args.strategy) / filename).open("r") as f:
        data = json.load(f)
    return data


@app.get("/price/{filename}")
async def fetch_price(filename: str):
    with (DataPath(args.symbol) / filename).open("r") as f:
        data = json.load(f)
    return data


# Mount static files
app.mount("/", StaticFiles(directory="vis"), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9898)
