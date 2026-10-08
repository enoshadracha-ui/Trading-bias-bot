import os
import requests

BASE_URL = "https://api.twelvedata.com/time_series"
API_KEY = os.getenv("TWELVE_DATA_API_KEY", "")

class MarketDataError(Exception):
    pass

def _request(symbols, interval, outputsize):
    if not API_KEY:
        raise MarketDataError("TWELVE_DATA_API_KEY is missing")

    params = {
        "symbol": ",".join(symbols),
        "interval": interval,
        "outputsize": outputsize,
        "apikey": API_KEY,
        "format": "JSON",
    }
    r = requests.get(BASE_URL, params=params, timeout=30)
    r.raise_for_status()
    data = r.json()

    if isinstance(data, dict) and data.get("status") == "error":
        raise MarketDataError(data.get("message", "Twelve Data error"))
    return data

def _rows(value):
    if isinstance(value, dict) and "values" in value:
        return value["values"]
    return []

def get_batch(symbols, interval, outputsize):
    data = _request(symbols, interval, outputsize)
    out = {}
    if len(symbols) == 1:
        out[symbols[0]] = _rows(data)
        return out

    for symbol in symbols:
        out[symbol] = _rows(data.get(symbol, {})) if isinstance(data, dict) else []
    return out

def get_daily_and_4h(symbols, daily_size, h4_size):
    # Two API calls per /bias scan: one Daily batch and one 4H batch.
    daily = get_batch(symbols, "1day", daily_size)
    h4 = get_batch(symbols, "4h", h4_size)
    return daily, h4
