INSTRUMENTS = [
    {"display": "EUR/CHF", "symbol": "EUR/CHF"},
    {"display": "GBP/USD", "symbol": "GBP/USD"},
    {"display": "AUD/NZD", "symbol": "AUD/NZD"},
    {"display": "EUR/USD", "symbol": "EUR/USD"},
    {"display": "AUD/CHF", "symbol": "AUD/CHF"},
    {"display": "GBP/AUD", "symbol": "GBP/AUD"},
    {"display": "EUR/CAD", "symbol": "EUR/CAD"},
    {"display": "XAU/USD — Gold", "symbol": "XAU/USD"},
    {"display": "Nasdaq 100 Index", "symbol": "NDX"},
    {"display": "USD/CAD", "symbol": "USD/CAD"},
    {"display": "FTSE 100 Index — UK 100", "symbol": "FTSE"},
    {"display": "Japan 225 CFD — JP 225", "symbol": "N225"},
    {"display": "GBP/CAD", "symbol": "GBP/CAD"},
]

DAILY_BARS = 100
H4_BARS = 180

PIVOT_LEFT = 2
PIVOT_RIGHT = 2
ATR_PERIOD = 14

# Daily level tolerance.
LEVEL_ATR_TOLERANCE = 0.25

# Inefficient/displacement definition:
# A directional run must contain at least this many candles and at least one FVG.
MIN_DISPLACEMENT_CANDLES = 2
MAX_DISPLACEMENT_CANDLES = 8
MIN_BODY_ATR = 0.35
MIN_FVG_ATR = 0.05

# Breakout lookback on 4H.
BREAKOUT_LOOKBACK = 8
