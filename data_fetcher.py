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
def get_fundamentals(ticker):
    stock = yf.Ticker(ticker)

    info = stock.info  
    financials = stock.financials  
    quarterly = stock.quarterly_financials  

    fundamentals = {
        "Market Cap": info.get("marketCap"),
        "PE Ratio": info.get("trailingPE"),
        "PBV": info.get("priceToBook"),
        "Dividend Yield": info.get("dividendYield"),
        "Revenue (last annual)": financials.loc["Total Revenue"].iloc[0] if "Total Revenue" in financials.index else None,
        "Net Income (last annual)": financials.loc["Net Income"].iloc[0] if "Net Income" in financials.index else None,
        "Revenue (last quarter)": quarterly.loc["Total Revenue"].iloc[0] if "Total Revenue" in quarterly.index else None,
        "Net Income (last quarter)": quarterly.loc["Net Income"].iloc[0] if "Net Income" in quarterly.index else None,
    }

    return fundamentals

