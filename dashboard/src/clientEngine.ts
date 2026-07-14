export interface Kline {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface Trade {
  type: string;
  price: number;
  profit: number;
}

export interface BacktestResults {
  initial_balance: number;
  final_balance: number;
  net_profit: number;
  total_trades: number;
  winning_trades: number;
  losing_trades: number;
  win_rate: number;
  profit_factor: number;
  trades: Trade[];
}

export interface OrderFlowData {
  poc: number;
  vah: number;
  val: number;
  klines: Kline[];
}

interface SimulatedCandleMetrics {
  close: number;
  open: number;
  high: number;
  low: number;
  total_volume: number;
  delta: number;
  buy_imbalances: number[];
  sell_imbalances: number[];
  unfinished_high: boolean;
  unfinished_low: boolean;
}

export async function fetchKlinesFromBinance(symbol: string, interval: string, limit: number): Promise<Kline[]> {
  const url = `https://api.binance.com/api/v3/klines?symbol=${symbol.toUpperCase()}&interval=${interval}&limit=${limit}`;
  const resp = await fetch(url);
  if (!resp.ok) {
    throw new Error(`Binance API error: ${resp.statusText}`);
  }
  const data = await resp.json();
  return data.map((d: any) => ({
    timestamp: new Date(d[0]).toISOString(),
    open: parseFloat(d[1]),
    high: parseFloat(d[2]),
    low: parseFloat(d[3]),
    close: parseFloat(d[4]),
    volume: parseFloat(d[5]),
  }));
}

export function calculateVolumeProfile(klines: Kline[], valueAreaPct: number = 0.70, tickSize: number = 0.0001): { poc: number; vah: number; val: number } {
  if (klines.length === 0) return { poc: 0, vah: 0, val: 0 };
  const roundPrice = (price: number) => Math.round(price / tickSize) * tickSize;

  const priceMap: { [key: number]: number } = {};
  for (const row of klines) {
    const steps = 5;
    const low = row.low;
    const high = row.high;
    const volPerStep = row.volume / steps;
    for (let i = 0; i < steps; i++) {
      const price = steps > 1 ? low + (high - low) * (i / (steps - 1)) : low;
      const rounded = parseFloat(roundPrice(price).toFixed(4));
      priceMap[rounded] = (priceMap[rounded] || 0) + volPerStep;
    }
  }

  const sortedPrices = Object.keys(priceMap).map(Number).sort((a, b) => a - b);
  if (sortedPrices.length === 0) return { poc: 0, vah: 0, val: 0 };

  let poc = sortedPrices[0];
  let maxVol = -1;
  let totalVol = 0;
  for (const p of sortedPrices) {
    const vol = priceMap[p];
    totalVol += vol;
    if (vol > maxVol) {
      maxVol = vol;
      poc = p;
    }
  }

  const targetVol = totalVol * valueAreaPct;
  const pocIdx = sortedPrices.indexOf(poc);
  let currentVol = priceMap[poc];
  let left = pocIdx - 1;
  let right = pocIdx + 1;

  while (currentVol < targetVol) {
    const leftVol = left >= 0 ? priceMap[sortedPrices[left]] : 0;
    const rightVol = right < sortedPrices.length ? priceMap[sortedPrices[right]] : 0;

    if (leftVol >= rightVol && left >= 0) {
      currentVol += leftVol;
      left--;
    } else if (rightVol > leftVol && right < sortedPrices.length) {
      currentVol += rightVol;
      right++;
    } else {
      break;
    }
  }

  const vah = sortedPrices[Math.min(right - 1, sortedPrices.length - 1)];
  const val = sortedPrices[Math.max(left + 1, 0)];
  return { poc, vah, val };
}

function evaluateSignals(
  currentCandle: SimulatedCandleMetrics,
  prevCandle: SimulatedCandleMetrics | null,
  historicalCandles: SimulatedCandleMetrics[],
  vah: number,
  val: number,
  poc: number,
  vwap: number
): { action: string; reason: string } {
  const windowSlice = historicalCandles.slice(-20);
  const volumes = windowSlice.length > 0 ? windowSlice.map(c => c.total_volume) : [currentCandle.total_volume];
  const avgVolume = volumes.reduce((a, b) => a + b, 0) / volumes.length;

  const curVol = currentCandle.total_volume;
  const curDelta = currentCandle.delta;
  const curClose = currentCandle.close;
  const curHigh = currentCandle.high;
  const curLow = currentCandle.low;

  // 1. Volume Cluster Breakout
  const isVolCluster = curVol > avgVolume * 2.2;
  if (isVolCluster && curClose > vwap) {
    if (currentCandle.buy_imbalances.length > currentCandle.sell_imbalances.length) {
      return { action: "BUY", reason: "Volume Cluster Breakout (Bullish)" };
    }
  } else if (isVolCluster && curClose < vwap) {
    if (currentCandle.sell_imbalances.length > currentCandle.buy_imbalances.length) {
      return { action: "SELL", reason: "Volume Cluster Breakout (Bearish)" };
    }
  }

  // 2. Imbalance Continuation
  if (currentCandle.buy_imbalances.length >= 2 && curClose > vah) {
    return { action: "BUY", reason: "Imbalance Continuation (Stacked Buying Imbalance)" };
  }
  if (currentCandle.sell_imbalances.length >= 2 && curClose < val) {
    return { action: "SELL", reason: "Imbalance Continuation (Stacked Selling Imbalance)" };
  }

  // 3. Unfinished Business Reversal
  if (currentCandle.unfinished_low && curDelta > 0 && curClose < vwap) {
    return { action: "BUY", reason: "Unfinished Business Reversal (Low Magnet Test)" };
  }
  if (currentCandle.unfinished_high && curDelta < 0 && curClose > vwap) {
    return { action: "SELL", reason: "Unfinished Business Reversal (High Magnet Test)" };
  }

  // 4. Absorption Reversal
  const priceRange = curHigh - curLow;
  const prevRanges = historicalCandles.slice(-10).map(c => c.high - c.low);
  const avgRange = prevRanges.length > 0 ? prevRanges.reduce((a, b) => a + b, 0) / prevRanges.length : priceRange;

  const isAbsorption = curVol > avgVolume * 1.8 && priceRange < avgRange * 0.5;
  if (isAbsorption) {
    if (curClose < val && curDelta > 0) {
      return { action: "BUY", reason: "Bullish Absorption at Value Area Low" };
    }
    if (curClose > vah && curDelta < 0) {
      return { action: "SELL", reason: "Bearish Absorption at Value Area High" };
    }
  }

  // 5. Momentum Breakout
  const isExtremeVolume = curVol > avgVolume * 3.5;
  if (isExtremeVolume && prevCandle) {
    if (curClose > prevCandle.high && curDelta > 0) {
      return { action: "BUY", reason: "Momentum Breakout (Extreme Volume Bullish)" };
    }
    if (curClose < prevCandle.low && curDelta < 0) {
      return { action: "SELL", reason: "Momentum Breakout (Extreme Volume Bearish)" };
    }
  }

  return { action: "HOLD", reason: "No clear setup identified" };
}

export function runBacktest(klines: Kline[], imbalanceRatio: number = 2.5, tickSize: number = 0.0001): BacktestResults {
  if (klines.length === 0) {
    return {
      initial_balance: 10000,
      final_balance: 10000,
      net_profit: 0,
      total_trades: 0,
      winning_trades: 0,
      losing_trades: 0,
      win_rate: 0,
      profit_factor: 1,
      trades: [],
    };
  }

  const tradesLog: Trade[] = [];
  let position: { type: string; entry: number; stop: number; target: number } | null = null;

  let balance = 10000.0;
  const initialBalance = balance;
  let totalTrades = 0;
  let winningTrades = 0;
  let losingTrades = 0;
  let grossProfit = 0.0;
  let grossLoss = 0.0;

  const historicalProcessed: SimulatedCandleMetrics[] = [];

  for (let idx = 1; idx < klines.length; idx++) {
    const row = klines[idx];
    const close = row.close;
    const openVal = row.open;
    const high = row.high;
    const low = row.low;
    const volume = row.volume;

    const bidVolume = close < openVal ? volume * 0.6 : volume * 0.4;
    const askVolume = close > openVal ? volume * 0.6 : volume * 0.4;

    const buyImbalances = askVolume > bidVolume * imbalanceRatio ? [high] : [];
    const sellImbalances = bidVolume > askVolume * imbalanceRatio ? [low] : [];

    const currentCandleMetrics: SimulatedCandleMetrics = {
      close,
      open: openVal,
      high,
      low,
      total_volume: volume,
      delta: askVolume - bidVolume,
      buy_imbalances: buyImbalances,
      sell_imbalances: sellImbalances,
      unfinished_high: close < high * 0.998,
      unfinished_low: close > low * 1.002,
    };

    // Calculate Volume Profile over window
    const windowSlice = klines.slice(Math.max(0, idx - 20), idx);
    const { poc, vah, val } = calculateVolumeProfile(windowSlice, 0.70, tickSize);
    const vwap = windowSlice.reduce((sum, k) => sum + k.close, 0) / (windowSlice.length || 1);

    // Check position exits
    if (position) {
      const { type: posType, entry, stop, target } = position;
      if (posType === "BUY") {
        if (low <= stop) {
          const loss = entry - stop;
          balance -= loss * (balance * 0.008 / (loss || 0.0001));
          grossLoss += loss;
          losingTrades++;
          tradesLog.push({ type: "SL", price: stop, profit: -loss });
          position = null;
        } else if (high >= target) {
          const profit = target - entry;
          balance += profit * (balance * 0.008 / ((entry - stop) || 0.0001));
          grossProfit += profit;
          winningTrades++;
          tradesLog.push({ type: "TP", price: target, profit });
          position = null;
        }
      } else if (posType === "SELL") {
        if (high >= stop) {
          const loss = stop - entry;
          balance -= loss * (balance * 0.008 / (loss || 0.0001));
          grossLoss += loss;
          losingTrades++;
          tradesLog.push({ type: "SL", price: stop, profit: -loss });
          position = null;
        } else if (low <= target) {
          const profit = entry - target;
          balance += profit * (balance * 0.008 / ((stop - entry) || 0.0001));
          grossProfit += profit;
          winningTrades++;
          tradesLog.push({ type: "TP", price: target, profit });
          position = null;
        }
      }
    }

    // Evaluate signals if no position
    if (!position && historicalProcessed.length > 1) {
      const prevCandle = historicalProcessed[historicalProcessed.length - 1];
      const signal = evaluateSignals(
        currentCandleMetrics,
        prevCandle,
        historicalProcessed,
        vah,
        val,
        poc,
        vwap
      );

      const highLowDiffs = windowSlice.map(k => k.high - k.low);
      const atr = Math.max(0.0002, highLowDiffs.length > 0 ? highLowDiffs.reduce((a, b) => a + b, 0) / highLowDiffs.length : 0.0002);

      if (signal.action === "BUY") {
        const stopPrice = close - atr * 1.5;
        const targetPrice = close + (close - stopPrice) * 2.5;
        position = {
          type: "BUY",
          entry: close,
          stop: stopPrice,
          target: targetPrice,
        };
        totalTrades++;
      } else if (signal.action === "SELL") {
        const stopPrice = close + atr * 1.5;
        const targetPrice = close - (stopPrice - close) * 2.5;
        position = {
          type: "SELL",
          entry: close,
          stop: stopPrice,
          target: targetPrice,
        };
        totalTrades++;
      }
    }

    historicalProcessed.push(currentCandleMetrics);
  }

  const winRate = totalTrades > 0 ? (winningTrades / totalTrades) * 100 : 0.0;
  const profitFactor = grossLoss > 0 ? grossProfit / grossLoss : grossProfit;

  return {
    initial_balance: initialBalance,
    final_balance: balance,
    net_profit: balance - initialBalance,
    total_trades: totalTrades,
    winning_trades: winningTrades,
    losing_trades: losingTrades,
    win_rate: winRate,
    profit_factor: profitFactor,
    trades: tradesLog,
  };
}
