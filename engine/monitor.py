import asyncio
import json
import websockets
from datetime import datetime
from engine.order_flow import OrderFlowCalculator
from engine.strategy import OrderFlowStrategy
from typing import Dict, Any, List

class OrderFlowMonitor:
    """Monitors real-time aggregate trades via WebSockets and checks for setups."""

    def __init__(self, symbol: str = "XRPUSDT", timeframe_seconds: int = 60):
        self.symbol = symbol.lower()
        self.timeframe_seconds = timeframe_seconds
        self.calculator = OrderFlowCalculator()
        self.strategy = OrderFlowStrategy()
        
        self.current_trades: List[Dict[str, Any]] = []
        self.historical_candles: List[Dict[str, Any]] = []
        self.bar_start_time = datetime.now()

    def print_bar_summary(self, bar_metrics: Dict[str, Any]):
        """Prints a visual summary of the completed bar footprint & order flow."""
        print(f"\n==================================================")
        print(f"📊 BAR COMPLETED AT: {datetime.now().strftime('%H:%M:%S')}")
        print(f"💰 Close: {bar_metrics['close']:.4f} | Volume: {bar_metrics['total_volume']:.1f}")
        print(f"📈 Delta: {bar_metrics['delta']:+.1f}")
        
        # Display Imbalances
        if bar_metrics["buy_imbalances"]:
            print(f"🔥 Buying Imbalances (Bullish): {['{:.4f}'.format(p) for p in bar_metrics['buy_imbalances']]}")
        if bar_metrics["sell_imbalances"]:
            print(f"💧 Selling Imbalances (Bearish): {['{:.4f}'.format(p) for p in bar_metrics['sell_imbalances']]}")
            
        # Display failed auctions
        if bar_metrics["unfinished_high"]:
            print(f"⚠️ Unfinished Business at High (Magnet): {bar_metrics['high']:.4f}")
        if bar_metrics["unfinished_low"]:
            print(f"⚠️ Unfinished Business at Low (Magnet): {bar_metrics['low']:.4f}")
        print(f"==================================================")

    async def start(self):
        """Starts the real-time WebSocket connection to Binance."""
        url = f"wss://stream.binance.com:9443/ws/{self.symbol}@aggTrade"
        print(f"🔌 Connecting to Binance WebSocket for {self.symbol.upper()}...")
        
        async with websockets.connect(url) as ws:
            print(f"🟢 Connected! Monitoring real-time order flow...")
            self.bar_start_time = datetime.now()
            
            while True:
                try:
                    msg = await ws.recv()
                    trade = json.loads(msg)
                    self.current_trades.append(trade)
                    
                    elapsed = (datetime.now() - self.bar_start_time).total_seconds()
                    
                    # Print micro-updates for active trades
                    price = float(trade["p"])
                    qty = float(trade["q"])
                    side = "SELL (to Bid)" if trade["m"] else "BUY (to Ask)"
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Price: {price:.4f} | Qty: {qty:.1f} | {side}", end="\r")
                    
                    if elapsed >= self.timeframe_seconds:
                        # Process completed bar
                        if self.current_trades:
                            prices = [float(t["p"]) for t in self.current_trades]
                            close = prices[-1]
                            open_val = prices[0]
                            high = max(prices)
                            low = min(prices)
                            
                            # Construct footprint
                            footprint = self.calculator.build_footprint(self.current_trades)
                            metrics = self.calculator.calculate_metrics(footprint)
                            
                            bar_metrics = {
                                "close": close,
                                "open": open_val,
                                "high": high,
                                "low": low,
                                "total_volume": metrics["total_volume"],
                                "delta": metrics["delta"],
                                "buy_imbalances": metrics["buy_imbalances"],
                                "sell_imbalances": metrics["sell_imbalances"],
                                "unfinished_high": metrics["unfinished_high"],
                                "unfinished_low": metrics["unfinished_low"]
                            }
                            
                            self.print_bar_summary(bar_metrics)
                            
                            # Evaluate setups
                            if len(self.historical_candles) > 1:
                                vah, val, poc = close * 1.01, close * 0.99, close # simulated S/R profile
                                vwap = close
                                prev_candle = self.historical_candles[-1]
                                
                                signal = self.strategy.evaluate_signals(
                                    bar_metrics,
                                    prev_candle,
                                    self.historical_candles,
                                    vah, val, poc, vwap
                                )
                                
                                if signal["action"] != "HOLD":
                                    print(f"🚨 ORDER FLOW ALERT: {signal['action']} signal triggered! Reason: {signal['reason']}")
                            
                            self.historical_candles.append(bar_metrics)
                            
                        # Reset for next bar
                        self.current_trades = []
                        self.bar_start_time = datetime.now()
                        
                except Exception as e:
                    print(f"\n❌ Error processing trade message: {e}")
                    await asyncio.sleep(2)
