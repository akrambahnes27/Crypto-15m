import ccxt
import pandas as pd
import pandas_ta as ta
import time
import requests

# === إعدادات تليجرام ===
TELEGRAM_TOKEN = '8196868477:AAGPMnAc1fFqJvQcJGk8HsC5AYAnRkvu3cM'
CHAT_ID = '1055739217'

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
    requests.post(url, data=payload)

# === إعدادات التداول ===
exchange = ccxt.binance()
timeframe = '15m'
# قائمة العملات التي نجحت فيها الاستراتيجية بجدارة
symbols = ['ETH/USDT', 'SOL/USDT', 'NEAR/USDT', 'ADA/USDT', 'XRP/USDT', 'ROSE/USDT', 'SUI/USDT', 'LTC/USDT', 'TON/USDT', 'OP/USDT', 'IOTX/USDT', 'ANKR/USDT', 'GALA/USDT', 'UNI/USDT', 'RUNE/USDT', 'LINK/USDT', 'HBAR/USDT', 'DOT/USDT'] 

def analyze_and_alert(symbol):
    try:
        # جلب الشموع اليابانية
        bars = exchange.fetch_ohlcv(symbol, timeframe, limit=250)
        df = pd.DataFrame(bars, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        
        # حساب المؤشرات (EMA 200, RSI 14, ATR 14)
        df['ema200'] = ta.ema(df['close'], length=200)
        df['rsi'] = ta.rsi(df['close'], length=14)
        df['atr'] = ta.atr(df['high'], df['low'], df['close'], length=14)
        
        # أخذ آخر شمعتين مغلقتين للتحليل
        current_candle = df.iloc[-2]
        prev_candle = df.iloc[-3]
        
        # التحقق من الشروط (نفس منطق V39)
        is_uptrend = current_candle['close'] > current_candle['ema200']
        
        # هل الـ RSI كان تحت 30 في الشموع الخمس الأخيرة؟
        recent_rsi = df['rsi'].iloc[-7:-2]
        was_oversold = recent_rsi.min() < 30
        
        # تأكيد البرايس أكشن (شمعة خضراء تبتلع قمة الشمعة السابقة)
        bullish_confirm = (current_candle['close'] > current_candle['open']) and (current_candle['close'] > prev_candle['high'])
        
        if is_uptrend and was_oversold and bullish_confirm:
            # حساب الأهداف بناءً على ATR
            entry = current_candle['close']
            sl = entry - (current_candle['atr'] * 3.0)
            tp1 = entry + (current_candle['atr'] * 2.5)
            
            msg = f"🟢 *قناص الشموع V39 | إشارة شراء جديدة*\n" \
                  f"العملة: {symbol}\n" \
                  f"الدخول: {entry}\n" \
                  f"الهدف الأول: {tp1:.4f}\n" \
                  f"وقف الخسارة: {sl:.4f}\n" \
                  f"الفريم: 15 دقيقة"
            
            send_telegram_message(msg)
            print(f"Signal sent for {symbol}")
            
    except Exception as e:
        print(f"Error analyzing {symbol}: {e}")

# === تشغيل البوت على مدار الساعة ===
print("البوت يعمل الآن ويراقب الأسواق...")
send_telegram_message("🤖 تم تشغيل بوت قناص V39 بنجاح. سأقوم بمراقبة الأسواق وإرسال الإشارات لك.")

while True:
    for coin in symbols:
        analyze_and_alert(coin)
        time.sleep(2) # تجنب حظر الـ API
    
    # الانتظار 15 دقيقة حتى تغلق الشمعة التالية
    print("تم فحص جميع العملات. الانتظار للشمعة القادمة...")
    time.sleep(900)
