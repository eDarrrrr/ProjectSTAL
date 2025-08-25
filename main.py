import sys, os
from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox, QPushButton, QGraphicsDropShadowEffect, QDialog
from PyQt5 import uic, QtWidgets
from PyQt5.QtWidgets import QDialog
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QCursor, QColor, QIcon, QStandardItemModel, QStandardItem
import time
import pandas as pd

import resource

import Algoritm as al

class loginpage(QDialog):
    def __init__(self):
        super().__init__()
        uic.loadUi("ui/loginpage.ui", self)
        self.loginbutton.clicked.connect(self.loginfunction)
        self.password.setEchoMode(QtWidgets.QLineEdit.Password)

    def loginfunction(self):
        username = self.username.text()
        password = self.password.text()
        print("Login success!\n username : ", username, "password : ", password)

class MainMenu(QMainWindow):
    def __init__(self):
        super().__init__()
        uic.loadUi("ui/MainMenu.ui", self)
        self.showMaximized()
        self.Page.setCurrentIndex(0)  # misal index dashboard itu 0
        self.autocorrectlist.hide()

        df = pd.read_csv("listnasdaq.csv")
        self.company = df["Symbol"].dropna().tolist()

        # print(self.company[:10])
        # self.company = [
        #     "AAPL", "GOOGL", "AMZN", "MSFT", "TSLA",
        #     "BABA", "NFLX", "NVDA", "META", "ADBE",
        #     "TLKM", "BBRI", "BMRI", "BBCA"
        # ]


        
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
    window = MainMenu()
    window.show()
    app.exec()

if __name__ == "__main__":
    main()


