import ccxt
import pandas as pd
import numpy as np
import requests
import time
import schedule
import logging
from datetime import datetime

# ==========================================
# === 1. Ø¥Ø¹Ø¯Ø§Ø¯Ø§Øª Ø§Ù„Ø¨ÙˆØª Ø§Ù„Ø£Ø³Ø§Ø³ÙŠØ© ===
# ==========================================
TELEGRAM_TOKEN = "8161859979:AAFlliIFMfGNlr_xQUlxF92CgDX00PaqVQ8"
TELEGRAM_CHAT_ID = "1055739217"

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

DROP_PERC = 0.6
TP_PERC   = 2.5
SL_PERC   = 3.0

# Ø¥Ø¹Ø¯Ø§Ø¯Ø§Øª Ø§Ù„Ø³Ø¬Ù„
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(message)s",
    handlers=[
        logging.FileHandler("bot_log.txt", encoding='utf-8'),
        logging.StreamHandler()
    ]
)

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        logging.error(f"[Ø®Ø·Ø£ ØªÙŠÙ„ÙŠØ¬Ø±Ø§Ù…] {e}")

# ==========================================
# === 2. Ø­Ø³Ø§Ø¨ Ø§Ù„Ù…Ø¤Ø´Ø±Ø§Øª Ø§Ù„ØªÙ‚Ù†ÙŠØ© ===
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
    ohlcv_30m = exchange.fetch_ohlcv(symbol, timeframe='30m', limit=150)
    df_30 = pd.DataFrame(ohlcv_30m, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df_30['macdFast']   = df_30['close'].ewm(span=2, adjust=False).mean()
    df_30['macdSlow']   = df_30['close'].ewm(span=4, adjust=False).mean()
    df_30['macdLine']   = df_30['macdFast'] - df_30['macdSlow']
    df_30['signalLine'] = df_30['macdLine'].ewm(span=3, adjust=False).mean()
    df_30['macdBullish30'] = df_30['macdLine'] > df_30['signalLine']
    df_30 = calculate_ama(df_30)
    last_30m = df_30.iloc[-2]

    ohlcv_1m = exchange.fetch_ohlcv(symbol, timeframe='1m', limit=50)
    df_1 = pd.DataFrame(ohlcv_1m, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df_1['highest_close']    = df_1['close'].rolling(22).max()
    df_1['wvf']              = ((df_1['highest_close'] - df_1['low']) / df_1['highest_close']) * 100
    df_1['wvf_highest_prev'] = df_1['wvf'].shift(1).rolling(22).max()
    df_1['wvf_green']        = df_1['wvf'] >= df_1['wvf_highest_prev']
    df_1['sma_20']           = df_1['close'].rolling(20).mean()
    df_1['sqzValue']         = df_1['close'] - df_1['sma_20']
    df_1['sqzValue_prev']    = df_1['sqzValue'].shift(1)
    df_1['isStrongBullish']  = (df_1['sqzValue'] > 0) & (df_1['sqzValue'] > df_1['sqzValue_prev'])
    df_1['isWeakBearish']    = (df_1['sqzValue'] < 0) & (df_1['sqzValue'] > df_1['sqzValue_prev'])

    return df_1.iloc[-1], last_30m['ama'], last_30m['macdBullish30']

# ==========================================
# === 3. Ø¨ÙŠØ§Ù†Ø§Øª Order Flow Ø§Ù„Ø­ØµØ±ÙŠØ© ===
# ==========================================
def get_symbol_binance(symbol):
    """ETH/USDT â†’ ETHUSDT"""
    return symbol.replace("/", "")

def get_cvd(symbol, limit=500):
    """
    Ù†Ø³Ø¨Ø© Ø¶ØºØ· Ø§Ù„Ø´Ø±Ø§Ø¡ Ø§Ù„Ø­Ù‚ÙŠÙ‚ÙŠ Ù…Ù† Aggregate Trades.
    m=False â†’ Ø§Ù„Ù…Ø´ØªØ±ÙŠ Ù‡Ùˆ Taker (Ø¶ØºØ· Ø´Ø±Ø§Ø¡ Ø­Ù‚ÙŠÙ‚ÙŠ)
    m=True  â†’ Ø§Ù„Ø¨Ø§Ø¦Ø¹ Ù‡Ùˆ Taker  (Ø¶ØºØ· Ø¨ÙŠØ¹ Ø­Ù‚ÙŠÙ‚ÙŠ)
    """
    sym = get_symbol_binance(symbol)
    try:
        r = requests.get(
            "https://api.binance.com/api/v3/aggTrades",
            params={"symbol": sym, "limit": limit},
            timeout=5
        ).json()
        buy_vol  = sum(float(t['q']) for t in r if not t['m'])
        sell_vol = sum(float(t['q']) for t in r if t['m'])
        total = buy_vol + sell_vol
        return buy_vol / total if total > 0 else 0.5
    except Exception as e:
        logging.warning(f"[CVD Ø®Ø·Ø£ {symbol}] {e}")
        return 0.5  # Ù‚ÙŠÙ…Ø© Ù…Ø­Ø§ÙŠØ¯Ø© Ø¹Ù†Ø¯ Ø§Ù„Ø®Ø·Ø£

def get_orderbook_imbalance(symbol, levels=20):
    """
    Ù†Ø³Ø¨Ø© Ù‚ÙˆØ© Ø§Ù„Ø´Ø±Ø§Ø¡ Ù…Ù‚Ø§Ø¨Ù„ Ø§Ù„Ø¨ÙŠØ¹ ÙÙŠ Order Book.
    Ù‚ÙŠÙ…Ø© > 0.50 = Ø¬Ø¯Ø§Ø± Ø´Ø±Ø§Ø¡ Ø£Ù‚ÙˆÙ‰
    Ù‚ÙŠÙ…Ø© < 0.40 = Ø¬Ø¯Ø§Ø± Ø¨ÙŠØ¹ Ø«Ù‚ÙŠÙ„ ÙŠØ¹ÙŠÙ‚ Ø§Ù„ØµØ¹ÙˆØ¯
    """
    sym = get_symbol_binance(symbol)
    try:
        r = requests.get(
            "https://api.binance.com/api/v3/depth",
            params={"symbol": sym, "limit": 100},
            timeout=5
        ).json()
        bid_vol = sum(float(b[1]) for b in r['bids'][:levels])
        ask_vol = sum(float(a[1]) for a in r['asks'][:levels])
        total = bid_vol + ask_vol
        return bid_vol / total if total > 0 else 0.5
    except Exception as e:
        logging.warning(f"[OrderBook Ø®Ø·Ø£ {symbol}] {e}")
        return 0.5

# ÙƒØ§Ø´ Ù…Ø´ØªØ±Ùƒ Ù„Ù…Ø¤Ø´Ø± Ø§Ù„Ø®ÙˆÙ ÙˆØ§Ù„Ø·Ù…Ø¹ (ÙŠÙØ¬Ù„Ø¨ Ù…Ø±Ø© ÙƒÙ„ 5 Ø¯Ù‚Ø§Ø¦Ù‚ ÙÙ‚Ø·)
_fng_cache = {"value": 50, "last_fetch": 0}

def get_fear_greed():
    """
    Ù…Ø¤Ø´Ø± Ø§Ù„Ø®ÙˆÙ ÙˆØ§Ù„Ø·Ù…Ø¹ Ø§Ù„Ø¹Ø§Ù„Ù…ÙŠ â€” ÙŠÙØ­Ø¯ÙŽÙ‘Ø« ÙƒÙ„ 5 Ø¯Ù‚Ø§Ø¦Ù‚.
    0-24  = Ø®ÙˆÙ Ø´Ø¯ÙŠØ¯ Ø¬Ø¯Ø§Ù‹  â†’ ØªØ¬Ù†Ø¨ Ø§Ù„Ø´Ø±Ø§Ø¡
    25-49 = Ø®ÙˆÙ             â†’ Ø­Ø°Ø±
    50-74 = Ø·Ù…Ø¹             â†’ Ù…Ù‚Ø¨ÙˆÙ„
    75+   = Ø·Ù…Ø¹ Ù…ÙØ±Ø·        â†’ Ø§Ø­ØªÙ…Ø§Ù„ Ø§Ù†Ø¹ÙƒØ§Ø³
    """
    global _fng_cache
    now = time.time()
    if now - _fng_cache["last_fetch"] > 300:
        try:
            r = requests.get(
                "https://api.alternative.me/fng/?limit=1",
                timeout=5
            ).json()
            _fng_cache["value"]      = int(r['data'][0]['value'])
            _fng_cache["last_fetch"] = now
            logging.info(f"ðŸ“Š Fear & Greed Index Ù…Ø­Ø¯Ù‘Ø«: {_fng_cache['value']}")
        except Exception as e:
            logging.warning(f"[F&G Ø®Ø·Ø£] {e}")
    return _fng_cache["value"]

# ==========================================
# === 4. Ù…Ø­Ø±Ùƒ Ø§Ù„Ù…Ø±Ø§Ù‚Ø¨Ø© ÙˆØ§Ù„ØªÙ†Ø¨ÙŠÙ‡Ø§Øª ===
# ==========================================
class AlertBot:
    def __init__(self):
        self.exchange = getattr(ccxt, EXCHANGE_NAME)({'enableRateLimit': True})
        self.state = {
            sym: {
                "in_position":    False,
                "entry_price":    0.0,
                "entry_time":     None,
                "peak_since_exit": 0.0
            } for sym in SYMBOLS
        }
        self.stats = {"win": 0, "loss": 0}

        logging.info("=" * 50)
        logging.info("ðŸ¤– ØªÙ… ØªØ´ØºÙŠÙ„ Ø§Ù„Ø¨ÙˆØª Ø¨Ù†Ø¬Ø§Ø­! Ø¬Ø§Ù‡Ø² Ù„Ù„Ù…Ø±Ø§Ù‚Ø¨Ø©...")
        logging.info("=" * 50)
        send_telegram("ðŸŸ¢ <b>Ø¨Ø¯Ø£ Ø§Ù„Ø¨ÙˆØª Ø¨Ø§Ù„Ù…Ø±Ø§Ù‚Ø¨Ø©</b>")

    def run_strategy(self):
        logging.info("--- ÙØ­Øµ Ø¬Ø¯ÙŠØ¯ Ù„Ù„Ø£Ø³ÙˆØ§Ù‚ ---")

        # Ø¬Ù„Ø¨ F&G Ù…Ø±Ø© ÙˆØ§Ø­Ø¯Ø© Ù„ÙƒÙ„ Ø§Ù„Ø¯ÙˆØ±Ø© (Ù…Ø´ØªØ±Ùƒ Ø¨ÙŠÙ† Ø¬Ù…ÙŠØ¹ Ø§Ù„Ø¹Ù…Ù„Ø§Øª)
        fng_value = get_fear_greed()

        for symbol in SYMBOLS:
            try:
                current_bar, ama30, macdBullish30 = get_indicators(self.exchange, symbol)
                close     = current_bar['close']
                high      = current_bar['high']
                sym_state = self.state[symbol]

                if not sym_state["in_position"]:
                    if sym_state["peak_since_exit"] == 0.0:
                        sym_state["peak_since_exit"] = high
                    else:
                        sym_state["peak_since_exit"] = max(sym_state["peak_since_exit"], high)

                logging.info(
                    f"ðŸ” [{symbol}] Ø§Ù„Ø³Ø¹Ø±: {close:.4f} | "
                    f"Ø£Ø¹Ù„Ù‰ Ù‚Ù…Ø© Ù…Ø³Ø¬Ù„Ø©: {sym_state['peak_since_exit']:.4f}"
                )

                # -----------------------------------------------
                # Ø­Ø§Ù„Ø© Ø§Ù„Ø§Ù†ØªØ¸Ø§Ø± ÙˆØ§Ù„Ø´Ø±Ø§Ø¡
                # -----------------------------------------------
                if not sym_state["in_position"]:
                    req_price    = sym_state["peak_since_exit"] * (1 - DROP_PERC / 100)
                    isPriceDropped = (sym_state["peak_since_exit"] == 0.0) or (close <= req_price)
                    isSqzReady   = current_bar['isStrongBullish'] or current_bar['isWeakBearish']
                    buyCond      = current_bar['wvf_green'] and isSqzReady
                    isAboveAMA30 = close > ama30

                    # --- ÙÙ„Ø§ØªØ± Order Flow ---
                    cvd_ratio  = get_cvd(symbol)
                    ob_balance = get_orderbook_imbalance(symbol)

                    isBuyFlow  = cvd_ratio  > 0.50  # Ø§Ù„Ù…Ø´ØªØ±ÙˆÙ† ÙŠØ¶ØºØ·ÙˆÙ† Ø£ÙƒØ«Ø±
                    isBookOk   = ob_balance > 0.40  # Ù„Ø§ Ø¬Ø¯Ø§Ø± Ø¨ÙŠØ¹ Ø«Ù‚ÙŠÙ„
                    isNotPanic = fng_value  > 25    # Ø§Ù„Ø³ÙˆÙ‚ Ù„ÙŠØ³ ÙÙŠ Ø°Ø¹Ø± Ø¹Ø§Ù…

                    logging.info(
                        f"   â®‘ [Ø´Ø±ÙˆØ· Ø§Ù„Ø¯Ø®ÙˆÙ„] "
                        f"Ù‡Ø¨ÙˆØ· ÙƒØ§ÙÙŠØŸ {isPriceDropped} | "
                        f"VIX Ø£Ø®Ø¶Ø±ØŸ {current_bar['wvf_green']} | "
                        f"SQZ Ù…Ù†Ø§Ø³Ø¨ØŸ {bool(isSqzReady)} | "
                        f"ÙÙˆÙ‚ AMA30ØŸ {isAboveAMA30} | "
                        f"MACD30 ØµØ§Ø¹Ø¯ØŸ {macdBullish30}"
                    )
                    logging.info(
                        f"   â®‘ [Order Flow]  "
                        f"CVD: {cvd_ratio:.2f} ({('âœ…' if isBuyFlow else 'âŒ')}) | "
                        f"OB: {ob_balance:.2f} ({('âœ…' if isBookOk else 'âŒ')}) | "
                        f"F&G: {fng_value} ({('âœ…' if isNotPanic else 'âŒ')})"
                    )

                    if (buyCond and isAboveAMA30 and macdBullish30 and isPriceDropped
                            and isBuyFlow and isBookOk and isNotPanic):

                        sym_state["in_position"]    = True
                        sym_state["entry_price"]    = close
                        sym_state["entry_time"]     = datetime.now()
                        sym_state["peak_since_exit"] = 0.0

                        msg = (
                            f"ðŸ›’ <b>ØªÙ†Ø¨ÙŠÙ‡ Ø´Ø±Ø§Ø¡</b>\n"
                            f"ðŸ”¹ <b>Ø§Ù„Ø¹Ù…Ù„Ø©:</b> {symbol}\n"
                            f"ðŸ’µ <b>Ø§Ù„Ø³Ø¹Ø±:</b> {close} $\n"
                            f"ðŸŽ¯ <b>Ø§Ù„Ù‡Ø¯Ù:</b> {close * (1 + TP_PERC/100):.4f} $\n"
                            f"ðŸ›‘ <b>Ø§Ù„ÙˆÙ‚Ù:</b> {close * (1 - SL_PERC/100):.4f} $\n"
                            f"ðŸ“Š <b>CVD:</b> {cvd_ratio:.2f} | "
                            f"<b>OB:</b> {ob_balance:.2f} | "
                            f"<b>F&G:</b> {fng_value}"
                        )
                        send_telegram(msg)
                        logging.info(f"â­â­ ØªÙ… Ø¥Ø±Ø³Ø§Ù„ Ø¥Ø´Ø§Ø±Ø© Ø´Ø±Ø§Ø¡ Ù„Ù€ {symbol} Ø¨Ø³Ø¹Ø± {close} â­â­")

                # -----------------------------------------------
                # Ø­Ø§Ù„Ø© Ù…Ø±Ø§Ù‚Ø¨Ø© Ø§Ù„Ù‡Ø¯Ù ÙˆØ§Ù„ÙˆÙ‚Ù
                # -----------------------------------------------
                else:
                    tp_price     = sym_state["entry_price"] * (1 + TP_PERC / 100)
                    sl_price     = sym_state["entry_price"] * (1 - SL_PERC / 100)
                    profit_perc  = ((close - sym_state["entry_price"]) / sym_state["entry_price"]) * 100

                    logging.info(
                        f"   â®‘ [ØµÙÙ‚Ø© Ù…ÙØªÙˆØ­Ø©] "
                        f"Ø§Ù„Ø¯Ø®ÙˆÙ„: {sym_state['entry_price']:.4f} | "
                        f"Ø§Ù„Ø±Ø¨Ø­ Ø§Ù„Ø¹Ø§Ø¦Ù…: {profit_perc:.2f}% | "
                        f"Ø§Ù„Ù‡Ø¯Ù: {tp_price:.4f} | "
                        f"Ø§Ù„ÙˆÙ‚Ù: {sl_price:.4f}"
                    )

                    if close >= tp_price or close <= sl_price:
                        is_win   = close >= tp_price
                        duration = str(datetime.now() - sym_state["entry_time"]).split('.')[0]

                        if is_win:
                            self.stats["win"] += 1
                            icon, txt = "âœ…", "Ø§Ù„Ù‡Ø¯Ù (TP)"
                        else:
                            self.stats["loss"] += 1
                            icon, txt = "âŒ", "ÙˆÙ‚Ù Ø§Ù„Ø®Ø³Ø§Ø±Ø© (SL)"

                        msg = (
                            f"{icon} <b>ØªÙ†Ø¨ÙŠÙ‡ Ø¥ØºÙ„Ø§Ù‚ ({txt})</b>\n"
                            f"ðŸ”¹ <b>Ø§Ù„Ø¹Ù…Ù„Ø©:</b> {symbol}\n"
                            f"ðŸ’µ <b>Ø§Ù„Ø¯Ø®ÙˆÙ„:</b> {sym_state['entry_price']:.4f} $\n"
                            f"ðŸ’° <b>Ø§Ù„Ø¥ØºÙ„Ø§Ù‚:</b> {close:.4f} $\n"
                            f"ðŸ“ˆ <b>Ø§Ù„Ø±Ø¨Ø­:</b> {profit_perc:.2f}%\n"
                            f"â± <b>Ø§Ù„Ù…Ø¯Ø©:</b> {duration}"
                        )
                        send_telegram(msg)
                        logging.info(f"ðŸ ØªÙ… Ø¥ØºÙ„Ø§Ù‚ {symbol} ({txt}) Ø¨Ø±Ø¨Ø­ {profit_perc:.2f}%")

                        sym_state["in_position"]    = False
                        sym_state["entry_price"]    = 0.0
                        sym_state["peak_since_exit"] = high

            except Exception as e:
                logging.error(f"[Ø®Ø·Ø£ ÙÙŠ {symbol}] {e}")
                time.sleep(1)

    # ==========================================
    # === 5. Ø§Ù„ØªÙ‚Ø§Ø±ÙŠØ± ===
    # ==========================================
    def send_report(self, report_type):
        wins     = self.stats["win"]
        losses   = self.stats["loss"]
        total    = wins + losses
        win_rate = (wins / total * 100) if total > 0 else 0
        open_trades = sum(1 for sym in self.state if self.state[sym]["in_position"])

        title = "ðŸ“Š Ø§Ù„ØªÙ‚Ø±ÙŠØ± Ø§Ù„ÙŠÙˆÙ…ÙŠ" if report_type == "daily" else "ðŸ“ˆ Ø§Ù„ØªÙ‚Ø±ÙŠØ± Ø§Ù„Ø£Ø³Ø¨ÙˆØ¹ÙŠ"
        msg = (
            f"<b>{title}</b>\n"
            f"â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€\n"
            f"âœ… <b>Ø±Ø§Ø¨Ø­Ø©:</b> {wins}\n"
            f"âŒ <b>Ø®Ø§Ø³Ø±Ø©:</b> {losses}\n"
            f"ðŸŽ¯ <b>Ù†Ø³Ø¨Ø© Ø§Ù„Ù†Ø¬Ø§Ø­:</b> {win_rate:.1f}%\n"
            f"ðŸ”„ <b>Ù…ÙØªÙˆØ­Ø©:</b> {open_trades}\n"
            f"â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€"
        )
        send_telegram(msg)
        logging.info(f"ðŸ“ ØªÙ… Ø¥Ø±Ø³Ø§Ù„ {title}.")
        self.stats["win"]  = 0
        self.stats["loss"] = 0

# ==========================================
# === 6. Ø§Ù„ØªØ´ØºÙŠÙ„ ===
# ==========================================
if __name__ == "__main__":
    bot = AlertBot()
    schedule.every().minute.at(":03").do(bot.run_strategy)
    schedule.every().day.at("23:59").do(bot.send_report, report_type="daily")
    schedule.every().sunday.at("23:58").do(bot.send_report, report_type="weekly")

    while True:
        schedule.run_pending()
        time.sleep(1)
