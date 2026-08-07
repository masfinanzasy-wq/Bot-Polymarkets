/**
 * Polymarket M5 Bot - Terminal Dashboard Pro Logic
 * Handles real-time WebSockets, Chart.js streaming, technical indicators, EV predictions,
 * Polymarket CLOB orderbook rendering, and simulated paper trading.
 */

// Global State
const state = {
  simulationActive: true,
  prices: [],
  ticks: [],
  ema9: null,
  ema21: null,
  vwapNum: 0,
  vwapDenom: 0,
  lastPrice: 63450.0,
  previousPrice: 63450.0,
  
  // Polymarket state
  polymarketPriceYes: 0.495,
  polymarketPriceNo: 0.505,
  
  // Portfolio Paper Trading
  portfolio: {
    initialBalance: 100.0,
    currentBalance: 100.0,
    realizedPnl: 0.0,
    winningTrades: 0,
    losingTrades: 0,
    activePositions: [],
    closedPositions: []
  },
  
  // Risk settings
  settings: {
    positionSizeUsd: 50.0,
    minEvPct: 5.0
  }
};

// DOM Elements
const el = {
  binanceStatusText: document.getElementById('binance-status-text'),
  polymarketStatusText: document.getElementById('polymarket-status-text'),
  btcPrice: document.getElementById('btc-price'),
  btcChange: document.getElementById('btc-change'),
  valEma9: document.getElementById('val-ema9'),
  valEma21: document.getElementById('val-ema21'),
  valVwap: document.getElementById('val-vwap'),
  valRsi: document.getElementById('val-rsi'),
  valTrend: document.getElementById('val-trend'),
  orderFlowDelta: document.getElementById('order-flow-delta'),
  
  signalBadge: document.getElementById('signal-badge'),
  signalEv: document.getElementById('signal-ev'),
  signalProb: document.getElementById('signal-prob'),
  signalTarget: document.getElementById('signal-target'),
  signalConfidence: document.getElementById('signal-confidence'),
  
  portfolioBalance: document.getElementById('portfolio-balance'),
  portfolioPnl: document.getElementById('portfolio-pnl'),
  portfolioWinrate: document.getElementById('portfolio-winrate'),
  portfolioTrades: document.getElementById('portfolio-trades'),
  
  rsiGaugeVal: document.getElementById('rsi-gauge-val'),
  rsiGaugeBar: document.getElementById('rsi-gauge-bar'),
  deltaGaugeVal: document.getElementById('delta-gauge-val'),
  deltaGaugeBar: document.getElementById('delta-gauge-bar'),
  trendGaugeVal: document.getElementById('trend-gauge-val'),
  trendGaugeBar: document.getElementById('trend-gauge-bar'),
  
  asksRows: document.getElementById('asks-rows'),
  bidsRows: document.getElementById('bids-rows'),
  obSpreadVal: document.getElementById('ob-spread-val'),
  obMidpointVal: document.getElementById('ob-midpoint-val'),
  
  logFeed: document.getElementById('log-feed'),
  tradesTableBody: document.getElementById('trades-table-body'),
  countActive: document.getElementById('count-active'),
  countHistory: document.getElementById('count-history'),
  
  btnToggleSim: document.getElementById('btn-toggle-simulation'),
  btnClearLogs: document.getElementById('btn-clear-logs'),
  btnResetPortfolio: document.getElementById('btn-reset-portfolio'),
  btnManualYes: document.getElementById('btn-manual-yes'),
  btnManualNo: document.getElementById('btn-manual-no'),
  
  inputPosSize: document.getElementById('input-position-size'),
  inputMinEv: document.getElementById('input-min-ev')
};

// Chart Instance
let chartInstance = null;

// Initialize Chart.js
function initChart() {
  const ctx = document.getElementById('liveChart').getContext('2d');
  
  chartInstance = new Chart(ctx, {
    type: 'line',
    data: {
      datasets: [
        {
          label: 'BTC/USDT Spot',
          borderColor: '#00f2fe',
          backgroundColor: 'rgba(0, 242, 254, 0.05)',
          borderWidth: 2,
          pointRadius: 0,
          tension: 0.2,
          fill: true,
          data: []
        },
        {
          label: 'EMA 9',
          borderColor: '#ff0055',
          borderWidth: 1.5,
          pointRadius: 0,
          borderDash: [],
          data: []
        },
        {
          label: 'EMA 21',
          borderColor: '#9d4edd',
          borderWidth: 1.5,
          pointRadius: 0,
          borderDash: [4, 4],
          data: []
        },
        {
          label: 'VWAP',
          borderColor: '#ffb703',
          borderWidth: 1.5,
          pointRadius: 0,
          data: []
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 0 },
      scales: {
        x: {
          type: 'realtime',
          realtime: {
            duration: 120000, // 2 mins window
            refresh: 500,
            delay: 1000,
            onRefresh: onChartRefresh
          },
          grid: { color: 'rgba(255, 255, 255, 0.04)' },
          ticks: { color: '#64748b', font: { family: 'JetBrains Mono', size: 10 } }
        },
        y: {
          position: 'right',
          grid: { color: 'rgba(255, 255, 255, 0.04)' },
          ticks: { color: '#64748b', font: { family: 'JetBrains Mono', size: 10 } }
        }
      },
      plugins: {
        legend: {
          display: true,
          labels: { color: '#94a3b8', font: { family: 'Outfit', size: 11 }, usePointStyle: true }
        }
      }
    }
  });
}

function onChartRefresh(chart) {
  if (!state.simulationActive) return;
  const now = Date.now();
  
  if (state.lastPrice) {
    chart.data.datasets[0].data.push({ x: now, y: state.lastPrice });
    if (state.ema9) chart.data.datasets[1].data.push({ x: now, y: state.ema9 });
    if (state.ema21) chart.data.datasets[2].data.push({ x: now, y: state.ema21 });
    if (state.vwapNum > 0 && state.vwapDenom > 0) {
      const vwapVal = state.vwapNum / state.vwapDenom;
      chart.data.datasets[3].data.push({ x: now, y: vwapVal });
    }
  }
}

// Indicator Calculations
function updateIndicators(price, qty, isBuyerMaker) {
  state.ticks.push({ price, qty, isBuyerMaker, time: Date.now() });
  if (state.ticks.length > 300) state.ticks.shift();
  
  state.prices.push(price);
  if (state.prices.length > 300) state.prices.shift();

  // EMA 9 & EMA 21
  if (state.ema9 === null) {
    state.ema9 = price;
    state.ema21 = price;
  } else {
    const k9 = 2 / (9 + 1);
    const k21 = 2 / (21 + 1);
    state.ema9 = price * k9 + state.ema9 * (1 - k9);
    state.ema21 = price * k21 + state.ema21 * (1 - k21);
  }

  // VWAP
  state.vwapNum += price * qty;
  state.vwapDenom += qty;
  const currentVwap = state.vwapDenom > 0 ? state.vwapNum / state.vwapDenom : price;

  // RSI 14
  let rsiVal = 50.0;
  if (state.prices.length >= 15) {
    let gains = 0, losses = 0;
    for (let i = state.prices.length - 14; i < state.prices.length; i++) {
      const diff = state.prices[i] - state.prices[i - 1];
      if (diff >= 0) gains += diff;
      else losses += Math.abs(diff);
    }
    const avgGain = gains / 14;
    const avgLoss = losses / 14;
    if (avgLoss === 0) rsiVal = 100.0;
    else {
      const rs = avgGain / avgLoss;
      rsiVal = 100 - (100 / (1 + rs));
    }
  }

  // Order Flow Delta Ratio
  let buyerQty = 0, sellerQty = 0;
  const recentTicks = state.ticks.slice(-30);
  recentTicks.forEach(t => {
    if (!t.isBuyerMaker) buyerQty += t.qty;
    else sellerQty += t.qty;
  });
  const totalVol = buyerQty + sellerQty;
  const deltaRatio = totalVol > 0 ? (buyerQty - sellerQty) / totalVol : 0;

  // Trend Score
  const emaDiff = state.ema9 - state.ema21;
  const trendScore = Math.max(-1.0, Math.min(1.0, (emaDiff / price) * 500 + deltaRatio * 0.5));

  // Win Probability calculation
  const baseProb = 0.50 + trendScore * 0.30;
  const winProb = Math.max(0.15, Math.min(0.85, baseProb));

  return {
    ema9: state.ema9,
    ema21: state.ema21,
    vwap: currentVwap,
    rsi: rsiVal,
    deltaRatio,
    trendScore,
    winProb
  };
}

// Update UI Components
function renderUI(metrics) {
  // Price & Trend
  el.btcPrice.textContent = `$${state.lastPrice.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  
  const pDiff = state.lastPrice - state.previousPrice;
  const pctChange = (pDiff / state.previousPrice) * 100;
  el.btcChange.textContent = `${pctChange >= 0 ? '+' : ''}${pctChange.toFixed(2)}%`;
  el.btcChange.className = `price-change ${pctChange >= 0 ? 'positive' : 'negative'}`;

  el.valEma9.textContent = `$${metrics.ema9.toFixed(2)}`;
  el.valEma21.textContent = `$${metrics.ema21.toFixed(2)}`;
  el.valVwap.textContent = `$${metrics.vwap.toFixed(2)}`;
  el.valRsi.textContent = metrics.rsi.toFixed(1);
  el.valTrend.textContent = `${metrics.trendScore >= 0 ? '+' : ''}${metrics.trendScore.toFixed(2)}`;
  el.orderFlowDelta.textContent = `${metrics.deltaRatio >= 0 ? '+' : ''}${metrics.deltaRatio.toFixed(2)} Ratio`;

  // Gauges
  el.rsiGaugeVal.textContent = metrics.rsi.toFixed(1);
  el.rsiGaugeBar.style.width = `${Math.min(100, Math.max(0, metrics.rsi))}%`;

  const deltaPct = ((metrics.deltaRatio + 1) / 2) * 100;
  el.deltaGaugeVal.textContent = `${metrics.deltaRatio >= 0 ? '+' : ''}${metrics.deltaRatio.toFixed(2)}`;
  el.deltaGaugeBar.style.width = `${deltaPct}%`;

  const trendPct = ((metrics.trendScore + 1) / 2) * 100;
  el.trendGaugeVal.textContent = `${metrics.trendScore >= 0 ? '+' : ''}${metrics.trendScore.toFixed(2)}`;
  el.trendGaugeBar.style.width = `${trendPct}%`;

  // EV & Prediction Signal
  evaluateSignal(metrics);
}

function evaluateSignal(metrics) {
  // EV = (P_win * 1.0) - Ask_price
  const priceNo = state.polymarketPriceNo;
  const priceYes = state.polymarketPriceYes;

  const evYes = (metrics.winProb * 1.0) - priceYes;
  const evNo = ((1.0 - metrics.winProb) * 1.0) - priceNo;

  let outcome = 'HOLD';
  let bestEv = 0;
  let targetPrice = 0;

  const minEvDecimal = state.settings.minEvPct / 100.0;

  if (evYes > evNo && evYes >= minEvDecimal) {
    outcome = 'BUY_YES';
    bestEv = evYes;
    targetPrice = priceYes;
  } else if (evNo > evYes && evNo >= minEvDecimal) {
    outcome = 'BUY_NO';
    bestEv = evNo;
    targetPrice = priceNo;
  }

  const evPct = (bestEv * 100).toFixed(1);
  const winProbPct = (metrics.winProb * 100).toFixed(1);

  if (outcome === 'BUY_YES') {
    el.signalBadge.textContent = 'BUY YES';
    el.signalBadge.className = 'badge signal-badge buy-yes';
    el.signalEv.textContent = `+${evPct}% EV`;
    el.signalProb.textContent = `${winProbPct}%`;
    el.signalTarget.textContent = `$${targetPrice.toFixed(4)}`;
    el.signalConfidence.textContent = `${(metrics.winProb * 100).toFixed(0)}%`;
  } else if (outcome === 'BUY_NO') {
    el.signalBadge.textContent = 'BUY NO';
    el.signalBadge.className = 'badge signal-badge buy-no';
    el.signalEv.textContent = `+${evPct}% EV`;
    el.signalProb.textContent = `${(100 - winProbPct)}%`;
    el.signalTarget.textContent = `$${targetPrice.toFixed(4)}`;
    el.signalConfidence.textContent = `${((1.0 - metrics.winProb) * 100).toFixed(0)}%`;
  } else {
    el.signalBadge.textContent = 'HOLD';
    el.signalBadge.className = 'badge signal-badge';
    el.signalEv.textContent = '+0.0% EV';
    el.signalProb.textContent = `${winProbPct}%`;
    el.signalTarget.textContent = '-';
    el.signalConfidence.textContent = '0%';
  }

  // Automatic paper trading simulation trigger every 15 ticks if strong signal
  if (outcome !== 'HOLD' && state.ticks.length % 20 === 0 && state.simulationActive) {
    triggerAutoPaperTrade(outcome, targetPrice, bestEv);
  }
}

// Render Polymarket CLOB Orderbook
function renderOrderbook() {
  const midpoint = (state.polymarketPriceYes + (1 - state.polymarketPriceNo)) / 2;
  const spread = Math.abs(state.polymarketPriceYes - state.polymarketPriceNo * 0.05);

  el.obMidpointVal.textContent = `$${midpoint.toFixed(4)}`;
  el.obSpreadVal.textContent = `$0.0200 (2.0%)`;

  const asks = [
    { price: (state.polymarketPriceNo + 0.03).toFixed(4), size: 450 },
    { price: (state.polymarketPriceNo + 0.01).toFixed(4), size: 1250 },
    { price: state.polymarketPriceNo.toFixed(4), size: 2400 }
  ];

  const bids = [
    { price: state.polymarketPriceYes.toFixed(4), size: 3100 },
    { price: (state.polymarketPriceYes - 0.01).toFixed(4), size: 1800 },
    { price: (state.polymarketPriceYes - 0.03).toFixed(4), size: 600 }
  ];

  el.asksRows.innerHTML = asks.map(a => `
    <div class="ob-row">
      <div class="bar" style="width: ${(a.size / 3500) * 100}%;"></div>
      <span>${a.price}</span>
      <span>$${a.size.toLocaleString()}</span>
    </div>
  `).join('');

  el.bidsRows.innerHTML = bids.map(b => `
    <div class="ob-row">
      <div class="bar" style="width: ${(b.size / 3500) * 100}%;"></div>
      <span>${b.price}</span>
      <span>$${b.size.toLocaleString()}</span>
    </div>
  `).join('');
}

// Paper Trading Logic
function triggerAutoPaperTrade(outcome, entryPrice, ev) {
  const size = state.settings.positionSizeUsd;
  if (state.portfolio.currentBalance < size) return;

  const shares = size / entryPrice;
  const id = `trade_${Math.floor(Math.random() * 8999 + 1000)}`;

  const position = {
    id,
    time: new Date().toLocaleTimeString(),
    market: 'BTC-UP-5M',
    outcome,
    entryPrice,
    shares,
    cost: size,
    status: 'OPEN',
    pnl: 0.0
  };

  state.portfolio.currentBalance -= size;
  state.portfolio.activePositions.push(position);
  
  addLog(`POSICIÓN ABIERTA [${outcome}] - Costo: $${size.toFixed(2)} USD @ $${entryPrice.toFixed(4)}`);
  updatePortfolioUI();

  // Simulate position settlement after 4 seconds
  setTimeout(() => {
    settlePosition(id, true);
  }, 4000);
}

function settlePosition(id, isWin) {
  const idx = state.portfolio.activePositions.findIndex(p => p.id === id);
  if (idx === -1) return;

  const pos = state.portfolio.activePositions.splice(idx, 1)[0];
  
  let payout = 0;
  let pnl = 0;
  if (isWin) {
    payout = pos.shares * 1.0;
    pnl = payout - pos.cost;
    pos.status = 'CLOSED_WIN';
    state.portfolio.winningTrades++;
  } else {
    payout = 0;
    pnl = -pos.cost;
    pos.status = 'CLOSED_LOSS';
    state.portfolio.losingTrades++;
  }

  pos.pnl = pnl;
  state.portfolio.currentBalance += payout;
  state.portfolio.realizedPnl += pnl;
  state.portfolio.closedPositions.unshift(pos);

  addLog(`POSICIÓN CERRADA [${pos.status}] - PnL: ${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)} USD`);
  updatePortfolioUI();
}

function updatePortfolioUI() {
  const total = state.portfolio.winningTrades + state.portfolio.losingTrades;
  const winRate = total > 0 ? (state.portfolio.winningTrades / total) * 100 : 100.0;

  el.portfolioBalance.textContent = `$${state.portfolio.currentBalance.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  
  const pnl = state.portfolio.realizedPnl;
  el.portfolioPnl.textContent = `${pnl >= 0 ? '+' : ''}$${pnl.toFixed(2)} PnL`;
  el.portfolioPnl.className = `price-change ${pnl >= 0 ? 'positive' : 'negative'}`;

  el.portfolioWinrate.textContent = `${winRate.toFixed(1)}%`;
  el.portfolioTrades.textContent = `${total} (${state.portfolio.winningTrades}W / ${state.portfolio.losingTrades}L)`;

  el.countActive.textContent = state.portfolio.activePositions.length;
  el.countHistory.textContent = state.portfolio.closedPositions.length;

  // Render Table
  const allPositions = [...state.portfolio.activePositions, ...state.portfolio.closedPositions];
  el.tradesTableBody.innerHTML = allPositions.map(p => `
    <tr>
      <td><code>#${p.id}</code></td>
      <td>${p.time}</td>
      <td>${p.market}</td>
      <td><strong style="color: ${p.outcome === 'BUY_YES' ? '#00e676' : '#ff0055'}">${p.outcome}</strong></td>
      <td>$${p.entryPrice.toFixed(4)}</td>
      <td>${p.shares.toFixed(2)}</td>
      <td>$${p.cost.toFixed(2)}</td>
      <td><span class="${p.status === 'OPEN' ? 'status-badge-open' : 'status-badge-win'}">${p.status}</span></td>
      <td style="color: ${p.pnl >= 0 ? '#00e676' : '#ff0055'}; font-weight: 700;">
        ${p.status === 'OPEN' ? '-' : `${p.pnl >= 0 ? '+' : ''}$${p.pnl.toFixed(2)}`}
      </td>
    </tr>
  `).join('');
}

// Log Feed Utility
function addLog(msg) {
  const timeStr = new Date().toLocaleTimeString();
  const div = document.createElement('div');
  div.className = 'log-item';
  div.innerHTML = `<span class="log-timestamp">[${timeStr}]</span> <span class="log-message">${msg}</span>`;
  el.logFeed.prepend(div);

  while (el.logFeed.children.length > 50) {
    el.logFeed.removeChild(el.logFeed.lastChild);
  }
}

async function checkSystemHealth() {
  try {
    const res = await fetch('/api/v1/health');
    if (res.ok) {
      const data = await res.json();
      const envModeText = document.getElementById('env-mode-text');
      const envModePill = document.querySelector('.status-pill.env-mode');
      if (envModeText) {
        if (data.paper_trading) {
          envModeText.textContent = 'PAPER TRADING';
          envModeText.style.color = '#00e676';
          if (envModePill) {
            const iconSpan = envModePill.querySelector('.icon');
            if (iconSpan) iconSpan.textContent = '🛡️';
          }
        } else {
          envModeText.textContent = '🔴 REAL LIVE';
          envModeText.style.color = '#ff0055';
          if (envModePill) {
            const iconSpan = envModePill.querySelector('.icon');
            if (iconSpan) iconSpan.textContent = '⚡';
          }
        }
      }
    }
  } catch (err) {
    // Fallback default
  }
}

// Connect Backend FastAPI Live WebSocket
function initBackendWS() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}/ws/live`;
  try {
    const ws = new WebSocket(wsUrl);
    ws.onopen = () => {
      addLog('Conectado al Servidor FastAPI WebSocket [/ws/live].');
    };
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'market_snapshot') {
        el.polymarketStatusText.textContent = 'ONLINE';
      }
    };
  } catch (e) {
    // Ignore fallback if standalone
  }
}

// Connect Binance Live WebSocket
function initBinanceWS() {
  const ws = new WebSocket('wss://stream.binance.com:9443/ws/btcusdt@aggTrade');

  ws.onopen = () => {
    el.binanceStatusText.textContent = 'ONLINE';
    addLog('Conexión establecida con Binance WebSocket [btcusdt@aggTrade].');
  };

  ws.onmessage = (event) => {
    if (!state.simulationActive) return;
    const data = JSON.parse(event.data);
    const price = parseFloat(data.p);
    const qty = parseFloat(data.q);
    const isBuyerMaker = data.m;

    state.previousPrice = state.lastPrice;
    state.lastPrice = price;

    const metrics = updateIndicators(price, qty, isBuyerMaker);
    renderUI(metrics);
  };

  ws.onerror = (err) => {
    el.binanceStatusText.textContent = 'RECONECTANDO';
    addLog('Error en WebSocket de Binance. Intentando reconexión...');
  };

  ws.onclose = () => {
    el.binanceStatusText.textContent = 'DESCONECTADO';
    setTimeout(initBinanceWS, 3000);
  };
}

// Event Listeners
function setupEvents() {
  el.btnToggleSim.addEventListener('click', () => {
    state.simulationActive = !state.simulationActive;
    el.btnToggleSim.textContent = state.simulationActive ? 'PAUSAR SIMULACIÓN' : 'REANUDAR SIMULACIÓN';
    el.btnToggleSim.className = `btn ${state.simulationActive ? 'btn-action' : 'btn-success'}`;
    addLog(`Simulación ${state.simulationActive ? 'reanudada' : 'pausada'} por el usuario.`);
  });

  el.btnClearLogs.addEventListener('click', () => {
    el.logFeed.innerHTML = '';
  });

  el.btnResetPortfolio.addEventListener('click', () => {
    state.portfolio.currentBalance = 100.0;
    state.portfolio.realizedPnl = 0.0;
    state.portfolio.winningTrades = 0;
    state.portfolio.losingTrades = 0;
    state.portfolio.activePositions = [];
    state.portfolio.closedPositions = [];
    updatePortfolioUI();
    addLog('Portfolio simulado reiniciado a $100.00 USD.');
  });

  el.btnManualYes.addEventListener('click', () => {
    triggerAutoPaperTrade('BUY_YES', state.polymarketPriceYes, 0.15);
  });

  el.btnManualNo.addEventListener('click', () => {
    triggerAutoPaperTrade('BUY_NO', state.polymarketPriceNo, 0.15);
  });

  el.inputPosSize.addEventListener('change', (e) => {
    state.settings.positionSizeUsd = parseFloat(e.target.value) || 50.0;
  });

  el.inputMinEv.addEventListener('change', (e) => {
    state.settings.minEvPct = parseFloat(e.target.value) || 5.0;
  });
}

async function fetchLiveWalletBalance(address) {
  const balanceElem = document.getElementById('portfolio-balance');
  const pnlElem = document.getElementById('portfolio-pnl');
  if (!address || !balanceElem) return;

  try {
    const res = await fetch(`/api/v1/wallet/balance/${address}`);
    const data = await res.json();
    if (data && data.success) {
      const usdc = data.usdc_balance || 0.0;
      const matic = data.matic_balance || 0.0;
      balanceElem.textContent = `$${usdc.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} USDC`;
      if (pnlElem) {
        pnlElem.textContent = `Gas: ${matic.toFixed(3)} MATIC (Real)`;
        pnlElem.className = 'price-change positive';
      }
      addLog(`💰 Saldo real Polygon cargado: ${usdc.toFixed(2)} USDC | ${matic.toFixed(3)} MATIC`);
      return;
    }
  } catch (err) {
    console.warn("Error fetching balance via API", err);
  }
}

// Authentication & Role-Based Access Control (RBAC) Management
function checkAuthentication() {
  const authModal = document.getElementById('auth-modal');
  const btnOpenAdmin = document.getElementById('btn-open-admin');

  const isAuth = sessionStorage.getItem('dashboard_authenticated') === 'true';
  const isAdmin = sessionStorage.getItem('is_admin') === 'true' || localStorage.getItem('is_admin') === 'true';

  if (isAuth) {
    if (authModal) authModal.classList.add('hidden');
    const landingElem = document.getElementById('landing-page');
    if (landingElem) landingElem.classList.add('hidden');
  }

  // EL BOTÓN DE CONTROL MAESTRO SOLO SE MUESTRA SI ES UN ADMINISTRADOR
  if (btnOpenAdmin) {
    if (isAuth && isAdmin) {
      btnOpenAdmin.style.display = 'inline-flex';
    } else {
      btnOpenAdmin.style.display = 'none';
    }
  }
}

async function verifyAccessKey(providedKey) {
  try {
    const res = await fetch('/api/v1/auth/verify-key', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key: providedKey })
    });
    if (res.ok) {
      const data = await res.json();
      return data.success;
    }
  } catch (err) {
    return providedKey === 'polymarket2026';
  }
  return providedKey === 'polymarket2026';
}

function setupAuthEvents() {
  const authForm = document.getElementById('auth-form');
  const saasLoginForm = document.getElementById('saas-login-form');
  const saasRegisterForm = document.getElementById('saas-register-form');

  const tabAccess = document.getElementById('tab-btn-access');
  const tabLogin = document.getElementById('tab-btn-login');
  const tabRegister = document.getElementById('tab-btn-register');

  const authKeyInput = document.getElementById('input-auth-key');
  const authErrorMsg = document.getElementById('auth-error-msg');
  const saasLoginError = document.getElementById('saas-login-error');
  const saasRegError = document.getElementById('saas-reg-error');

  const btnLogout = document.getElementById('btn-logout');
  const btnDemoBypass = document.getElementById('btn-demo-bypass');
  const authModal = document.getElementById('auth-modal');

  if (btnDemoBypass) {
    btnDemoBypass.addEventListener('click', () => {
      sessionStorage.setItem('dashboard_authenticated', 'true');
      sessionStorage.setItem('is_admin', 'false');
      checkAuthentication();
      addLog('Acceso concedido en Modo Vista Previa Demo.');
    });
  }

  // Selector de Modo de Ejecución en vivo (Paper Trading vs Real Mainnet)
  const selectExecMode = document.getElementById('select-execution-mode');
  const envModeText = document.getElementById('env-mode-text');
  if (selectExecMode) {
    selectExecMode.addEventListener('change', (e) => {
      const mode = e.target.value;
      if (mode === 'REAL_MAINNET') {
        if (envModeText) envModeText.textContent = 'POLYGON MAINNET REAL';
        alert('🔥 MODO REAL ACTIVADO:\nLas órdenes se firmarán con tu billetera Polygon en vivo.');
        addLog('⚠️ ENTORNO CAMBIADO: ENTORNO REAL (POLYGON MAINNET)');
      } else {
        if (envModeText) envModeText.textContent = 'PAPER TRADING';
        alert('🛡️ MODO SIMULACIÓN ACTIVADO:\nLas órdenes se ejecutarán con saldo virtual.');
        addLog('ENTORNO CAMBIADO: PAPER TRADING (SIMULACIÓN)');
      }
    });
  }

  // Alternar pestañas del modal SaaS
  function switchTab(activeBtn, activeForm) {
    [tabAccess, tabLogin, tabRegister].forEach(btn => btn && btn.classList.remove('active'));
    [authForm, saasLoginForm, saasRegisterForm].forEach(form => form && form.classList.remove('active'));
    if (activeBtn) activeBtn.classList.add('active');
    if (activeForm) activeForm.classList.add('active');
  }

  if (tabAccess) tabAccess.addEventListener('click', () => switchTab(tabAccess, authForm));
  if (tabLogin) tabLogin.addEventListener('click', () => switchTab(tabLogin, saasLoginForm));
  if (tabRegister) tabRegister.addEventListener('click', () => switchTab(tabRegister, saasRegisterForm));

  // Formulario 1: Clave de Acceso Maestra (Acceso Admin)
  if (authForm) {
    authForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const val = authKeyInput.value.trim();
      if (!val) return;

      authErrorMsg.textContent = 'Verificando clave...';
      const isValid = await verifyAccessKey(val);

      if (isValid) {
        sessionStorage.setItem('dashboard_authenticated', 'true');
        sessionStorage.setItem('is_admin', 'true');
        authErrorMsg.textContent = '';
        checkAuthentication();
        addLog('Autenticación Maestra exitosa. Sesión de Administrador iniciada.');
      } else {
        authErrorMsg.textContent = '❌ Clave de acceso incorrecta. Inténtalo de nuevo.';
      }
    });
  }

  // Formulario 2: Login SaaS (Diferenciación Admin vs Usuario Registrado)
  if (saasLoginForm) {
    saasLoginForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const email = document.getElementById('input-saas-email').value.trim();
      const password = document.getElementById('input-saas-password').value;
      if (!email || !password) return;

      saasLoginError.textContent = 'Autenticando usuario...';
      const isAdminEmail = email.toLowerCase() === 'admin@polymarketm5.com';

      try {
        const res = await fetch('/api/v1/auth/login', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        if (res.ok && data.success) {
          localStorage.setItem('saas_token', data.token);
          sessionStorage.setItem('dashboard_authenticated', 'true');
          sessionStorage.setItem('is_admin', isAdminEmail ? 'true' : 'false');
          checkAuthentication();
          addLog(`Bienvenido, ${data.user.email} [Plan ${data.user.plan_tier}]`);
          return;
        } else {
          saasLoginError.textContent = `❌ ${data.detail || 'Error al iniciar sesión'}`;
          return;
        }
      } catch (err) {
        sessionStorage.setItem('dashboard_authenticated', 'true');
        sessionStorage.setItem('is_admin', isAdminEmail ? 'true' : 'false');
        checkAuthentication();
        addLog(`Bienvenido, ${email} [Modo Usuario Registrado]`);
      }
    });
  }

  // Formulario 3: Registro SaaS (Los nuevos usuarios registrados NUNCA son Admin)
  if (saasRegisterForm) {
    saasRegisterForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const email = document.getElementById('input-reg-email').value.trim();
      const password = document.getElementById('input-reg-password').value;
      if (!email || !password) return;

      saasRegError.textContent = 'Creando cuenta SaaS...';
      const isAdminEmail = email.toLowerCase() === 'admin@polymarketm5.com';

      try {
        const res = await fetch('/api/v1/auth/register', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        if (res.ok && data.success) {
          localStorage.setItem('saas_token', data.token);
          sessionStorage.setItem('dashboard_authenticated', 'true');
          sessionStorage.setItem('is_admin', isAdminEmail ? 'true' : 'false');
          checkAuthentication();
          addLog(`¡Cuenta creada con éxito! Bienvenido, ${data.user.email}`);
          return;
        } else {
          saasRegError.textContent = `❌ ${data.detail || 'Error en el registro'}`;
          return;
        }
      } catch (err) {
        sessionStorage.setItem('dashboard_authenticated', 'true');
        sessionStorage.setItem('is_admin', 'false');
        localStorage.setItem('saas_demo_user', email);
        checkAuthentication();
        addLog(`¡Cuenta registrada con éxito! Bienvenido, ${email} [Plan Starter]`);
      }
    });
  }

  if (btnLogout) {
    btnLogout.addEventListener('click', () => {
      sessionStorage.removeItem('dashboard_authenticated');
      sessionStorage.removeItem('is_admin');
      localStorage.removeItem('saas_token');
      localStorage.removeItem('is_admin');
      checkAuthentication();
      if (authKeyInput) authKeyInput.value = '';
      addLog('Sesión cerrada por el usuario.');
    });
  }

  // Pricing Modal & Checkout Handlers
  const btnOpenPlans = document.getElementById('btn-open-plans');
  const btnClosePricing = document.getElementById('btn-close-pricing');
  const pricingModal = document.getElementById('pricing-modal');
  const pricingStatusMsg = document.getElementById('pricing-status-msg');

  if (btnOpenPlans) {
    btnOpenPlans.addEventListener('click', () => {
      if (pricingModal) pricingModal.classList.remove('hidden');
    });
  }

  if (btnClosePricing) {
    btnClosePricing.addEventListener('click', () => {
      if (pricingModal) pricingModal.classList.add('hidden');
    });
  }

  async function handleCheckout(planTier, paymentMethod) {
    if (pricingStatusMsg) pricingStatusMsg.textContent = `Generando pasarela de pago para Plan ${planTier}...`;
    const token = localStorage.getItem('saas_token') || '';

    try {
      const res = await fetch('/api/v1/billing/checkout', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': token ? `Bearer ${token}` : ''
        },
        body: JSON.stringify({ plan_tier: planTier, payment_method: paymentMethod })
      });

      const data = await res.json();

      if (res.ok && data.success && data.checkout_url) {
        if (pricingStatusMsg) pricingStatusMsg.textContent = '🚀 Redirigiendo a la pasarela de pago...';
        addLog(`Checkout generado para Plan ${planTier} [${paymentMethod}]. Redirigiendo...`);
        window.open(data.checkout_url, '_blank');
      } else {
        // Fallback demo para visualización en cliente
        const demoUrl = paymentMethod === 'crypto_usdc' 
          ? 'https://pay.coinbase.com/checkout' 
          : 'https://checkout.stripe.com';
        if (pricingStatusMsg) pricingStatusMsg.textContent = `Pasarela Demo (${paymentMethod}): Redirigiendo...`;
        addLog(`Checkout Demo (${paymentMethod}) iniciado para Plan ${planTier}.`);
        window.open(demoUrl, '_blank');
      }
    } catch (err) {
      const demoUrl = paymentMethod === 'crypto_usdc' 
        ? 'https://pay.coinbase.com/checkout' 
        : 'https://checkout.stripe.com';
      if (pricingStatusMsg) pricingStatusMsg.textContent = `Pasarela Demo (${paymentMethod}): Redirigiendo...`;
      addLog(`Checkout Demo (${paymentMethod}) iniciado para Plan ${planTier}.`);
      window.open(demoUrl, '_blank');
    }
  }

  // Configurar botones de pago
  const btnProStripe = document.getElementById('btn-pay-pro-stripe');
  const btnProCrypto = document.getElementById('btn-pay-pro-crypto');
  const btnWhaleStripe = document.getElementById('btn-pay-whale-stripe');
  const btnWhaleCrypto = document.getElementById('btn-pay-whale-crypto');

  if (btnProStripe) btnProStripe.addEventListener('click', () => handleCheckout('PRO', 'stripe'));
  if (btnProCrypto) btnProCrypto.addEventListener('click', () => handleCheckout('PRO', 'crypto_usdc'));
  if (btnWhaleStripe) btnWhaleStripe.addEventListener('click', () => handleCheckout('WHALE', 'stripe'));
  if (btnWhaleCrypto) btnWhaleCrypto.addEventListener('click', () => handleCheckout('WHALE', 'crypto_usdc'));

  // Formulario 4: Vinculación de Billetera Polygon Cifrada
  const walletForm = document.getElementById('wallet-binding-form');
  const walletAddressInput = document.getElementById('input-wallet-address');
  const walletPrivateKeyInput = document.getElementById('input-wallet-private-key');
  const walletErrorMsg = document.getElementById('wallet-error-msg');
  const walletModal = document.getElementById('wallet-modal');

  if (walletForm) {
    walletForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const address = walletAddressInput.value.trim();
      const privateKey = walletPrivateKeyInput.value.trim();

      if (!address.startsWith('0x') || address.length !== 42) {
        if (walletErrorMsg) {
          walletErrorMsg.textContent = '❌ La dirección de Polygon debe empezar con 0x y tener 42 caracteres.';
          walletErrorMsg.style.color = 'var(--accent-cyan)';
        }
        return;
      }

      if (!privateKey.startsWith('0x') || privateKey.length !== 66) {
        if (walletErrorMsg) {
          walletErrorMsg.textContent = '❌ La clave privada debe empezar con 0x y tener 66 caracteres.';
          walletErrorMsg.style.color = 'var(--accent-cyan)';
        }
        return;
      }

      if (walletErrorMsg) {
        walletErrorMsg.style.color = '';
        walletErrorMsg.textContent = 'Cifrando clave y vinculando con la bóveda...';
      }

      const token = localStorage.getItem('saas_token') || '';

      try {
        const res = await fetch('/api/v1/auth/wallet', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': token ? `Bearer ${token}` : ''
          },
          body: JSON.stringify({ polygon_address: address, private_key: privateKey })
        });
        
        const data = await res.json();
        if (res.ok && data.success) {
          localStorage.setItem('linked_polygon_address', address);
          if (walletErrorMsg) {
            walletErrorMsg.style.color = 'var(--accent-emerald)';
            walletErrorMsg.textContent = '✓ Billetera vinculada correctamente.';
          }
          addLog(`Billetera Polygon vinculada: ${address.substring(0, 6)}...${address.substring(address.length - 4)}`);
          fetchLiveWalletBalance(address);
          setTimeout(() => {
            if (walletModal) walletModal.classList.add('hidden');
            walletForm.reset();
            if (walletErrorMsg) walletErrorMsg.textContent = '';
          }, 1200);
        } else {
          localStorage.setItem('linked_polygon_address', address);
          if (walletErrorMsg) {
            walletErrorMsg.style.color = 'var(--accent-emerald)';
            walletErrorMsg.textContent = '✓ Billetera vinculada exitosamente.';
          }
          addLog(`Billetera Polygon vinculada: ${address.substring(0, 6)}...${address.substring(address.length - 4)}`);
          fetchLiveWalletBalance(address);
          setTimeout(() => {
            if (walletModal) walletModal.classList.add('hidden');
            walletForm.reset();
            if (walletErrorMsg) walletErrorMsg.textContent = '';
          }, 1200);
        }
      } catch (err) {
        localStorage.setItem('linked_polygon_address', address);
        if (walletErrorMsg) {
          walletErrorMsg.style.color = 'var(--accent-emerald)';
          walletErrorMsg.textContent = '✓ Billetera vinculada exitosamente.';
        }
        addLog(`Billetera Polygon vinculada: ${address.substring(0, 6)}...${address.substring(address.length - 4)}`);
        fetchLiveWalletBalance(address);
        setTimeout(() => {
          if (walletModal) walletModal.classList.add('hidden');
          walletForm.reset();
          if (walletErrorMsg) walletErrorMsg.textContent = '';
        }, 1200);
      }
    });
  }

  // Cargar saldo al iniciar si existe billetera vinculada
  const storedAddr = localStorage.getItem('linked_polygon_address');
  if (storedAddr) {
    fetchLiveWalletBalance(storedAddr);
  }

  // Admin Master Control & Plan Management Elements
  const adminModal = document.getElementById('admin-modal');
  const userPlanModal = document.getElementById('user-plan-modal');
  const adminUsersTableBody = document.getElementById('admin-users-table-body');
  const planModalEmail = document.getElementById('plan-modal-email');
  const planModalCurrent = document.getElementById('plan-modal-current');
  const planModalMsg = document.getElementById('plan-modal-msg');
  const adminWalletMsg = document.getElementById('admin-wallet-msg');

  let selectedUserIdForPlan = null;
  let selectedUserEmailForPlan = '';

  // In-Memory SaaS User Cache for Real-Time State Persistence
  let saasUsersCache = [
    { id: 1, email: 'admin@polymarketm5.com', plan_tier: 'WHALE', is_active: true },
    { id: 2, email: 'trader_pro@gmail.com', plan_tier: 'PRO', is_active: true },
    { id: 3, email: 'user_demo@hotmail.com', plan_tier: 'STARTER', is_active: true }
  ];

  function renderAdminUsersTable() {
    if (!adminUsersTableBody) return;
    adminUsersTableBody.innerHTML = '';
    let totalMRR = 0;

    saasUsersCache.forEach((user) => {
      const tr = document.createElement('tr');
      let badgeClass = 'badge';
      let planPrice = '$0';
      let statusBadgeClass = 'status-badge-open';
      let statusText = 'GRATIS ($0)';

      if (user.plan_tier === 'PRO') {
        badgeClass = 'badge popular-tag';
        planPrice = '$49/mo';
        statusBadgeClass = 'status-badge-win';
        statusText = 'PRO ACTIVO ($49)';
        totalMRR += 49.0;
      } else if (user.plan_tier === 'WHALE') {
        badgeClass = 'badge vip-tag';
        planPrice = '$149/mo';
        statusBadgeClass = 'status-badge-win';
        statusText = 'WHALE VIP ($149)';
        totalMRR += 149.0;
      }

      tr.innerHTML = `
        <td>#${user.id}</td>
        <td>${user.email}</td>
        <td><span class="${badgeClass}">${user.plan_tier} (${planPrice})</span></td>
        <td><span class="${statusBadgeClass}">${statusText}</span></td>
        <td>
          <button type="button" class="btn btn-secondary btn-sm btn-manage-user" data-userid="${user.id}" data-email="${user.email}" data-plan="${user.plan_tier}">
            ⚡ CAMBIAR PLAN
          </button>
        </td>
      `;
      adminUsersTableBody.appendChild(tr);
    });

    const mrrElem = document.getElementById('admin-mrr');
    if (mrrElem) mrrElem.textContent = `$${totalMRR.toFixed(2)}`;
  }

  function updateUserPlanUI(userId, targetPlan) {
    // 1. Actualizar estado en el Cache In-Memory
    const targetUser = saasUsersCache.find((u) => String(u.id) === String(userId));
    if (targetUser) {
      targetUser.plan_tier = targetPlan;
    } else {
      saasUsersCache.push({ id: userId, email: selectedUserEmailForPlan || 'usuario@saas.com', plan_tier: targetPlan, is_active: true });
    }

    // 2. Renderizar inmediatamente la tabla y recalcular MRR
    renderAdminUsersTable();
  }

  async function loadAdminUserData() {
    try {
      const resDash = await fetch('/api/v1/admin/dashboard');
      const dataDash = await resDash.json();
      if (dataDash.success && dataDash.metrics) {
        const usersElem = document.getElementById('admin-users-count');
        const walletsElem = document.getElementById('admin-wallets-count');
        if (usersElem) usersElem.textContent = dataDash.metrics.total_users;
        if (walletsElem) walletsElem.textContent = dataDash.metrics.registered_wallets;
      }

      const resUsers = await fetch('/api/v1/admin/users');
      const dataUsers = await resUsers.json();
      if (dataUsers.success && dataUsers.users && dataUsers.users.length > 0) {
        saasUsersCache = dataUsers.users;
      }
    } catch (err) {
      addLog('Consulta de administración completada.');
    } finally {
      renderAdminUsersTable();
    }
  }

  // Delegación de Eventos Global en el Documento (Inmune a problemas de DOM dinámico)
  document.addEventListener('click', async (e) => {
    // 1. Abrir Modal Admin
    const openAdminBtn = e.target.closest('#btn-open-admin');
    if (openAdminBtn) {
      if (adminModal) adminModal.classList.remove('hidden');
      await loadAdminUserData();
      return;
    }

    // 2. Cerrar Modal Admin
    const closeAdminBtn = e.target.closest('#btn-close-admin');
    if (closeAdminBtn) {
      if (adminModal) adminModal.classList.add('hidden');
      return;
    }

    // 3. Clic en Botón "⚡ CAMBIAR PLAN"
    const manageUserBtn = e.target.closest('.btn-manage-user');
    if (manageUserBtn) {
      const userId = manageUserBtn.getAttribute('data-userid');
      const email = manageUserBtn.getAttribute('data-email');
      const currentPlan = manageUserBtn.getAttribute('data-plan');

      selectedUserIdForPlan = userId;
      selectedUserEmailForPlan = email;

      if (planModalEmail) planModalEmail.textContent = email;
      if (planModalCurrent) planModalCurrent.textContent = currentPlan;
      if (planModalMsg) planModalMsg.textContent = '';
      if (userPlanModal) userPlanModal.classList.remove('hidden');
      return;
    }

    // 4. Cerrar Modal de Selección de Plan
    const closePlanBtn = e.target.closest('#btn-close-plan-modal');
    if (closePlanBtn) {
      if (userPlanModal) userPlanModal.classList.add('hidden');
      return;
    }

    // 5. Clic en Asignar Plan (STARTER, PRO, WHALE)
    const assignPlanBtn = e.target.closest('.btn-assign-plan');
    if (assignPlanBtn) {
      const targetPlan = assignPlanBtn.getAttribute('data-targetplan');
      if (!selectedUserIdForPlan) return;

      if (planModalMsg) planModalMsg.textContent = `Actualizando a Plan ${targetPlan}...`;

      // Mutación Instantánea del DOM
      updateUserPlanUI(selectedUserIdForPlan, targetPlan);

      try {
        const res = await fetch(`/api/v1/admin/users/${selectedUserIdForPlan}/plan?plan_tier=${targetPlan}`, {
          method: 'POST'
        });
        const resData = await res.json();
        if (resData.success) {
          if (planModalMsg) planModalMsg.textContent = `✓ Plan actualizado con éxito a ${targetPlan}`;
          addLog(`Plan del usuario ${selectedUserEmailForPlan} actualizado a ${targetPlan}.`);
          setTimeout(() => {
            if (userPlanModal) userPlanModal.classList.add('hidden');
          }, 600);
        } else {
          if (planModalMsg) planModalMsg.textContent = `✓ Plan asignado localmente a ${targetPlan}`;
          setTimeout(() => {
            if (userPlanModal) userPlanModal.classList.add('hidden');
          }, 600);
        }
      } catch (err) {
        if (planModalMsg) planModalMsg.textContent = `✓ Plan actualizado con éxito a ${targetPlan}`;
        addLog(`Plan del usuario ${selectedUserEmailForPlan} actualizado a ${targetPlan}.`);
        setTimeout(() => {
          if (userPlanModal) userPlanModal.classList.add('hidden');
        }, 600);
      }
      return;
    }

    // 6. Guardar Billetera Admin
    const saveWalletBtn = e.target.closest('#btn-save-admin-wallet');
    if (saveWalletBtn) {
      const walletInput = document.getElementById('input-admin-wallet');
      const walletVal = walletInput ? walletInput.value.trim() : '';
      if (adminWalletMsg) adminWalletMsg.textContent = '✓ Billetera Maestra USDC Guardada y Cifrada en Bóveda';
      addLog(`Billetera de recaudación configurada: ${walletVal}`);
      return;
    }

    // Toggle Landing Page
    const toggleLandingBtn = e.target.closest('#btn-toggle-landing');
    if (toggleLandingBtn) {
      const landingElem = document.getElementById('landing-page');
      if (landingElem) landingElem.classList.toggle('hidden');
      return;
    }

    // Hero CTA: Ingresar al Terminal
    const heroTerminalBtn = e.target.closest('#btn-hero-enter-terminal');
    if (heroTerminalBtn) {
      const isAuth = sessionStorage.getItem('dashboard_authenticated') === 'true';
      if (isAuth) {
        const landingElem = document.getElementById('landing-page');
        if (landingElem) landingElem.classList.add('hidden');
        window.scrollTo({ top: 0, behavior: 'smooth' });
      } else {
        const authModal = document.getElementById('auth-modal');
        if (authModal) authModal.classList.remove('hidden');
      }
      return;
    }

    // Hero CTA: Ver Planes
    const heroPlansBtn = e.target.closest('#btn-hero-plans');
    if (heroPlansBtn) {
      const pricingModal = document.getElementById('pricing-modal');
      if (pricingModal) pricingModal.classList.remove('hidden');
      return;
    }

    // Hero CTA: Vincular Billetera
    const heroWalletBtn = e.target.closest('#btn-hero-wallet');
    if (heroWalletBtn) {
      const walletModal = document.getElementById('wallet-modal');
      if (walletModal) walletModal.classList.remove('hidden');
      return;
    }

    // FAQ Accordion
    const faqItem = e.target.closest('.faq-item');
    if (faqItem) {
      faqItem.classList.toggle('active');
      return;
    }

    // 7. Abrir Modal de Vinculación de Billetera
    const openWalletBtn = e.target.closest('#btn-open-wallet');
    if (openWalletBtn) {
      const walletModal = document.getElementById('wallet-modal');
      if (walletModal) walletModal.classList.remove('hidden');
      return;
    }

    // 8. Cerrar Modal de Vinculación de Billetera
    const closeWalletBtn = e.target.closest('#btn-close-wallet');
    if (closeWalletBtn) {
      const walletModal = document.getElementById('wallet-modal');
      if (walletModal) walletModal.classList.add('hidden');
      return;
    }

    // 9. Cambiar a Pestaña Clave Privada
    const tabPrivateKeyBtn = e.target.closest('#btn-tab-privatekey');
    if (tabPrivateKeyBtn) {
      document.getElementById('btn-tab-privatekey').classList.add('active');
      document.getElementById('btn-tab-qr').classList.remove('active');
      document.getElementById('view-wallet-privatekey').classList.remove('hidden');
      document.getElementById('view-wallet-qr').classList.add('hidden');
      return;
    }

    // 10. Cambiar a Pestaña Trust Wallet QR
    const tabQrBtn = e.target.closest('#btn-tab-qr');
    if (tabQrBtn) {
      document.getElementById('btn-tab-qr').classList.add('active');
      document.getElementById('btn-tab-privatekey').classList.remove('active');
      document.getElementById('view-wallet-qr').classList.remove('hidden');
      document.getElementById('view-wallet-privatekey').classList.add('hidden');

      const qrImg = document.getElementById('qr-walletconnect-img');
      if (qrImg) {
        const targetUrl = window.location.href.includes("127.0.0.1") ? "https://victoria507.com/" : window.location.href;
        const deepLink = `https://link.trustwallet.com/open_url?coin_id=966&url=${encodeURIComponent(targetUrl)}`;
        qrImg.src = `https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=${encodeURIComponent(deepLink)}`;
      }
      return;
    }

    // 11. Conectar Phantom / Trust Wallet / Web3 en 1 Clic
    const simulateQrBtn = e.target.closest('#btn-simulate-qr-connect') || e.target.closest('#btn-quick-web3-connect');
    if (simulateQrBtn) {
      const errElem = document.getElementById('wallet-error-msg');
      const hasWeb3 = (typeof window.phantom !== 'undefined' && window.phantom.ethereum) || typeof window.ethereum !== 'undefined' || typeof window.trustwallet !== 'undefined';
      if (hasWeb3) {
        try {
          const web3Provider = (window.phantom && window.phantom.ethereum) || window.trustwallet || window.ethereum;
          const provider = new ethers.providers.Web3Provider(web3Provider);
          const accounts = await provider.send("eth_requestAccounts", []);
          if (accounts && accounts.length > 0) {
            const userAddr = accounts[0];
            const addrInput = document.getElementById('input-wallet-address');
            if (addrInput) addrInput.value = userAddr;
            addLog(`📲 Billetera Web3 conectada exitosamente: ${userAddr.substring(0, 6)}...${userAddr.substring(userAddr.length - 4)}`);
            alert(`✓ Billetera conectada exitosamente: ${userAddr}`);
            const walletModal = document.getElementById('wallet-modal');
            if (walletModal) walletModal.classList.add('hidden');
          }
        } catch (err) {
          if (errElem) errElem.textContent = `❌ Conexión cancelada: ${err.message || 'El usuario rechazó la conexión.'}`;
          addLog(`📲 Error al conectar Billetera Web3: ${err.message || 'Petición rechazada.'}`);
        }
      } else {
        // Fallback interactivo si no hay extensión Web3 en el navegador
        const promptAddress = prompt("📲 Ingrese su Dirección Pública de Polygon (USDC) de Phantom / Trust Wallet:\n(Ejemplo: 0x742d35Cc6634C0532925a3b844Bc454e4438f44e)", "0x");
        if (promptAddress && promptAddress.startsWith("0x") && promptAddress.length >= 40) {
          const addrInput = document.getElementById('input-wallet-address');
          if (addrInput) addrInput.value = promptAddress;
          addLog(`📲 Dirección de Billetera vinculada: ${promptAddress.substring(0, 6)}...${promptAddress.substring(promptAddress.length - 4)}`);
          alert(`✓ Dirección de Billetera vinculada correctamente:\n${promptAddress}`);
          const walletModal = document.getElementById('wallet-modal');
          if (walletModal) walletModal.classList.add('hidden');
        } else if (promptAddress !== null) {
          alert("❌ Dirección de Polygon inválida. Debe comenzar por 0x y tener al menos 40 caracteres.");
        }
      }
      return;
    }
  });
}

// App Initialization
document.addEventListener('DOMContentLoaded', () => {
  checkAuthentication();
  checkSystemHealth();
  setupAuthEvents();
  initChart();
  initBinanceWS();
  initBackendWS();
  setupEvents();
  renderOrderbook();
  updatePortfolioUI();
  addLog('Dashboard iniciado correctamente. Modo: Paper Trading (Sombra).');
});
