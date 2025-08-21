import sys, os
from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox, QPushButton, QGraphicsDropShadowEffect, QDialog
from PyQt5 import uic, QtWidgets
from PyQt5.QtWidgets import QDialog
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QCursor, QColor, QIcon
import time

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


