import ccxt
import pandas as pd
import numpy as np
import requests
import time
import schedule
import logging
from datetime import datetime

# ==========================================
# === 1. إعدادات البوت الأساسية ===
# ==========================================
TELEGRAM_TOKEN = "8161859979:AAFlliIFMfGNlr_xQUlxF92CgDX00PaqVQ8"
TELEGRAM_CHAT_ID = "1055739217"

# قائمة العملات التي سيراقبها البوت
SYMBOLS = ["ETH/USDT", "SOL/USDT", "TRX/USDT", "ADA/USDT", "XLM/USDT", "SUI/USDT", "LINK/USDT", "HBAR/USDT",
"BCH/USDT", "AVAX/USDT", "LTC/USDT", "TON/USDT", "UNI/USDT", "DOT/USDT", "XMR/USDT", "AAVE/USDT",
"TAO/USDT", "NEAR/USDT", "ETC/USDT", "ONDO/USDT", "APT/USDT", "ICP/USDT", "FTM/USDT", "POL/USDT",
"ALGO/USDT", "ARB/USDT", "VET/USDT", "RNDR/USDT", "WLD/USDT", "SEI/USDT", "ATOM/USDT", "FIL/USDT",
"LRC/USDT", "JUP/USDT", "QNT/USDT", "INJ/USDT", "TIA/USDT", "STX/USDT", "OP/USDT", "ENS/USDT",
"IMX/USDT", "GRT/USDT", "LDO/USDT", "CFX/USDT", "CAKE/USDT", "XTZ/USDT", "THETA/USDT", "JASMY/USDT",
"NEXO/USDT", "IOTA/USDT", "RAY/USDT", "GALA/USDT", "SAND/USDT", "PENDLE/USDT", "JTO/USDT", "FLOW/USDT",
"ZEC/USDT", "HNT/USDT", "MANA/USDT", "CVX/USDT", "RUNE/USDT", "AR/USDT", "APE/USDT", "STRK/USDT",
"DYDX/USDT", "NEO/USDT", "EGLD/USDT", "COMP/USDT", "AXS/USDT", "AXL/USDT", "CELR/USDT", "ENJ/USDT",
"MATIC/USDT", "OMG/USDT", "HOT/USDT", "CHZ/USDT", "DOGE/USDT", "SHIB/USDT", "PEPE/USDT", "FET/USDT",
"CRV/USDT", "BTT/USDT", "CHR/USDT", "MASK/USDT", "EOS/USDT", "RPL/USDT", "AIXBT/USDT", "IOTX/USDT",
"ANKR/USDT", "PENGU/USDT"]
EXCHANGE_NAME = "binance"

# إعدادات الاستراتيجية
DROP_PERC = 0.6  # نسبة الهبوط المطلوبة للقمة
TP_PERC = 2.5    # هدف الربح (%)
SL_PERC = 3.0    # وقف الخسارة (%)

# إعدادات السجل (Logging)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        logging.error(f"خطأ في إرسال التليجرام: {e}")

# ==========================================
# === 2. حساب المؤشرات (Indicators) ===
# ==========================================
def calculate_ama(df, length=90, att=0.3, pwr=1.0):
    hh = df['high'].rolling(window=length).max()
    ll = df['low'].rolling(window=length).min()
    mid = (hh + ll) / 2
    range_half = (hh - ll) / 2
    
    ama = np.full(len(df), np.nan)
    closes = df['close'].values
    mids = mid.values
    rhs = range_half.values
    
    for i in range(len(closes)):
        if np.isnan(mids[i]) or np.isnan(rhs[i]):
            continue
        dist = 0 if rhs[i] == 0 else abs(closes[i] - mids[i]) / rhs[i]
        alpha = 1 if att == 0 else pow(dist / att, pwr)
        alpha = max(0, min(1, alpha))
        
        if i == 0 or np.isnan(ama[i-1]):
            ama[i] = closes[i]
        else:
            ama[i] = ama[i-1] + alpha * (closes[i] - ama[i-1])
            
    df['ama'] = ama
    return df

def get_indicators(exchange, symbol):
    # جلب فريم 30 دقيقة
    ohlcv_30m = exchange.fetch_ohlcv(symbol, timeframe='30m', limit=150)
    df_30 = pd.DataFrame(ohlcv_30m, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df_30['macdFast'] = df_30['close'].ewm(span=2, adjust=False).mean()
    df_30['macdSlow'] = df_30['close'].ewm(span=4, adjust=False).mean()
    df_30['macdLine'] = df_30['macdFast'] - df_30['macdSlow']
    df_30['signalLine'] = df_30['macdLine'].ewm(span=3, adjust=False).mean()
    df_30['macdBullish30'] = df_30['macdLine'] > df_30['signalLine']
    df_30 = calculate_ama(df_30)
    last_30m = df_30.iloc[-2]

    # جلب فريم 1 دقيقة
    ohlcv_1m = exchange.fetch_ohlcv(symbol, timeframe='1m', limit=50)
    df_1 = pd.DataFrame(ohlcv_1m, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df_1['highest_close'] = df_1['close'].rolling(22).max()
    df_1['wvf'] = ((df_1['highest_close'] - df_1['low']) / df_1['highest_close']) * 100
    df_1['wvf_highest_prev'] = df_1['wvf'].shift(1).rolling(22).max()
    df_1['wvf_green'] = df_1['wvf'] >= df_1['wvf_highest_prev']
    df_1['sma_20'] = df_1['close'].rolling(20).mean()
    df_1['sqzValue'] = df_1['close'] - df_1['sma_20']
    df_1['sqzValue_prev'] = df_1['sqzValue'].shift(1)
    df_1['isStrongBullish'] = (df_1['sqzValue'] > 0) & (df_1['sqzValue'] > df_1['sqzValue_prev'])
    df_1['isWeakBearish'] = (df_1['sqzValue'] < 0) & (df_1['sqzValue'] > df_1['sqzValue_prev'])
    
    return df_1.iloc[-1], last_30m['ama'], last_30m['macdBullish30']

# ==========================================
# === 3. محرك المراقبة والتنبيهات الوهمية ===
# ==========================================
class AlertBot:
    def __init__(self):
        # اتصال عام مجاني (بدون API Key)
        self.exchange = getattr(ccxt, EXCHANGE_NAME)({'enableRateLimit': True})
        
        # إنشاء ذاكرة مستقلة لكل عملة
        self.state = {sym: {
            "in_position": False, 
            "entry_price": 0.0, 
            "entry_time": None, 
            "peak_since_exit": 0.0
        } for sym in SYMBOLS}
        
        # إحصائيات عامة
        self.stats = {"win": 0, "loss": 0}
        
        logging.info("🤖 تم تشغيل بوت التنبيهات بنجاح!")
        send_telegram("🟢 <b>بدأ بوت التنبيهات بالمراقبة</b>\nالوضع: تداول وهمي (تنبيهات فقط لعدة عملات).")

    def run_strategy(self):
        for symbol in SYMBOLS:
            try:
                current_bar, ama30, macdBullish30 = get_indicators(self.exchange, symbol)
                close = current_bar['close']
                high = current_bar['high']
                sym_state = self.state[symbol]
                curr_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                # تحديث قمة العملة إذا لم نكن في صفقة وهمية
                if not sym_state["in_position"]:
                    if sym_state["peak_since_exit"] == 0.0:
                        sym_state["peak_since_exit"] = high
                    else:
                        sym_state["peak_since_exit"] = max(sym_state["peak_since_exit"], high)

                # --- منطق الدخول (تنبيه شراء) ---
                if not sym_state["in_position"]:
                    req_price = sym_state["peak_since_exit"] * (1 - DROP_PERC / 100)
                    isPriceDropped = (sym_state["peak_since_exit"] == 0.0) or (close <= req_price)
                    buyCond = current_bar['wvf_green'] and (current_bar['isStrongBullish'] or current_bar['isWeakBearish'])

                    if buyCond and (close > ama30) and macdBullish30 and isPriceDropped:
                        # حفظ بيانات الصفقة الوهمية
                        sym_state["in_position"] = True
                        sym_state["entry_price"] = close
                        sym_state["entry_time"] = datetime.now()
                        sym_state["peak_since_exit"] = 0.0
                        
                        msg = f"🛒 <b>تنبيه شراء (إشارة دخول)</b>\n" \
                              f"🔹 <b>العملة:</b> {symbol}\n" \
                              f"🕒 <b>الوقت:</b> {curr_time}\n" \
                              f"💵 <b>السعر الحالي:</b> {close} $\n" \
                              f"🎯 <b>الهدف المبرمج:</b> {close * (1 + TP_PERC/100):.4f} $\n" \
                              f"🛑 <b>وقف الخسارة:</b> {close * (1 - SL_PERC/100):.4f} $"
                        
                        send_telegram(msg)
                        logging.info(f"إشارة شراء: {symbol} بسعر {close}")

                # --- منطق الخروج (تنبيه بيع) ---
                else:
                    tp_price = sym_state["entry_price"] * (1 + TP_PERC / 100)
                    sl_price = sym_state["entry_price"] * (1 - SL_PERC / 100)

                    if close >= tp_price or close <= sl_price:
                        is_win = close >= tp_price
                        profit_perc = ((close - sym_state["entry_price"]) / sym_state["entry_price"]) * 100
                        duration = str(datetime.now() - sym_state["entry_time"]).split('.')[0]
                        
                        if is_win:
                            self.stats["win"] += 1
                            icon, txt = "✅", "الهدف (TP)"
                        else:
                            self.stats["loss"] += 1
                            icon, txt = "❌", "وقف الخسارة (SL)"
                        
                        msg = f"{icon} <b>تنبيه إغلاق ({txt})</b>\n" \
                              f"🔹 <b>العملة:</b> {symbol}\n" \
                              f"💵 <b>سعر الدخول:</b> {sym_state['entry_price']:.4f} $\n" \
                              f"💰 <b>سعر الإغلاق:</b> {close:.4f} $\n" \
                              f"📈 <b>الربح/الخسارة:</b> {profit_perc:.2f}%\n" \
                              f"⏳ <b>وقت الدخول:</b> {sym_state['entry_time'].strftime('%H:%M:%S')}\n" \
                              f"🕒 <b>وقت الإغلاق:</b> {datetime.now().strftime('%H:%M:%S')}\n" \
                              f"⏱ <b>المدة المستغرقة:</b> {duration}"
                        
                        send_telegram(msg)
                        logging.info(f"إغلاق {symbol} | الربح: {profit_perc:.2f}%")
                        
                        # تصفير حالة العملة للمراقبة من جديد
                        sym_state["in_position"] = False
                        sym_state["entry_price"] = 0.0
                        sym_state["peak_since_exit"] = high

            except Exception as e:
                logging.error(f"خطأ في جلب بيانات {symbol}: {e}")
                time.sleep(1) 

    # ==========================================
    # === 4. تقارير الأرباح (اليومية والأسبوعية) ===
    # ==========================================
    def send_report(self, report_type):
        wins = self.stats["win"]
        losses = self.stats["loss"]
        total = wins + losses
        win_rate = (wins / total * 100) if total > 0 else 0
        
        # حساب الصفقات المفتوحة حالياً من الذاكرة
        open_trades = sum(1 for sym in self.state if self.state[sym]["in_position"])
        
        title = "📊 تقرير التنبيهات اليومي" if report_type == "daily" else "📈 تقرير التنبيهات الأسبوعي"
        
        msg = f"<b>{title}</b>\n" \
              f"────────────────\n" \
              f"✅ <b>التوصيات الناجحة:</b> {wins}\n" \
              f"❌ <b>التوصيات الخاسرة:</b> {losses}\n" \
              f"🎯 <b>نسبة نجاح البوت:</b> {win_rate:.1f}%\n" \
              f"🔄 <b>الصفقات المفتوحة حالياً:</b> {open_trades}\n" \
              f"────────────────"
        
        send_telegram(msg)
        logging.info(f"تم إرسال {report_type} تقرير.")
        
        # تصفير عداد الأرباح للتقرير القادم (لا نصفر الصفقات المفتوحة)
        self.stats["win"] = 0
        self.stats["loss"] = 0

# ==========================================
# === 5. التشغيل والمزامنة الدقيقة ===
# ==========================================
if __name__ == "__main__":
    bot = AlertBot()
    
    # فحص جميع العملات في بداية كل دقيقة جديدة (عند الثانية :03)
    schedule.every().minute.at(":03").do(bot.run_strategy)
    
    # جدولة التقارير
    schedule.every().day.at("23:59").do(bot.send_report, report_type="daily")
    schedule.every().sunday.at("23:58").do(bot.send_report, report_type="weekly")

    logging.info("⏳ جاري المراقبة... سيتم فحص قائمة العملات كل دقيقة.")

    while True:
        schedule.run_pending()
        time.sleep(1)
