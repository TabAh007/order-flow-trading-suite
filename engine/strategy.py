import pandas as pd
from typing import Dict, Any, List

class OrderFlowStrategy:
    """Implements Trader Dale's 5 main setups and risk management rules."""

    def __init__(self, risk_per_trade: float = 0.8, reward_ratio: float = 2.5):
        self.risk_per_trade = risk_per_trade
        self.reward_ratio = reward_ratio

    def evaluate_signals(
        self,
        current_candle: Dict[str, Any],
        prev_candle: Dict[str, Any],
        historical_candles: List[Dict[str, Any]],
        vah: float,
        val: float,
        poc: float,
        vwap: float
    ) -> Dict[str, str]:
        """
        Evaluates signals based on current and previous candle metrics.
        Returns a dict: {"action": "BUY" | "SELL" | "HOLD", "reason": str}
        """
        # Calculate moving averages of volume
        volumes = [c["total_volume"] for c in historical_candles[-20:]] if historical_candles else [current_candle["total_volume"]]
        avg_volume = sum(volumes) / len(volumes) if volumes else 1.0
        
        cur_vol = current_candle["total_volume"]
        cur_delta = current_candle["delta"]
        cur_close = current_candle["close"]
        cur_high = current_candle["high"]
        cur_low = current_candle["low"]
        
        # 1. Volume Cluster Breakout
        is_vol_cluster = cur_vol > avg_volume * 2.2
        if is_vol_cluster and cur_close > vwap:
            # Buying imbalance dominates
            if len(current_candle["buy_imbalances"]) > len(current_candle["sell_imbalances"]):
                return {"action": "BUY", "reason": "Volume Cluster Breakout (Bullish)"}
        elif is_vol_cluster and cur_close < vwap:
            # Selling imbalance dominates
            if len(current_candle["sell_imbalances"]) > len(current_candle["buy_imbalances"]):
                return {"action": "SELL", "reason": "Volume Cluster Breakout (Bearish)"}

        # 2. Imbalance Continuation
        # Check if stacked imbalances exist (e.g. 2+ imbalances in the same direction)
        if len(current_candle["buy_imbalances"]) >= 2 and cur_close > vah:
            return {"action": "BUY", "reason": "Imbalance Continuation (Stacked Buying Imbalance)"}
        if len(current_candle["sell_imbalances"]) >= 2 and cur_close < val:
            return {"action": "SELL", "reason": "Imbalance Continuation (Stacked Selling Imbalance)"}

        # 3. Unfinished Business Reversal
        if current_candle["unfinished_low"] and cur_delta > 0 and cur_close < vwap:
            return {"action": "BUY", "reason": "Unfinished Business Reversal (Low Magnet Test)"}
        if current_candle["unfinished_high"] and cur_delta < 0 and cur_close > vwap:
            return {"action": "SELL", "reason": "Unfinished Business Reversal (High Magnet Test)"}

        # 4. Absorption Reversal (Tight range but high volume)
        price_range = cur_high - cur_low
        prev_ranges = [c["high"] - c["low"] for c in historical_candles[-10:]] if historical_candles else [price_range]
        avg_range = sum(prev_ranges) / len(prev_ranges) if prev_ranges else 1.0
        
        is_absorption = cur_vol > avg_volume * 1.8 and price_range < avg_range * 0.5
        if is_absorption:
            # Price absorbed by passive buyers at low levels
            if cur_close < val and cur_delta > 0:
                return {"action": "BUY", "reason": "Bullish Absorption at Value Area Low"}
            # Price absorbed by passive sellers at high levels
            if cur_close > vah and cur_delta < 0:
                return {"action": "SELL", "reason": "Bearish Absorption at Value Area High"}

        # 5. Momentum Breakout (XRP Extreme Volume)
        is_extreme_volume = cur_vol > avg_volume * 3.5
        if is_extreme_volume and prev_candle:
            if cur_close > prev_candle["high"] and cur_delta > 0:
                return {"action": "BUY", "reason": "Momentum Breakout (Extreme Volume Bullish)"}
            if cur_close < prev_candle["low"] and cur_delta < 0:
                return {"action": "SELL", "reason": "Momentum Breakout (Extreme Volume Bearish)"}

        return {"action": "HOLD", "reason": "No clear setup identified"}
