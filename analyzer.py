from config import (
    INSTRUMENTS, DAILY_BARS, H4_BARS, PIVOT_LEFT, PIVOT_RIGHT,
    ATR_PERIOD, LEVEL_ATR_TOLERANCE, MIN_DISPLACEMENT_CANDLES,
    MAX_DISPLACEMENT_CANDLES, MIN_BODY_ATR, MIN_FVG_ATR,
    BREAKOUT_LOOKBACK,
)
from market_data import get_daily_and_4h


def f(x):
    return float(x)


def normalize(rows):
    out = []
    for r in reversed(rows or []):
        try:
            out.append({
                "open": f(r["open"]),
                "high": f(r["high"]),
                "low": f(r["low"]),
                "close": f(r["close"]),
                "datetime": r.get("datetime", ""),
            })
        except (KeyError, TypeError, ValueError):
            pass
    return out


def atr(bars, period=ATR_PERIOD):
    if len(bars) < period + 1:
        return None
    trs = []
    for i in range(1, len(bars)):
        b, p = bars[i], bars[i - 1]
        trs.append(max(
            b["high"] - b["low"],
            abs(b["high"] - p["close"]),
            abs(b["low"] - p["close"]),
        ))
    return sum(trs[-period:]) / period


def candle_body(b):
    return abs(b["close"] - b["open"])


def pivots(bars):
    lows, highs = [], []
    for i in range(PIVOT_LEFT, len(bars) - PIVOT_RIGHT):
        window = bars[i-PIVOT_LEFT:i+PIVOT_RIGHT+1]
        if bars[i]["low"] == min(x["low"] for x in window):
            lows.append((i, bars[i]["low"]))
        if bars[i]["high"] == max(x["high"] for x in window):
            highs.append((i, bars[i]["high"]))
    return lows, highs


def line_chart_levels(bars):
    """
    Mechanical interpretation of the line-chart key levels in the supplied
    reference image.

    A-shape: a confirmed swing high -> resistance.
    V-shape: a confirmed swing low -> support.
    RBS: a former resistance level that was broken upward and later retested.
    SBR: a former support level that was broken downward and later retested.
    OCL: an open/close boundary that is subsequently respected/rejected.
    """
    if len(bars) < 15:
        return []

    lows, highs = pivots(bars[:-1])
    levels = []

    # A-shape / resistance and V-shape / support.
    for idx, price in highs[-8:]:
        levels.append(("A-Shape Resistance", price, "resistance"))
    for idx, price in lows[-8:]:
        levels.append(("V-Shape Support", price, "support"))

    # RBS/SBR: use older pivot levels that were crossed and then revisited.
    tol = (atr(bars) or abs(bars[-1]["close"]) * 0.001) * LEVEL_ATR_TOLERANCE
    sample = bars[-30:-1]

    for _, level, _ in levels[:]:
        crossed_up = any(b["close"] > level + tol for b in sample)
        crossed_down = any(b["close"] < level - tol for b in sample)
        if crossed_up:
            levels.append(("RBS", level, "support"))
        if crossed_down:
            levels.append(("SBR", level, "resistance"))

    # OCL: recent candle open/close boundaries.
    for b in bars[-8:-1]:
        levels.append(("OCL", b["open"], "neutral"))
        levels.append(("OCL", b["close"], "neutral"))

    return levels


def daily_rejection(bars):
    """
    Daily rule:
      line-chart key level -> latest completed Daily candle interacts with
      the level -> candle closes away from it.

    The result is directional only. It does not define an entry.
    """
    if len(bars) < 25:
        return 0

    last = bars[-1]
    a = atr(bars)
    if not a:
        return 0

    tol = a * LEVEL_ATR_TOLERANCE
    levels = line_chart_levels(bars[:-1])
    if not levels:
        return 0

    candidates = []
    for kind, level, role in levels:
        if last["low"] <= level + tol and last["high"] >= level - tol:
            candidates.append((kind, level, role))

    if not candidates:
        return 0

    rng = max(last["high"] - last["low"], 1e-12)
    upper_wick = last["high"] - max(last["open"], last["close"])
    lower_wick = min(last["open"], last["close"]) - last["low"]

    bullish_close = last["close"] > last["open"] and last["close"] >= last["low"] + rng * 0.60
    bearish_close = last["close"] < last["open"] and last["close"] <= last["low"] + rng * 0.40

    for _, _, role in candidates:
        # Support-side rejection -> bullish.
        if role == "support" and bullish_close and lower_wick >= rng * 0.20:
            return 1
        # Resistance-side rejection -> bearish.
        if role == "resistance" and bearish_close and upper_wick >= rng * 0.20:
            return -1

    # OCL can be neutral, so use the candle's rejection direction only when
    # it clearly rejects an open/close boundary.
    if any(role == "neutral" for _, _, role in candidates):
        if bullish_close and lower_wick >= rng * 0.25:
            return 1
        if bearish_close and upper_wick >= rng * 0.25:
            return -1

    return 0


def fvg_at(bars, i, direction):
    """
    Three-candle FVG:
      bullish: current low > candle two bars back high
      bearish: current high < candle two bars back low
    """
    if i < 2:
        return None
    a, c = bars[i - 2], bars[i]
    gap = (c["low"] - a["high"]) if direction == 1 else (a["low"] - c["high"])
    if gap <= 0:
        return None
    return gap


def displacement_sequence(bars, direction):
    """
    Finds the directional breakout impulse itself.

    It must contain:
      - multiple directional candles
      - meaningful candle bodies
      - at least one FVG/imbalance created by those candles
      - the sequence must end in a breakout of the prior range

    This deliberately does NOT look for the user's later retracement/entry.
    """
    if len(bars) < 30:
        return False

    a = atr(bars)
    if not a:
        return False

    breakout_start = len(bars) - 1
    prior = bars[max(0, breakout_start - BREAKOUT_LOOKBACK):breakout_start]

    if direction == 1:
        prior_extreme = max(b["high"] for b in prior)
        broke = bars[-1]["close"] > prior_extreme
        directional = lambda b: b["close"] > b["open"]
    else:
        prior_extreme = min(b["low"] for b in prior)
        broke = bars[-1]["close"] < prior_extreme
        directional = lambda b: b["close"] < b["open"]

    if not broke:
        return False

    # Walk backwards from the breakout candle to find its directional run.
    run = []
    i = len(bars) - 1
    while i >= 0 and len(run) < MAX_DISPLACEMENT_CANDLES:
        b = bars[i]
        if not directional(b):
            break
        run.append(i)
        i -= 1

    run.reverse()

    if len(run) < MIN_DISPLACEMENT_CANDLES:
        return False

    meaningful = sum(candle_body(bars[i]) >= a * MIN_BODY_ATR for i in run)
    if meaningful < MIN_DISPLACEMENT_CANDLES:
        return False

    # The imbalance must be created inside the breakout run, not somewhere
    # unrelated many candles earlier.
    has_fvg = False
    for i in run:
        gap = fvg_at(bars, i, direction)
        if gap is not None and gap >= a * MIN_FVG_ATR:
            has_fvg = True
            break

    return has_fvg


def breakout_only(bars, direction):
    if len(bars) < BREAKOUT_LOOKBACK + 2:
        return False
    prior = bars[-(BREAKOUT_LOOKBACK + 1):-1]
    last = bars[-1]
    if direction == 1:
        return last["close"] > max(b["high"] for b in prior)
    return last["close"] < min(b["low"] for b in prior)


def liquidity_sweep_before_breakout(bars, direction):
    """
    Scenario A:
    liquidity is taken first, then the directional breakout occurs.
    """
    if len(bars) < BREAKOUT_LOOKBACK + 5:
        return False

    breakout_bar = bars[-1]
    setup = bars[-(BREAKOUT_LOOKBACK + 5):-1]
    split = max(2, len(setup) // 2)
    before = setup[:split]
    after = setup[split:]

    if direction == 1:
        swept = min(b["low"] for b in after) < min(b["low"] for b in before)
        broke = breakout_bar["close"] > max(b["high"] for b in setup)
    else:
        swept = max(b["high"] for b in after) > max(b["high"] for b in before)
        broke = breakout_bar["close"] < min(b["low"] for b in setup)

    return swept and broke


def h4_confirmation(bars, direction):
    """
    Two valid scenarios; either is enough.

    A) liquidity sweep + breakout, with inefficient price action
    B) most recent breakout, with inefficient price action

    No retracement/entry condition is checked.
    """
    if not displacement_sequence(bars, direction):
        return False

    scenario_a = liquidity_sweep_before_breakout(bars, direction)
    scenario_b = breakout_only(bars, direction)

    return scenario_a or scenario_b


def analyze(daily_rows, h4_rows):
    daily = normalize(daily_rows)
    h4 = normalize(h4_rows)

    d = daily_rejection(daily)
    if d == 0:
        return "NO BIAS"

    if h4_confirmation(h4, d):
        return "BULLISH BIAS" if d == 1 else "BEARISH BIAS"

    return "NO BIAS"


def scan_all():
    symbols = [x["symbol"] for x in INSTRUMENTS]
    daily, h4 = get_daily_and_4h(symbols, DAILY_BARS, H4_BARS)

    results = []
    for item in INSTRUMENTS:
        try:
            bias = analyze(daily.get(item["symbol"], []), h4.get(item["symbol"], []))
        except Exception as exc:
            print("ANALYSIS ERROR", item["symbol"], repr(exc))
            bias = "NO BIAS"
        results.append({
            "display": item["display"],
            "symbol": item["symbol"],
            "bias": bias,
        })
    return results
