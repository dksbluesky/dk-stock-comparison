import streamlit as st
import yfinance as yf
import pandas as pd

# --- 1. App Config ---
st.set_page_config(page_title="Universal Stock Gladiator", page_icon="⚔️")
st.title("⚔️ Universal Stock Gladiator")
st.markdown("### The King (2330) vs. The World")
st.info("💡 **Tip:** For OTC stocks (like Gudeng), type `.TWO` (e.g., `3680.TWO`). For Listed stocks, type `.TW`.")

# --- 2. Sidebar: The Control Center ---
st.sidebar.header("⚙️ Match Settings")

# Date & Capital
start_date = st.sidebar.date_input("Start Date", value=pd.to_datetime("2025-10-01"))
end_date = st.sidebar.date_input("End Date", value=pd.to_datetime("today"))
capital = st.sidebar.number_input("Capital (NTD)", value=400000, step=10000)

st.sidebar.markdown("---")
st.sidebar.header("🥊 The Fighters")

# --- DYNAMIC INPUTS ---
# We create a dictionary to store your fighters
fighters = {}

# 1. The King (Fixed but Premium is adjustable)
st.sidebar.markdown("### 👑 The King")
ticker_king = "2330.TW"
prem_king = st.sidebar.number_input(f"Premium for 2330", value=5.0, step=0.5)
fighters[ticker_king] = prem_king

# 2. The Challengers (User Editable!)
st.sidebar.markdown("### ⚔️ The Challengers")

# Challenger 1
c1_ticker = st.sidebar.text_input("Challenger 1 Ticker", value="3680.TWO")
c1_prem = st.sidebar.number_input(f"Premium for {c1_ticker}", value=0.0, step=0.1)
fighters[c1_ticker] = c1_prem

# Challenger 2
c2_ticker = st.sidebar.text_input("Challenger 2 Ticker", value="2317.TW")
c2_prem = st.sidebar.number_input(f"Premium for {c2_ticker}", value=0.5, step=0.1)
fighters[c2_ticker] = c2_prem

# Challenger 3
c3_ticker = st.sidebar.text_input("Challenger 3 Ticker", value="0050.TW")
c3_prem = st.sidebar.number_input(f"Premium for {c3_ticker}", value=0.0, step=0.1)
fighters[c3_ticker] = c3_prem

# --- 3. Run Logic ---
if st.button("🚀 Run Simulation"):
    
    with st.spinner(f"Downloading data for {list(fighters.keys())}..."):
        try:
            # Download all tickers at once
            ticker_list = list(fighters.keys())
            data = yf.download(ticker_list, start=start_date, end=end_date, progress=False)["Close"]
            
            # Safe Cleaning (Fill gaps)
            data = data.ffill().bfill()
            
            if len(data) == 0:
                st.error("❌ No data found! Check your tickers (did you forget .TW or .TWO?)")
                st.stop()

            st.success("Simulation Complete!")
            st.markdown("---")

            # --- CALCULATE & DISPLAY LOOP ---
            # This loop handles ANY stock you type. No more hardcoding!
            
            best_return = -999
            best_ticker = ""
            
            # Create columns dynamically (2 rows of 2)
            cols = st.columns(2) + st.columns(2) 
            
            for i, (ticker, premium) in enumerate(fighters.items()):
                # Handle error if a specific ticker is missing from download
                if ticker not in data.columns:
                    st.warning(f"⚠️ Could not find data for {ticker}. Skipping.")
                    continue
                
                # Math
                p_start = data[ticker].iloc[0]
                p_end   = data[ticker].iloc[-1]
                
                # Buy logic (Capital / (Price + Premium))
                entry_price = p_start + premium
                shares = capital / entry_price
                final_val = shares * p_end
                ret_pct = ((final_val - capital) / capital) * 100
                
                # Track Winner
                if ret_pct > best_return:
                    best_return = ret_pct
                    best_ticker = ticker
                
                # Display in the grid
                with cols[i]:
                    st.metric(
                        label=f"{ticker} (Prem: ${premium})", 
                        value=f"${int(final_val):,}", 
                        delta=f"{ret_pct:.2f}%"
                    )

            # --- VERDICT ---
            st.markdown("---")
            if best_ticker == ticker_king:
                st.balloons()
                st.success(f"🏆 **WINNER: The King ({best_ticker})**")
                st.write(f"TSMC is still the best place for your money, even with a ${prem_king} premium!")
            else:
                st.balloons()
                st.success(f"🏆 **WINNER: {best_ticker}**")
                st.write(f"This challenger beat TSMC by **{(best_return - ((data[ticker_king].iloc[-1]/(data[ticker_king].iloc[0]+prem_king)-1)*100)):.2f}%**!")

            # --- CHART ---
            st.markdown("### 📈 Visual Race")
            # Normalize to 100 so lines start at same point
            normalized_data = data / data.iloc[0] * 100
            st.line_chart(normalized_data)

        except Exception as e:
            st.error(f"Something went wrong: {e}")
            st.write("Check if you typed a valid ticker (e.g., `2330` should be `2330.TW`).")