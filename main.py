import sys, os, json
from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox, QPushButton, QGraphicsDropShadowEffect, QDialog
from PyQt5 import uic, QtWidgets
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSpacerItem, QSizePolicy
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QCursor, QColor, QIcon, QStandardItemModel, QStandardItem
from PyQt5.QtCore import pyqtSignal
import time
import pandas as pd
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt

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
    def __init__(self, stock_name="", stock_df=None, parent=None):
        super().__init__(parent)
        uic.loadUi("ui/stockdata.ui", self)
        self.setWindowTitle("Stock Data")
        # Get long name from yfinance
        long_name = self.get_company_long_name(stock_name)
        self.set_stock_name(long_name)
        # Plot price chart in the 'harga' frame if data is provided
        if stock_df is not None and not stock_df.empty:
            self.plot_price(stock_df, stock_name)
        # Show company profile in the profile frame
        self.set_company_profile(stock_name)

    def get_company_long_name(self, ticker):
        try:
            import yfinance as yf
            info = yf.Ticker(ticker).info
            return info.get("longName", ticker)
        except Exception:
            return ticker

    def set_stock_name(self, stock_name):
        # Try to add a QLabel to the 'nama' frame and set its text
        if hasattr(self, "nama"):
            from PyQt5.QtWidgets import QLabel, QVBoxLayout
            layout = self.nama.layout()
            if layout is None:
                layout = QVBoxLayout()
                self.nama.setLayout(layout)
            else:
                for i in reversed(range(layout.count())):
                    widget = layout.itemAt(i).widget()
                    if widget:
                        widget.setParent(None)
            label = QLabel(stock_name)
            label.setStyleSheet("color: white; font-size: 22px; font-weight: bold;")
            label.setAlignment(Qt.AlignCenter)
            layout.addWidget(label)

    def plot_price(self, df, ticker):
        # Only show data from the last year
        if not df.empty:
            last_date = df['Date'].max()
            one_year_ago = last_date - pd.Timedelta(days=365)
            df = df[df['Date'] >= one_year_ago]
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.plot(df['Date'], df['Open'], label=f'{ticker} - Open Price')
        ax.set_xlabel("Date")
        ax.set_ylabel("Price")
        ax.set_title(f"Harga Open {ticker}")
        ax.legend()
        fig.tight_layout()
        canvas = FigureCanvas(fig)
        # Remove previous widgets if any
        for i in reversed(range(self.harga.layout().count() if self.harga.layout() else 0)):
            item = self.harga.layout().itemAt(i)
            widget = item.widget()
            if widget:
                widget.setParent(None)
        # Set layout if not set
        if not self.harga.layout():
            from PyQt5.QtWidgets import QVBoxLayout
            self.harga.setLayout(QVBoxLayout())
        self.harga.layout().addWidget(canvas)

    def set_company_profile(self, ticker):
        try:
            import yfinance as yf
            info = yf.Ticker(ticker).info
            profile_text = []
            profile_text.append(f"<b>Name:</b> {info.get('longName', '-')}")
            profile_text.append(f"<b>Symbol:</b> {info.get('symbol', '-')}")
            profile_text.append(f"<b>Exchange:</b> {info.get('exchange', '-')}")
            profile_text.append(f"<b>Sector:</b> {info.get('sector', '-')}")
            profile_text.append(f"<b>Industry:</b> {info.get('industry', '-')}")
            profile_text.append(f"<b>Country:</b> {info.get('country', '-')}")
            profile_text.append(f"<b>Website:</b> <a href='{info.get('website', '-')}' style='color:#00aaff'>{info.get('website', '-')}</a>")
            # profile_text.append(f"<b>Description:</b><br>{info.get('longBusinessSummary', '-')}")
            """profile_text.append("<hr><b>Key Statistics</b>")
            profile_text.append(f"Market Cap: {info.get('marketCap', '-')}")
            profile_text.append(f"Shares Outstanding: {info.get('sharesOutstanding', '-')}")
            profile_text.append(f"Trailing P/E: {info.get('trailingPE', '-')}")
            profile_text.append(f"Forward P/E: {info.get('forwardPE', '-')}")
            profile_text.append(f"PEG Ratio: {info.get('pegRatio', '-')}")
            profile_text.append(f"Price to Book: {info.get('priceToBook', '-')}")
            profile_text.append(f"Dividend Yield: {info.get('dividendYield', '-')}")
            profile_text.append(f"52 Week High: {info.get('fiftyTwoWeekHigh', '-')}")
            profile_text.append(f"52 Week Low: {info.get('fiftyTwoWeekLow', '-')}")
            profile_text.append(f"Beta: {info.get('beta', '-')}")
            profile_text.append(f"Average Volume: {info.get('averageVolume', '-')}")"""
            html = "<br>".join(profile_text)
        except Exception as e:
            html = f"Could not fetch company profile/statistics: {e}"
        # Set the text in the QTextEdit if it exists
        if hasattr(self, "profileText"):
            self.profileText.setHtml(html)


class MainMenu(QMainWindow):
    def __init__(self, username=None, email=None, password=None):
        super().__init__()
        uic.loadUi("ui/MainMenu.ui", self)
        self.showMaximized()
        self.Page.setCurrentIndex(0)
        self.autocorrectlist.hide()
        self.setProfile(username, email)


        df = pd.read_csv("Data/listnasdaq.csv")
        df2 = pd.read_csv("Data/DaftarSaham.csv")
        self.company = df["Symbol"].dropna().tolist()
        self.company += df2["Code"].dropna().tolist()
        
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
        if isinstance(hasilPencarian, tuple) and hasilPencarian[0] == "Found":
            self.HasilSearchLabel.setText(f"Hasil pencarian ditemukan.")
            # Show the StockDataWindow popup with DataFrame
            _, stock_df, ticker = hasilPencarian
            self.stock_data_window = StockDataWindow(stock_name=ticker, stock_df=stock_df, parent=self)
            self.stock_data_window.exec_()
        else:
            self.HasilSearchLabel.setText(f"{hasilPencarian}" )

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
    window = MainMenu()
    window.show()
    app.exec()

if __name__ == "__main__":
    main()


