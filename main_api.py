from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from engine.data_fetcher import BinanceDataFetcher
from engine.backtester import OrderFlowBacktester
from engine.order_flow import OrderFlowCalculator
import uvicorn

app = FastAPI(title="Trader Dale - Order Flow API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class BacktestRequest(BaseModel):
    symbol: str = "XRPUSDT"
    interval: str = "15m"
    limit: int = 150
    imbalance_ratio: float = 2.5

@app.post("/api/backtest")
async def run_backtest(req: BacktestRequest):
    fetcher = BinanceDataFetcher(symbol=req.symbol)
    try:
        klines = fetcher.fetch_klines(interval=req.interval, limit=req.limit)
        backtester = OrderFlowBacktester()
        # Overwrite strategy imbalance ratio
        backtester.calculator.imbalance_ratio = req.imbalance_ratio
        results = backtester.run(klines)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/order_flow")
async def get_order_flow(symbol: str = "XRPUSDT", interval: str = "15m", limit: int = 100):
    fetcher = BinanceDataFetcher(symbol=symbol)
    try:
        klines = fetcher.fetch_klines(interval=interval, limit=limit)
        calculator = OrderFlowCalculator()
        poc, vah, val = calculator.calculate_volume_profile(klines)
        
        # Format klines for display
        kline_list = klines.to_dict(orient="records")
        for k in kline_list:
            k["timestamp"] = k["timestamp"].isoformat()
            
        return {
            "poc": poc,
            "vah": vah,
            "val": val,
            "klines": kline_list
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
