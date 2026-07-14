import requests
import pandas as pd
from typing import Dict, List, Any

class BinanceDataFetcher:
    """Fetches historical market data from Binance Public API."""
    
    BASE_URL = "https://api.binance.com"

    def __init__(self, symbol: str = "XRPUSDT"):
        self.symbol = symbol.upper()

    def fetch_klines(self, interval: str = "15m", limit: int = 100) -> pd.DataFrame:
        """
        Fetches historical OHLCV klines.
        Returns a DataFrame with columns: [timestamp, open, high, low, close, volume]
        """
        url = f"{self.BASE_URL}/api/v3/klines"
        params = {
            "symbol": self.symbol,
            "interval": interval,
            "limit": limit
        }
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()
        
        df = pd.DataFrame(data, columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_volume", "count", "taker_buy_volume",
            "taker_buy_quote_volume", "ignore"
        ])
        
        # Convert types
        df["timestamp"] = pd.to_datetime(df["open_time"], unit="ms")
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = df[col].astype(float)
            
        return df[["timestamp", "open", "high", "low", "close", "volume"]]

    def fetch_agg_trades(self, limit: int = 1000, start_time: int = None, end_time: int = None) -> List[Dict[str, Any]]:
        """
        Fetches historical aggregate trades.
        Each trade has:
          'a': aggregate trade ID
          'p': price
          'q': quantity
          'f': first trade ID
          'l': last trade ID
          'T': timestamp
          'm': Was the buyer the maker? (If True, it's a sell order. If False, it's a buy order).
        """
        url = f"{self.BASE_URL}/api/v3/aggTrades"
        params = {
            "symbol": self.symbol,
            "limit": limit
        }
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time
            
        resp = requests.get(url, params=params)
        resp.raise_for_status()
        return resp.json()
