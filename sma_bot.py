# sma_bot.py
import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
import pytz
import os
import argparse
import requests

BOT_TOKEN = "7755488017:AAGnyAnKFk1GLj99Ryy-yjm0bQRxmCFDsnA"
CHAT_ID = "6899792991"
LOG_FILE = "trade_log.csv"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message})

def initialize_mt5():
    if not mt5.initialize():
        raise RuntimeError("MetaTrader5 initialization failed")

def shutdown_mt5():
    mt5.shutdown()

def fetch_data(symbol, bars=100):
    tz = pytz.timezone("Etc/UTC")
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M1, 0, bars)
    if rates is None or len(rates) == 0:
        return None
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s').dt.tz_localize('UTC').dt.tz_convert(tz)
    df = df[['time', 'close']]
    return df

def calculate_signals(df, fast=5, slow=10):
    df['sma_fast'] = df['close'].rolling(fast).mean()
    df['sma_slow'] = df['close'].rolling(slow).mean()
    df['signal'] = 0
    df.loc[df['sma_fast'] > df['sma_slow'], 'signal'] = 1
    df.loc[df['sma_fast'] < df['sma_slow'], 'signal'] = -1
    return df

def execute_trade(symbol, signal, tp_offset, sl_offset):
    tick = mt5.symbol_info_tick(symbol)
    if not tick:
        send_telegram(f"❌ Failed to get tick data for {symbol}")
        return

    price = tick.ask if signal == 1 else tick.bid
    trade_type = mt5.ORDER_TYPE_BUY if signal == 1 else mt5.ORDER_TYPE_SELL
    type_name = "BUY" if signal == 1 else "SELL"
    sl = price - sl_offset if signal == 1 else price + sl_offset
    tp = price + tp_offset if signal == 1 else price - tp_offset

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": 0.01,
        "type": trade_type,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 20,
        "magic": 123456,
        "comment": "sma-bot-trade",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC
    }

    result = mt5.order_send(request)
    if result.retcode == mt5.TRADE_RETCODE_DONE:
        send_telegram(f"✅ {type_name} order placed for {symbol} at {price}")
        log_trade(symbol, signal, price, tp, sl, type_name)
    else:
        send_telegram(f"❌ {type_name} trade failed for {symbol}: Code {result.retcode}")

def log_trade(symbol, signal, price, tp, sl, trade_type):
    time_str = datetime.now()
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w") as f:
            f.write("Symbol,Time,Signal,Price,TP,SL,Type\n")
    with open(LOG_FILE, "a") as f:
        f.write(f"{symbol},{time_str},{signal},{price},{tp},{sl},{trade_type}\n")

def main(symbol, tp_offset, sl_offset):
    initialize_mt5()
    df = fetch_data(symbol)
    if df is None:
        print(f"❌ No data for {symbol}")
        shutdown_mt5()
        return

    df = calculate_signals(df)
    last_signal = df['signal'].iloc[-1]
    prev_signal = df['signal'].iloc[-2]

    print(f"{symbol} ⏱ {df['time'].iloc[-1]} | Signal: {last_signal} | Last: {prev_signal}")

    if last_signal != prev_signal:
        send_telegram(f"📊 {'Buy' if last_signal == 1 else 'Sell'} signal on {symbol}")
        execute_trade(symbol, last_signal, tp_offset, sl_offset)
    else:
        print("⏸ No new signal. No trade executed.")
    shutdown_mt5()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", type=str, default="EURUSDm")
    parser.add_argument("--tp", type=float, default=0.002)
    parser.add_argument("--sl", type=float, default=0.001)
    args = parser.parse_args()
    main(args.symbol, args.tp, args.sl)
