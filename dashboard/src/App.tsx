import React, { useState, useEffect } from 'react';
import { 
  TrendingUp, 
  TrendingDown, 
  Settings, 
  Activity, 
  RefreshCw, 
  ShieldAlert, 
  CheckCircle, 
  XCircle,
  HelpCircle,
  Percent,
  Play
} from 'lucide-react';
import './App.css';
import {
  fetchKlinesFromBinance,
  calculateVolumeProfile,
  runBacktest
} from './clientEngine';
import type {
  Kline,
  BacktestResults,
  OrderFlowData
} from './clientEngine';

function App() {
  const [symbol, setSymbol] = useState('XRPUSDT');
  const [interval, setIntervalVal] = useState('15m');
  const [limit, setLimit] = useState(150);
  const [imbalanceRatio, setImbalanceRatio] = useState(2.5);
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<BacktestResults | null>(null);
  const [orderFlow, setOrderFlow] = useState<OrderFlowData | null>(null);
  const [connected, setConnected] = useState(true);

  // Fetch initial profile/S&R metrics
  const fetchOrderFlow = async () => {
    try {
      const klines = await fetchKlinesFromBinance(symbol, interval, limit);
      const { poc, vah, val } = calculateVolumeProfile(klines, 0.70);
      setOrderFlow({
        poc,
        vah,
        val,
        klines
      });
      setConnected(true);
    } catch (err) {
      console.error(err);
      setConnected(false);
    }
  };

  useEffect(() => {
    fetchOrderFlow();
  }, [symbol, interval, limit]);

  const handleBacktest = async () => {
    setLoading(true);
    try {
      const klines = await fetchKlinesFromBinance(symbol, interval, limit);
      const results = runBacktest(klines, imbalanceRatio);
      setResults(results);
      setConnected(true);
    } catch (err) {
      console.error(err);
      alert("Error fetching data or running backtest");
      setConnected(false);
    } finally {
      setLoading(false);
    }
  };


  return (
    <div className="dashboard-container">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="logo-section">
          <Activity className="brand-icon" />
          <span className="brand-name">Trader Dale</span>
        </div>
        
        <nav className="nav-menu">
          <div className="section-title">Engine Configuration</div>
          
          <div className="input-group">
            <label>Asset Symbol</label>
            <select value={symbol} onChange={(e) => setSymbol(e.target.value)}>
              <option value="XRPUSDT">XRP / USDT</option>
              <option value="BTCUSDT">BTC / USDT</option>
              <option value="ETHUSDT">ETH / USDT</option>
              <option value="SOLUSDT">SOL / USDT</option>
            </select>
          </div>

          <div className="input-group">
            <label>Timeframe Interval</label>
            <select value={interval} onChange={(e) => setIntervalVal(e.target.value)}>
              <option value="5m">5 Minutes</option>
              <option value="15m">15 Minutes</option>
              <option value="1h">1 Hour</option>
              <option value="4h">4 Hours</option>
            </select>
          </div>

          <div className="input-group">
            <label>Candles Limit ({limit})</label>
            <input 
              type="range" 
              min="50" 
              max="500" 
              value={limit} 
              onChange={(e) => setLimit(parseInt(e.target.value))} 
            />
          </div>

          <div className="input-group">
            <label>Imbalance Ratio ({imbalanceRatio.toFixed(1)}x)</label>
            <input 
              type="range" 
              min="1.5" 
              max="4.0" 
              step="0.1" 
              value={imbalanceRatio} 
              onChange={(e) => setImbalanceRatio(parseFloat(e.target.value))} 
            />
          </div>
          
          <button 
            className="btn-primary" 
            onClick={handleBacktest} 
            disabled={loading}
          >
            {loading ? <RefreshCw className="animate-spin" /> : <Play />}
            {loading ? "Running Backtest..." : "Execute Strategy"}
          </button>
        </nav>
        
        <div className="sidebar-footer">
          <div className={`status-indicator ${connected ? 'status-online' : 'status-offline'}`}>
            <span className="status-dot"></span>
            {connected ? 'Live Engine (Client-Side)' : 'Network Offline'}
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="main-content">
        <header className="header">
          <div>
            <h1>Order Flow Trading Suite</h1>
            <p className="subtitle">High-fidelity backtest engine & footprint diagnostics</p>
          </div>
          <button className="btn-secondary" onClick={fetchOrderFlow}>
            <RefreshCw className="icon-sm" /> Refresh Data
          </button>
        </header>

        {/* Profile Metrics Grid */}
        <section className="metrics-grid">
          <div className="card metric-card">
            <span className="card-label">Point of Control (POC)</span>
            <h2 className="card-value font-mono text-yellow">${orderFlow?.poc.toFixed(4) || "0.00"}</h2>
            <div className="card-hint">Heavy volume level</div>
          </div>
          <div className="card metric-card">
            <span className="card-label">Value Area High (VAH)</span>
            <h2 className="card-value font-mono text-red">${orderFlow?.vah.toFixed(4) || "0.00"}</h2>
            <div className="card-hint">Upper value boundary</div>
          </div>
          <div className="card metric-card">
            <span className="card-label">Value Area Low (VAL)</span>
            <h2 className="card-value font-mono text-green">${orderFlow?.val.toFixed(4) || "0.00"}</h2>
            <div className="card-hint">Lower value boundary</div>
          </div>
        </section>

        {/* Backtest Results Panel */}
        {results && (
          <section className="results-section">
            <h2>🎯 Backtest Diagnostic Report</h2>
            <div className="metrics-grid grid-4">
              <div className="card stats-card">
                <span className="card-label">Net Profit</span>
                <h3 className={`card-value ${results.net_profit >= 0 ? 'text-green' : 'text-red'}`}>
                  ${results.net_profit.toFixed(2)}
                </h3>
              </div>
              <div className="card stats-card">
                <span className="card-label">Win Rate</span>
                <h3 className="card-value text-blue">{results.win_rate.toFixed(1)}%</h3>
              </div>
              <div className="card stats-card">
                <span className="card-label">Total Trades</span>
                <h3 className="card-value">{results.total_trades}</h3>
              </div>
              <div className="card stats-card">
                <span className="card-label">Profit Factor</span>
                <h3 className="card-value text-yellow">{results.profit_factor.toFixed(2)}</h3>
              </div>
            </div>

            {/* Trade Log Table */}
            <div className="card logs-card">
              <h3>📜 Execution Audit Logs</h3>
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Trade Index</th>
                      <th>Exit Trigger</th>
                      <th>Price</th>
                      <th>Profit / Loss</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {results.trades.map((t, idx) => (
                      <tr key={idx}>
                        <td>#{idx + 1}</td>
                        <td>
                          <span className={`badge ${t.type === 'TP' ? 'badge-success' : 'badge-danger'}`}>
                            {t.type === 'TP' ? 'Take Profit' : 'Stop Loss'}
                          </span>
                        </td>
                        <td className="font-mono">${t.price.toFixed(4)}</td>
                        <td className={`font-mono ${t.profit >= 0 ? 'text-green' : 'text-red'}`}>
                          {t.profit >= 0 ? '+' : ''}${t.profit.toFixed(2)}
                        </td>
                        <td>
                          {t.profit >= 0 ? (
                            <CheckCircle className="icon-sm text-green inline-icon" />
                          ) : (
                            <XCircle className="icon-sm text-red inline-icon" />
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </section>
        )}
      </main>
    </div>
  );
}

export default App;
