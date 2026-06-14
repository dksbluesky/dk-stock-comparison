const BUY_COMM = 0.001425;   // 手續費
const SELL_TAX = 0.003;      // 證交稅
const BENCHMARK = "0050.TW";

const CORS_PROXIES = [
  url => `https://corsproxy.io/?url=${encodeURIComponent(url)}`,
  url => `https://api.allorigins.win/raw?url=${encodeURIComponent(url)}`,
];

// ── Date helpers ─────────────────────────────────────────────────────────
function ymd(d) {
  return d.toISOString().slice(0, 10);
}
function dateOnly(d) {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate());
}
function addDays(d, n) {
  const r = new Date(d);
  r.setDate(r.getDate() + n);
  return r;
}
function yearsAgo(n) {
  const d = new Date();
  d.setFullYear(d.getFullYear() - n);
  return d;
}

// ── Fetch ────────────────────────────────────────────────────────────────
async function fetchYahoo(symbol, period1, period2) {
  const target = `https://query1.finance.yahoo.com/v8/finance/chart/${encodeURIComponent(symbol)}` +
    `?period1=${Math.floor(period1.getTime() / 1000)}&period2=${Math.floor(period2.getTime() / 1000)}` +
    `&interval=1d&events=div&includeAdjustedClose=true`;

  let lastErr;
  for (const proxy of CORS_PROXIES) {
    try {
      const res = await fetch(proxy(target));
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      const result = json?.chart?.result?.[0];
      if (!result || !result.timestamp) throw new Error("No data");
      return result;
    } catch (e) {
      lastErr = e;
    }
  }
  throw lastErr || new Error("All proxies failed");
}

// ── Array helpers ────────────────────────────────────────────────────────
function ffill(arr) {
  let last = null;
  return arr.map(v => {
    if (v != null && !Number.isNaN(v)) { last = v; return v; }
    return last;
  });
}
function bfill(arr) {
  return ffill(arr.slice().reverse()).reverse();
}
function ffillBfill(arr) {
  return bfill(ffill(arr));
}

// ── Core calculations (ported from Python) ─────────────────────────────────
function netReturn(cap, p0, p1, prem) {
  const entry = p0 + prem;
  const shares = Math.floor(cap / entry);
  const usedCap = shares * entry;
  const cashLeft = cap - usedCap;
  const buyCost = usedCap * BUY_COMM;
  const proceeds = shares * p1;
  const sellCost = proceeds * SELL_TAX;
  const net = proceeds - buyCost - sellCost + cashLeft;
  return [net, (net - cap) / cap * 100];
}

function maxDrawdown(values) {
  let rollMax = -Infinity;
  let minDD = 0;
  for (const v of values) {
    if (v > rollMax) rollMax = v;
    const dd = (v - rollMax) / rollMax * 100;
    if (dd < minDD) minDD = dd;
  }
  return minDD;
}

function checkDivCuts(divs) {
  if (divs.length === 0) return "No dividends";
  const annual = {};
  for (const d of divs) {
    const y = d.date.getFullYear();
    annual[y] = (annual[y] || 0) + d.amount;
  }
  const currentYear = new Date().getFullYear();
  const years = Object.keys(annual).map(Number).filter(y => annual[y] > 0 && y < currentYear).sort((a, b) => a - b);
  if (years.length < 2) return "< 2 yrs data";
  const cuts = [];
  for (let i = 1; i < years.length; i++) {
    if (annual[years[i]] < annual[years[i - 1]] * 0.9) cuts.push(years[i]);
  }
  return cuts.length ? `Cut: [${cuts.join(", ")}]` : "Consistent ✓";
}

function fillipAnalysis(rawCloseSeries, divs) {
  if (divs.length === 0 || rawCloseSeries.length === 0) return ["No dividends", "—"];

  const cutoff = yearsAgo(3);
  const recent = divs.filter(d => d.date >= cutoff);
  if (recent.length === 0) return ["No recent divs", "—"];

  const fillDays = [];
  for (const div of recent) {
    const exDate = dateOnly(div.date);
    const pre = rawCloseSeries.filter(p => p.date < exDate);
    if (pre.length === 0) continue;
    const prePrice = pre[pre.length - 1].value;

    const after = rawCloseSeries.filter(p => p.date >= exDate);
    if (after.length === 0) continue;

    const idx = after.findIndex(p => p.value >= prePrice);
    fillDays.push(idx !== -1 ? idx + 1 : null);
  }

  if (fillDays.length === 0) return ["—", "—"];
  const filled = fillDays.filter(x => x !== null);
  const nFilled = filled.length;
  const nTotal = fillDays.length;
  const avg = nFilled ? filled.reduce((a, b) => a + b, 0) / nFilled : null;

  return [`${nFilled}/${nTotal} filled`, avg !== null ? `${Math.round(avg)} 天` : "未填息"];
}

// ── Rendering ────────────────────────────────────────────────────────────
function setStatus(msg, cls) {
  const el = document.getElementById("status");
  el.textContent = msg;
  el.className = cls || "";
}

let chartInstance = null;

function renderResults({ fighters, dataset, startDate, endDate }) {
  const cardsEl = document.getElementById("cards");
  const tbody = document.querySelector("#analysisTable tbody");
  cardsEl.innerHTML = "";
  tbody.innerHTML = "";

  const results = {};
  let bestRet = -Infinity;
  let bestTick = null;

  // ── Section 1: Returns ──
  for (const [ticker, prem] of Object.entries(fighters)) {
    const d = dataset[ticker];
    const card = document.createElement("div");
    card.className = "card";

    if (!d || d.cmpAdj.length === 0) {
      card.classList.add("err");
      card.textContent = `❌ ${ticker}: No data`;
      cardsEl.appendChild(card);
      continue;
    }

    const p0 = d.cmpAdj[0].value;
    const p1 = d.cmpAdj[d.cmpAdj.length - 1].value;
    if (!p0) {
      card.classList.add("err");
      card.textContent = `⚠️ ${ticker}: Invalid price`;
      cardsEl.appendChild(card);
      continue;
    }

    const entry = p0 + prem;
    const premPct = (prem / p0) * 100;
    const [final, ret] = netReturn(capitalValue(), p0, p1, prem);
    results[ticker] = { entry, ret, final };

    if (ret > bestRet) { bestRet = ret; bestTick = ticker; }

    const gain = Math.round(final - capitalValue());
    card.innerHTML = `
      <div class="label">${ticker} (prem ${prem.toFixed(1)} NTD = ${premPct.toFixed(2)}%)</div>
      <div class="value">NT$${Math.round(final).toLocaleString()}</div>
      <div class="delta ${gain >= 0 ? "pos" : "neg"}">${gain >= 0 ? "+" : ""}${gain.toLocaleString()} NTD | ${ret >= 0 ? "+" : ""}${ret.toFixed(2)}%</div>
    `;
    cardsEl.appendChild(card);
  }

  // ── Section 2: Deep analysis ──
  for (const ticker of Object.keys(fighters)) {
    const d = dataset[ticker];
    if (!d || d.threeYAdj.length === 0) continue;

    const values = d.threeYAdj.map(p => p.value);
    const hi = Math.max(...values);
    const lo = Math.min(...values);
    const swing = ((hi - lo) / hi) * 100;
    const worstDD = maxDrawdown(values);

    const divLabel = checkDivCuts(d.dividends);
    const [fillRate, fillAvg] = fillipAnalysis(d.threeYRaw, d.dividends);

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${ticker}</td>
      <td>${hi.toLocaleString(undefined, { maximumFractionDigits: 0 })}</td>
      <td>${lo.toLocaleString(undefined, { maximumFractionDigits: 0 })}</td>
      <td>${swing.toFixed(1)}%</td>
      <td>${worstDD.toFixed(1)}%</td>
      <td>${divLabel}</td>
      <td>${fillRate}</td>
      <td>${fillAvg}</td>
    `;
    tbody.appendChild(tr);
  }

  // ── Section 3: Winner ──
  const winnerEl = document.getElementById("winner");
  if (bestTick) {
    const label = bestTick === "2330.TW" ? `The King (${bestTick})` : bestTick;
    winnerEl.textContent = `🏆 WINNER: ${label} — ${bestRet.toFixed(2)}% net return`;
  } else {
    winnerEl.textContent = "";
  }

  // ── Section 4: Chart ──
  const chartTickers = Object.keys(fighters).filter(t => results[t] && dataset[t]?.cmpAdj.length);
  const ctx = document.getElementById("chart").getContext("2d");
  if (chartInstance) chartInstance.destroy();

  if (chartTickers.length) {
    const labels = dataset[chartTickers[0]].cmpAdj.map(p => ymd(p.date));
    const colors = ["#ff4b4b", "#4b9bff", "#6bff8f", "#ffcc66"];
    chartInstance = new Chart(ctx, {
      type: "line",
      data: {
        labels,
        datasets: chartTickers.map((t, i) => ({
          label: t,
          data: dataset[t].cmpAdj.map(p => (p.value / results[t].entry) * 100),
          borderColor: colors[i % colors.length],
          fill: false,
          pointRadius: 0,
          borderWidth: 2,
        })),
      },
      options: {
        responsive: true,
        scales: {
          x: { ticks: { color: "#aaa", maxTicksLimit: 10 }, grid: { color: "#2a2f3a" } },
          y: { ticks: { color: "#aaa" }, grid: { color: "#2a2f3a" } },
        },
        plugins: { legend: { labels: { color: "#e6e6e6" } } },
      },
    });
  }

  document.getElementById("results").classList.remove("hidden");
}

function capitalValue() {
  return Number(document.getElementById("capital").value);
}

// ── Main run ─────────────────────────────────────────────────────────────
async function run() {
  const runBtn = document.getElementById("runBtn");
  runBtn.disabled = true;
  document.getElementById("results").classList.add("hidden");

  const startDate = dateOnly(new Date(document.getElementById("startDate").value));
  const endDate = dateOnly(new Date(document.getElementById("endDate").value));

  const fighters = {};
  fighters["2330.TW"] = Number(document.getElementById("kingPrem").value);
  const challengers = [
    [document.getElementById("c1").value.trim(), Number(document.getElementById("p1").value)],
    [document.getElementById("c2").value.trim(), Number(document.getElementById("p2").value)],
    [document.getElementById("c3").value.trim(), Number(document.getElementById("p3").value)],
  ];
  for (const [ticker, prem] of challengers) {
    if (ticker) fighters[ticker] = prem;
  }

  const fetchList = Array.from(new Set([...Object.keys(fighters), BENCHMARK]));

  const threeYAgo = yearsAgo(3);
  const period1 = startDate < threeYAgo ? startDate : threeYAgo;
  const period2 = addDays(new Date(), 1); // exclusive end -> include today

  setStatus("⏳ Downloading price data…");

  const dataset = {};
  try {
    await Promise.all(fetchList.map(async ticker => {
      const result = await fetchYahoo(ticker, period1, period2);
      const timestamps = result.timestamp.map(t => new Date(t * 1000));
      const quote = result.indicators.quote[0];
      const adj = result.indicators.adjclose?.[0]?.adjclose || quote.close;
      const close = ffillBfill(quote.close);
      const adjclose = ffillBfill(adj);

      const dividends = [];
      const divEvents = result.events?.dividends;
      if (divEvents) {
        for (const ev of Object.values(divEvents)) {
          dividends.push({ date: new Date(ev.date * 1000), amount: ev.amount });
        }
        dividends.sort((a, b) => a.date - b.date);
      }

      const all = timestamps.map((date, i) => ({
        date: dateOnly(date),
        close: close[i],
        adjclose: adjclose[i],
      }));

      const cmpAdj = all
        .filter(p => p.date >= startDate && p.date <= endDate)
        .map(p => ({ date: p.date, value: p.adjclose }));

      const threeYAdj = all
        .filter(p => p.date >= threeYAgo)
        .map(p => ({ date: p.date, value: p.adjclose }));

      const threeYRaw = all
        .filter(p => p.date >= threeYAgo)
        .map(p => ({ date: p.date, value: p.close }));

      dataset[ticker] = { cmpAdj, threeYAdj, threeYRaw, dividends };
    }));
  } catch (e) {
    setStatus(`❌ Download failed: ${e.message}`, "error");
    runBtn.disabled = false;
    return;
  }

  setStatus("✅ Data loaded!", "success");
  renderResults({ fighters, dataset, startDate, endDate });
  runBtn.disabled = false;
}

// ── Init ─────────────────────────────────────────────────────────────────
window.addEventListener("DOMContentLoaded", () => {
  const today = new Date();
  document.getElementById("endDate").value = ymd(today);
  document.getElementById("startDate").value = "2025-10-01";
  document.getElementById("runBtn").addEventListener("click", run);
});
