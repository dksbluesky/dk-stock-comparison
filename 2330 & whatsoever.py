import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# --- 1. App Config ---
st.set_page_config(page_title="Universal Stock Gladiator", page_icon="⚔️")
st.title("⚔️ Universal Stock Gladiator")
st.markdown("### The King (2330) vs. The World")
st.info("💡 **Tip:** OTC stocks (like Gudeng) need `.TWO`. Listed stocks need `.TW`.")

# --- 2. Sidebar ---
st.sidebar.header("⚙️ Match Settings")
start_date = st.sidebar.date_input("Start Date", value=pd.to_datetime("2025-10-01"))
end_date = st.sidebar.date_input("End Date", value=pd.to_datetime("today"))
capital = st.sidebar.number_input("Capital (NTD)", value=400000, step=10000)

st.sidebar.markdown("---")
st.sidebar.header("🥊 The Fighters")

fighters = {}

# The King
st.sidebar.markdown("### 👑 The King")
ticker_king = "2330.TW"
prem_king = st.sidebar.number_input(f"Premium for 2330", value=5.0, step=0.5)
fighters[ticker_king] = prem_king

# The Challengers
st.sidebar.markdown("### ⚔️ The Challengers")
c1_ticker = st.sidebar.text_input("Challenger 1", value="3680.TWO")
fighters[c1_ticker] = st.sidebar.number_input(f"Prem for {c1_ticker}", value=0.0)

c2_ticker = st.sidebar.text_input("Challenger 2", value="2317.TW")
fighters[c2_ticker] = st.sidebar.number_input(f"Prem for {c2_ticker}", value=0.5)

c3_ticker = st.sidebar.text_input("Challenger 3", value="0050.TW")
fighters[c3_ticker] = st.sidebar.number_input(f"Prem for {c3_ticker}", value=0.0)

# --- 3. Run Logic ---
if st.button("🚀 Run Simulation"):
    
    # Remove empty inputs if user cleared a box
    valid_fighters = {k: v for k, v in fighters.items() if k.strip() != ""}
    
    with st.spinner(f"Downloading data..."):
        try:
            ticker_list = list(valid_fighters.keys())
            data = yf.download(ticker_list, start=start_date, end=end_date, progress=False)["Close"]
            
            # Safe Cleaning
            data = data.ffill().bfill()
            
            # --- LOOP THROUGH FIGHTERS ---
            best_return = -999
            best_ticker = "None"
            
            st.success("Simulation Complete!")
            st.markdown("---")
            
            # Create grid
            cols = st.columns(2) + st.columns(2)
            
            for i, (ticker, premium) in enumerate(valid_fighters.items()):
                with cols[i]:
                    # SAFETY CHECK 1: Did we get the column?
                    if ticker not in data.columns:
                        st.error(f"❌ {ticker}: No Data found.")
                        continue
                    
                    # SAFETY CHECK 2: Is the data actually numbers?
                    series = data[ticker]
                    if series.isnull().all():
                        st.error(f"❌ {ticker}: Data is empty (NaN).")
                        continue
                        
                    # Math
                    p_start = series.iloc[0]
                    p_end   = series.iloc[-1]
                    
                    # SAFETY CHECK 3: Avoid division by zero or NaN math
                    if pd.isna(p_start) or pd.isna(p_end) or p_start == 0:
                        st.warning(f"⚠️ {ticker}: Price data invalid.")
                        continue
                        
                    entry_price = p_start + premium
                    shares = capital / entry_price
                    final_val = shares * p_end
                    ret_pct = ((final_val - capital) / capital) * 100
                    
                    # Track Winner
                    if ret_pct > best_return:
                        best_return = ret_pct
                        best_ticker = ticker
                    
                    # Display
                    st.metric(
                        label=f"{ticker} (Prem: ${premium})", 
                        value=f"${int(final_val):,}", 
                        delta=f"{ret_pct:.2f}%"
                    )

            # --- VERDICT ---
            st.markdown("---")
            if best_ticker != "None":
                if best_ticker == ticker_king:
                    st.balloons()
                    st.success(f"🏆 **WINNER: The King ({best_ticker})**")
                else:
                    st.balloons()
                    st.success(f"🏆 **WINNER: {best_ticker}**")
                    st.write(f"Beat the others with **{best_return:.2f}%** return.")

            # --- CHART ---
            st.markdown("### 📈 Visual Race")
            if not data.empty:
                # Normalize only valid columns
                valid_cols = [c for c in valid_fighters.keys() if c in data.columns]
                chart_data = data[valid_cols] / data[valid_cols].iloc[0] * 100
                st.line_chart(chart_data)

        except Exception as e:
            st.error(f"Critical Error: {e}")
