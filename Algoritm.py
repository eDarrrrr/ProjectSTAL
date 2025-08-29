import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf


SUFFIXES = ["", ".JK", ".NS", ".BO", ".L", ".TO", ".AX", ".HK", ".T", ".SI", ".DE", ".PA", ".SW", ".MI", ".MC"]
# ========== UTIL ==========

def normalize_ticker(user_input: str) -> str:
    """Uppercase + trim; tidak menambah suffix di sini."""
    return user_input.strip().upper()

    
def try_all_suffixes(ticker: str, suffixes=None):
    """Coba ticker apa adanya, lalu semua suffix."""
    if suffixes is None:
        suffixes = [".JK", ".NS", ".AX", ".TO", ".L", ".HK", ".SS", ".SZ", ".TW", ".KS"]

    tried = []

    # 1. coba ticker original
    try:
        return download_one_ticker(ticker), ticker
    except Exception as e:
        tried.append(ticker)

    # 2. coba ticker + suffix
    for s in suffixes:
        t = f"{ticker}{s}"
        try:
            return download_one_ticker(t), t
        except Exception as e:
            tried.append(t)

    # 3. kalau semua gagal
    raise ValueError(f"{ticker} Tidak ditemukan.")


def download_one_ticker(ticker: str) -> pd.DataFrame:
    """
    Download 1 ticker dari yfinance, ratakan kolom jika MultiIndex,
    pastikan 'Date' jadi kolom biasa, dan tambah Year/Month/Day.
    """
    raw = yf.download(
        ticker,
        period="max",
        interval="1d",
        auto_adjust=False,
        group_by="ticker",
        progress=False,
        threads=False,
    )
    if raw is None or raw.empty:
        raise ValueError("Data kosong.")

    # Jika kolom MultiIndex, ambil level untuk ticker
    if isinstance(raw.columns, pd.MultiIndex):
        lv0 = raw.columns.get_level_values(0)
        lv1 = raw.columns.get_level_values(1)
        if ticker in lv1:            # (field, ticker)
            dfp = raw.xs(ticker, axis=1, level=1)
        elif ticker in lv0:          # (ticker, field)
            dfp = raw.xs(ticker, axis=1, level=0)
        else:
            dfp = raw.copy()
        dfp = dfp.loc[:, ~dfp.columns.duplicated()].copy()
    else:
        dfp = raw.copy()

    # Buang timezone di index jika ada, lalu jadikan kolom 'Date'
    if isinstance(dfp.index, pd.DatetimeIndex):
        try:
            dfp.index = dfp.index.tz_localize(None)
        except Exception:
            pass
    dfp = dfp.reset_index()
    # Pastikan kolom nama 'Date'
    if 'Date' not in dfp.columns:
        dfp = dfp.rename(columns={dfp.columns[0]: 'Date'})

    # Rapikan dan kolom bantu
    dfp = dfp.sort_values('Date').reset_index(drop=True)
    dfp['Year'] = dfp['Date'].dt.year
    dfp['Month'] = dfp['Date'].dt.month
    dfp['Day'] = dfp['Date'].dt.day
    return dfp

# ========== VISUAL ==========

def StockData(SearchResult: pd.DataFrame, ticker: str, currency_label="$"):
    # Only show data from the last year
    df = SearchResult.copy()
    if not df.empty:
        last_date = df['Date'].max()
        one_year_ago = last_date - pd.Timedelta(days=365)
        df = df[df['Date'] >= one_year_ago]
    plt.figure(figsize=(10, 5))
    plt.plot(df['Date'], df['Open'], label=f'{ticker} - Open Price')
    plt.xlabel("Date")
    plt.ylabel(f"Price ({currency_label})")
    plt.title(f"Harga Open {ticker} ({currency_label})")
    plt.legend()
    plt.tight_layout()
        # No plt.show() here; handled by UI embedding

def VolumeData(SearchResult: pd.DataFrame, ticker: str):
    plt.figure(figsize=(10, 5))
    plt.plot(SearchResult['Date'], SearchResult['Volume'], label=f'{ticker} - Volume')
    plt.xlabel("Date")
    plt.ylabel("Volume")
    plt.title(f"Volume {ticker}")
    plt.legend()
    plt.tight_layout()
        # No plt.show() here; handled by UI embedding

# ========== ROI (SIP) ==========

def ROI(SearchResult: pd.DataFrame, ticker: str, max_months=None):
    """
    Simulasi SIP bulanan:
    - MODE 1: beli 1 lembar tiap bulan
    - MODE 2: fixed amount tiap bulan
    Harga dikonversi ke IDR via FX_RATE.
    """
    SIP_DAY = 30
    FX_RATE = 1         # Ubah sesuai kurs: contoh 1 INR/USD -> IDR
    CURRENCY = "$"
    FIXED_AMOUNT = 1_000.0  # IDR per bulan

    dfp = SearchResult.copy()
    dfp = dfp.loc[:, ~dfp.columns.duplicated()].copy()
    dfp = dfp.sort_values('Date').reset_index(drop=True)

    # Tentukan kolom harga referensi
    price_ref = 'Close' if 'Close' in dfp.columns else ('Adj Close' if 'Adj Close' in dfp.columns else None)
    if price_ref is None:
        raise ValueError("Butuh kolom 'Close' atau 'Adj Close'.")

    # Konversi semua harga ke IDR (volume tidak dikonversi)
    for c in ['Open', 'High', 'Low', 'Close', 'Adj Close']:
        if c in dfp.columns:
            dfp[c] = dfp[c] * FX_RATE

    # Ambil 1 baris per bulan: tgl 30 kalau ada, kalau tidak hari terakhir bulan tsb.
    def pick_monthly_row(g: pd.DataFrame) -> pd.Series:
        hit = g[g['Day'] == SIP_DAY]
        return hit.iloc[-1] if len(hit) else g.iloc[-1]

    buys = (
        dfp.groupby(['Year', 'Month'], as_index=False)
          .apply(pick_monthly_row)
          .reset_index(drop=True)
          .sort_values('Date')
    )

    if max_months is not None:
        buys = buys.head(max_months)

    # MODE 1: 1 lembar / bulan
    buys_1 = buys.copy()
    buys_1['shares_bought'] = 1.0
    buys_1['cash_out'] = buys_1[price_ref] * buys_1['shares_bought']

    total_shares_1 = float(buys_1['shares_bought'].sum())
    total_cost_1 = float(buys_1['cash_out'].sum())
    final_price = float(dfp[price_ref].iloc[-1])
    final_value_1 = total_shares_1 * final_price
    roi_1 = (final_value_1 - total_cost_1) / total_cost_1 if total_cost_1 > 0 else float('nan')

    months = len(buys_1)
    years = months / 12 if months > 0 else float('nan')
    cagr_1 = (final_value_1 / total_cost_1) ** (1 / years) - 1 if (months > 0 and total_cost_1 > 0) else float('nan')

    # MODE 2: Fixed amount / bulan
    buys_2 = buys.copy()
    buys_2['cash_out'] = FIXED_AMOUNT
    buys_2['shares_bought'] = buys_2['cash_out'] / buys_2[price_ref]

    total_shares_2 = float(buys_2['shares_bought'].sum())
    total_cost_2 = float(buys_2['cash_out'].sum())
    final_value_2 = total_shares_2 * final_price
    roi_2 = (final_value_2 - total_cost_2) / total_cost_2 if total_cost_2 > 0 else float('nan')
    cagr_2 = (final_value_2 / total_cost_2) ** (1 / years) - 1 if (months > 0 and total_cost_2 > 0) else float('nan')

    # Ringkasan
    print("=== SIP Summary (beli per bulan) ===")
    print(f"Ticker: {ticker}")
    print(f"Kurs konversi: 1 unit -> {FX_RATE:.2f} {CURRENCY}")
    print(f"Periode pembelian: {months} bulan (~{years:.2f} tahun)")
    print(f"Harga terakhir: {final_price:,.2f} {CURRENCY}")

    print("\n-- MODE 1: 1 lembar/bulan --")
    print(f"Total lembar  : {total_shares_1:.0f}")
    print(f"Total modal   : {total_cost_1:,.2f} {CURRENCY}")
            # No plt.show() here; handled by UI embedding
    print(f"ROI           : {roi_1*100:.2f}%")
    print(f"CAGR (approx) : {cagr_1*100:.2f}% / tahun")

    print("\n-- MODE 2: Fixed amount/bulan --")
    print(f"Fixed amount  : {FIXED_AMOUNT:,.2f} {CURRENCY} / bulan")
    print(f"Total lembar  : {total_shares_2:.4f}")
    print(f"Total modal   : {total_cost_2:,.2f} {CURRENCY}")
    print(f"Nilai akhir   : {final_value_2:,.2f} {CURRENCY}")
    print(f"ROI           : {roi_2*100:.2f}%")
    print(f"CAGR (approx) : {cagr_2*100:.2f}% / tahun")

    # Plot harga + titik beli (IDR)
    plt.figure(figsize=(11, 5))
    plt.plot(dfp['Date'], dfp[price_ref], label=f'{ticker} {price_ref}')
    plt.scatter(buys['Date'], buys[price_ref], s=30, marker='o', label='Buy points')
    plt.title(f'{price_ref} & Monthly SIP Buy Points ({CURRENCY})')
    plt.xlabel('Date')
    plt.ylabel(f'Price ({CURRENCY})')
            # No plt.show() here; handled by UI embedding
    plt.tight_layout()
    # plt.show()  # REMOVE: now embedded in UI

    # Equity curve (Fixed Amount)
    equity_dates, equity_values = [], []
    shares_cum, buy_idx = 0.0, 0
    for _, row in dfp.iterrows():
        while buy_idx < len(buys_2) and buys_2.iloc[buy_idx]['Date'].date() == row['Date'].date():
            shares_cum += float(buys_2.iloc[buy_idx]['shares_bought'])
            buy_idx += 1
        equity_dates.append(row['Date'])
        equity_values.append(shares_cum * float(row[price_ref]))

    plt.figure(figsize=(11, 5))
    plt.plot(equity_dates, equity_values, label=f'Equity (Fixed Amount SIP, {CURRENCY})')
    plt.title(f'Equity Curve – Fixed Amount SIP ({ticker}, {CURRENCY})')
    plt.xlabel('Date')
    plt.ylabel(f'Portfolio Value ({CURRENCY})')
    plt.legend()
    plt.tight_layout()
    # plt.show()  # REMOVE: now embedded in UI

# ========== MAIN ==========

def company_worth_score(pbv, pe, market_cap):
    """
    Calculate a simple 'worth it' score (1-4) based on PBV, P/E, and Market Cap.
    Returns the score and prints an explanation.
    """
    score_details = []
    score = 0
    # PBV scoring
    try:
        pbv_val = float(pbv)
        if pbv_val < 1:
            score += 4
            score_details.append("PBV < 1 (Undervalued): +4")
        elif pbv_val < 1.5:
            score += 3
            score_details.append("PBV < 1.5: +3")
        elif pbv_val < 3:
            score += 2
            score_details.append("PBV < 3: +2")
        else:
            score += 1
            score_details.append("PBV >= 3: +1")
    except:
        score_details.append("PBV not available: +0")

    # P/E scoring
    try:
        pe_val = float(pe)
        if pe_val <= 0:
            score += 1
            score_details.append("P/E <= 0: +1 (unprofitable or negative earnings)")
        elif pe_val < 10:
            score += 3
            score_details.append("P/E < 10: +3 (cheap)")
        elif pe_val < 20:
            score += 4
            score_details.append("P/E 10-20: +4 (healthy)")
        elif pe_val < 35:
            score += 2
            score_details.append("P/E 20-35: +2 (expensive)")
        else:
            score += 1
            score_details.append("P/E >= 35: +1 (very expensive)")
    except:
        score_details.append("P/E not available: +0")

    # Market Cap scoring (very simple: bigger is safer, but not always better for growth)
    try:
        # Accept market cap as string like "$1.23B" or "$456M"
        mc = str(market_cap).replace("$", "").replace(",", "").strip().upper()
        if "T" in mc:
            mc_val = float(mc.replace("T", "")) * 1e12
        elif "B" in mc:
            mc_val = float(mc.replace("B", "")) * 1e9
        elif "M" in mc:
            mc_val = float(mc.replace("M", "")) * 1e6
        else:
            mc_val = float(mc)
        if mc_val >= 1e11:
            score += 4
            score_details.append("Market Cap >= $100B: +4 (very large)")
        elif mc_val >= 1e10:
            score += 3
            score_details.append("Market Cap >= $10B: +3 (large)")
        elif mc_val >= 1e9:
            score += 2
            score_details.append("Market Cap >= $1B: +2 (mid)")
        else:
            score += 1
            score_details.append("Market Cap < $1B: +1 (small)")
    except:
        score_details.append("Market Cap not available: +0")

    # Average and scale to 1-4
    n_metrics = 3
    raw_score = score / n_metrics
    scaled_score = min(4, max(1, round(raw_score)))
    print("\n=== Company Worth Score ===")
    for d in score_details:
        print(d)
    print(f"Raw score: {raw_score:.2f}  |  Final Score (1-4): {scaled_score}")
    if scaled_score == 4:
        print("Interpretation: Excellent value and safety based on these metrics.")
    elif scaled_score == 3:
        print("Interpretation: Good value and/or safety.")
    elif scaled_score == 2:
        print("Interpretation: Average or mixed signals.")
    else:
        print("Interpretation: Risky or overvalued based on these metrics.")
    return scaled_score
def predict_next_month_open_price(SearchResult: pd.DataFrame):

    """
    Prediksi harga open untuk 30 hari ke depan menggunakan regresi linear
    berdasarkan 30 hari harga open terakhir, hanya dengan numpy.
    """
    df = SearchResult.copy()
    df = df.sort_values('Date').reset_index(drop=True)
    if len(df) < 30:
        print("Data kurang dari 30 hari, prediksi tidak dapat dilakukan.")
        return None

    # Ambil 30 hari terakhir
    last_30 = df.tail(30)
    X = np.arange(30)  # Hari ke-0 sampai ke-29
    y = last_30['Open'].values

    # Regresi linear manual: y = a*X + b
    A = np.vstack([X, np.ones(len(X))]).T
    a, b = np.linalg.lstsq(A, y, rcond=None)[0]

    # Prediksi 30 hari ke depan (hari ke-30 sampai ke-59)
    X_future = np.arange(30, 60)
    y_pred = a * X_future + b

    # Buat tanggal prediksi
    last_date = last_30['Date'].iloc[-1]
    future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=30, freq='B')  # hari kerja

    # Plot hasil prediksi
    plt.figure(figsize=(10, 5))
    plt.plot(last_30['Date'], last_30['Open'], label='Open Price (Last 30 days)')
    plt.plot(future_dates, y_pred, label='Predicted Open Price (Next 30 days)', linestyle='--')
    plt.xlabel("Date")
    plt.ylabel("Open Price")
    plt.title("Prediksi Harga Open 30 Hari ke Depan (Regresi Linear, Numpy)")
    plt.legend()
    plt.tight_layout()
        # No plt.show() here; handled by UI embedding

    # Tampilkan prediksi hari pertama dan terakhir
    print(f"Prediksi harga open 1 hari ke depan: {y_pred[0]:,.2f}")
    print(f"Prediksi harga open 30 hari ke depan: {y_pred[-1]:,.2f}")

    return future_dates, y_pred

def display_company_profile_and_stats(ticker: str):
    """
    Display company profile and statistics using yfinance.
    """
    try:
        yf_ticker = yf.Ticker(ticker)
        info = yf_ticker.info
        # Basic profile
        print("\n=== Company Profile ===")
        print(f"Name: {info.get('longName', '-')}")
        print(f"Symbol: {info.get('symbol', '-')}")
        print(f"Exchange: {info.get('exchange', '-')}")
        print(f"Sector: {info.get('sector', '-')}")
        print(f"Industry: {info.get('industry', '-')}")
        print(f"Country: {info.get('country', '-')}")
        print(f"Website: {info.get('website', '-')}")
        print(f"Description: {info.get('longBusinessSummary', '-')}\n")
        # Statistics
        print("=== Key Statistics ===")
        print(f"Market Cap: {info.get('marketCap', '-')}")
        print(f"Shares Outstanding: {info.get('sharesOutstanding', '-')}")
        print(f"Trailing P/E: {info.get('trailingPE', '-')}")
        print(f"Forward P/E: {info.get('forwardPE', '-')}")
        print(f"PEG Ratio: {info.get('pegRatio', '-')}")
        print(f"Price to Book: {info.get('priceToBook', '-')}")
        print(f"Dividend Yield: {info.get('dividendYield', '-')}")
        print(f"52 Week High: {info.get('fiftyTwoWeekHigh', '-')}")
        print(f"52 Week Low: {info.get('fiftyTwoWeekLow', '-')}")
        print(f"Beta: {info.get('beta', '-')}")
        print(f"Average Volume: {info.get('averageVolume', '-')}")
    except Exception as e:
        print(f"Could not fetch company profile/statistics: {e}")

def plot_quarterly_revenue_last_5_years(ticker: str):
    """
    Fetch and plot quarterly revenue for the last 5 years (20 quarters) using yfinance.
    """
    try:
        yf_ticker = yf.Ticker(ticker)
        # yfinance quarterly financials: columns are quarters (YYYY-MM-DD)
        income_stmt = getattr(yf_ticker, "quarterly_income_stmt", None)
        if income_stmt is None or income_stmt.empty:
            income_stmt = getattr(yf_ticker, "quarterly_financials", None)
        if income_stmt is None or income_stmt.empty:
            print("Tidak ada data revenue (quarterly income statement) untuk ticker ini.")
            return
        # Revenue row: 'Total Revenue' or 'TotalRevenue'
        for rev_key in ['Total Revenue', 'TotalRevenue', 'totalRevenue']:
            if rev_key in income_stmt.index:
                revenue_row = income_stmt.loc[rev_key]
                break
        else:
            print("Tidak ada data revenue (Total Revenue) di quarterly income statement.")
            return
        # Sort by date ascending, take last 20 quarters (5 years)
        revenue_row = revenue_row.sort_index(ascending=True)
        quarters = [str(d)[:7] for d in revenue_row.index][-20:]
        revenues = revenue_row.values[-20:]
        plt.figure(figsize=(14, 5))
        plt.bar(quarters, revenues, color="#2eb11f")
        plt.xlabel("Quarter")
        plt.ylabel("Revenue")
        plt.title(f"Quarterly Revenue for {ticker} (Last 5 Years)")
        plt.xticks(rotation=45)
        plt.tight_layout()
        # No plt.show() here; handled by UI embedding
        # Print revenue values
        for q, r in zip(quarters, revenues):
            print(f"Revenue {q}: {r:,.0f}")
    except Exception as e:
        print(f"Could not fetch or plot quarterly revenue data: {e}")

def main(SearchInput):
    while True:
        # raw = input("Search (contoh: AAPL atau TATAMOTORS): ")
        raw = SearchInput
        ticker = normalize_ticker(raw)
        try:
            SearchResult, used_ticker = try_all_suffixes(ticker)
            print(" Ketemu:", used_ticker)
            break
        except ValueError as e:
            print(" Error:", e)
            return f"Hasil pencarian tidak ditemukan. karena: {e}"

    # Debug singkat:
    print(SearchResult.columns.tolist())
    print(SearchResult.head())

    # Jalankan analisis
    VolumeData(SearchResult, ticker)
    StockData(SearchResult, ticker)
    ROI(SearchResult, ticker, max_months=12)
    # Print company profile and statistics
    display_company_profile_and_stats(used_ticker)
    # Prediksi harga open 1 bulan ke depan
    predict_next_month_open_price(SearchResult)
    # Plot quarterly revenue for the last 5 years
    plot_quarterly_revenue_last_5_years(used_ticker)
    return "Found", SearchResult, ticker
