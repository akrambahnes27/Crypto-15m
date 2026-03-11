import ccxt
import pandas as pd
import pandas_ta as ta
import time
from datetime import datetime
import requests

# === إعدادات تليجرام ===
TELEGRAM_TOKEN = '8196868477:AAGPMnAc1fFqJvQcJGk8HsC5AYAnRkvu3cM'
CHAT_ID = '1055739217'

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"خطأ في إرسال التليجرام: {e}")

# === إعدادات التداول ===
exchange = ccxt.binance() 
symbols = ['ETH/USDT', 'SOL/USDT', 'NEAR/USDT', 'ADA/USDT']
timeframe = '15m'
active_trades = {} 

def check_markets():
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[{current_time}] 🔍 جاري فحص الأسواق...") 
    
    for symbol in symbols:
        try:
            ticker = exchange.fetch_ticker(symbol)
            current_price = ticker['last']
            
            # 1. إدارة الصفقات المفتوحة
            if symbol in active_trades:
                trade = active_trades[symbol]
                pnl_pct = ((current_price - trade['entry']) / trade['entry']) * 100
                
                # --- تصميم إشعار جني الأرباح ---
                if current_price >= trade['tp']:
                    msg = (f"✅ *جني أرباح (Take Profit)* ✅\n"
                           f"━━━━━━━━━━━━━━\n"
                           f"🪙 *العملة:* {symbol}\n"
                           f"⏱️ *الوقت:* {current_time}\n"
                           f"💰 *سعر البيع:* {current_price}\n"
                           f"📈 *صافي الربح:* +{pnl_pct:.2f}% 🟢\n"
                           f"━━━━━━━━━━━━━━\n"
                           f"🎉 *ألف مبروك الأرباح!*")
                    send_telegram_message(msg)
                    print(f"[{current_time}] تم بيع {symbol} بربح.")
                    del active_trades[symbol]
                
                # --- تصميم إشعار وقف الخسارة ---
                elif current_price <= trade['sl']:
                    msg = (f"⚠️ *إغلاق صفقة (Stop Loss)* ⚠️\n"
                           f"━━━━━━━━━━━━━━\n"
                           f"🪙 *العملة:* {symbol}\n"
                           f"⏱️ *الوقت:* {current_time}\n"
                           f"🩸 *سعر البيع:* {current_price}\n"
                           f"📉 *التراجع:* {pnl_pct:.2f}% 🔴\n"
                           f"━━━━━━━━━━━━━━\n"
                           f"🔄 *جاري البحث عن فرصة للتعويض...*")
                    send_telegram_message(msg)
                    print(f"[{current_time}] تم ضرب وقف خسارة {symbol}.")
                    del active_trades[symbol]
                continue 
            
            # 2. جلب البيانات والتحليل
            bars = exchange.fetch_ohlcv(symbol, timeframe, limit=300) 
            df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            df['ema200'] = ta.ema(df['close'], length=200)
            df['rsi'] = ta.rsi(df['close'], length=14)
            df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
            
            last_closed = df.iloc[-2]
            prev_closed = df.iloc[-3]
            
            is_uptrend = last_closed['close'] > last_closed['ema200']
            recent_rsi = df['rsi'].iloc[-7:-2]
            was_oversold = recent_rsi.min() < 30
            bullish_confirm = (last_closed['close'] > last_closed['open']) and (last_closed['close'] > prev_closed['high'])
            
            # طباعة السجل التفصيلي في Railway
            trend_str = "صاعد 🟢" if is_uptrend else "هابط 🔴"
            rsi_val = last_closed['rsi']
            print(f"  ➜ {symbol} | السعر: {current_price} | RSI: {rsi_val:.1f} | الترند: {trend_str}")
            
            # 3. اتخاذ القرار
            if is_uptrend and was_oversold and bullish_confirm:
                entry = current_price
                atr_val = last_closed['atr']
                sl = entry - (atr_val * 3.0)
                tp = entry + (atr_val * 2.5) 
                
                active_trades[symbol] = {'entry': entry, 'tp': tp, 'sl': sl}
                
                # --- تصميم إشعار الدخول (الشراء) ---
                msg = (f"🚀 *إشارة دخول جديدة (BUY)* 🚀\n"
                       f"━━━━━━━━━━━━━━\n"
                       f"🪙 *العملة:* {symbol}\n"
                       f"⏱️ *الوقت:* {current_time}\n"
                       f"💵 *سعر الدخول:* {entry}\n"
                       f"🎯 *الهدف الأول:* {tp:.4f}\n"
                       f"🛡️ *وقف الخسارة:* {sl:.4f}\n"
                       f"━━━━━━━━━━━━━━\n"
                       f"📊 *الاستراتيجية:* قناص V39")
                send_telegram_message(msg)
                print(f"[{current_time}] تم شراء {symbol} وإرسال إشعار.")
                
        except Exception as e:
            print(f"[{current_time}] خطأ في فحص {symbol}: {e}")

# === تشغيل البوت ===
print("🤖 البوت يعمل الآن ويقوم بفحص الأسواق...")

# --- تصميم إشعار تفعيل البوت ---
startup_msg = (f"🟢 *تـم تـشـغـيـل الـنـظـام* 🟢\n"
               f"━━━━━━━━━━━━━━\n"
               f"🤖 *البوت:* المتداول الآلي (V39)\n"
               f"🔍 *الحالة:* جاري فحص الأسواق...\n"
               f"📲 *التنبيهات:* متصل وجاهز 100%")
send_telegram_message(startup_msg)

while True:
    check_markets()
    time.sleep(60)
