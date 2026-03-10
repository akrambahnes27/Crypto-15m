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
# استخدم bybit إذا كانت سيرفرات Railway محظورة من باينانس
exchange = ccxt.bybit() 

symbols = ['ETH/USDT', 'SOL/USDT', 'NEAR/USDT', 'ADA/USDT', 'XRP/USDT', 'ROSE/USDT', 'SUI/USDT', 'LTC/USDT', 'TON/USDT', 'OP/USDT', 'IOTX/USDT', 'ANKR/USDT', 'GALA/USDT', 'UNI/USDT', 'RUNE/USDT', 'LINK/USDT', 'HBAR/USDT', 'DOT/USDT']
timeframe = '15m'

# ذاكرة البوت لتتبع الصفقات المفتوحة
active_trades = {} 

def check_markets():
    # الحصول على الوقت الحالي بتنسيق جميل
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    for symbol in symbols:
        try:
            # 1. جلب السعر الحالي للعملة (تحديث فوري)
            ticker = exchange.fetch_ticker(symbol)
            current_price = ticker['last']
            
            # === 2. فحص الصفقات المفتوحة (هل نبيع؟) ===
            if symbol in active_trades:
                trade = active_trades[symbol]
                entry_price = trade['entry']
                tp_price = trade['tp']
                sl_price = trade['sl']
                
                # حساب النسبة المئوية للتحرك
                pnl_pct = ((current_price - entry_price) / entry_price) * 100
                
                # حالة الربح (لمس الهدف)
                if current_price >= tp_price:
                    msg = (f"🎯 *إشعار بيع (جني أرباح)* 🎯\n"
                           f"العملة: {symbol}\n"
                           f"الوقت: {current_time}\n"
                           f"سعر البيع: {current_price}\n"
                           f"نسبة الربح: +{pnl_pct:.2f}% 🟢")
                    send_telegram_message(msg)
                    del active_trades[symbol] # حذف الصفقة من الذاكرة
                    print(f"[{current_time}] تم بيع {symbol} بربح.")
                
                # حالة الخسارة (لمس وقف الخسارة)
                elif current_price <= sl_price:
                    msg = (f"🛑 *إشعار بيع (وقف خسارة)* 🛑\n"
                           f"العملة: {symbol}\n"
                           f"الوقت: {current_time}\n"
                           f"سعر البيع: {current_price}\n"
                           f"الخسارة: {pnl_pct:.2f}% 🔴")
                    send_telegram_message(msg)
                    del active_trades[symbol] # حذف الصفقة من الذاكرة
                    print(f"[{current_time}] تم ضرب وقف خسارة {symbol}.")
                
                # إذا لم يلمس الهدف أو الوقف، نتخطى هذه العملة وننتقل للتالية
                continue 
            
            # === 3. البحث عن فرص شراء جديدة (إذا لم تكن العملة في الذاكرة) ===
            bars = exchange.fetch_ohlcv(symbol, timeframe, limit=100)
            df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            
            # حساب المؤشرات
            df['ema200'] = ta.ema(df['close'], length=200)
            df['rsi'] = ta.rsi(df['close'], length=14)
            df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
            
            # نأخذ آخر شمعتين مغلقتين لضمان دقة الإشارة
            last_closed = df.iloc[-2]
            prev_closed = df.iloc[-3]
            
            # الشروط (استراتيجية V39)
            is_uptrend = last_closed['close'] > last_closed['ema200']
            recent_rsi = df['rsi'].iloc[-7:-2]
            was_oversold = recent_rsi.min() < 30
            bullish_confirm = (last_closed['close'] > last_closed['open']) and (last_closed['close'] > prev_closed['high'])
            
            # هل تحققت الشروط؟
            if is_uptrend and was_oversold and bullish_confirm:
                # حساب مستويات الدخول والأهداف بناءً على ATR
                entry = current_price
                atr_val = last_closed['atr']
                sl = entry - (atr_val * 3.0)
                tp = entry + (atr_val * 2.5) # نستخدم الهدف الأول كهدف رئيسي للإشعار
                
                # تخزين الصفقة في الذاكرة
                active_trades[symbol] = {'entry': entry, 'tp': tp, 'sl': sl}
                
                msg = (f"🚀 *إشعار شراء جديد* 🚀\n"
                       f"العملة: {symbol}\n"
                       f"الوقت: {current_time}\n"
                       f"السعر الحالي: {entry}\n"
                       f"الهدف: {tp:.4f}\n"
                       f"الوقف: {sl:.4f}")
                send_telegram_message(msg)
                print(f"[{current_time}] تم شراء {symbol}.")
                
        except Exception as e:
            print(f"[{current_time}] خطأ في فحص {symbol}: {e}")

# === تشغيل البوت ===
print("🤖 البوت يعمل الآن ويقوم بفحص الأسواق كل دقيقة...")
send_telegram_message("🤖 *تم تشغيل بوت المتداول الآلي.*\nسأقوم بفحص الأسواق كل دقيقة وإرسال الإشعارات إليك فوراً.")

while True:
    check_markets()
    # جعل البوت ينام لمدة 60 ثانية (دقيقة واحدة) قبل الفحص القادم
    time.sleep(60)
