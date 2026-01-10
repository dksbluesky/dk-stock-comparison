import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# --- 1. App Title & Config ---
st.set_page_config(page_title="Stock Gladiator", page_icon="🥊")
st.title("🥊 The Stock Gladiator")
st.markdown("Compare **3680 vs 2317 vs 2330 vs 0050**")

# --- 2. Sidebar (Your Control Panel) ---
st.sidebar.header("⚙️ Simulation Settings")

# Date Pickers
start_date = st.sidebar.date_input("Start Date", value=pd.to_datetime("2025-10-01"))
end_date = st.sidebar.date_input("End Date", value=pd.to_datetime("today"))

# Money Settings
capital = st.sidebar.number_input("Capital (NTD)", value=400000, step=10000)
st.sidebar.markdown("---")
st.sidebar.write("### 🐢 Friction / Premium")
premium_2330 = st.sidebar.number_input("2330 Premium (TWD)", value=5.0, step=0.5, help="Extra price paid per share for TSMC Odd Lots")
premium_2317 = st.sidebar.number_input("2317 Premium (TWD)", value=0.5, step=0.1, help="Extra price paid per share for Hon Hai")

# --- 3. The Run Logic ---
if st.button("🚀 Run Simulation"):
    
    with st.spinner(f"Downloading market data from {start_date} to {end_date}..."):
        try:
        # CHANGE 1: Use .TWO for Gudeng (OTC Market)           
            tickers = ["3680.TWO", "0050.TW", "2330.TW", "2317.TW"]
            data = yf.download(tickers, start=start_date, end=end_date, progress=False)["Close"]
           # Instead of dropping rows immediately, we fill gaps forward (ffill) and backward (bfill)
            data = data.ffill().bfill()
            
           # CHANGE 3: Handle the ".TWO" column name change
            # (Yahoo returns the column name exactly as requested)
            if len(data) == 0:
                st.error("❌ No data found! Try checking the date range.")
                st.stop()

            # --- CALCULATIONS ---
            
           # --- CALCULATIONS ---
            # Update the variable to match the new .TWO ticker
            p_start_3680 = data["3680.TWO"].iloc[0]
            p_end_3680   = data["3680.TWO"].iloc[-1]
            shares_3680  = capital / p_start_3680
            final_3680   = shares_3680 * p_end_3680
            ret_3680     = ((final_3680 - capital) / capital) * 100

            # 2. 2317 (Hon Hai) w/ Premium
            p_start_2317 = data["2317.TW"].iloc[0]
            p_end_2317   = data["2317.TW"].iloc[-1]
            shares_2317  = capital / (p_start_2317 + premium_2317)
            final_2317   = shares_2317 * p_end_2317
            ret_2317     = ((final_2317 - capital) / capital) * 100

            # 3. 2330 (TSMC) w/ Premium
            p_start_2330 = data["2330.TW"].iloc[0]
            p_end_2330   = data["2330.TW"].iloc[-1]
            shares_2330  = capital / (p_start_2330 + premium_2330)
            final_2330   = shares_2330 * p_end_2330
            ret_2330     = ((final_2330 - capital) / capital) * 100

            # 4. 0050 (Safe ETF)
            p_start_050 = data["0050.TW"].iloc[0]
            p_end_050   = data["0050.TW"].iloc[-1]
            shares_050  = capital / p_start_050
            final_050   = shares_050 * p_end_050
            ret_050     = ((final_050 - capital) / capital) * 100

             # ... (Calculations stay the same) ...

            # --- DISPLAY RESULTS ---
            st.success("Simulation Complete!")
            
            # Row 1
            col1, col2 = st.columns(2)
            # FIX: Label changed to Gudeng Precision
            col1.metric("3680 (Gudeng / 家登)", f"${int(final_3680):,}", f"{ret_3680:.2f}%")
            col2.metric("2317 (Hon Hai)", f"${int(final_2317):,}", f"{ret_2317:.2f}%")
            
            # Row 2
            col3, col4 = st.columns(2)
            col3.metric("2330 (TSMC)", f"${int(final_2330):,}", f"{ret_2330:.2f}%")
            col4.metric("0050 (Safe ETF)", f"${int(final_050):,}", f"{ret_050:.2f}%")

            st.markdown("---")

            # --- THE VERDICT ---
            winner_val = max(final_3680, final_2317, final_2330, final_050)
            
            if winner_val == final_3680:
                st.balloons()
                # FIX: Text updated to match Gudeng
                st.success("🏆 **WINNER: 3680 (Gudeng Precision)**")
                st.write("The EUV Pod supplier beat the King! (High Beta on TSMC)")
            elif winner_val == final_2317:
                st.balloons()
                st.success("🏆 **WINNER: 2317 (Hon Hai)**")
                st.write("The AI Server rotation trade paid off!")
            elif winner_val == final_2330:
                st.balloons()
                st.success("🏆 **WINNER: 2330 (TSMC)**")
                st.write("The King is still King, even with the price premium.")
            else:
                st.info("🏆 **WINNER: 0050 (Safety)**")
                st.write("Slow and steady won the race.")

            # --- BONUS: Simple Chart ---
            st.markdown("### 📈 Visual Comparison (Rebased to 100)")
            # Rebase all to start at 100 for fair comparison
            chart_data = data / data.iloc[0] * 100
            st.line_chart(chart_data)

        except Exception as e:
            st.error(f"Something went wrong: {e}")
