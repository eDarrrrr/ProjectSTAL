import sys, os, json
from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox, QPushButton, QGraphicsDropShadowEffect, QDialog
from PyQt5 import uic, QtWidgets
from PyQt5.QtWidgets import QDialog
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QCursor, QColor, QIcon, QStandardItemModel, QStandardItem
import time
import pandas as pd

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
                self.accept()
                self.mainmenu = MainMenu()
                self.mainmenu.show()
            else:
                QMessageBox.warning(self, "Error", "Username or password is incorrect!")

    def gotosignup(self):
        self.hide()                     # sembunyikan login page
        self.signup_window = SignUp()   # simpan ke atribut biar ga kehapus
        self.signup_window.show()



class MainMenu(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("ui/MainMenu.ui", self)
        self.showMaximized()
        self.Page.setCurrentIndex(0)  # misal index dashboard itu 0
        self.autocorrectlist.hide()

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
    window = loginpage()
    window.show()
    app.exec()

if __name__ == "__main__":
    main()


