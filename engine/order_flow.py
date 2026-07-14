import numpy as np
import pandas as pd
from typing import Dict, List, Any, Tuple

class OrderFlowCalculator:
    """Calculates footprints, delta, imbalances, and volume profile metrics."""

    def __init__(self, tick_size: float = 0.0001, imbalance_ratio: float = 2.5, volume_cluster_threshold: float = 2.2):
        self.tick_size = tick_size
        self.imbalance_ratio = imbalance_ratio
        self.volume_cluster_threshold = volume_cluster_threshold

    def round_price(self, price: float) -> float:
        return round(price / self.tick_size) * self.tick_size

    def build_footprint(self, trades: List[Dict[str, Any]]) -> Dict[float, Dict[str, float]]:
        """
        Builds a footprint dictionary mapping rounded price levels to bid/ask volumes.
        If 'm' (maker) is True: it's a market sell order (goes to bid).
        If 'm' (maker) is False: it's a market buy order (goes to ask).
        """
        footprint = {}
        for t in trades:
            price = self.round_price(float(t["p"]))
            qty = float(t["q"])
            is_sell = t["m"]  # Buyer is maker -> Market Sell
            
            if price not in footprint:
                footprint[price] = {"bid": 0.0, "ask": 0.0}
            
            if is_sell:
                footprint[price]["bid"] += qty
            else:
                footprint[price]["ask"] += qty
        return footprint

    def calculate_metrics(self, footprint: Dict[float, Dict[str, float]]) -> Dict[str, Any]:
        """
        Calculates delta, POC, imbalances, unfinished business, and absorption for a footprint.
        """
        if not footprint:
            return {
                "delta": 0.0, "poc": None, "total_volume": 0.0,
                "buy_imbalances": [], "sell_imbalances": [],
                "unfinished_high": False, "unfinished_low": False
            }
            
        prices = sorted(footprint.keys())
        total_volume = 0.0
        total_ask = 0.0
        total_bid = 0.0
        max_vol = -1.0
        poc = None
        
        buy_imbalances = []
        sell_imbalances = []
        
        for price in prices:
            bid = footprint[price]["bid"]
            ask = footprint[price]["ask"]
            vol = bid + ask
            total_volume += vol
            total_ask += ask
            total_bid += bid
            
            if vol > max_vol:
                max_vol = vol
                poc = price
                
            # Imbalance check
            if bid > 0 and ask >= bid * self.imbalance_ratio:
                buy_imbalances.append(price)
            if ask > 0 and bid >= ask * self.imbalance_ratio:
                sell_imbalances.append(price)
                
        # Unfinished Business checks (Trader Dale style: non-zero volume at extremes)
        # Proper high has 0 contracts at Ask (right side). Proper low has 0 contracts at Bid (left side).
        unfinished_high = footprint[prices[-1]]["ask"] > 0 if prices else False
        unfinished_low = footprint[prices[0]]["bid"] > 0 if prices else False
        
        return {
            "delta": total_ask - total_bid,
            "total_volume": total_volume,
            "poc": poc,
            "buy_imbalances": buy_imbalances,
            "sell_imbalances": sell_imbalances,
            "unfinished_high": unfinished_high,
            "unfinished_low": unfinished_low
        }

    def calculate_volume_profile(self, klines: pd.DataFrame, value_area_pct: float = 0.70) -> Tuple[float, float, float]:
        """
        Calculates POC, Value Area High (VAH), and Value Area Low (VAL) from klines.
        """
        if klines.empty:
            return 0.0, 0.0, 0.0
            
        # Simulating volume profile from OHLCV
        prices = []
        volumes = []
        for _, row in klines.iterrows():
            steps = 5
            price_range = np.linspace(row["low"], row["high"], steps)
            vol_per_step = row["volume"] / steps
            prices.extend(price_range)
            volumes.extend([vol_per_step] * steps)
            
        df_vp = pd.DataFrame({"price": prices, "volume": volumes})
        df_vp["rounded_price"] = df_vp["price"].apply(self.round_price)
        profile = df_vp.groupby("rounded_price")["volume"].sum().sort_values(ascending=False)
        
        if profile.empty:
            return 0.0, 0.0, 0.0
            
        poc = profile.index[0]
        total_vol = profile.sum()
        target_vol = total_vol * value_area_pct
        
        # Expand around POC to find Value Area
        profile_sorted = profile.sort_index()
        poc_idx = profile_sorted.index.get_loc(poc)
        
        current_vol = profile_sorted.iloc[poc_idx]
        left = poc_idx - 1
        right = poc_idx + 1
        
        while current_vol < target_vol:
            left_vol = profile_sorted.iloc[left] if left >= 0 else 0
            right_vol = profile_sorted.iloc[right] if right < len(profile_sorted) else 0
            
            if left_vol >= right_vol and left >= 0:
                current_vol += left_vol
                left -= 1
            elif right_vol > left_vol and right < len(profile_sorted):
                current_vol += right_vol
                right += 1
            else:
                break
                
        vah = profile_sorted.index[right - 1] if right - 1 < len(profile_sorted) else profile_sorted.index[-1]
        val = profile_sorted.index[left + 1] if left + 1 >= 0 else profile_sorted.index[0]
        
        return poc, vah, val
