import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="Universal Stock Gladiator", page_icon="⚔️", layout="wide")
st.title("⚔️ Universal Stock Gladiator")
st.markdown("### The King (2330) vs. The World")
st.info("💡 OTC stocks need `.TWO`. Listed stocks need `.TW`.")

# ── Sidebar ───────────────────────────────────────────────────────────────────
st.sidebar.header("⚙️ Match Settings")
start_date = st.sidebar.date_input("Start Date", value=pd.to_datetime("2025-10-01"))
end_date   = st.sidebar.date_input("End Date",   value=pd.to_datetime("today"))
capital    = st.sidebar.number_input("Capital (NTD)", value=400_000, step=10_000)

st.sidebar.markdown("---")
st.sidebar.header("🥊 The Fighters")

fighters = {}

st.sidebar.markdown("### 👑 The King")
KING = "2330.TW"
fighters[KING] = st.sidebar.number_input("Premium for 2330", value=5.0, step=0.5)

st.sidebar.markdown("### ⚔️ The Challengers")
c1 = st.sidebar.text_input("Challenger 1", value="3680.TWO")
fighters[c1] = st.sidebar.number_input(f"Prem for {c1}", value=0.0, key="p1")
c2 = st.sidebar.text_input("Challenger 2", value="2317.TW")
fighters[c2] = st.sidebar.number_input(f"Prem for {c2}", value=0.5, key="p2")
c3 = st.sidebar.text_input("Challenger 3", value="0050.TW")
fighters[c3] = st.sidebar.number_input(f"Prem for {c3}", value=0.0, key="p3")

# ── Constants ─────────────────────────────────────────────────────────────────
BUY_COMM  = 0.001425   # 手續費
SELL_TAX  = 0.003      # 證交稅
BENCHMARK = "0050.TW"


# ── Helpers ───────────────────────────────────────────────────────────────────
def net_return(cap, p0, p1, prem):
    """Net return after Taiwan buy commission and sell tax."""
    entry     = p0 + prem
    shares    = cap / entry
    buy_cost  = shares * entry * BUY_COMM
    proceeds  = shares * p1
    sell_cost = proceeds * SELL_TAX
    net       = proceeds - buy_cost - sell_cost
    return net, (net - cap) / cap * 100


def max_drawdown(s):
    roll_max = s.cummax()
    return float(((s - roll_max) / roll_max * 100).min())


def strip_tz(idx):
    return idx.tz_convert(None) if idx.tz is not None else idx


def check_div_cuts(divs):
    """Compare annual dividend totals year-on-year; >10% drop counts as a cut."""
    if divs.empty:
        return "No dividends"
    d = divs.copy()
    d.index = strip_tz(d.index)
    annual = d.resample("YE").sum()
    annual = annual[annual > 0]
    if len(annual) < 2:
        return "< 2 yrs data"
    cuts = [
        annual.index[i].year
        for i in range(1, len(annual))
        if annual.iloc[i] < annual.iloc[i - 1] * 0.9
    ]
    return f"Cut: {cuts}" if cuts else "Consistent ✓"


def fillip_analysis(raw_close, divs):
    """
    Measures 填息 using unadjusted close prices so the ex-div drop is visible.
    For each 除息 event in the last 3 years, counts trading days until the price
    closes back at or above the pre-ex-div close.
    """
    if divs.empty or raw_close.empty:
        return "No dividends", "—"

    close = raw_close.copy()
    close.index = strip_tz(close.index)

    d = divs.copy()
    d.index = strip_tz(d.index)
    cutoff = pd.Timestamp.now() - pd.DateOffset(years=3)
    recent = d[d.index >= cutoff]

    if recent.empty:
        return "No recent divs", "—"

    fill_days = []
    for ex_date in recent.index:
        ex_date   = pd.Timestamp(ex_date).normalize()
        pre       = close[close.index < ex_date]
        if pre.empty:
            continue
        pre_price = float(pre.iloc[-1])
        after     = close[close.index >= ex_date]
        if after.empty:
            continue
        filled = after[after >= pre_price]
        if not filled.empty:
            fill_days.append(int((after.index <= filled.index[0]).sum()))
        else:
            fill_days.append(None)  # 尚未填息

    if not fill_days:
        return "—", "—"

    n_filled = sum(1 for x in fill_days if x is not None)
    n_total  = len(fill_days)
    avg      = np.mean([x for x in fill_days if x is not None]) if n_filled else None

    return (
        f"{n_filled}/{n_total} filled",
        f"{avg:.0f} 天" if avg is not None else "未填息",
    )


def to_df(obj, fallback_name):
    """Promote Series to DataFrame — happens when yfinance gets a single ticker."""
    return obj.to_frame(name=fallback_name) if isinstance(obj, pd.Series) else obj


# ── Run ───────────────────────────────────────────────────────────────────────
if st.button("🚀 Run Simulation"):
    valid = {k: v for k, v in fighters.items() if k.strip()}
    fetch = list(set(list(valid.keys()) + [BENCHMARK]))
    three_yr = (pd.Timestamp.now() - pd.DateOffset(years=3)).strftime("%Y-%m-%d")

    with st.spinner("Downloading price data…"):
        try:
            data = to_df(
                yf.download(fetch, start=start_date, end=end_date,
                            auto_adjust=True, progress=False)["Close"],
                fetch[0],
            )
            data_3y = to_df(
                yf.download(fetch, start=three_yr, end=end_date,
                            auto_adjust=True, progress=False)["Close"],
                fetch[0],
            )
            # Unadjusted prices for 填息 so the ex-div price drop is preserved
            data_raw = to_df(
                yf.download(fetch, start=three_yr, end=end_date,
                            auto_adjust=False, progress=False)["Close"],
                fetch[0],
            )
        except Exception as e:
            st.error(f"Download failed: {e}")
            st.stop()

    data     = data.ffill().bfill()
    data_3y  = data_3y.ffill().bfill()
    data_raw = data_raw.ffill().bfill()

    # Benchmark return for the selected comparison window
    bench_ret = None
    if BENCHMARK in data.columns:
        bp0 = float(data[BENCHMARK].iloc[0])
        bp1 = float(data[BENCHMARK].iloc[-1])
        if bp0 > 0:
            _, bench_ret = net_return(capital, bp0, bp1, 0)

    st.success("Data loaded!")
    st.markdown("---")

    # ── Section 1: Return cards ───────────────────────────────────────────
    st.markdown("### 💰 Returns  *(手續費 0.1425% + 證交稅 0.3% already deducted)*")

    results   = {}
    best_ret  = -999
    best_tick = "None"

    for i, (ticker, prem) in enumerate(valid.items()):
        if i % 2 == 0:
            cols = st.columns(2)
        with cols[i % 2]:
            if ticker not in data.columns or data[ticker].isnull().all():
                st.error(f"❌ {ticker}: No data")
                continue
            p0 = float(data[ticker].iloc[0])
            p1 = float(data[ticker].iloc[-1])
            if pd.isna(p0) or p0 == 0:
                st.warning(f"⚠️ {ticker}: Invalid price")
                continue

            entry    = p0 + prem
            prem_pct = prem / p0 * 100
            final, ret = net_return(capital, p0, p1, prem)
            results[ticker] = {"entry": entry, "ret": ret, "final": final}

            if ret > best_ret:
                best_ret  = ret
                best_tick = ticker

            alpha_tag = ""
            if bench_ret is not None and ticker != BENCHMARK:
                a = ret - bench_ret
                alpha_tag = f"  |  vs 0050: {'▲' if a >= 0 else '▼'}{abs(a):.1f}%"

            st.metric(
                label=f"{ticker}  (prem {prem:.1f} NTD = {prem_pct:.2f}%)",
                value=f"NT${int(final):,}",
                delta=f"{ret:.2f}%{alpha_tag}",
            )

    # ── Section 2: Deep analysis table ───────────────────────────────────
    st.markdown("---")
    st.markdown("### 🔬 Deep Analysis  *(3-Year View)*")

    rows = []
    with st.spinner("Fetching dividend history…"):
        for ticker in valid:
            if ticker not in data_3y.columns:
                continue
            s3 = data_3y[ticker].dropna()
            sr = data_raw[ticker].dropna() if ticker in data_raw.columns else pd.Series(dtype=float)
            if s3.empty:
                continue

            hi, lo   = float(s3.max()), float(s3.min())
            swing    = (hi - lo) / hi * 100
            worst_dd = max_drawdown(s3)

            # Performance vs 0050 over the same 3-year window
            if BENCHMARK in data_3y.columns and ticker != BENCHMARK:
                ret_3y   = (float(s3.iloc[-1]) / float(s3.iloc[0]) - 1) * 100
                bench_3y = (
                    float(data_3y[BENCHMARK].iloc[-1]) / float(data_3y[BENCHMARK].iloc[0]) - 1
                ) * 100
                diff  = ret_3y - bench_3y
                vs050 = f"{'▲' if diff >= 0 else '▼'}{abs(diff):.1f}%"
            else:
                vs050 = "— (is 0050)"

            # Dividend + 填息
            try:
                t         = yf.Ticker(ticker)
                divs      = t.dividends
                div_label = check_div_cuts(divs)
                fill_rate, fill_avg = fillip_analysis(sr, divs)
            except Exception:
                div_label = "Error"
                fill_rate = "—"
                fill_avg  = "—"

            rows.append({
                "Ticker":         ticker,
                "3Y High":        f"{hi:,.0f}",
                "3Y Low":         f"{lo:,.0f}",
                "Price Swing":    f"{swing:.1f}%",
                "Worst Drawdown": f"{worst_dd:.1f}%",
                "Dividend":       div_label,
                "填息 (3Y)":      fill_rate,
                "Avg 填息 Days":  fill_avg,
                "vs 0050 (3Y)":   vs050,
            })

    if rows:
        st.dataframe(
            pd.DataFrame(rows).set_index("Ticker"),
            use_container_width=True,
        )

    # ── Section 3: Verdict ────────────────────────────────────────────────
    st.markdown("---")
    if best_tick != "None":
        label = f"The King ({best_tick})" if best_tick == KING else best_tick
        st.balloons()
        st.success(f"🏆 **WINNER: {label}** — {best_ret:.2f}% net return")

    # ── Section 4: Chart (indexed to your actual entry price) ─────────────
    st.markdown("### 📈 Visual Race  *(indexed to your entry price = 100)*")
    chart_tickers = [t for t in valid if t in data.columns and t in results]
    if chart_tickers:
        chart = pd.DataFrame({
            t: data[t] / results[t]["entry"] * 100
            for t in chart_tickers
        })
        st.line_chart(chart)
