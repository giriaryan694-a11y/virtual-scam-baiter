#!/usr/bin/env python3
"""
# Author: Aryan
# Copyright: 2025 Aryan
# GitHub: https://github.com/giriaryan694-a11y
# Note: Unauthorized copying without credit is prohibited
Virtual Scam Baiter - PyQt5 GUI
Educational tool to simulate scam conversations for training purposes.
"""

import os
import sys
import json
import datetime
import textwrap
import traceback
import subprocess

from PyQt5.QtCore import QThread, pyqtSignal, Qt
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLineEdit, QLabel, QFileDialog,
    QMessageBox, QAction, QToolBar
)

# --- Config ---
KEY_FILE = "key.txt"
TRANSCRIPTS_DIR = "transcripts"
MODEL_NAME = "gemini-1.5-flash"
GITHUB_URL = "https://github.com/giriaryan694-a11y/virtual-scam-baiter"
BASE_SYSTEM = textwrap.dedent("""
You are a simulated social engineer (virtual scam-baiter) for educational purposes.
Your goal: roleplay a scammer to help a local user learn social engineering red flags.
IMPORTANT RULES:
 - NEVER ask the human to provide real sensitive data.
 - If normally passwords/OTPs/SSNs/bank details are requested, ask for fake placeholders only.
 - Include one short educational hint in [brackets].
 - Stay conversational and realistic.
""").strip()

MODE_PROMPTS = {
    "romance": "Act like an online romantic interest using flattery and emotions.",
    "financial": "Act like a financial scammer using urgency and authority.",
    "unauthorized": "Act like IT/HR staff or a hacker pretexting for access.",
}


# --- Helpers ---
def load_api_key(path=KEY_FILE):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def ensure_transcripts_dir():
    os.makedirs(TRANSCRIPTS_DIR, exist_ok=True)


def save_transcript(session_name, messages):
    ensure_transcripts_dir()
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(TRANSCRIPTS_DIR, f"{session_name}_{ts}.json")
    with open(filename, "w", encoding="utf-8") as f:
        json.dump({"session": session_name, "messages": messages}, f, indent=2, ensure_ascii=False)
    return filename


# --- Gemini Worker ---
class GeminiWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, api_key: str, system_prompt: str, user_prompt: str, model=MODEL_NAME, parent=None):
        super().__init__(parent)
        self.api_key = api_key
        self.system_prompt = system_prompt
        self.user_prompt = user_prompt
        self.model = model

    def run(self):
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)

            joined_prompt = self.system_prompt + "\n\n" + self.user_prompt
            resp = client.models.generate_content(model=self.model, contents=joined_prompt)

            text = getattr(resp, "text", "") or getattr(resp, "output_text", "")
            if not text:
                try:
                    text = resp.output[0].content[0].text
                except Exception:
                    text = str(resp)

            self.finished.emit(text.strip())
        except Exception as e:
            tb = traceback.format_exc()
            self.error.emit(f"{e}\n\nTraceback:\n{tb}")


# --- Main Window ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Virtual Scam Baiter — GUI")
        self.resize(720, 600)

        self.api_key = load_api_key()
        self.session_messages = []
        self.current_mode = "romance"

        self._build_ui()

        if not self.api_key:
            self._ask_for_key()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        # Mode buttons
        toolbar_layout = QHBoxLayout()
        self.btn_romance = QPushButton("Romance Scam")
        self.btn_finance = QPushButton("Financial Scam")
        self.btn_unauth = QPushButton("Unauthorized Access")
        for b in (self.btn_romance, self.btn_finance, self.btn_unauth):
            b.setCheckable(True)
            toolbar_layout.addWidget(b)
        self.btn_romance.clicked.connect(lambda: self._set_mode("romance"))
        self.btn_finance.clicked.connect(lambda: self._set_mode("financial"))
        self.btn_unauth.clicked.connect(lambda: self._set_mode("unauthorized"))
        self.btn_romance.setChecked(True)
        main_layout.addLayout(toolbar_layout)

        # Warning
        info = QLabel("⚠ Educational only — DO NOT paste real sensitive data.")
        info.setWordWrap(True)
        main_layout.addWidget(info)

        # Chat area
        self.chat = QTextEdit()
        self.chat.setReadOnly(True)
        self.chat.setStyleSheet("QTextEdit { background: #f6f6f6; font-family: Arial; }")
        main_layout.addWidget(self.chat, stretch=1)

        # Input
        input_layout = QHBoxLayout()
        self.input_box = QLineEdit()
        self.input_box.setPlaceholderText("Paste scammer message and press Send...")
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self._on_send_clicked)
        input_layout.addWidget(self.input_box, stretch=1)
        input_layout.addWidget(self.send_btn)
        main_layout.addLayout(input_layout)

        # Footer credits + GitHub
        footer_layout = QHBoxLayout()
        credit_label = QLabel("👨💻 Made by Aryan Giri")
        github_btn = QPushButton("🌐 GitHub Repo")
        github_btn.clicked.connect(self._open_github)
        footer_layout.addWidget(credit_label)
        footer_layout.addStretch(1)
        footer_layout.addWidget(github_btn)
        main_layout.addLayout(footer_layout)

        # Toolbar
        toolbar = QToolBar("Main")
        self.addToolBar(toolbar)
        save_act = QAction("Save Transcript", self)
        save_act.triggered.connect(self._save_current_transcript)
        toolbar.addAction(save_act)
        clear_act = QAction("Clear Chat", self)
        clear_act.triggered.connect(self._clear_chat)
        toolbar.addAction(clear_act)
        loadkey_act = QAction("Load/Change Key", self)
        loadkey_act.triggered.connect(self._ask_for_key)
        toolbar.addAction(loadkey_act)

    def _set_mode(self, mode_key: str):
        self.current_mode = mode_key
        self.btn_romance.setChecked(mode_key == "romance")
        self.btn_finance.setChecked(mode_key == "financial")
        self.btn_unauth.setChecked(mode_key == "unauthorized")
        self._append_system_message(f"Mode set to: {mode_key}")

    def _append_system_message(self, text: str):
        self.chat.append(f"<i><small>{text}</small></i>")
        self._scroll_chat_to_bottom()

    def _append_chat_message(self, sender: str, text: str):
        if sender == "user":
            html = f'<div style="margin:6px 0; text-align:left"><b>User:</b> {text}</div>'
        else:
            html = f'<div style="margin:6px 0; text-align:right"><b>Baiter:</b> {text}</div>'
        self.chat.append(html)
        self._scroll_chat_to_bottom()

    def _scroll_chat_to_bottom(self):
        cursor = self.chat.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.chat.setTextCursor(cursor)

    def _on_send_clicked(self):
        scam_text = self.input_box.text().strip()
        if not scam_text:
            return
        self._append_chat_message("user", scam_text)
        self.session_messages.append({"role": "user", "content": scam_text})
        self.input_box.clear()

        system_prompt = BASE_SYSTEM + "\n\n" + MODE_PROMPTS[self.current_mode]
        user_prompt = f"Scammer: {scam_text}\nRespond as victim + add tactic note."
        self._append_system_message("Scammer is typing...")

        if not self.api_key:
            QMessageBox.warning(self, "No API key", "Add Gemini API key in key.txt")
            return

        self.worker = GeminiWorker(self.api_key, system_prompt, user_prompt)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.error.connect(self._on_worker_error)
        self.worker.start()

    def _on_worker_finished(self, text: str):
        self._append_chat_message("baiter", text)
        self.session_messages.append({"role": "Scammer", "content": text})

    def _on_worker_error(self, err: str):
        QMessageBox.critical(self, "API Error", f"Gemini API error:\n{err}")

    def _open_github(self):
        try:
            if sys.platform.startswith("linux"):
                subprocess.Popen(["xdg-open", GITHUB_URL])
            elif sys.platform.startswith("darwin"):
                subprocess.Popen(["open", GITHUB_URL])
            elif os.name == "nt":
                os.startfile(GITHUB_URL)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to open GitHub: {e}")

    def _ask_for_key(self):
        from PyQt5.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(self, "API Key", "Paste Gemini API key:")
        if ok and text.strip():
            with open(KEY_FILE, "w", encoding="utf-8") as f:
                f.write(text.strip())
            self.api_key = text.strip()

    def _save_current_transcript(self):
        filename = save_transcript(f"vsb_{self.current_mode}", self.session_messages)
        QMessageBox.information(self, "Saved", f"Transcript saved to {filename}")

    def _clear_chat(self):
        self.chat.clear()
        self.session_messages = []


# --- Main ---
def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
           
