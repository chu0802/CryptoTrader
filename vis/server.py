import json
import logging
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Environment configuration
BASE_DIR = Path(__file__).resolve().parent.parent

app = FastAPI()

# Serve HTML files
@app.get("/", response_class=FileResponse)
async def read_root(symbol: str = "ondousdt"):
    return FileResponse(BASE_DIR / "vis/index.html")


class PriceData(BaseModel):
    symbol: str
    filename: str


@app.get("/results/{strategy}/{symbol}/{filename}")
async def read_results(strategy: str, symbol: str, filename: str):
    results_path = BASE_DIR / "results" / strategy / symbol / filename
    logging.info(results_path)
    if not results_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    with results_path.open("r") as f:
        data = json.load(f)
    return data


@app.get("/price/{symbol}/{filename}")
async def fetch_price(symbol: str, filename: str):
    data_path = BASE_DIR / "data" / symbol / filename
    if not data_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    with data_path.open("r") as f:
        data = json.load(f)
    return data


# Mount static files
app.mount("/", StaticFiles(directory=BASE_DIR / "vis"), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=9898)
