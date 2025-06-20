# dashboard.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

LOG_FILE = "trade_log.csv"

def load_trade_log():
    if not os.path.exists(LOG_FILE):
        return pd.DataFrame()
    df = pd.read_csv(LOG_FILE)
    df['Time'] = pd.to_datetime(df['Time'])
    df['PnL'] = df['TP'] - df['Price']
    return df

def compute_monthly_summary(df):
    df['Month'] = df['Time'].dt.to_period('M').astype(str)
    return df.groupby('Month')['PnL'].sum().reset_index(name='Monthly PnL')

def compute_streaks(df):
    df = df.sort_values("Time").reset_index(drop=True)
    df['Win'] = df['PnL'] > 0
    streaks = []
    current_streak = 1
    for i in range(1, len(df)):
        if df.loc[i, 'Win'] == df.loc[i-1, 'Win']:
            current_streak += 1
        else:
            streaks.append((df.loc[i-1, 'Win'], current_streak))
            current_streak = 1
    if not df.empty:
        streaks.append((df.loc[len(df)-1, 'Win'], current_streak))
    longest_win = max((s for s in streaks if s[0]), default=(True, 0))[1]
    longest_loss = max((s for s in streaks if not s[0]), default=(False, 0))[1]
    return longest_win, longest_loss

def compute_equity_curve(df):
    df_sorted = df.sort_values("Time")
    df_sorted["Cumulative PnL"] = df_sorted["PnL"].cumsum()
    return df_sorted[["Time", "Cumulative PnL"]]

st.set_page_config(page_title="Forex Bot Dashboard", layout="centered")
st.title("📈 Forex Bot Dashboard")

df_log = load_trade_log()
if df_log.empty:
    st.warning("No trade data available.")
    st.stop()

if "Type" in df_log.columns:
    trade_types = df_log['Type'].dropna().unique().tolist()
    selected_types = st.multiselect("Filter by Trade Type:", trade_types, default=trade_types)
    df_log = df_log[df_log['Type'].isin(selected_types)]
else:
    st.warning("⚠️ 'Type' column not found in the trade log. Skipping trade type filter.")

st.subheader("📈 Monthly PnL Summary")
monthly_df = compute_monthly_summary(df_log)
fig_month = px.bar(monthly_df, x="Month", y="Monthly PnL", title="Monthly Profit and Loss")
st.plotly_chart(fig_month, use_container_width=True)

st.subheader("🔥 Win/Loss Streaks")
win_streak, loss_streak = compute_streaks(df_log)
st.info(f"Longest Win Streak: {win_streak} | Longest Loss Streak: {loss_streak}")

st.subheader("📊 Cumulative Equity Curve")
eq_df = compute_equity_curve(df_log)
fig_eq = go.Figure()
fig_eq.add_trace(go.Scatter(x=eq_df['Time'], y=eq_df['Cumulative PnL'], mode='lines', name='Equity'))
fig_eq.update_layout(title="Cumulative PnL Over Time")
st.plotly_chart(fig_eq, use_container_width=True)

st.subheader("🧾 Recent Trades")
st.dataframe(df_log.sort_values("Time", ascending=False).head(10), use_container_width=True)
