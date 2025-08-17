import yfinance as yf
import pandas as pd

def get_stock_data(ticker: str, period="6mo", interval="1d"):

    stock = yf.Ticker(ticker)
    data = stock.history(period=period, interval=interval)
    data.reset_index(inplace=True)  
    return data

def get_company_info(ticker: str):

    stock = yf.Ticker(ticker)
    info = stock.info
    company_info = {
        "Company": info.get("longName"),
        "Sector": info.get("sector"),
        "Industry": info.get("industry"),
        "Exchange": info.get("exchange"),
        "Currency": info.get("currency"),
        "Website": info.get("website"),
    }
    return company_info

def get_dividends(ticker: str):

    stock = yf.Ticker(ticker)
    dividends = stock.dividends
    return dividends


