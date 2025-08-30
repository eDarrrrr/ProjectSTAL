import sys, os, json
from PyQt5.QtWidgets import QMainWindow, QApplication, QMessageBox, QPushButton, QGraphicsDropShadowEffect, QDialog
from PyQt5 import uic, QtWidgets
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSpacerItem, QSizePolicy, QTableWidgetItem, QHeaderView, QInputDialog
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QCursor, QColor, QIcon, QStandardItemModel, QStandardItem
from PyQt5.QtCore import pyqtSignal

import time
import pandas as pd
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import yfinance as yf
from pathlib import Path
from datetime import datetime
import requests, re


import resource

import Algoritm as al
from mplcanvas import MplCanvas

API_KEY = "AIzaSyCt103_Flr7bvliMztINX-nQYdz6lQaJbo"
PROJECT_ID = "testemailpass-e20cf"

class SignUp(QDialog):
    def __init__(self):
        super().__init__()
        uic.loadUi("ui/signup.ui", self)
        self.signupbutton.clicked.connect(self.signupfunction)
        self.password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.confirmpassword.setEchoMode(QtWidgets.QLineEdit.Password)
        self.btn_toggle.setCheckable(True)
        self.btn_toggle.toggled.connect(self._toggle_password)
        self.btn_toggle2.setCheckable(True)
        self.btn_toggle2.toggled.connect(self._toggle_confirmpassword)
        self.backbutton.clicked.connect(self.backtologin)
        self.setFixedSize(440, 600)
        self.setWindowFlags(Qt.WindowCloseButtonHint)

    def _toggle_password(self, checked: bool):
        if checked:
            self.password.setEchoMode(QLineEdit.Normal)
            self.btn_toggle.setText("Hide")
        else:
            self.password.setEchoMode(QLineEdit.Password)
            self.btn_toggle.setText("Show")
    
    def _toggle_confirmpassword(self, checked: bool):
        if checked:
            self.confirmpassword.setEchoMode(QLineEdit.Normal)
            self.btn_toggle2.setText("Hide")
        else:
            self.confirmpassword.setEchoMode(QLineEdit.Password)
            self.btn_toggle2.setText("Show")

    def backtologin(self):
        self.hide()
        self.loginpage = loginpage()
        self.loginpage.show()

    def signupfunction(self):
        email = self.email.text().strip()
        username = self.username.text().strip()
        password = self.password.text()
        confirm  = self.confirmpassword.text()

        if password != confirm:
            QMessageBox.warning(self, "Error", "Password and confirmation do not match!")
            return
        if not self.validate_email(email):
            QMessageBox.warning(self, "Error", "Invalid email format.")
            return
        if not self.validate_password(password):
            QMessageBox.warning(self, "Error", "Password must be at least 6 characters.")
            return
        if not username:
            QMessageBox.warning(self, "Error", "Username cannot be empty.")
            return

        # 1) Cek ketersediaan username (tanpa auth)
        try:
            if self.firebase_username_exists(username):
                QMessageBox.warning(self, "Error", "Username is already taken.")
                return
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to check username: {e}")
            return

        # 2) Buat akun di Firebase Auth
        try:
            auth_info = self.firebase_sign_up(email, password)
            id_token = auth_info["idToken"]
            uid      = auth_info["localId"]
        except requests.HTTPError as e:
            # tampilkan pesan error dari Firebase
            try:
                msg = e.response.json().get("error", {}).get("message", str(e))
            except Exception:
                msg = str(e)
            QMessageBox.critical(self, "Sign Up Failed", msg)
            return
        except Exception as e:
            QMessageBox.critical(self, "Sign Up Failed", str(e))
            return

        # 3) Reserve username (cegah dipakai user lain)
        try:
            r = self.firestore_reserve_username(id_token, uid, username)
            if r.status_code != 200:
                # kalau gagal karena balapan (sudah keburu dipakai), batalkan
                if r.status_code == 409:  # conflict
                    QMessageBox.warning(self, "Error", "Username is already taken. Please try another.")
                else:
                    QMessageBox.warning(self, "Error", f"Failed to reserve username: {r.text}")
                return
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to reserve username: {e}")
            return

        # 4) Simpan profil user di Firestore (/users/{uid})
        try:
            self.firestore_set_user(id_token, uid, {
                "email": email,
                "username": username,
                "createdAt": "now()"  # placeholder string; gunakan Cloud Functions kalau mau timestamp server
            })
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save user profile: {e}")
            return

        QMessageBox.information(self, "Success", f"Account created for {email}")
        self.hide()
        self.loginpage = loginpage()
        self.loginpage.show()
        

    def firebase_username_exists(self, username):
        # Cek apakah dokumen usernames/{username_lower} sudah ada (tanpa auth)
        uname = username.strip().lower()
        doc = f"projects/{PROJECT_ID}/databases/(default)/documents/usernames/{uname}"
        url = f"https://firestore.googleapis.com/v1/{doc}"
        r = requests.get(url)
        if r.status_code == 200:
            return True
        if r.status_code == 404:
            return False
        # error lain
        r.raise_for_status()

    def firebase_sign_up(self, email, password):
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={API_KEY}"
        r = requests.post(url, json={"email": email, "password": password, "returnSecureToken": True})
        # kalau email sudah dipakai, Firebase balikin 400 dgn error message
        r.raise_for_status()
        return r.json()  # berisi idToken, refreshToken, localId (uid)

    def firestore_set_user(self, id_token, uid, data: dict):
        # Set dokumen users/{uid}
        doc = f"projects/{PROJECT_ID}/databases/(default)/documents/users/{uid}"
        url = f"https://firestore.googleapis.com/v1/{doc}"
        headers = {"Authorization": f"Bearer {id_token}"}
        payload = self._fs_fields(data)
        r = requests.patch(url, headers=headers, json=payload)
        r.raise_for_status()

    def firestore_reserve_username(self, id_token, uid, username):
        # Tulis dokumen usernames/{username_lower} = {uid: "..."}
        uname = username.strip().lower()
        doc = f"projects/{PROJECT_ID}/databases/(default)/documents/usernames/{uname}"
        url = f"https://firestore.googleapis.com/v1/{doc}"
        headers = {"Authorization": f"Bearer {id_token}"}
        payload = self._fs_fields({"uid": uid})
        # pakai PATCH; kalau ingin cegah race condition keras, bisa tambah param:
        # ?currentDocument.exists=false  → gagal bila sudah ada
        r = requests.patch(url + "?currentDocument.exists=false", headers=headers, json=payload)
        return r
    
    def _fs_fields(self, d):
        # ubah dict Python → Firestore REST typed fields (stringValue)
        fields = {}
        for k, v in d.items():
            if isinstance(v, bool):
                fields[k] = {"booleanValue": v}
            elif isinstance(v, (int, float)) and not isinstance(v, bool):
                # simple: simpan semua angka sebagai double
                fields[k] = {"doubleValue": float(v)}
            else:
                fields[k] = {"stringValue": str(v)}
        return {"fields": fields}

    def firestore_update_user_with_username(self, id_token, uid, username):
        # Simpan juga username pada users/{uid}
        return self.firestore_set_user(id_token, uid, {"username": username})

    def validate_email(self, email: str):
        return "@" in email and "." in email.split("@")[-1]

    def validate_password(self, pw: str):
        return len(pw) >= 6  # syarat minimal Firebase



class loginpage(QDialog):
    def __init__(self):
        super().__init__()
        uic.loadUi("ui/loginpage.ui", self)
        self.loginbutton.setAutoDefault(False)
        self.loginbutton.setDefault(False)
        self.loginbutton.clicked.connect(self.loginfunction)
        self.password.setEchoMode(QtWidgets.QLineEdit.Password)
        self.createaccount.clicked.connect(self.gotosignup)
        self.setWindowFlags(Qt.WindowCloseButtonHint)
        self.forgotpass.clicked.connect(self.on_forgot_password_clicked)
        self.setFixedSize(400, 500)
        self.btn_toggle.setCheckable(True)
        self.btn_toggle.toggled.connect(self._toggle_password)

    def loginfunction(self):
        username_input = self.username.text().strip()
        password_input = self.password.text().strip()

        if not username_input or not password_input:
            QMessageBox.warning(self, "Error", "Username dan password wajib diisi.")
            return

        try:
            # Jika user memasukkan email langsung, izinkan juga
            if "@" in username_input:
                QMessageBox.warning(self, "Error", "Berikan username bukan email.")
                return
            else:
                # Login pakai username → ambil email dari Firestore: usernames/{usernameLower}
                uname_lower = username_input.lower()
                doc = self.firestore_get_username_doc(uname_lower)
                if not doc:
                    QMessageBox.warning(self, "Error", "Username tidak ditemukan.")
                    return

                email_for_login = self.extract_email_from_username_doc(doc)
                if not email_for_login:
                    # Kamu belum menyimpan email di dokumen /usernames. Solusi cepat:
                    # Saat signup, simpan juga field "email" di /usernames/{usernameLower}.
                    QMessageBox.critical(
                        self, "Error",
                        "Dokumen username tidak berisi email. Perbarui schema /usernames agar menyimpan {email}."
                    )
                    return

            # Panggil Firebase Auth
            auth = self.firebase_sign_in(email_for_login, password_input)
            id_token = auth["idToken"]
            uid      = auth["localId"]
            email    = auth.get("email", email_for_login)

            # ← Di sini kamu sudah LOGIN. Jangan simpan password ke state / file.
            QMessageBox.information(self, "Success", f"Login successful! (Email: {email})")

            self.accept()
            self.mainmenu = MainMenu(
                username=username_input,  # tampilkan yang diketik (atau ambil dari profil Firestore jika mau akurat)
                email=email,
                password=password_input  # sebaiknya tidak diteruskan; kalau butuh, hilangkan parameter ini dari MainMenu
            )
            self.mainmenu.show()

        except requests.HTTPError as e:
            # Ambil pesan error dari Firebase
            try:
                msg = e.response.json().get("error", {}).get("message", str(e))
            except Exception:
                msg = str(e)
            # Pesan umum Firebase yang sering muncul:
            # EMAIL_NOT_FOUND, INVALID_PASSWORD, USER_DISABLED
            if msg == "EMAIL_NOT_FOUND":
                msg = "Akun tidak ditemukan."
            elif msg == "INVALID_PASSWORD":
                msg = "Password salah."
            elif msg == "USER_DISABLED":
                msg = "Akun dinonaktifkan."
            QMessageBox.critical(self, "Login Failed", msg)

        except Exception as e:
            QMessageBox.critical(self, "Login Failed", str(e))


    def gotosignup(self):
        self.hide()                     # sembunyikan login page
        self.signup_window = SignUp()   
        self.signup_window.show()

    def _toggle_password(self, checked: bool):
        if checked:
            self.password.setEchoMode(QLineEdit.Normal)
            self.btn_toggle.setText("Hide")
        else:
            self.password.setEchoMode(QLineEdit.Password)
            self.btn_toggle.setText("Show")

    def firebase_sign_in(self, email, password):
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={API_KEY}"
        r = requests.post(url, json={"email": email, "password": password, "returnSecureToken": True}, timeout=15)
        r.raise_for_status()
        return r.json()  # {idToken, refreshToken, localId(uid), email, ...}

    def firestore_get_username_doc(self, username_lower):
        # GET dokumen usernames/{usernameLower} (read publik sesuai rules)
        doc = f"projects/{PROJECT_ID}/databases/(default)/documents/usernames/{username_lower}"
        url = f"https://firestore.googleapis.com/v1/{doc}"
        r = requests.get(url, timeout=15)
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()

    def extract_email_from_username_doc(self, doc_json):
        # Mendukung dua skema umum:
        # 1) fields.email.stringValue
        # 2) fields.uid.stringValue  (kalau hanya ada uid, sebaiknya tambahkan email di dokumen ini saat signup)
        fields = doc_json.get("fields", {})
        if "uid" in fields and "stringValue" in fields["uid"]:
            doc = f"projects/{PROJECT_ID}/databases/(default)/documents/users/{fields['uid']['stringValue']}"
            url = f"https://firestore.googleapis.com/v1/{doc}"
            r = requests.get(url, timeout=15)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            user_doc = r.json()
            user_doc.get("fields", {})
            if "email" in user_doc.get("fields", {}) and "stringValue" in user_doc["fields"]["email"]:
                return user_doc["fields"]["email"]["stringValue"]
        return None  # tidak ada email; sulit login dengan username saja
    
    def send_password_reset(self, email: str, continue_url: str | None = None):
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={API_KEY}"
        payload = {"requestType": "PASSWORD_RESET", "email": email}
        if continue_url:
            payload["continueUrl"] = continue_url  # opsional: redirect setelah user selesai reset
        r = requests.post(url, json=payload, timeout=15)
        # Firebase akan balas 200 meski email tidak terdaftar **jika di-enable di sisi mereka**;
        # tapi seringnya 400: EMAIL_NOT_FOUND. Untuk keamanan, kita tampilkan pesan generik.
        if r.status_code != 200:
            try:
                msg = r.json().get("error", {}).get("message")
            except Exception:
                msg = r.text
            # Jangan bocorkan status akun (anti account enumeration)
            # -> tetap tampilkan pesan sukses generik
        return True
    
    def firebase_send_password_reset(self, email: str):
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:sendOobCode?key={API_KEY}"
        payload = {
            "requestType": "PASSWORD_RESET",
            "email": email
        }
        r = requests.post(url, json=payload, timeout=15)
        j = r.json()
        if r.status_code != 200:
            raise RuntimeError(j.get("error", {}).get("message", r.text))
        return True

    def firebase_verify_reset_code(self, oob_code: str) -> str:
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:resetPassword?key={API_KEY}"
        payload = {"oobCode": oob_code}
        r = requests.post(url, json=payload, timeout=15)
        j = r.json()
        if r.status_code != 200:
            raise RuntimeError(j.get("error", {}).get("message", r.text))
        return j.get("email", "")

    def firebase_confirm_reset(self, oob_code: str, new_password: str):
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:resetPassword?key={API_KEY}"
        payload = {"oobCode": oob_code, "newPassword": new_password}
        r = requests.post(url, json=payload, timeout=15)
        j = r.json()
        if r.status_code != 200:
            raise RuntimeError(j.get("error", {}).get("message", r.text))
        return True
    
    def ask_email(self):
        msg = QMessageBox(self)
        msg.setWindowTitle("Forgot Password")
        msg.setText("Masukkan email Anda:")

        # tambahkan input field
        email_input = QLineEdit(msg)
        email_input.setPlaceholderText("contoh: user@example.com")
        msg.layout().addWidget(email_input, 1, 1)
        email_input.setStyleSheet("color: white; background-color: #2b2b2b;")

        msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        result = msg.exec_()

        if result == QMessageBox.Ok:
            email = email_input.text().strip()
            if email:
                QMessageBox.information(self, "Email Input", f"Anda memasukkan: {email}")
                return email
            else:
                QMessageBox.warning(self, "Error", "Email tidak boleh kosong.")
                return

    def on_forgot_password_clicked(self):
        # 1. minta email
        dlg = QInputDialog(self)
        dlg.setWindowTitle("Forgot Password")
        dlg.setLabelText("Masukkan email:")
        dlg.setTextEchoMode(QLineEdit.Normal)
        dlg.setStyleSheet("""
            QLineEdit {
                color: white;
                background-color: #2b2b2b;
                border: 1px solid #555;
                padding: 4px;
            }
            QLabel {
                color: white;
            }
            QPushButton {
                color: white;
                background-color: #444;
                border: 1px solid #666;
                padding: 4px 10px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #555;
            }
            QPushButton:pressed {
                background-color: #333;
            }
        """)
        ok = dlg.exec_()
        email = dlg.textValue().strip()
        if not ok or not email:
            return

        # 2. kirim email reset
        try:
            self.firebase_send_password_reset(email)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Gagal kirim reset: {e}")
            return

        QMessageBox.information(self, "Email terkirim",
            "Kami sudah mengirim email reset password jika email terdaftar.\n"
            "Silakan buka email, lalu copy link tersebut atau klik link tersebut.\n"
            "Cek folder spam jika tidak ada di inbox.")

        # 3. minta user paste kode/link dari email
        dlg = QInputDialog(self)
        dlg.setWindowTitle("Kode Reset")
        dlg.setLabelText("Paste link/kode dari email:")
        dlg.setTextEchoMode(QLineEdit.Normal)
        dlg.setStyleSheet("""
            QLineEdit {
                color: white;
                background-color: #2b2b2b;
                border: 1px solid #555;
                padding: 4px;
            }
            QLabel {
                color: white;
            }
            QPushButton {
                color: white;
                background-color: #444;
                border: 1px solid #666;
                padding: 4px 10px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #555;
            }
            QPushButton:pressed {
                background-color: #333;
            }
""")
        ok = dlg.exec_()
        code = dlg.textValue().strip()
        if not ok or not code:
            return

        import re
        m = re.search(r"[?&]oobCode=([^&]+)", code)
        oob = m.group(1) if m else code

        try:
            email_from_code = self.firebase_verify_reset_code(oob)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Kode tidak valid: {e}")
            return

        # 4. minta password baru
        for title in ["Password Baru", "Konfirmasi Password"]:
            dlg = QInputDialog(self)
            dlg.setWindowTitle(title)
            dlg.setLabelText(title)
            dlg.setTextEchoMode(QLineEdit.Password)
            dlg.setStyleSheet("""
                QLineEdit {
                    color: white;
                    background-color: #2b2b2b;
                    border: 1px solid #555;
                    padding: 4px;
                }
                QLabel {
                    color: white;
                }
                QPushButton {
                    color: white;
                    background-color: #444;
                    border: 1px solid #666;
                    padding: 4px 10px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #555;
                }
                QPushButton:pressed {
                    background-color: #333;
                }
            """)
            ok = dlg.exec_()
            if not ok: return
            if title == "Password Baru":
                new1 = dlg.textValue()
            else:
                new2 = dlg.textValue()

        if new1 != new2:
            QMessageBox.warning(self, "Error", "Password tidak cocok.")
            return

        try:
            self.firebase_confirm_reset(oob, new1)
            QMessageBox.information(self, "Sukses", "Password berhasil direset.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Gagal reset: {e}")



class StockDataWindow(QMainWindow):
    def __init__(self, stock_name="", stock_df=None, parent=None):
        super().__init__(parent)
        uic.loadUi("ui/CompanyStockDashboard.ui", self)
        self.setWindowTitle("Stock Data")
        # Set company long name, profile, market cap, volume, price, and change
        long_name, profile, market_cap, volume, pbv, price, change, eps, pe_ratio, net_profit_margin = self.get_company_info(stock_name)
        # Print company worth score in terminal
        try:
            import Algoritm as al
            print("\nCalculating company worth score for:")
            print(f"PBV={pbv}, PE={pe_ratio}, Market Cap={market_cap}")
            score = al.company_worth_score(pbv, pe_ratio, market_cap)
            if hasattr(self, "worthmeter"):
                self.worthmeter.setText(f"Worthmeter : {score}")
        except Exception as e:
            print(f"[Error calculating company worth score]: {e}")
        if hasattr(self, "companyName"):
            self.companyName.setText(long_name)
        if hasattr(self, "companySubtitle"):
            self.companySubtitle.setText(profile)
        if hasattr(self, "lblMarketcap"):
            self.lblMarketcap.setText(f"Market Cap: {market_cap}")
        if hasattr(self, "lblVolume"):
            self.lblVolume.setText(f"Volume: {volume}")
        if hasattr(self, "lblPBV"):
            self.lblPBV.setText(f"PBV: {pbv}")
        if hasattr(self, "lblPrice"):
            self.lblPrice.setText(price)
        if hasattr(self, "lblChange"):
            self.lblChange.setText(change)
        if hasattr(self, "lblEPS"):
            self.lblEPS.setText(f"EPS: {eps}")
        if hasattr(self, "lblPE"):
            self.lblPE.setText(f"PE Ratio: {pe_ratio}")
        if hasattr(self, "lblNP"):
            self.lblNP.setText(f"Net Profit Margin: {net_profit_margin}")

        # Plot price charts in tab widgets: day, month, year
        if stock_name:
            self.plot_price_tabs(stock_name)
            self.plot_another_charts(stock_name)

        # Connect btnBack to go back to MainMenu
        if hasattr(self, "btnBack"):
            self.btnBack.clicked.connect(self.go_back_to_main_menu)

    def go_back_to_main_menu(self):
        # Show MainMenu and close this window
        from PyQt5 import uic
        from PyQt5.QtWidgets import QMainWindow
        # Try to find parent MainMenu or create new if not found
        parent = self.parent()
        if parent is not None and parent.__class__.__name__ == "MainMenu":
            parent.show()
        else:
            from main import MainMenu
            self.main_menu = MainMenu()
            self.main_menu.show()
        self.close()

    def plot_another_charts(self, ticker):
        yf_ticker = yf.Ticker(ticker)
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
        import matplotlib.pyplot as plt
        from PyQt5.QtWidgets import QVBoxLayout
        import pandas as pd
        def set_canvas(widget, fig):
            layout = widget.layout()
            if not layout:
                layout = QVBoxLayout()
                widget.setLayout(layout)
            for i in reversed(range(layout.count())):
                item = layout.itemAt(i)
                w = item.widget()
                if w:
                    w.setParent(None)
            canvas = FigureCanvas(fig)
            layout.addWidget(canvas)

        # Revenue
        try:
            fin = yf_ticker.quarterly_financials
            if fin is not None and not fin.empty:
                rev = None
                for key in ['Total Revenue', 'TotalRevenue', 'totalRevenue']:
                    if key in fin.index:
                        rev = fin.loc[key]
                        break
                if rev is not None:
                    rev = rev.sort_index(ascending=True)
                    rev = rev[-8:]
                    fig, ax = plt.subplots(figsize=(6,3))
                    ax.bar([str(d)[:7] for d in rev.index], rev.values, color="#2eb11f")
                    ax.set_title(f"Quarterly Revenue")
                    ax.set_xlabel("Quarter")
                    ax.set_ylabel("Revenue")
                    ax.tick_params(axis='x', rotation=45)
                    fig.tight_layout()
                    widget = getattr(self, "revenue", None)
                    if widget:
                        set_canvas(widget, fig)
        except Exception:
            pass

        # Profit (Net Income)
        try:
            fin = yf_ticker.quarterly_financials
            if fin is not None and not fin.empty:
                profit = None
                for key in ['Net Income', 'NetIncome', 'netIncome']:
                    if key in fin.index:
                        profit = fin.loc[key]
                        break
                if profit is not None:
                    profit = profit.sort_index(ascending=True)
                    profit = profit[-8:]
                    fig, ax = plt.subplots(figsize=(6,3))
                    ax.bar([str(d)[:7] for d in profit.index], profit.values, color="#1f77b4")
                    ax.set_title(f"Quarterly Net Profit")
                    ax.set_xlabel("Quarter")
                    ax.set_ylabel("Net Profit")
                    ax.tick_params(axis='x', rotation=45)
                    fig.tight_layout()
                    widget = getattr(self, "profit", None)
                    if widget:
                        set_canvas(widget, fig)
        except Exception:
            pass

        # Equity curve (Fixed Amount SIP) using Algoritm.py
        try:
            import Algoritm as al
            df = al.download_one_ticker(ticker)
            # Equity curve logic from Algoritm.py ROI()
            price_ref = 'Close' if 'Close' in df.columns else ('Adj Close' if 'Adj Close' in df.columns else None)
            if price_ref is not None:
                dfp = df.copy()
                dfp = dfp.loc[:, ~dfp.columns.duplicated()].copy()
                dfp = dfp.sort_values('Date').reset_index(drop=True)
                SIP_DAY = 30
                FIXED_AMOUNT = 1_000.0
                def pick_monthly_row(g):
                    hit = g[g['Day'] == SIP_DAY]
                    return hit.iloc[-1] if len(hit) else g.iloc[-1]
                buys = (
                    dfp.groupby(['Year', 'Month'], as_index=False)
                    .apply(pick_monthly_row)
                    .reset_index(drop=True)
                    .sort_values('Date')
                )
                buys_2 = buys.copy()
                buys_2['cash_out'] = FIXED_AMOUNT
                buys_2['shares_bought'] = buys_2['cash_out'] / buys_2[price_ref]
                equity_dates, equity_values = [], []
                shares_cum, buy_idx = 0.0, 0
                for _, row in dfp.iterrows():
                    while buy_idx < len(buys_2) and buys_2.iloc[buy_idx]['Date'].date() == row['Date'].date():
                        shares_cum += float(buys_2.iloc[buy_idx]['shares_bought'])
                        buy_idx += 1
                    equity_dates.append(row['Date'])
                    equity_values.append(shares_cum * float(row[price_ref]))
                import matplotlib.pyplot as plt
                fig, ax = plt.subplots(figsize=(6,3))
                ax.plot(equity_dates, equity_values, label='Equity (Fixed Amount SIP)')
                ax.set_title(f'Equity Curve – Fixed Amount SIP ({ticker})')
                ax.set_xlabel('Date')
                ax.set_ylabel('Portfolio Value')
                ax.legend()
                fig.tight_layout()
                widget = getattr(self, "equity", None)
                if widget:
                    set_canvas(widget, fig)
        except Exception:
            pass

        # Predict next month open price using Algoritm.py and embed in predicttab's frame
        try:
            import Algoritm as al
            df = al.download_one_ticker(ticker)
            result = al.predict_next_month_open_price(df)
            if result is not None:
                future_dates, y_pred = result
                import matplotlib.pyplot as plt
                last_30 = df.sort_values('Date').reset_index(drop=True).tail(30)
                fig, ax = plt.subplots(figsize=(6,3))
                ax.plot(last_30['Date'], last_30['Open'], label='Open Price (Last 30 days)')
                ax.plot(future_dates, y_pred, label='Predicted Open Price (Next 30 days)', linestyle='--')
                ax.set_xlabel("Date")
                ax.set_ylabel("Open Price")
                ax.set_title("Prediksi Harga Open 30 Hari ke Depan (Regresi Linear, Numpy)")
                ax.legend()
                fig.tight_layout()
                # Find the frame inside the predicttab tab
                predicttab = getattr(self, "predicttab", None)
                predict_frame = None
                if predicttab is not None:
                    # Find the QFrame named "frame" inside predicttab
                    predict_frame = predicttab.findChild(type(predicttab), "frame")
                if predict_frame is not None:
                    set_canvas(predict_frame, fig)
        except Exception:
            pass

    def plot_price_tabs(self, ticker):
        import yfinance as yf
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
        import matplotlib.pyplot as plt
        import datetime
        # Helper to clear and add canvas to a widget
        def set_canvas(widget, fig):
            layout = widget.layout()
            if not layout:
                from PyQt5.QtWidgets import QVBoxLayout
                layout = QVBoxLayout()
                widget.setLayout(layout)
            # Remove old widgets
            for i in reversed(range(layout.count())):
                item = layout.itemAt(i)
                w = item.widget()
                if w:
                    w.setParent(None)
            canvas = FigureCanvas(fig)
            layout.addWidget(canvas)

        # Download data for different periods
        periods = {
            'day': ('1d', '1m'),
            'month': ('1mo', '30m'),
            'year': ('1y', '1d'),
        }
        for tab_name, (period, interval) in periods.items():
            try:
                df = yf.download(ticker, period=period, interval=interval, progress=False)
                if df.empty:
                    continue
                fig, ax = plt.subplots(figsize=(6, 3))
                ax.plot(df.index, df['Close'], label='Close Price')
                ax.set_title(f"{ticker} Price - {tab_name.capitalize()}")
                ax.set_xlabel("Date")
                ax.set_ylabel("Price")
                ax.legend()
                fig.tight_layout()
                # Add to the correct tab widget
                widget = getattr(self, tab_name, None)
                if widget:
                    set_canvas(widget, fig)
            except Exception:
                pass

    def get_company_info(self, ticker):
        try:
            import yfinance as yf
            info = yf.Ticker(ticker).info
            long_name = info.get("longName", ticker)
            # Compose profile string: symbol, exchange, sector, industry, country
            symbol = info.get("symbol", "")
            exchange = info.get("exchange", "")
            sector = info.get("sector", "")
            industry = info.get("industry", "")
            country = info.get("country", "")
            profile = " | ".join([v for v in [symbol, exchange, sector, industry, country] if v])
            # Market Cap formatting
            market_cap_val = info.get("marketCap", None)
            if market_cap_val is not None:
                if market_cap_val >= 1e12:
                    market_cap = f"${market_cap_val/1e12:.2f}T"
                elif market_cap_val >= 1e9:
                    market_cap = f"${market_cap_val/1e9:.2f}B"
                elif market_cap_val >= 1e6:
                    market_cap = f"${market_cap_val/1e6:.2f}M"
                else:
                    market_cap = f"${market_cap_val:,}"
            else:
                market_cap = "—"
            # Volume formatting
            volume_val = info.get("volume", None)
            if volume_val is not None:
                if volume_val >= 1e9:
                    volume = f"{volume_val/1e9:.2f}B"
                elif volume_val >= 1e6:
                    volume = f"{volume_val/1e6:.2f}M"
                elif volume_val >= 1e3:
                    volume = f"{volume_val/1e3:.2f}K"
                else:
                    volume = f"{volume_val:,}"
            else:
                volume = "—"
            # PBV formatting
            pbv_val = info.get("priceToBook", None)
            if pbv_val is not None:
                pbv = f"{pbv_val:.2f}"
            else:
                pbv = "—"
            # EPS formatting
            eps_val = info.get("trailingEps", None)
            if eps_val is not None:
                eps = f"{eps_val:.2f}"
            else:
                eps = "—"
            # PE Ratio formatting
            pe_val = info.get("trailingPE", None)
            if pe_val is None:
                pe_val = info.get("forwardPE", None)
            if pe_val is not None:
                pe_ratio = f"{pe_val:.2f}"
            else:
                pe_ratio = "—"
            # Net Profit Margin formatting
            net_profit_margin_val = info.get("netMargins", None)
            if net_profit_margin_val is not None:
                net_profit_margin = f"{net_profit_margin_val*100:.2f}%"
            else:
                net_profit_margin = "—"
            # Price and change
            price_val = info.get("regularMarketPrice", None)
            prev_close = info.get("regularMarketPreviousClose", None)
            if price_val is not None:
                price = f"${price_val:,.2f}"
            else:
                price = "—"
            if price_val is not None and prev_close is not None and prev_close != 0:
                pct_change = ((price_val - prev_close) / prev_close) * 100
                change = f"{pct_change:+.2f}%"
            else:
                change = "—"
            return long_name, profile, market_cap, volume, pbv, price, change, eps, pe_ratio, net_profit_margin
        except Exception:
            return ticker, "", "—", "—", "—", "—", "—", "—", "—", "—"



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



        self.symbol_name_map = self._load_symbol_name_map([
            "Data/listnasdaq.csv",     
        ])
        
        self.get_top_movers(tickers, n=10)
        self.load_top_movers_into_tables(tickers, n=5)
        
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
        if not SearchBar:
            self.HasilSearchLabel.setText("Error, Input pencarian tidak boleh kosong!")
            return
        self.HasilSearchLabel.setText(f"Searching for: {SearchBar}")
        QApplication.processEvents()

        hasilPencarian = al.main(SearchBar)
        self.HasilSearchLabel.setWordWrap(True)
        if isinstance(hasilPencarian, tuple) and hasilPencarian[0] == "Found":
            self.HasilSearchLabel.setText(f"Hasil pencarian ditemukan.")
            # Show the StockDataWindow popup with DataFrame
            _, stock_df, ticker = hasilPencarian
            self.stock_data_window = StockDataWindow(stock_name=ticker, stock_df=stock_df, parent=self)
            self.stock_data_window.show()
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
