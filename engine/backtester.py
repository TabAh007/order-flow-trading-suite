import pandas as pd
from typing import List, Dict, Any
from engine.order_flow import OrderFlowCalculator
from engine.strategy import OrderFlowStrategy

class OrderFlowBacktester:
    """Simulates trading on historical candles with footprint calculations."""

    def __init__(self, tick_size: float = 0.0001):
        self.calculator = OrderFlowCalculator(tick_size=tick_size)
        self.strategy = OrderFlowStrategy()

    def run(self, klines: pd.DataFrame) -> Dict[str, Any]:
        """
        Runs backtesting on historical kline data.
        Since tick-level trade history for long periods is extremely large,
        this backtester uses a high-fidelity simulation of footprint data for backtesting speed,
        converting standard klines to simulated footprints.
        """
        if klines.empty:
            return {"error": "No data to backtest."}

        trades_log = []
        position = None  # Current position: {"type": "BUY"|"SELL", "entry": float, "stop": float, "target": float}
        
        # Performance trackers
        balance = 10000.0
        initial_balance = balance
        total_trades = 0
        winning_trades = 0
        losing_trades = 0
        profit_factor = 1.0
        gross_profit = 0.0
        gross_loss = 0.0
        
        historical_processed = []

        for idx in range(1, len(klines)):
            row = klines.iloc[idx]
            prev_row = klines.iloc[idx - 1]
            
            # Reconstruct simulated footprint metrics for the candle
            # (Close-Open volume split approximation as in TradingView script)
            close = row["close"]
            open_val = row["open"]
            high = row["high"]
            low = row["low"]
            volume = row["volume"]
            
            bid_volume = volume * 0.6 if close < open_val else volume * 0.4
            ask_volume = volume * 0.6 if close > open_val else volume * 0.4
            
            # Approximating imbalances and failed auctions
            buy_imbalances = [high] if ask_volume > bid_volume * 2.5 else []
            sell_imbalances = [low] if bid_volume > ask_volume * 2.5 else []
            
            current_candle_metrics = {
                "close": close,
                "open": open_val,
                "high": high,
                "low": low,
                "total_volume": volume,
                "delta": ask_volume - bid_volume,
                "buy_imbalances": buy_imbalances,
                "sell_imbalances": sell_imbalances,
                "unfinished_high": close < high * 0.998,
                "unfinished_low": close > low * 1.002
            }

            # Simulating rolling VAH / VAL / POC / VWAP
            window = klines.iloc[max(0, idx - 20):idx]
            poc, vah, val = self.calculator.calculate_volume_profile(window)
            vwap = window["close"].mean()  # Simple VWAP approximation

            # Check exits for open position
            if position:
                pos_type = position["type"]
                entry = position["entry"]
                stop = position["stop"]
                target = position["target"]
                
                # Check long position exit
                if pos_type == "BUY":
                    if low <= stop:
                        loss = entry - stop
                        balance -= loss * (balance * 0.008 / loss)  # 0.8% risk
                        gross_loss += loss
                        losing_trades += 1
                        trades_log.append({"type": "SL", "price": stop, "profit": -loss})
                        position = None
                    elif high >= target:
                        profit = target - entry
                        balance += profit * (balance * 0.008 / (entry - stop))
                        gross_profit += profit
                        winning_trades += 1
                        trades_log.append({"type": "TP", "price": target, "profit": profit})
                        position = None
                
                # Check short position exit
                elif pos_type == "SELL":
                    if high >= stop:
                        loss = stop - entry
                        balance -= loss * (balance * 0.008 / loss)
                        gross_loss += loss
                        losing_trades += 1
                        trades_log.append({"type": "SL", "price": stop, "profit": -loss})
                        position = None
                    elif low <= target:
                        profit = entry - target
                        balance += profit * (balance * 0.008 / (stop - entry))
                        gross_profit += profit
                        winning_trades += 1
                        trades_log.append({"type": "TP", "price": target, "profit": profit})
                        position = None

            # Evaluate strategy signals if no active position
            if not position and len(historical_processed) > 1:
                prev_candle = historical_processed[-1]
                signal = self.strategy.evaluate_signals(
                    current_candle_metrics,
                    prev_candle,
                    historical_processed,
                    vah, val, poc, vwap
                )
                
                # Calculate dynamic ATR-based Stop Loss
                atr = max(0.0002, (window["high"] - window["low"]).mean())
                
                if signal["action"] == "BUY":
                    stop_price = close - (atr * 1.5)
                    target_price = close + ((close - stop_price) * 2.5)
                    position = {
                        "type": "BUY",
                        "entry": close,
                        "stop": stop_price,
                        "target": target_price,
                        "reason": signal["reason"]
                    }
                    total_trades += 1
                elif signal["action"] == "SELL":
                    stop_price = close + (atr * 1.5)
                    target_price = close - ((stop_price - close) * 2.5)
                    position = {
                        "type": "SELL",
                        "entry": close,
                        "stop": stop_price,
                        "target": target_price,
                        "reason": signal["reason"]
                    }
                    total_trades += 1

            historical_processed.append(current_candle_metrics)

        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else gross_profit

        return {
            "initial_balance": initial_balance,
            "final_balance": balance,
            "net_profit": balance - initial_balance,
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "losing_trades": losing_trades,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "trades": trades_log
        }
