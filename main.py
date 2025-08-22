import sys, os
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QDialog, QApplication, QMessageBox, QGraphicsDropShadowEffect, QMainWindow
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QCursor, QColor, QIcon
from PyQt5.uic import loadUi

import resource

class LoginPage(QDialog):
    def __init__(self):
        super(LoginPage, self).__init__()
        loadUi("ui/loginpage.ui", self)
        self.loginbutton.clicked.connect(self.loginfunction)
        self.password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.createaccbutton.clicked.connect(self.gotocreateacc)

    def loginfunction(self):
        username = self.username.text()
        password = self.password.text()
        print("Login success!\n username:", username, "password:", password)

    def gotocreateacc(self):
        createacc = CreateAcc()
        widget.addWidget(createacc)
        widget.setCurrentIndex(widget.currentIndex() + 1)


class CreateAcc(QDialog):
    def __init__(self):
        super(CreateAcc, self).__init__()
        loadUi("ui/createacc.ui", self)
        self.SignupButton.clicked.connect(self.createaccfunction)
        self.Password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.ConfirmPass.setEchoMode(QtWidgets.QLineEdit.Password)

    def createaccfunction(self):
        name = self.Name.text()
        password = self.Password.text()
        confirm = self.ConfirmPass.text()

        if password == confirm:
            print("Account created for:", name)
            login = LoginPage()
            widget.addWidget(login)
            widget.setCurrentIndex(widget.currentIndex() + 1)
        else:
            print("Password mismatch!")

class MainMenu(QMainWindow):
    def __init__(self):
        super().__init__()
        loadUi("ui/MainMenu.ui", self)
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
         

os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "1"
os.environ["QT_AUTO_SCREEN_SCALE_FACTOR"] = "1"
os.environ["QT_SCALE_FACTOR_ROUNDING_POLICY"] = "PassThrough"

if __name__ == "__main__":
    app = QApplication(sys.argv)
    widget = QtWidgets.QStackedWidget()
    app.setStyle("Fusion")

    login = LoginPage()
    widget.addWidget(login)

    widget.setFixedWidth(480)
    widget.setFixedHeight(620)
    widget.show()

    sys.exit(app.exec_())
