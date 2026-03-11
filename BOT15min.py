import ccxt
import pandas as pd
import pandas_ta as ta
import time
from datetime import datetime, timezone, timedelta
import requests

# === إعدادات تليجرام ===
TELEGRAM_TOKEN = '8161859979:AAFlliIFMfGNlr_xQUlxF92CgDX00PaqVQ8'
CHAT_ID = '1055739217'

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {'chat_id': CHAT_ID, 'text': message, 'parse_mode': 'Markdown'}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"خطأ في إرسال التليجرام: {e}")

# === إعدادات التداول والوقت ===
exchange = ccxt.binance() 
symbols = ['ETH/USDT', 'SOL/USDT', 'TRX/USDT', 'ADA/USDT', 'XLM/USDT', 'SUI/USDT', 'LINK/USDT', 'HBAR/USDT',
'BCH/USDT', 'AVAX/USDT', 'LTC/USDT', 'TON/USDT', 'UNI/USDT', 'DOT/USDT', 'XMR/USDT', 'AAVE/USDT',
'TAO/USDT', 'NEAR/USDT', 'ETC/USDT', 'ONDO/USDT', 'APT/USDT', 'ICP/USDT', 'FTM/USDT', 'POL/USDT',
'ALGO/USDT', 'ARB/USDT', 'VET/USDT', 'RNDR/USDT', 'WLD/USDT', 'SEI/USDT', 'ATOM/USDT', 'FIL/USDT',
'LRC/USDT', 'JUP/USDT', 'QNT/USDT', 'INJ/USDT', 'TIA/USDT', 'STX/USDT', 'OP/USDT', 'ENS/USDT',
'IMX/USDT', 'GRT/USDT', 'LDO/USDT', 'CFX/USDT', 'CAKE/USDT', 'XTZ/USDT', 'THETA/USDT', 'JASMY/USDT',
'NEXO/USDT', 'IOTA/USDT', 'RAY/USDT', 'GALA/USDT', 'SAND/USDT', 'PENDLE/USDT', 'JTO/USDT', 'FLOW/USDT',
'ZEC/USDT', 'HNT/USDT', 'MANA/USDT', 'CVX/USDT', 'RUNE/USDT', 'AR/USDT', 'APE/USDT', 'STRK/USDT',
'DYDX/USDT', 'NEO/USDT', 'EGLD/USDT', 'COMP/USDT', 'AXS/USDT', 'AXL/USDT', 'CELR/USDT', 'ENJ/USDT',
'MATIC/USDT', 'OMG/USDT', 'HOT/USDT', 'CHZ/USDT', 'DOGE/USDT', 'SHIB/USDT', 'PEPE/USDT', 'FET/USDT',
'CRV/USDT', 'BTT/USDT', 'CHR/USDT', 'MASK/USDT', 'EOS/USDT', 'RPL/USDT', 'AIXBT/USDT', 'IOTX/USDT',
'ANKR/USDT', 'PENGU/USDT']
timeframe = '15m'

# ضبط توقيت الجزائر (UTC+1)
algeria_tz = timezone(timedelta(hours=1))

# === ذاكرة البوت ===
active_trades = {} 

# عدادات الأرباح والخسائر
stats = {
    'daily': {'wins': 0, 'losses': 0, 'pnl': 0.0},
    'weekly': {'wins': 0, 'losses': 0, 'pnl': 0.0}
}

# تسجيل تاريخ اليوم لمعرفة متى يمر منتصف الليل
last_checked_date = datetime.now(algeria_tz).date()

def check_markets():
    current_time_dz = datetime.now(algeria_tz)
    current_time_str = current_time_dz.strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[{current_time_str}] 🔍 جاري فحص الأسواق...") 
    
    for symbol in symbols:
        try:
            ticker = exchange.fetch_ticker(symbol)
            current_price = ticker['last']
            
            # === 1. إدارة الصفقات المفتوحة (وتسجيل الأرباح/الخسائر) ===
            if symbol in active_trades:
                trade = active_trades[symbol]
                pnl_pct = ((current_price - trade['entry']) / trade['entry']) * 100
                
                # --- حالة جني الأرباح ---
                if current_price >= trade['tp']:
                    msg = (f"✅ *جني أرباح (Take Profit)* ✅\n"
                           f"━━━━━━━━━━━━━━\n"
                           f"🪙 *العملة:* {symbol}\n"
                           f"⏱️ *الوقت:* {current_time_str}\n"
                           f"💰 *سعر البيع:* {current_price}\n"
                           f"📈 *صافي الربح:* +{pnl_pct:.2f}% 🟢\n"
                           f"━━━━━━━━━━━━━━\n"
                           f"🎉 *ألف مبروك الأرباح!*")
                    send_telegram_message(msg)
                    print(f"[{current_time_str}] تم بيع {symbol} بربح.")
                    
                    # تسجيل الربح في العدادات
                    stats['daily']['wins'] += 1
                    stats['daily']['pnl'] += pnl_pct
                    stats['weekly']['wins'] += 1
                    stats['weekly']['pnl'] += pnl_pct
                    
                    del active_trades[symbol]
                
                # --- حالة وقف الخسارة ---
                elif current_price <= trade['sl']:
                    msg = (f"⚠️ *إغلاق صفقة (Stop Loss)* ⚠️\n"
                           f"━━━━━━━━━━━━━━\n"
                           f"🪙 *العملة:* {symbol}\n"
                           f"⏱️ *الوقت:* {current_time_str}\n"
                           f"🩸 *سعر البيع:* {current_price}\n"
                           f"📉 *التراجع:* {pnl_pct:.2f}% 🔴\n"
                           f"━━━━━━━━━━━━━━\n"
                           f"🔄 *جاري البحث عن فرصة للتعويض...*")
                    send_telegram_message(msg)
                    print(f"[{current_time_str}] تم ضرب وقف خسارة {symbol}.")
                    
                    # تسجيل الخسارة في العدادات
                    stats['daily']['losses'] += 1
                    stats['daily']['pnl'] += pnl_pct
                    stats['weekly']['losses'] += 1
                    stats['weekly']['pnl'] += pnl_pct
                    
                    del active_trades[symbol]
                continue 
            
            # === 2. جلب البيانات والتحليل ===
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
            
            trend_str = "صاعد 🟢" if is_uptrend else "هابط 🔴"
            rsi_val = last_closed['rsi']
            print(f"  ➜ {symbol} | السعر: {current_price} | RSI: {rsi_val:.1f} | الترند: {trend_str}")
            
            # === 3. الشراء ===
            if is_uptrend and was_oversold and bullish_confirm:
                entry = current_price
                atr_val = last_closed['atr']
                sl = entry - (atr_val * 3.0)
                tp = entry + (atr_val * 2.5) 
                
                active_trades[symbol] = {'entry': entry, 'tp': tp, 'sl': sl}
                
                msg = (f"🚀 *إشارة دخول جديدة (BUY)* 🚀\n"
                       f"━━━━━━━━━━━━━━\n"
                       f"🪙 *العملة:* {symbol}\n"
                       f"⏱️ *الوقت:* {current_time_str}\n"
                       f"💵 *سعر الدخول:* {entry}\n"
                       f"🎯 *الهدف الأول:* {tp:.4f}\n"
                       f"🛡️ *وقف الخسارة:* {sl:.4f}\n"
                       f"━━━━━━━━━━━━━━\n"
                       f"📊 *الاستراتيجية:* قناص V39")
                send_telegram_message(msg)
                print(f"[{current_time_str}] تم شراء {symbol} وإرسال إشعار.")
                
        except Exception as e:
            print(f"[{current_time_str}] خطأ في فحص {symbol}: {e}")

def check_and_send_reports():
    global last_checked_date
    now_dz = datetime.now(algeria_tz)
    current_date = now_dz.date()
    
    # إذا تغير اليوم (تجاوزنا منتصف الليل بتوقيت الجزائر 00:00)
    if current_date > last_checked_date:
        
        # 1. إعداد التقرير اليومي
        daily = stats['daily']
        d_color = "🟢" if daily['pnl'] >= 0 else "🔴"
        d_sign = "+" if daily['pnl'] > 0 else ""
        
        daily_msg = (f"📊 *حـصـاد الـيـوم* 📊\n"
                     f"━━━━━━━━━━━━━━\n"
                     f"📅 *التاريخ:* {last_checked_date}\n"
                     f"✅ *صفقات رابحة:* {daily['wins']}\n"
                     f"❌ *صفقات خاسرة:* {daily['losses']}\n"
                     f"💰 *النتيجة النهائية:* {d_sign}{daily['pnl']:.2f}% {d_color}\n"
                     f"━━━━━━━━━━━━━━\n"
                     f"🌙 *تصبح على أرباح!*")
        send_telegram_message(daily_msg)
        
        # 2. إعداد التقرير الأسبوعي (يُرسل فجر الاثنين، أي أن يوم الأحد قد انتهى)
        if current_date.weekday() == 0: 
            weekly = stats['weekly']
            w_color = "🟢" if weekly['pnl'] >= 0 else "🔴"
            w_sign = "+" if weekly['pnl'] > 0 else ""
            
            weekly_msg = (f"🏆 *الـحـصـاد الأَسـبـوعـي* 🏆\n"
                          f"━━━━━━━━━━━━━━\n"
                          f"📅 *الأسبوع المنتهي:* {last_checked_date}\n"
                          f"✅ *إجمالي الرابحة:* {weekly['wins']}\n"
                          f"❌ *إجمالي الخاسرة:* {weekly['losses']}\n"
                          f"💰 *النتيجة الأسبوعية:* {w_sign}{weekly['pnl']:.2f}% {w_color}\n"
                          f"━━━━━━━━━━━━━━\n"
                          f"🔥 *أسبوع جديد، أهداف جديدة!*")
            send_telegram_message(weekly_msg)
            
            # تصفير العداد الأسبوعي
            stats['weekly'] = {'wins': 0, 'losses': 0, 'pnl': 0.0}
        
        # تصفير العداد اليومي
        stats['daily'] = {'wins': 0, 'losses': 0, 'pnl': 0.0}
        
        # تحديث التاريخ ليوم الغد
        last_checked_date = current_date

# === تشغيل البوت ===
print("🤖 البوت يعمل الآن ويقوم بفحص الأسواق...")
startup_msg = (f"🟢 *تـم تـشـغـيـل الـنـظـام* 🟢\n"
               f"━━━━━━━━━━━━━━\n"
               f"🤖 *البوت:* المتداول الآلي (V39)\n"
               f"🇩🇿 *التوقيت:* الجزائر (محاسبة منتصف الليل)\n"
               f"📲 *التنبيهات:* متصل وجاهز 100%")
send_telegram_message(startup_msg)

while True:
    check_markets()
    check_and_send_reports() # فحص هل حان منتصف الليل؟
    time.sleep(60)
