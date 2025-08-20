import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

import os

while True:
    inputan = input("Search: ")
    file_path = f"Data/Stock Market Data/{inputan}.csv"
    if os.path.exists(file_path):
        SearchResult = pd.read_csv(file_path)
        break
    else:
        print("File not found. Silakan coba lagi.")


SearchResult=pd.read_csv(f"Data/Stock Market Data/{inputan}.csv")

SearchResult['Date'] = pd.to_datetime(SearchResult['Date'])

# 3. Buang kolom yang tidak dipakai
drop_cols = ['Trades', 'Deliverable Volume', '%Deliverble']
SearchResult = SearchResult.drop(columns=[c for c in drop_cols if c in SearchResult.columns], errors='ignore')

# 4. Tambah kolom Year, Month, Day
SearchResult['Year'] = SearchResult['Date'].dt.year
SearchResult['Month'] = SearchResult['Date'].dt.month
SearchResult['Day'] = SearchResult['Date'].dt.day

# 5. Lihat data awal
print(SearchResult.head())



def StockData():
    plt.figure(figsize=(10,5))
    plt.plot(SearchResult['Date'], SearchResult['Open'], label=f'{inputan} - Open Price')
    plt.xlabel("Date")
    plt.ylabel("Price (INR)")
    plt.title(f"Harga Open {inputan}")
    plt.legend()
    plt.show()

def VolumeData():
    plt.figure(figsize=(10,5))
    plt.plot(SearchResult['Date'], SearchResult['Volume'], label=f'{inputan} - Volume', color='orange')
    plt.xlabel("Date")
    plt.ylabel("Volume")
    plt.title(f"Volume {inputan}")
    plt.legend()
    plt.show()


def ROI():
    # ====== CONFIG ======
    CSV_PATH = f"Data/Stock Market Data/{inputan}.csv"  # pakai saham yang dicari
    SIP_DAY   = 30                                      # beli tiap tgl 30
    FX_RATE   = 195.0                                   # 1 INR = 195 IDR (contoh; silakan ganti)
    CURRENCY  = "IDR"
    FIXED_AMOUNT = 1_000_000.0                          # Fixed amount per bulan dalam IDR
    # ====================

    # 1) Load & prep
    df = pd.read_csv(CSV_PATH)
    df['Date'] = pd.to_datetime(df['Date'])
    df = df.sort_values('Date').reset_index(drop=True)

    # pastikan Close ada
    assert 'Close' in df.columns, "Kolom 'Close' wajib ada."

    # konversi harga INR -> IDR (kolom harga saja)
    price_cols = [c for c in ['Open','High','Low','Last','Close','VWAP'] if c in df.columns]
    for c in price_cols:
        df[c] = df[c] * FX_RATE

    df['Year']  = df['Date'].dt.year
    df['Month'] = df['Date'].dt.month
    df['Day']   = df['Date'].dt.day

    # 2) ambil satu baris per bulan (tgl 30, kalau gak ada ambil hari terakhir bulan itu)
    def pick_monthly_row(g):
        hit = g[g['Day'] == SIP_DAY]
        return hit.iloc[-1] if len(hit) > 0 else g.iloc[-1]

    buys = (
        df.groupby(['Year', 'Month'], as_index=False)
          .apply(pick_monthly_row)
          .reset_index(drop=True)
          .sort_values('Date')
    )

    # 3A) MODE 1: 1 lembar/bulan
    buys_1share = buys.copy()
    buys_1share['shares_bought'] = 1.0
    buys_1share['cash_out'] = buys_1share['Close'] * buys_1share['shares_bought']

    total_shares_1 = buys_1share['shares_bought'].sum()
    total_cost_1   = buys_1share['cash_out'].sum()           # dalam IDR
    final_price    = df['Close'].iloc[-1]                    # dalam IDR
    final_value_1  = total_shares_1 * final_price            # dalam IDR
    roi_1          = (final_value_1 - total_cost_1) / total_cost_1

    months = len(buys_1share)
    years  = months / 12 if months > 0 else np.nan
    cagr_1 = (final_value_1 / total_cost_1)**(1/years) - 1 if years > 0 else np.nan

    # 3B) MODE 2: Fixed amount/bulan (dalam IDR)
    buys_amt = buys.copy()
    buys_amt['cash_out'] = FIXED_AMOUNT
    buys_amt['shares_bought'] = buys_amt['cash_out'] / buys_amt['Close']

    total_shares_2 = buys_amt['shares_bought'].sum()
    total_cost_2   = buys_amt['cash_out'].sum()              # IDR
    final_value_2  = total_shares_2 * final_price            # IDR
    roi_2          = (final_value_2 - total_cost_2) / total_cost_2
    cagr_2         = (final_value_2 / total_cost_2)**(1/years) - 1 if years > 0 else np.nan

    # 4) Ringkasan
    print("=== SIP Summary (beli per bulan) ===")
    print(f"Data: {CSV_PATH}")
    print(f"Kurs: 1 INR = {FX_RATE:.2f} {CURRENCY}")
    print(f"Periode pembelian: {months} bulan (~{years:.2f} tahun)")
    print(f"Harga terakhir: {final_price:,.2f} {CURRENCY}")

    print("\n-- MODE 1: 1 lembar/bulan --")
    print(f"Total lembar  : {total_shares_1:.0f}")
    print(f"Total modal   : {total_cost_1:,.2f} {CURRENCY}")
    print(f"Nilai akhir   : {final_value_1:,.2f} {CURRENCY}")
    print(f"ROI           : {roi_1*100:.2f}%")
    print(f"CAGR (approx) : {cagr_1*100:.2f}% / tahun")

    print("\n-- MODE 2: Fixed amount/bulan --")
    print(f"Fixed amount  : {FIXED_AMOUNT:,.2f} {CURRENCY} per bulan")
    print(f"Total lembar  : {total_shares_2:.4f}")
    print(f"Total modal   : {total_cost_2:,.2f} {CURRENCY}")
    print(f"Nilai akhir   : {final_value_2:,.2f} {CURRENCY}")
    print(f"ROI           : {roi_2*100:.2f}%")
    print(f"CAGR (approx) : {cagr_2*100:.2f}% / tahun")

    # 5) Plot harga + titik beli (dalam IDR)
    plt.figure(figsize=(11,5))
    plt.plot(df['Date'], df['Close'], label='Close Price')
    plt.scatter(buys['Date'], buys['Close'], s=30, marker='o', label='Buy points')
    plt.title(f'Close Price & Monthly SIP Buy Points ({CURRENCY})')
    plt.xlabel('Date')
    plt.ylabel(f'Price ({CURRENCY})')
    plt.legend()
    plt.tight_layout()
    plt.show()

    # 6) Equity curve (mode fixed-amount)
    equity_dates, equity_values = [], []
    shares_cum, cash_cum, buy_idx = 0.0, 0.0, 0
    for _, row in df.iterrows():
        while buy_idx < len(buys_amt) and buys_amt.iloc[buy_idx]['Date'].date() == row['Date'].date():
            shares_cum += buys_amt.iloc[buy_idx]['shares_bought']
            cash_cum   += buys_amt.iloc[buy_idx]['cash_out']
            buy_idx += 1
        equity = shares_cum * row['Close']  # IDR
        equity_dates.append(row['Date'])
        equity_values.append(equity)

    plt.figure(figsize=(11,5))
    plt.plot(equity_dates, equity_values, label=f'Equity (Fixed Amount SIP, {CURRENCY})')
    plt.title(f'Equity Curve – Fixed Amount SIP ({CURRENCY})')
    plt.xlabel('Date')
    plt.ylabel(f'Portfolio Value ({CURRENCY})')
    plt.legend()
    plt.tight_layout()
    plt.show()



ROI()