import argparse
import asyncio
from engine.data_fetcher import BinanceDataFetcher
from engine.backtester import OrderFlowBacktester
from engine.monitor import OrderFlowMonitor

def run_backtest(symbol: str, interval: str, limit: int):
    print(f"📥 Fetching historical data for {symbol} ({interval}, {limit} candles)...")
    fetcher = BinanceDataFetcher(symbol=symbol)
    try:
        klines = fetcher.fetch_klines(interval=interval, limit=limit)
        print("✅ Data successfully loaded. Running backtest...")
        
        backtester = OrderFlowBacktester()
        results = backtester.run(klines)
        
        print("\n📈 BACKTEST RESULTS:")
        print(f"--------------------------------------------------")
        print(f"🪙 Symbol: {symbol.upper()}")
        print(f"💵 Initial Balance: ${results['initial_balance']:.2f}")
        print(f"💰 Final Balance: ${results['final_balance']:.2f}")
        print(f"💵 Net Profit: ${results['net_profit']:.2f}")
        print(f"📊 Total Trades: {results['total_trades']}")
        print(f"🟢 Winning Trades: {results['winning_trades']}")
        print(f"🔴 Losing Trades: {results['losing_trades']}")
        print(f"🏆 Win Rate: {results['win_rate']:.2f}%")
        print(f"🔑 Profit Factor: {results['profit_factor']:.2f}")
        print(f"--------------------------------------------------")
    except Exception as e:
        print(f"❌ Backtest failed: {e}")

def main():
    parser = argparse.ArgumentParser(description="Standalone Python Order Flow Engine")
    parser.add_argument("--mode", choices=["backtest", "live"], default="backtest", help="Trading mode: backtest or live monitoring")
    parser.add_argument("--symbol", default="XRPUSDT", help="Crypto pair ticker (default: XRPUSDT)")
    parser.add_argument("--interval", default="15m", help="Timeframe interval for backtest (default: 15m)")
    parser.add_argument("--limit", type=int, default=150, help="Number of candles for backtest (default: 150)")
    parser.add_argument("--timeframe", type=int, default=60, help="Live monitoring bar timeframe in seconds (default: 60)")

    args = parser.parse_args()

    if args.mode == "backtest":
        run_backtest(args.symbol, args.interval, args.limit)
    elif args.mode == "live":
        monitor = OrderFlowMonitor(symbol=args.symbol, timeframe_seconds=args.timeframe)
        try:
            asyncio.run(monitor.start())
        except KeyboardInterrupt:
            print("\n🔌 Disconnecting from WebSocket. Exiting...")

if __name__ == "__main__":
    main()
