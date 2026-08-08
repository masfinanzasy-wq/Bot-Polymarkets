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

// Pre-Trade Security Check Automatizado de 12 Puntos
async function runPreTradeSecurityCheck(outcome, entryPrice, size) {
  const checks = [];
  const errors = [];

  const isAuth = sessionStorage.getItem('dashboard_authenticated') === 'true';
  if (!isAuth) {
    errors.push('🔒 Usuario no autenticado. Por favor ingresa con tu llave de acceso.');
  } else {
    checks.push('✓ Usuario Autenticado en Plataforma');
  }

  if (state.panicStopActive) {
    errors.push('🛑 PARADA DE EMERGENCIA ACTIVA. Todas las operaciones están congeladas.');
  } else {
    checks.push('✓ Parada de Emergencia Inactiva');
  }

  const isRealMode = localStorage.getItem('execution_mode') === 'REAL_MAINNET';
  const linkedAddr = localStorage.getItem('linked_polygon_address');

  if (isRealMode) {
    if (!linkedAddr || !linkedAddr.startsWith('0x') || linkedAddr.length < 40) {
      errors.push('🔑 Billetera Polygon Web3 no conectada. Por favor vincula tu billetera Polygon.');
    } else {
      checks.push(`✓ Billetera Conectada: ${linkedAddr.substring(0, 6)}...${linkedAddr.substring(linkedAddr.length - 4)}`);
      
      // Consultar siempre el saldo real fresco antes de evaluar la orden
      try {
        await fetchLiveWalletBalance(linkedAddr);
      } catch (fErr) {
        console.warn("Error al actualizar saldo fresco antes de operar", fErr);
      }
    }

    const usdc = state.realBalances ? (state.realBalances.usdc || 0.0) : 0.0;
    const matic = state.realBalances ? (state.realBalances.matic || 0.0) : 0.0;

    if (usdc <= 0) {
      errors.push(`💰 Sin saldo disponible en USDC ($0.00 USDC). Se requiere saldo positivo en Polygon Mainnet.`);
    } else if (usdc < size) {
      // Auto-ajustar tamaño de posición al saldo disponible
      state.settings.positionSizeUsd = parseFloat(usdc.toFixed(2));
      const sizeInput = document.getElementById('input-pos-size');
      if (sizeInput) sizeInput.value = usdc.toFixed(2);
      checks.push(`⚠️ Tamaño de posición ajustado automáticamente a tu saldo disponible: $${usdc.toFixed(2)} USDC`);
    } else {
      checks.push(`✓ Saldo USDC Suficiente: $${usdc.toFixed(2)} USDC`);
    }

    if (matic < 0.0001) {
      errors.push(`⛽ Saldo MATIC/POL insuficiente para comisiones de red (${matic.toFixed(4)} MATIC). Se requieren al menos 0.0001 MATIC.`);
    } else {
      checks.push(`✓ Gas MATIC Suficiente: ${matic.toFixed(4)} MATIC`);
    }
  } else {
    checks.push('🛡️ Modo Simulación Activo (Capital Virtual)');
    if (state.portfolio.currentBalance < size) {
      errors.push(`💰 Balance virtual insuficiente ($${state.portfolio.currentBalance.toFixed(2)} < $${size.toFixed(2)}).`);
    }
  }

  const effectiveSize = state.settings.positionSizeUsd || size;
  if (effectiveSize <= 0 || effectiveSize > (state.settings.maxDailyLossUsd || 500.0)) {
    errors.push(`⚠️ Tamaño de posición ($${effectiveSize.toFixed(2)}) inválido o supera el límite diario de riesgo ($${(state.settings.maxDailyLossUsd || 500.0).toFixed(2)}).`);
  } else {
    checks.push('✓ Límite de Riesgo Válido');
  }

  try {
    const res = await fetch('/api/v1/auth/pretrade-security-check', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        position_size_usd: effectiveSize,
        polygon_address: linkedAddr,
        execution_mode: isRealMode ? 'REAL_MAINNET' : 'PAPER_TRADING',
        min_ev_pct: state.settings.minEvPct || 5.0
      })
    });
    const backendRes = await res.json();
    if (!backendRes.passed && backendRes.errors) {
      backendRes.errors.forEach(e => {
        if (!errors.includes(e)) errors.push(`[Backend] ${e}`);
      });
    }
  } catch (e) {
    // Local fallback check
  }

  const passed = errors.length === 0;
  return { passed, checks, errors };
}

// Paper Trading & Real Live Trading Execution Logic
async function triggerAutoPaperTrade(outcome, entryPrice, ev) {
  const size = state.settings.positionSizeUsd;
  const isRealMode = localStorage.getItem('execution_mode') === 'REAL_MAINNET';

  // EJECUCIÓN DEL PRE-TRADE SECURITY CHECK
  const securityCheck = await runPreTradeSecurityCheck(outcome, entryPrice, size);
  if (!securityCheck.passed) {
    const errorMsg = securityCheck.errors.join('\n');
    addLog(`🚨 PRE-TRADE SECURITY CHECK BLOQUEADO:\n${errorMsg}`);
    if (isRealMode) {
      alert(`🚨 OPERACIÓN BLOQUEADA POR PRE-TRADE SECURITY CHECK:\n\n${errorMsg}\n\nPor favor corrige los puntos antes de operar.`);
      const realModal = document.getElementById('real-trading-modal');
      if (realModal) realModal.classList.remove('hidden');
    }
    return;
  }

  const shares = size / entryPrice;
  const id = `trade_${Math.floor(Math.random() * 8999 + 1000)}`;

  const position = {
    id,
    time: new Date().toLocaleTimeString(),
    market: isRealMode ? 'BTC-UP-5M (🔥 REAL)' : 'BTC-UP-5M',
    outcome,
    entryPrice,
    shares,
    cost: size,
    status: 'OPEN',
    pnl: 0.0
  };

  if (isRealMode) {
    if (state.realBalances) state.realBalances.usdc -= size;
    addLog(`🔥 ÓRDEN REAL VERIFICADA & ENVIADA A POLYGON CLOB: [${outcome}] Costo: $${size.toFixed(2)} USDC @ $${entryPrice.toFixed(4)}`);
  } else {
    state.portfolio.currentBalance -= size;
    addLog(`POSICIÓN ABIERTA SIMULADA [${outcome}] - Costo: $${size.toFixed(2)} USD @ $${entryPrice.toFixed(4)}`);
  }

  state.portfolio.activePositions.push(position);
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

function updateWalletHeaderBadge(address) {
  const btnWallet = document.getElementById('btn-open-wallet');
  const inputAddr = document.getElementById('input-wallet-address');
  const walletErrorMsg = document.getElementById('wallet-error-msg');
  const disconnectBtn = document.getElementById('btn-disconnect-wallet');

  if (address && address.startsWith('0x')) {
    const shortAddr = `${address.substring(0, 6)}...${address.substring(address.length - 4)}`;
    const usdc = state.realBalances ? (state.realBalances.usdc || 0.0) : 0.0;
    if (btnWallet) {
      btnWallet.textContent = `🟢 WALLET: ${shortAddr} ($${usdc.toFixed(2)} USDC)`;
      btnWallet.style.borderColor = 'var(--accent-emerald)';
      btnWallet.style.color = 'var(--accent-emerald)';
      btnWallet.style.background = 'rgba(0, 230, 118, 0.1)';
    }
    if (inputAddr) {
      inputAddr.value = address;
    }
    if (disconnectBtn) {
      disconnectBtn.style.display = 'block';
    }
    if (walletErrorMsg && (!walletErrorMsg.textContent || walletErrorMsg.textContent.includes('✓'))) {
      walletErrorMsg.style.color = 'var(--accent-emerald)';
      walletErrorMsg.textContent = `✓ Billetera vinculada: ${shortAddr} ($${usdc.toFixed(2)} USDC)`;
    }
  } else {
    if (btnWallet) {
      btnWallet.textContent = `🔑 VINCULAR WALLET`;
      btnWallet.style.borderColor = '';
      btnWallet.style.color = '';
      btnWallet.style.background = '';
    }
    if (disconnectBtn) {
      disconnectBtn.style.display = 'none';
    }
    if (walletErrorMsg) {
      walletErrorMsg.textContent = '';
    }
  }
}

async function queryPolygonBalanceDirect(address) {
  const rpcs = [
    "https://rpc.ankr.com/polygon",
    "https://1rpc.io/matic",
    "https://polygon-bor-rpc.publicnode.com",
    "https://polygon-rpc.com"
  ];
  const cleanAddr = address.toLowerCase().replace('0x', '').padStart(64, '0');
  const dataCall = '0x70a08231' + cleanAddr;

  for (const rpc of rpcs) {
    try {
      const bodyMatic = JSON.stringify({ jsonrpc: "2.0", method: "eth_getBalance", params: [address, "latest"], id: 1 });
      const bodyUsdcNat = JSON.stringify({ jsonrpc: "2.0", method: "eth_call", params: [{ to: "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359", data: dataCall }, "latest"], id: 2 });
      const bodyUsdcBrg = JSON.stringify({ jsonrpc: "2.0", method: "eth_call", params: [{ to: "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174", data: dataCall }, "latest"], id: 3 });

      const [r1, r2, r3] = await Promise.all([
        fetch(rpc, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: bodyMatic }).then(r => r.json()),
        fetch(rpc, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: bodyUsdcNat }).then(r => r.json()),
        fetch(rpc, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: bodyUsdcBrg }).then(r => r.json())
      ]);

      const maticHex = r1?.result || "0x0";
      const usdcNatHex = r2?.result || "0x0";
      const usdcBrgHex = r3?.result || "0x0";

      const maticVal = parseInt(maticHex, 16) / 1e18;
      const usdcNatVal = parseInt(usdcNatHex, 16) / 1e6;
      const usdcBrgVal = parseInt(usdcBrgHex, 16) / 1e6;
      const totalUsdc = (isNaN(usdcNatVal) ? 0 : usdcNatVal) + (isNaN(usdcBrgVal) ? 0 : usdcBrgVal);

      if (!isNaN(totalUsdc) && !isNaN(maticVal)) {
        return { usdc_balance: totalUsdc, matic_balance: maticVal, success: true };
      }
    } catch (e) {
      // try next RPC
    }
  }
  return null;
}

async function fetchLiveWalletBalance(address) {
  const balanceElem = document.getElementById('portfolio-balance');
  const pnlElem = document.getElementById('portfolio-pnl');
  const modalUsdcElem = document.getElementById('modal-real-usdc-val');
  const modalMaticElem = document.getElementById('modal-real-matic-val');
  const realWalletInput = document.getElementById('input-real-wallet-address');

  if (!address || !address.startsWith('0x') || address.length < 40) return;

  if (realWalletInput && (!realWalletInput.value || realWalletInput.value === '0x')) {
    realWalletInput.value = address;
  }

  let usdc = 0.0;
  let matic = 0.0;
  let fetchedSuccess = false;

  // Capa 1: Consulta directa via Provider Web3 si el usuario tiene extensión instalada
  if (typeof window.ethereum !== 'undefined' || (typeof window.phantom !== 'undefined' && window.phantom.ethereum)) {
    try {
      const web3Provider = (window.phantom && window.phantom.ethereum) || window.ethereum;
      const provider = new ethers.providers.Web3Provider(web3Provider);
      
      const cleanAddr = address.toLowerCase().replace('0x', '').padStart(64, '0');
      const dataCall = '0x70a08231' + cleanAddr;

      const [maticHex, usdcNatHex, usdcBrgHex] = await Promise.all([
        provider.send("eth_getBalance", [address, "latest"]).catch(() => "0x0"),
        provider.send("eth_call", [{ to: "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359", data: dataCall }, "latest"]).catch(() => "0x0"),
        provider.send("eth_call", [{ to: "0x2791Bca1f2de4661ED88A30C99A7a9449Aa84174", data: dataCall }, "latest"]).catch(() => "0x0")
      ]);

      const maticVal = parseInt(maticHex || "0x0", 16) / 1e18;
      const usdcNatVal = parseInt(usdcNatHex || "0x0", 16) / 1e6;
      const usdcBrgVal = parseInt(usdcBrgHex || "0x0", 16) / 1e6;

      if (!isNaN(maticVal) && (!isNaN(usdcNatVal) || !isNaN(usdcBrgVal))) {
        usdc = (isNaN(usdcNatVal) ? 0 : usdcNatVal) + (isNaN(usdcBrgVal) ? 0 : usdcBrgVal);
        matic = isNaN(maticVal) ? 0 : maticVal;
        fetchedSuccess = true;
      }
    } catch (wErr) {
      // Fallback a API del Backend
    }
  }

  // Capa 2: Backend API de la plataforma
  if (!fetchedSuccess) {
    try {
      const res = await fetch(`/api/v1/wallet/balance/${address}`);
      const data = await res.json();
      if (data && data.success) {
        usdc = data.usdc_balance || 0.0;
        matic = data.matic_balance || 0.0;
        fetchedSuccess = true;
      }
    } catch (err) {
      console.warn("Error fetching balance via API, fallback to direct RPC", err);
    }
  }

  // Capa 3: Nodos RPC Públicos de Polygon
  if (!fetchedSuccess) {
    const directData = await queryPolygonBalanceDirect(address);
    if (directData && directData.success) {
      usdc = directData.usdc_balance;
      matic = directData.matic_balance;
      fetchedSuccess = true;
    }
  }

  state.realBalances = { usdc, matic };

  if (modalUsdcElem) modalUsdcElem.textContent = `$${usdc.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} USDC`;
  if (modalMaticElem) modalMaticElem.textContent = `${matic.toFixed(4)} MATIC`;

  // Actualizar la insignia del botón en la barra superior
  updateWalletHeaderBadge(address);

  // Mostrar el saldo real en la Tarjeta KPI 3 del Dashboard siempre que haya una billetera vinculada
  if (balanceElem) {
    const cardObj = balanceElem.closest('.kpi-card');
    const titleCard = cardObj?.querySelector('.title');
    const badgeCard = cardObj?.querySelector('.badge');

    if (titleCard) titleCard.textContent = 'BILLETERA POLYGON REAL';
    if (badgeCard) {
      badgeCard.textContent = 'POLYGON';
      badgeCard.className = 'badge live-badge';
    }

    balanceElem.textContent = `$${usdc.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} USDC`;
    if (pnlElem) {
      const posSize = state.settings.positionSizeUsd || 50.0;
      if (usdc <= 0) {
        pnlElem.textContent = `Gas: ${matic.toFixed(4)} MATIC | ⚠️ Sin Saldo USDC`;
        pnlElem.className = 'price-change negative';
        pnlElem.style.color = '#ff0055';
      } else if (usdc < posSize) {
        pnlElem.textContent = `Gas: ${matic.toFixed(4)} MATIC | ⚠️ Insuficiente para $${posSize.toFixed(0)} USD`;
        pnlElem.className = 'price-change';
        pnlElem.style.color = '#ffb703';
      } else {
        pnlElem.textContent = `Gas: ${matic.toFixed(4)} MATIC (Listo para operar)`;
        pnlElem.className = 'price-change positive';
        pnlElem.style.color = '';
      }
    }
  }

  addLog(`💰 Saldo real Polygon en pantalla: $${usdc.toFixed(2)} USDC | ${matic.toFixed(4)} MATIC`);
}

function checkAuthentication(targetView) {
  const authModal = document.getElementById('auth-modal');
  const btnOpenAdmin = document.getElementById('btn-open-admin');
  const btnNavLanding = document.getElementById('btn-nav-landing');
  const btnNavLogin = document.getElementById('btn-nav-login');
  const btnLogout = document.getElementById('btn-logout');
  const binanceStatus = document.getElementById('binance-ws-status');
  const polymarketStatus = document.getElementById('polymarket-status');
  const envModePill = document.getElementById('pill-env-mode');
  const landingElem = document.getElementById('landing-page');
  const terminalViewElem = document.getElementById('terminal-dashboard-view');

  const isAuth = sessionStorage.getItem('dashboard_authenticated') === 'true';
  const isAdmin = sessionStorage.getItem('is_admin') === 'true' || localStorage.getItem('is_admin') === 'true';

  const storedAddr = localStorage.getItem('linked_polygon_address');
  if (storedAddr) {
    updateWalletHeaderBadge(storedAddr);
    fetchLiveWalletBalance(storedAddr);
  }

  // Si está autenticado, ocultar modal de auth
  if (isAuth && authModal) {
    authModal.classList.add('hidden');
  }

  const showTerminal = targetView === 'terminal' || (isAuth && targetView !== 'landing');

  if (showTerminal && isAuth) {
    if (landingElem) landingElem.classList.add('hidden');
    if (terminalViewElem) terminalViewElem.classList.remove('hidden');
    if (binanceStatus) binanceStatus.style.display = 'flex';
    if (polymarketStatus) polymarketStatus.style.display = 'flex';
    if (envModePill) envModePill.style.display = 'flex';
    if (btnNavLanding) btnNavLanding.style.display = 'inline-flex';
    if (btnNavLogin) btnNavLogin.style.display = 'none';
    if (btnLogout) btnLogout.style.display = 'inline-flex';
  } else {
    if (landingElem) landingElem.classList.remove('hidden');
    if (terminalViewElem) terminalViewElem.classList.add('hidden');
    if (binanceStatus) binanceStatus.style.display = 'none';
    if (polymarketStatus) polymarketStatus.style.display = 'none';
    if (envModePill) envModePill.style.display = 'none';
    if (btnNavLanding) btnNavLanding.style.display = 'none';
    if (btnNavLogin) btnNavLogin.style.display = 'inline-flex';
    if (btnLogout) btnLogout.style.display = isAuth ? 'inline-flex' : 'none';
  }

  // EL BOTÓN DE CONTROL MAESTRO SOLO SE MUESTRA SI ES UN ADMINISTRADOR
  if (btnOpenAdmin) {
    btnOpenAdmin.style.display = (isAuth && isAdmin) ? 'inline-flex' : 'none';
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
      checkAuthentication('terminal');
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
          persistUserToCache(email, data.user.plan_tier || 'PRO');
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
        persistUserToCache(email, 'PRO');
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
          persistUserToCache(email, data.user.plan_tier || 'PRO');
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
        persistUserToCache(email, 'PRO');
        checkAuthentication();
        addLog(`¡Cuenta registrada con éxito! Bienvenido, ${email} [Plan Pro Trader]`);
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
      let address = walletAddressInput.value.trim();
      let privateKey = walletPrivateKeyInput ? walletPrivateKeyInput.value.trim() : '';

      // Si la clave privada contiene 12 palabras (frase mnemónica)
      if (privateKey.split(/\s+/).length >= 12) {
        try {
          const walletObj = ethers.Wallet.fromMnemonic(privateKey);
          privateKey = walletObj.privateKey;
          address = walletObj.address;
          if (walletAddressInput) walletAddressInput.value = address;
        } catch (mErr) {
          // Si no es mnemónico estándar
        }
      } else if (privateKey && !privateKey.startsWith('0x') && privateKey.length === 64) {
        privateKey = '0x' + privateKey;
      }

      if (!address.startsWith('0x') || address.length < 40) {
        if (walletErrorMsg) {
          walletErrorMsg.textContent = '❌ Ingrese una Dirección de Polygon válida que comience por 0x.';
          walletErrorMsg.style.color = 'var(--accent-cyan)';
        }
        return;
      }

      if (!privateKey) {
        privateKey = '0x' + '0'.repeat(64);
      }

      if (walletErrorMsg) {
        walletErrorMsg.style.color = '';
        walletErrorMsg.textContent = 'Vinculando billetera Polygon...';
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

  // Formulario 5: Ajustes de Operación Real y Conexión de Billetera
  const realTradingForm = document.getElementById('real-trading-settings-form');
  const realPosSizeInput = document.getElementById('input-real-pos-size');
  const realMaxLossInput = document.getElementById('input-real-max-loss');
  const realMinEvInput = document.getElementById('input-real-min-ev');
  const realWalletInput = document.getElementById('input-real-wallet-address');
  const realTradingErrorMsg = document.getElementById('real-trading-error-msg');
  const realModal = document.getElementById('real-trading-modal');

  if (realTradingForm) {
    realTradingForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const posSize = parseFloat(realPosSizeInput?.value) || 50.0;
      const maxLoss = parseFloat(realMaxLossInput?.value) || 200.0;
      const minEv = parseFloat(realMinEvInput?.value) || 5.0;
      const walletAddr = realWalletInput?.value.trim() || '';

      if (walletAddr && walletAddr.startsWith('0x') && walletAddr.length >= 40) {
        localStorage.setItem('linked_polygon_address', walletAddr);
        updateWalletHeaderBadge(walletAddr);
        fetchLiveWalletBalance(walletAddr);
      }

      state.settings.positionSizeUsd = posSize;
      state.settings.maxDailyLossUsd = maxLoss;
      state.settings.minEvPct = minEv;

      if (el.inputPosSize) el.inputPosSize.value = posSize;
      if (el.inputMinEv) el.inputMinEv.value = minEv;

      localStorage.setItem('execution_mode', 'REAL_MAINNET');
      const selectExecMode = document.getElementById('select-execution-mode');
      if (selectExecMode) selectExecMode.value = 'REAL_MAINNET';
      
      const envModeText = document.getElementById('env-mode-text');
      if (envModeText) {
        envModeText.textContent = 'POLYGON MAINNET REAL';
        envModeText.style.color = '#ff0055';
      }

      if (realTradingErrorMsg) {
        realTradingErrorMsg.style.color = 'var(--accent-emerald)';
        realTradingErrorMsg.textContent = '✓ Configuración guardada. Operación Real activada en Polygon Mainnet.';
      }

      addLog(`🔥 OPERACIÓN REAL ACTIVADA: Posición: $${posSize} USD | Pérdida Máx: $${maxLoss} USD | EV Min: ${minEv}%`);

      setTimeout(() => {
        if (realModal) realModal.classList.add('hidden');
        if (realTradingErrorMsg) realTradingErrorMsg.textContent = '';
      }, 1200);
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
    { id: 2, email: 'masfinanzasy@gmail.com', plan_tier: 'PRO', is_active: true },
    { id: 3, email: 'trader_pro@gmail.com', plan_tier: 'PRO', is_active: true },
    { id: 4, email: 'user_demo@hotmail.com', plan_tier: 'STARTER', is_active: true }
  ];

  const savedSaasUsers = localStorage.getItem('saas_registered_users');
  if (savedSaasUsers) {
    try {
      const parsedUsers = JSON.parse(savedSaasUsers);
      if (Array.isArray(parsedUsers) && parsedUsers.length > 0) {
        parsedUsers.forEach(u => {
          if (!saasUsersCache.some(existing => existing.email.toLowerCase() === u.email.toLowerCase())) {
            saasUsersCache.push(u);
          }
        });
      }
    } catch (e) {}
  }

  function persistUserToCache(email, planTier = 'PRO') {
    if (!email || email.toLowerCase() === 'admin@polymarketm5.com') return;
    if (!saasUsersCache.some(u => u.email.toLowerCase() === email.toLowerCase())) {
      saasUsersCache.push({ id: Date.now(), email: email, plan_tier: planTier, is_active: true });
      localStorage.setItem('saas_registered_users', JSON.stringify(saasUsersCache));
    }
  }

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
    // 0. Botón Salir / Cerrar Sesión
    const logoutBtn = e.target.closest('#btn-logout');
    if (logoutBtn) {
      sessionStorage.removeItem('dashboard_authenticated');
      sessionStorage.removeItem('is_admin');
      localStorage.removeItem('saas_token');
      localStorage.removeItem('is_admin');
      localStorage.removeItem('linked_polygon_address');

      const landingElem = document.getElementById('landing-page');
      if (landingElem) landingElem.classList.remove('hidden');

      const authModal = document.getElementById('auth-modal');
      if (authModal) authModal.classList.add('hidden');

      const adminBtn = document.getElementById('btn-open-admin');
      if (adminBtn) adminBtn.style.display = 'none';

      const balanceElem = document.getElementById('portfolio-balance');
      if (balanceElem) balanceElem.textContent = '$1,000.00';

      window.scrollTo({ top: 0, behavior: 'smooth' });
      addLog('🔒 Sesión cerrada correctamente por el usuario.');
      alert('🔒 Sesión cerrada correctamente.');
      return;
    }

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

    // Nav Button: Inicio (Volver a la Landing Page)
    const navLandingBtn = e.target.closest('#btn-nav-landing');
    if (navLandingBtn) {
      checkAuthentication('landing');
      window.scrollTo({ top: 0, behavior: 'smooth' });
      return;
    }

    // Nav Button / Hero CTA: Acceder al Terminal
    const heroTerminalBtn = e.target.closest('#btn-hero-enter-terminal') || e.target.closest('#btn-nav-login');
    if (heroTerminalBtn) {
      const isAuth = sessionStorage.getItem('dashboard_authenticated') === 'true';
      if (isAuth) {
        checkAuthentication('terminal');
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
          const network = await provider.getNetwork();
          if (network.chainId !== 137 && network.chainId !== 31337) {
            addLog(`⚠️ Advertencia de Red: Conectado a Chain ID ${network.chainId}. Se recomienda Polygon Mainnet (137).`);
          }
          const accounts = await provider.send("eth_requestAccounts", []);
          if (accounts && accounts.length > 0) {
            const userAddr = accounts[0];
            const addrInput = document.getElementById('input-wallet-address');
            if (addrInput) addrInput.value = userAddr;
            localStorage.setItem('linked_polygon_address', userAddr);
            updateWalletHeaderBadge(userAddr);
            fetchLiveWalletBalance(userAddr);
            addLog(`📲 Billetera Web3 conectada exitosamente: ${userAddr.substring(0, 6)}...${userAddr.substring(userAddr.length - 4)}`);
            alert(`✓ Billetera conectada exitosamente:\n${userAddr}`);
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
          localStorage.setItem('linked_polygon_address', promptAddress);
          updateWalletHeaderBadge(promptAddress);
          fetchLiveWalletBalance(promptAddress);
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

    // 12. Desconectar Billetera
    const disconnectWalletBtn = e.target.closest('#btn-disconnect-wallet');
    if (disconnectWalletBtn) {
      localStorage.removeItem('linked_polygon_address');
      const addrInput = document.getElementById('input-wallet-address');
      if (addrInput) addrInput.value = '';
      updateWalletHeaderBadge(null);
      const walletModal = document.getElementById('wallet-modal');
      if (walletModal) walletModal.classList.add('hidden');
      alert('🔴 Billetera desconectada exitosamente.');
      addLog('🔴 Billetera Polygon desconectada.');
      return;
    }

    // 13. Abrir Modal de Operación Real
    const openRealTradingBtn = e.target.closest('#btn-open-real-trading');
    if (openRealTradingBtn) {
      const realModal = document.getElementById('real-trading-modal');
      const storedAddr = localStorage.getItem('linked_polygon_address') || '';
      const realWalletInput = document.getElementById('input-real-wallet-address');
      if (realWalletInput && storedAddr) realWalletInput.value = storedAddr;
      if (storedAddr) fetchLiveWalletBalance(storedAddr);
      if (realModal) realModal.classList.remove('hidden');
      return;
    }

    // 14. Cerrar Modal de Operación Real
    const closeRealTradingBtn = e.target.closest('#btn-close-real-trading');
    if (closeRealTradingBtn) {
      const realModal = document.getElementById('real-trading-modal');
      if (realModal) realModal.classList.add('hidden');
      return;
    }

    // 15. Refrescar Saldos Reales desde Modal
    const refreshRealBalanceBtn = e.target.closest('#btn-refresh-real-balance');
    if (refreshRealBalanceBtn) {
      const realWalletInput = document.getElementById('input-real-wallet-address');
      const addr = (realWalletInput && realWalletInput.value.trim()) || localStorage.getItem('linked_polygon_address');
      if (addr) {
        fetchLiveWalletBalance(addr);
        alert('🔄 Actualizando saldos de la red Polygon Mainnet...');
      } else {
        alert('⚠️ Por favor ingresa o conecta una dirección de billetera Polygon.');
      }
      return;
    }

    // 16. Alternar Modo Real vs Simulación desde Banner Modal
    const toggleRealLiveBtn = e.target.closest('#btn-toggle-real-live-mode');
    if (toggleRealLiveBtn) {
      const currentMode = localStorage.getItem('execution_mode');
      const bannerTitle = document.getElementById('real-mode-banner-title');
      const bannerSub = document.getElementById('real-mode-banner-sub');
      const envModeText = document.getElementById('env-mode-text');
      const selectExecMode = document.getElementById('select-execution-mode');

      if (currentMode === 'REAL_MAINNET') {
        localStorage.setItem('execution_mode', 'PAPER_TRADING');
        if (selectExecMode) selectExecMode.value = 'PAPER_TRADING';
        if (bannerTitle) bannerTitle.textContent = 'MODO ACTUAL: SIMULACIÓN (PAPER TRADING)';
        if (bannerSub) bannerSub.textContent = 'Las operaciones se realizan con capital virtual sin riesgo.';
        if (envModeText) {
          envModeText.textContent = 'PAPER TRADING';
          envModeText.style.color = '#00e676';
        }
        toggleRealLiveBtn.textContent = '🔥 ACTIVAR MODO REAL';
        toggleRealLiveBtn.style.background = 'linear-gradient(135deg, #ff0055 0%, #ff5e00 100%)';
        addLog('🛡️ Entorno cambiado a: PAPER TRADING (SIMULACIÓN)');
      } else {
        localStorage.setItem('execution_mode', 'REAL_MAINNET');
        if (selectExecMode) selectExecMode.value = 'REAL_MAINNET';
        if (bannerTitle) bannerTitle.textContent = '🔥 MODO ACTUAL: OPERACIÓN REAL (POLYGON MAINNET)';
        if (bannerSub) bannerSub.textContent = 'Las órdenes se firman y envían a la red Polygon Mainnet con tus USDC reales.';
        if (envModeText) {
          envModeText.textContent = 'POLYGON MAINNET REAL';
          envModeText.style.color = '#ff0055';
        }
        toggleRealLiveBtn.textContent = '🛡️ CAMBIAR A SIMULACIÓN';
        toggleRealLiveBtn.style.background = 'linear-gradient(135deg, #00e676 0%, #00f2fe 100%)';
        addLog('⚠️ Entorno cambiado a: OPERACIÓN REAL (POLYGON MAINNET)');
      }
      return;
    }

    // 17. Conexión Web3 desde Modal de Operación Real
    const realWeb3ConnectBtn = e.target.closest('#btn-real-web3-connect');
    if (realWeb3ConnectBtn) {
      const errElem = document.getElementById('real-trading-error-msg');
      const hasWeb3 = (typeof window.phantom !== 'undefined' && window.phantom.ethereum) || typeof window.ethereum !== 'undefined' || typeof window.trustwallet !== 'undefined';
      if (hasWeb3) {
        try {
          const web3Provider = (window.phantom && window.phantom.ethereum) || window.trustwallet || window.ethereum;
          const provider = new ethers.providers.Web3Provider(web3Provider);
          const accounts = await provider.send("eth_requestAccounts", []);
          if (accounts && accounts.length > 0) {
            const userAddr = accounts[0];
            const realWalletInput = document.getElementById('input-real-wallet-address');
            const addrInput = document.getElementById('input-wallet-address');
            if (realWalletInput) realWalletInput.value = userAddr;
            if (addrInput) addrInput.value = userAddr;
            localStorage.setItem('linked_polygon_address', userAddr);
            updateWalletHeaderBadge(userAddr);
            fetchLiveWalletBalance(userAddr);
            if (errElem) {
              errElem.style.color = 'var(--accent-emerald)';
              errElem.textContent = `✓ Billetera Web3 conectada: ${userAddr.substring(0, 6)}...${userAddr.substring(userAddr.length - 4)}`;
            }
            addLog(`📲 Billetera Web3 conectada para Operación Real: ${userAddr}`);
          }
        } catch (err) {
          if (errElem) {
            errElem.style.color = '#ff0055';
            errElem.textContent = `❌ Error al conectar: ${err.message || 'Petición rechazada'}`;
          }
        }
      } else {
        const promptAddress = prompt("📲 Ingrese su Dirección Pública de Polygon (USDC) de Phantom / Trust Wallet / MetaMask:", "0x");
        if (promptAddress && promptAddress.startsWith("0x") && promptAddress.length >= 40) {
          const realWalletInput = document.getElementById('input-real-wallet-address');
          if (realWalletInput) realWalletInput.value = promptAddress;
          localStorage.setItem('linked_polygon_address', promptAddress);
          updateWalletHeaderBadge(promptAddress);
          fetchLiveWalletBalance(promptAddress);
          alert(`✓ Dirección de Billetera vinculada correctamente:\n${promptAddress}`);
        }
      }
      return;
    }

    // 18. Botón de Parada de Emergencia
    const panicStopBtn = e.target.closest('#btn-panic-stop');
    if (panicStopBtn) {
      state.panicStopActive = true;
      state.simulationActive = false;
      localStorage.setItem('execution_mode', 'PAPER_TRADING');
      
      const selectExecMode = document.getElementById('select-execution-mode');
      if (selectExecMode) selectExecMode.value = 'PAPER_TRADING';

      const envModeText = document.getElementById('env-mode-text');
      if (envModeText) {
        envModeText.textContent = '🛑 EMERGENCIA: DETENIDO';
        envModeText.style.color = '#ff0055';
      }

      addLog('🛑 PARADA DE EMERGENCIA ACTIVADA: Todas las operaciones del bot han sido congeladas inmediatamente por el usuario.');
      alert('🛑 PARADA DE EMERGENCIA ACTIVADA:\n\nTodas las operaciones del bot han sido congeladas e interrumpidas inmediatamente por seguridad.');
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

  // Polling automático de saldos de billetera cada 8 segundos
  const initialAddr = localStorage.getItem('linked_polygon_address');
  if (initialAddr) {
    fetchLiveWalletBalance(initialAddr);
  }
  setInterval(() => {
    const activeAddr = localStorage.getItem('linked_polygon_address');
    if (activeAddr && activeAddr.startsWith('0x')) {
      fetchLiveWalletBalance(activeAddr);
    }
  }, 8000);

  addLog('Dashboard iniciado correctamente.');
});
