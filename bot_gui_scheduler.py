import streamlit as st
import subprocess

st.set_page_config(page_title="Forex Bot Control", layout="centered")
st.title("🤖 Forex Bot GUI")

symbol = st.text_input("Symbol", value="EURUSDm")
tp_offset = st.number_input("Take Profit Offset (e.g. 0.002)", value=0.002, step=0.0001)
sl_offset = st.number_input("Stop Loss Offset (e.g. 0.001)", value=0.001, step=0.0001)

if st.button("▶️ Run Bot Now"):
    cmd = [
        "python", "sma_bot.py",
        "--symbol", symbol,
        "--tp", str(tp_offset),
        "--sl", str(sl_offset)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    st.code(result.stdout + result.stderr)
