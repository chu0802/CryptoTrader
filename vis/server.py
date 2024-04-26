import argparse
import json

import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from utils.config import ResultsPath

parser = argparse.ArgumentParser()
parser.add_argument("--strategy", type=str, default="grid_trading")
args = parser.parse_args()

app = FastAPI()

# Serve HTML files
@app.get("/", response_class=FileResponse)
def read_root():
    return FileResponse("vis/index.html")


@app.get("/data/{filename}")
async def read_data(filename: str):
    with (ResultsPath(args.strategy) / filename).open("r") as f:
        data = json.load(f)
    return data


# Mount static files
app.mount("/", StaticFiles(directory="vis"), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9898)
