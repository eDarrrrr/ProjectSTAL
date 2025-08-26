import sys, os, json
from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox, QPushButton, QGraphicsDropShadowEffect, QDialog
from PyQt5 import uic, QtWidgets
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSpacerItem, QSizePolicy, QTableWidgetItem, QHeaderView
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QCursor, QColor, QIcon, QStandardItemModel, QStandardItem
from PyQt5.QtCore import pyqtSignal

import time
import pandas as pd
import yfinance as yf
from pathlib import Path
from datetime import datetime

import resource

import Algoritm as al

class SignUp(QDialog):
    def __init__(self):
        super().__init__()
        uic.loadUi("ui/signup.ui", self)
        self.signupbutton.clicked.connect(self.signupfunction)
        self.password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.confirmpassword.setEchoMode(QtWidgets.QLineEdit.Password)
     
    def signupfunction(self):
        email = self.email.text()
        username = self.username.text()
        password = self.password.text()
        confirm = self.confirmpassword.text()
        if password != confirm:
            QMessageBox.warning(self, "Error", "Password and confirmation do not match!")
            return
        
        print("Successfully registered account with email", email, "and password", password)

        # File tempat simpan data user
        filename = "users.json"

        users = {}

        if os.path.exists(filename):
            with open(filename, "r") as f:
                content = f.read().strip()   # baca isi file
                if content:                  # kalau tidak kosong
                    try:
                        users = json.loads(content)
                    except json.JSONDecodeError:
                        users = {}

        if email in users:
            QMessageBox.warning(self, "Error", "Email have been registered!")
            return
        
        for u in users.values():
            if u["username"] == username:
                QMessageBox.warning(self, "Error", "Username have been registered!")
                return

        # Tambah user baru
        users[email] = {
            "username": username,
            "password": password
        }

        with open(filename, "w") as f:
            json.dump(users, f, indent=4)

        self.hide()
        self.loginpage = loginpage()
        self.loginpage.show()



class loginpage(QDialog):
    def __init__(self):
        super().__init__()
        uic.loadUi("ui/loginpage.ui", self)
        self.loginbutton.setAutoDefault(False)
        self.loginbutton.setDefault(False)
        self.loginbutton.clicked.connect(self.loginfunction)
        self.password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.createaccount.clicked.connect(self.gotosignup)

    def loginfunction(self):
        username = self.username.text().strip()
        password = self.password.text().strip()
        
        filename = "users.json"
        if not os.path.exists(filename):
            QMessageBox.warning(self, "Error", "No account registered yet!")
            return

        with open(filename, "r") as f:
            users = json.load(f)

        # cari username di dalam semua users (karena key = email)
        for email, data in users.items():
            if data["username"] == username and data["password"] == password:
                print("Login success!\n username : ", username, "password : ", password)
                QMessageBox.information(self, "Success", f"Login succesful! (Email: {email})")
                LoginUsername = data["username"]
                LoginEmail = email
                LoginPassword = data["password"]
                self.accept()
                self.mainmenu = MainMenu(
                    username=LoginUsername,
                    email=LoginEmail,
                    password=LoginPassword
                    )
                self.mainmenu.show()
            else:
                QMessageBox.warning(self, "Error", "Username or password is incorrect!")



    def gotosignup(self):
        self.hide()                     # sembunyikan login page
        self.signup_window = SignUp()   
        self.signup_window.show()



class StockDataWindow(QDialog):
    def __init__(self, stock_name="", parent=None):
        super().__init__(parent)
        uic.loadUi("ui/stockdata.ui", self)
        self.setWindowTitle("Stock Data")
        # Example: set a label if you have one in your UI
        # self.stockNameLabel.setText(stock_name)
        # You can add more logic here to display stock data



class MainMenu(QMainWindow):
    def __init__(self, username=None, email=None, password=None):
        super().__init__()
        uic.loadUi("ui/MainMenu.ui", self)
        self.showMaximized()
        self.Page.setCurrentIndex(0)
        self.autocorrectlist.hide()
        self.setProfile(username, email)
        self.currency = "$"

        self.TopGainers.itemDoubleClicked.connect(lambda _: self._apply_selected(self.TopGainers))
        self.TopLosers.itemDoubleClicked.connect(lambda _: self._apply_selected(self.TopLosers))

        df = pd.read_csv("Data/listnasdaq.csv")
        df2 = pd.read_csv("Data/DaftarSaham.csv")
        self.company = df["Symbol"].dropna().tolist()
        self.company += df2["Code"].dropna().tolist()

        self.symbol_name_map = self._load_symbol_name_map([
            "Data/listnasdaq.csv",     
        ])
        
        self.autocorrectlist.addItems(self.company)
        self.autocorrectlist.setStyleSheet("""
        QListWidget {
            background: #242424;
            border: none;
        }
        QListWidget::item {
            color:white;
        }
        QListWidget::item:hover {
            background: #151515;
        }
        QListWidget::item:selected {
            background: #151515;
            color: white;
        }
        """)

        table_style = """
        QTableWidget {
            background-color: #1e1e1e;
            color: white;
            gridline-color: #444;
            border: 1px solid #444;
            selection-background-color: #0078d7;
            selection-color: white;
        }

        QHeaderView::section {
            background-color: #2d2d2d;
            color: white;
            padding: 4px;
            border: 1px solid #444;
        }

        QTableWidget::item {
            padding: 4px;
        }

        QTableWidget::item:selected {
            background-color: #0078d7;
            color: white;
        }
        """

        style_gainers = """
        QTableWidget { background:#1e1e1e; color:white; gridline-color:#444; border:1px solid #444; }
        QHeaderView::section { background:#2d2d2d; color:white; border:1px solid #444; padding:4px; }
        QTableWidget::item { padding:4px; }
        QTableWidget::item:selected { background:#1e3b1e; color:white; }  /* hijau gelap */
        """
        style_losers = """
        QTableWidget { background:#1e1e1e; color:white; gridline-color:#444; border:1px solid #444; }
        QHeaderView::section { background:#2d2d2d; color:white; border:1px solid #444; padding:4px; }
        QTableWidget::item { padding:4px; }
        QTableWidget::item:selected { background:#3b1e1e; color:white; }  /* merah gelap */
        """
        
        self.TopGainers.setStyleSheet(style_gainers)
        self.TopLosers.setStyleSheet(style_losers)


        self.autocorrectlist.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.SearchBar.textChanged.connect(self._on_search_text)
        
        self.Dashboard.clicked.connect(
            lambda: self.Page.setCurrentWidget(self.PageDashboard)
        )
        self.About.clicked.connect(
            lambda: self.Page.setCurrentWidget(self.PageAbout)
        )
        self.actionExit.triggered.connect(
             lambda: self.exit()
        )

        self.SearchButton.clicked.connect(self.searchbar)
        self.SearchBar.returnPressed.connect(self.searchbar)

        self.autocorrectlist.itemClicked.connect(self.on_item_clicked)

        
        self.Profile.clicked.connect(lambda: self.open_profile_dialog(username, email, password))
        

    def setProfile(self, LoginUsername, LoginEmail):
        self.Profile.setText(LoginUsername)

    def on_item_clicked(self, item):
        print("Dipilih:", item.text())
        self.SearchBar.setText(item.text())
        self.autocorrectlist.hide()


    def _on_search_text(self, text: str):
        q = text.strip()
        lw = self.autocorrectlist
        lw.clear()

        if not q:
            lw.hide()
            return

        # match sederhana: contains (case-insensitive)
        matches = [c for c in self.company if q.lower() in c.lower()]

        if not matches:
            lw.hide()
            return

        # batasi jumlah yang ditampilkan (mis. 8)
        matches = matches[:8]
        lw.addItems(matches)

        # auto tinggi agar tak perlu scrollbar
        row_h = lw.sizeHintForRow(0) if lw.count() else 24
        lw.setFixedHeight(min(lw.count(), 8) * row_h + 6)

        # pilih baris pertama supaya Enter langsung ambil
        lw.setCurrentRow(0)
        lw.show()

    def searchbar(self):
        SearchBar = self.SearchBar.text()
        self.HasilSearchLabel.setText(f"Searching for: {SearchBar}")
        QApplication.processEvents()

        hasilPencarian = al.main(SearchBar)
        self.HasilSearchLabel.setWordWrap(True)
        if hasilPencarian[0] is "Found":
            self.HasilSearchLabel.setText(f"Hasil pencarian ditemukan.")
        else:
            self.HasilSearchLabel.setText(f"{hasilPencarian}" )

        # Show the StockDataWindow popup
        self.stock_data_window = StockDataWindow(stock_name=SearchBar, parent=self)
        self.stock_data_window.exec_()

    def open_profile_dialog(self, username, email, password):
        dlg = ProfileDialog(
            username=username or "",
            email=email or "",
            password=password or "",
            parent=self
        )
        dlg.signOutRequested.connect(self._sign_out)
        dlg.exec_()

    def _sign_out(self):
        self.close()
        self.login_window = loginpage()
        self.login_window.show()

    def get_top_movers(self, tickers, n=10, period="5d"):
        data = yf.download(
            tickers,
            period=period,
            group_by="column",
            auto_adjust=False,
            progress=False,
            threads=True,
        )
        if data.empty:
            raise ValueError("Data kosong dari yfinance.")

        # pilih harga: pakai Adj Close kalau ada, else Close
        def pick_price_frame(df):
            if isinstance(df.columns, pd.MultiIndex):
                lvl0 = df.columns.get_level_values(0)
                if "Adj Close" in lvl0:
                    return df["Adj Close"]
                elif "Close" in lvl0:
                    return df["Close"]
                else:
                    raise KeyError("Tidak ada 'Adj Close' / 'Close'.")
            else:
                if "Adj Close" in df.columns:
                    return df["Adj Close"].to_frame(name="Price")
                elif "Close" in df.columns:
                    return df["Close"].to_frame(name="Price")
                else:
                    raise KeyError("Tidak ada 'Adj Close' / 'Close'.")

        px = pick_price_frame(data).dropna(how="all")
        if len(px.index) < 2:
            raise ValueError("Butuh >= 2 hari data untuk hitung perubahan.")
        
        last_ts = px.index[-1]                   # pandas Timestamp
        try:
            # yfinance biasanya UTC-naive; jadikan ET biar sama seperti Yahoo Finance
            last_et_date = last_ts.tz_localize("UTC").tz_convert("US/Eastern").date()
        except Exception:
            # kalau sudah tz-aware atau gagal konversi, ambil .date() saja
            last_et_date = last_ts.date()

        # format: "Updated Aug 25, 2025"
        updated_text = f"Updated {last_et_date.strftime('%b %d, %Y')}"

        # set ke label di UI (pastikan objectName tepat: datUpdated)
        if hasattr(self, "datUpdated"):
            self.datUpdated.setText(updated_text)
            self.datUpdated_2.setText(updated_text)
        last_local = pd.Timestamp(last_ts).to_pydatetime()
        self.datUpdated.setText(f"Updated {last_local.strftime('%b %d, %Y')}")
        self.datUpdated_2.setText(f"Updated {last_local.strftime('%b %d, %Y')}")

        last = px.iloc[-1]
        prev = px.iloc[-2]

        # normalisasi ke DataFrame
        if isinstance(last, pd.Series) and last.ndim == 1 and not isinstance(last.index, pd.MultiIndex):
            df = pd.DataFrame({
                "Symbol": last.index.astype(str),
                "Price": last.values.astype(float),
                "Change %": ((last.values - prev.values) / prev.values * 100.0)
            })
        else:
            df = pd.DataFrame({"Price": last}).reset_index()
            df.rename(columns={"level_0": "Field", "level_1": "Symbol"}, inplace=True)
            df = df[df["Field"].isin(["Adj Close","Close"])]
            df = df[["Symbol","Price"]].drop_duplicates("Symbol").set_index("Symbol")
            prev_df = pd.DataFrame({"Prev": prev}).reset_index()
            prev_df.rename(columns={"level_0": "Field", "level_1": "Symbol"}, inplace=True)
            prev_df = prev_df[prev_df["Field"].isin(["Adj Close","Close"])]
            prev_df = prev_df[["Symbol","Prev"]].drop_duplicates("Symbol").set_index("Symbol")
            df = df.join(prev_df, how="inner")
            df["Change %"] = (df["Price"] - df["Prev"]) / df["Prev"] * 100.0
            df = df.reset_index()

        df = df.dropna(subset=["Change %"]).sort_values("Change %", ascending=False)

        # ambil top gainers & losers
        top_gainers = df.head(n).reset_index(drop=True)
        top_losers  = df.tail(n).reset_index(drop=True)

        # === Tambahkan kolom Name ===
        top_gainers["Name"] = top_gainers["Symbol"].map(self.symbol_name_map).fillna("")
        top_losers["Name"]  = top_losers["Symbol"].map(self.symbol_name_map).fillna("")

        # atur urutan kolom
        top_gainers = top_gainers[["Symbol", "Name", "Price", "Change %"]]
        top_losers  = top_losers[["Symbol", "Name", "Price", "Change %"]]

        return top_gainers, top_losers

    # --- Helper isi QTableWidget dari DataFrame ---
    def _fill_table_from_df(self, table, df: pd.DataFrame, columns=("Symbol","Name","Price","Change %"), is_gainer=True):
        table.clear()
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.setRowCount(len(df))
        table.verticalHeader().setVisible(False)

        for r, (_, row) in enumerate(df.iterrows()):
            for c, col in enumerate(columns):
                val = row[col]
                if col == "Change %":
                    text = f"{val:+.2f}%"
                elif col == "Price":
                    text = f"{val:,.2f} {self.currency}"
                else:
                    text = str(val)

                item = QTableWidgetItem(text)

                # kalau kolom Change %
                if col == "Change %":
                    if val >= 0:
                        item.setForeground(QColor("lime"))   # hijau utk positif
                    else:
                        item.setForeground(QColor("red"))    # merah utk negatif
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

                elif col == "Price":
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

                table.setItem(r, c, item)

        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)
        table.setEditTriggers(table.NoEditTriggers)
        table.setSelectionBehavior(table.SelectRows)
        table.setSelectionMode(table.SingleSelection)

    # --- Load & tampilkan ke 2 tabel ---
    def load_top_movers_into_tables(self, tickers, n=10):
        try:
            gainers, losers = self.get_top_movers(tickers, n=10)
        except Exception as e:
            # kalau gagal, kosongkan tabel & bisa tampilkan pesan
            self.TopGainers.setRowCount(0)
            self.TopLosers.setRowCount(0)
            print("Gagal ambil top movers:", e)
            return

        self._fill_table_from_df(self.TopGainers, gainers)
        self._fill_table_from_df(self.TopLosers, losers)
    
    def _load_symbol_name_map(self, csv_files):
        try:
            dfs = []
            for p in csv_files:
                p = Path(p)
                if p.exists():
                    # pastikan kolom yang dipakai ada
                    df = pd.read_csv(p, usecols=["Symbol", "Company Name"])
                    dfs.append(df)
            if not dfs:
                return {}
            df_all = pd.concat(dfs, ignore_index=True)
            df_all = df_all.dropna(subset=["Symbol"]).drop_duplicates("Symbol")
            return dict(zip(df_all["Symbol"], df_all["Company Name"]))
        except Exception as e:
            print("Gagal load symbol_name_map:", e)
            return {}
        
    def _apply_selected(self, table):
        row = table.currentRow()
        if row < 0: return
        sym = table.item(row, 0).text()  # kolom 0 = Symbol
        if hasattr(self, "SearchBar"):
            self.SearchBar.setText(sym)

class ProfileDialog(QDialog):
    signOutRequested = pyqtSignal()  # sinyal ke MainMenu

    def __init__(self, username, email, password, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Profile")

        # ukuran fix
        self.setFixedSize(400, 350)

        # style dark
        self.setStyleSheet("""
            QDialog {
                background-color: #121212;
            }
            QLabel {
                color: white;
            }
            QLineEdit {
                background-color: #2c2c2c;
                color: white;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 2px;
            }
            QPushButton {
                background-color: #333;
                color: white;
                border: 1px solid #555;
                border-radius: 5px;
                padding: 4px 8px;
            }
            QPushButton:hover {
                background-color: #444;
            }
        """)

        self.username = username
        self.email = email
        self._password_plain = password

        lay = QVBoxLayout(self)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("Username:"))
        self.le_user = QLineEdit(username)
        self.le_user.setReadOnly(True)
        row1.addWidget(self.le_user)
        lay.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Email:"))
        self.le_email = QLineEdit(email)
        self.le_email.setReadOnly(True)
        row2.addWidget(self.le_email)
        lay.addLayout(row2)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel("Password:"))
        self.le_pass = QLineEdit(password)
        self.le_pass.setEchoMode(QLineEdit.Password)
        self.le_pass.setReadOnly(True)
        self.btn_toggle = QPushButton("Show")
        self.btn_toggle.setCheckable(True)
        self.btn_toggle.toggled.connect(self._toggle_password)
        row3.addWidget(self.le_pass)
        row3.addWidget(self.btn_toggle)
        lay.addLayout(row3)

        lay.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        self.btn_signout = QPushButton("Sign Out")
        self.btn_signout.clicked.connect(self._do_signout)
        lay.addWidget(self.btn_signout)

    def _toggle_password(self, checked: bool):
        if checked:
            self.le_pass.setEchoMode(QLineEdit.Normal)
            self.btn_toggle.setText("Hide")
        else:
            self.le_pass.setEchoMode(QLineEdit.Password)
            self.btn_toggle.setText("Show")

    def _do_signout(self):
        # Emit sinyal ke MainMenu
        self.signOutRequested.emit()
        self.accept()


def main():
    os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
    os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
    os.environ["QT_SCALE_FACTOR_ROUNDING_POLICY"] = "PassThrough"
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet("""
    QMessageBox QLabel { color: white; }
    QMessageBox QPushButton { color: white; 
        background-color: white;
        }
    QMessageBox QPushButton:hover {
        background-color: lightgray;
    }
    QMessageBox QPushButton:pressed {
        background-color: gray;
        color: white;
    }                  
    """)

    tickers = [
        "AAPL", "MSFT", "AMZN", "NVDA", "META",
        "GOOGL", "GOOG", "TSLA", "PEP", "COST",
        "AVGO", "ADBE", "NFLX", "AMD", "CSCO",
        "INTC", "QCOM", "TXN", "AMGN", "SBUX",
        "INTU", "HON", "AMAT", "PDD", "BKNG",
        "CHTR", "ADP", "MU", "MDLZ", "LRCX",
        "REGN", "GILD", "VRTX", "ISRG", "CSX",
        "PANW", "MAR", "ABNB", "FTNT", "MRVL",
        "KLAC", "SNPS", "CDNS", "KDP", "MELI",
        "CRWD", "MNST", "ADI", "ORLY", "NXPI",
        "CTAS", "ODFL", "ROP", "PAYX", "TEAM",
        "WDAY", "XEL", "PCAR", "IDXX", "CTSH",
        "CPRT", "DLTR", "EXC", "AEP", "CEG",
        "MRNA", "DXCM", "ZS", "CSGP", "LCID",
        "SPLK", "VRSK", "ROST", "KHC", "ALGN",
        "BIDU", "EBAY", "DDOG", "ANSS", "NTES",
        "CHKP", "VERX", "PDD", "BIIB", "DOCU",
        "ZM", "OKTA", "SIRI", "LULU", "JD",
        "PYPL", "VRSN", "FAST", "CTLT", "SGEN",
        "CDW", "AZN", "WDAY", "ZS", "CRWD",
        "MCHP", "SWKS", "MTCH", "INCY", "CSIQ"
    ]

    window = MainMenu()
    gainers, losers = window.get_top_movers(tickers, n=10)
    window.load_top_movers_into_tables(tickers, n=5)
    
    print("=== Top Gainers ===")
    print(gainers)
    print("\n=== Top Losers ===")
    print(losers)

    window.show()
    app.exec()


if __name__ == "__main__":
    main()


