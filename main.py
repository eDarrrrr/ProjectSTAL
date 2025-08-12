import sys
from PyQt5 import uic, QtWidgets
from PyQt5.QtWidgets import QDialog, QMainWindow, QApplication, QMessageBox, QPushButton, QGraphicsDropShadowEffect
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QCursor, QColor, QIcon

import resource

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


def main():
    app = QApplication(sys.argv)
    window = loginpage()
    window.show()
    app.exec()

if __name__ == "__main__":
    main()
