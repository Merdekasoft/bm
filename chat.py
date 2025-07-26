#!/usr/bin/env python3
# Description: P2P Chat Application with Auto-Discovery (NSD) and Encryption (TLS)
# Final Version by Gemini (Chunked file streaming with all bug fixes)

import sys
import socket
import getpass
import json
import time
import os
import random
import threading
import ssl
import html
import base64
import struct 
import uuid 
from pathlib import Path
from datetime import datetime
from zeroconf import ServiceInfo, Zeroconf, ServiceBrowser
import subprocess

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QListWidget, QListWidgetItem, QTextBrowser, QLineEdit, QPushButton, QStackedWidget,
    QLabel, QFileDialog, QProgressBar, QMenu, QMessageBox, QSizePolicy, QSpacerItem,
    QScrollArea, QSystemTrayIcon, QMenu as QTrayMenu
)
from PySide6.QtCore import QThread, Signal, QObject, Qt, QUrl, QTimer, QSize
from PySide6.QtGui import (
    QIcon, QFont, QDesktopServices, QAction, QPalette, QPixmap, QPainter, QColor,
    QPainterPath
)
from PySide6.QtMultimedia import QSoundEffect
from PySide6.QtSvg import QSvgRenderer

# Tambahkan import untuk KDE theme
try:
    from PySide6.QtWidgets import QStyleFactory
except ImportError:
    QStyleFactory = None

# --- Application Configuration ---
HOME_DIR = str(Path.home())
APP_COLORS = {
    "primary_green": "#00A884", "primary_green_dark": "#075E54", "secondary_green": "#25D366",
    "chat_bg": "#EFEAE2", "incoming_bg": "#FFFFFF", "outgoing_bg": "#D9FDD3",
    "text_primary": "#303030", "timestamp": "#667781", "header_bg": "#F0F2F5",
    "sidebar_bg": "#F0F2F5", "active_chat": "#E9EDEF", "notification": "#25D366",
    "icon_color": "#54656F",
    "input_border": "#DEE2E6",
    "ping_color": "#D32F2F"
}
ICONS = {
    "user": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>""",
    "send": """<svg viewBox="0 0 24 24" height="24" width="24"><path fill="currentColor" d="M1.101,21.757L23.8,12.028L1.101,2.3l0.011,7.912l13.623,1.816L1.112,13.845 L1.101,21.757z"></path></svg>""",
    "ping": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path></svg>""",
    "attach": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path></svg>""",
    "file": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>"""
}
SERVICE_TYPE = "_b-messenger._tcp.local."
CERTFILE = os.path.join(HOME_DIR, ".cert.pem")
KEYFILE = os.path.join(HOME_DIR, ".key.pem")
CHUNK_SIZE = 4096 # Ukuran potongan file dalam byte

# --- Helper Functions & UI Components ---
def make_circular_pixmap(source_pixmap):
    size = source_pixmap.size()
    mask = QPixmap(size); mask.fill(Qt.GlobalColor.transparent)
    painter = QPainter(mask); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath(); path.addEllipse(0, 0, size.width(), size.height())
    painter.fillPath(path, Qt.GlobalColor.white); painter.end()
    result = QPixmap(size); result.fill(Qt.GlobalColor.transparent)
    painter.begin(result); painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setClipPath(path); painter.drawPixmap(0, 0, source_pixmap); painter.end()
    return result
def create_icon_from_svg(svg_string, color="currentColor", size=QSize(24, 24)):
    colored_svg = svg_string.replace('currentColor', color)
    renderer = QSvgRenderer(colored_svg.encode('utf-8'))
    pixmap = QPixmap(size); pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap); renderer.render(painter); painter.end()
    return QIcon(pixmap)

class ChatListItem(QWidget):
    def __init__(self, username):
        super().__init__()
        self.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(0)
        self.profile_pic_label = QLabel()
        icon_pixmap = create_icon_from_svg(ICONS['user'], color=APP_COLORS["icon_color"], size=QSize(42, 42)).pixmap(QSize(42, 42))
        self.profile_pic_label.setPixmap(make_circular_pixmap(icon_pixmap))
        layout.addWidget(self.profile_pic_label)
        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(12, 0, 0, 0)
        text_layout.setSpacing(0)
        self.username_label = QLabel(username)
        self.username_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.username_label.setStyleSheet(f"color: {APP_COLORS['text_primary']};")
        text_layout.addWidget(self.username_label)
        text_layout.addStretch()
        layout.addLayout(text_layout, 1)
        self.setMinimumHeight(68)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

# --- Network Logic ---
class ZeroconfListener:
    def __init__(self, network_manager): self.network_manager = network_manager
    def remove_service(self, zeroconf, type, name): self.network_manager.user_went_offline.emit(name)
    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        try:
            my_hostname = socket.gethostname()
            # FIX: add missing closing bracket for the list (syntax error)
            if info and info.server not in [f"{my_hostname}.local.", f"{my_hostname}."]:
                peer_data = {"name": name, "username": info.properties.get(b'username', b'unknown').decode('utf-8'), "address": socket.inet_ntoa(info.addresses[0]), "port": info.port}
                self.network_manager.user_discovered.emit(peer_data)
        except Exception as e: print(f"Error processing service {name}: {e}")
    def update_service(self, zeroconf, type, name): self.add_service(zeroconf, type, name)

class AdvancedNetworkManager(QObject):
    user_discovered = Signal(dict); user_went_offline = Signal(str); private_message_received = Signal(dict)
    def __init__(self):
        super().__init__()
        self.username = getpass.getuser(); self.my_ip = self._get_local_ip(); self.port = self._get_free_port()
        self.running = True; self.zeroconf = Zeroconf(); self.listener = ZeroconfListener(self); self.browser = None
        self.service_info = ServiceInfo(SERVICE_TYPE, f"{self.username}._S.{SERVICE_TYPE}", addresses=[socket.inet_aton(self.my_ip)], port=self.port, properties={'username': self.username})
    def _get_local_ip(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            try: s.connect(("8.8.8.8", 80)); return s.getsockname()[0]
            except OSError: return "127.0.0.1"
    def _get_free_port(self):
        with socket.socket() as s: s.bind(('', 0)); return s.getsockname()[1]
    def start_discovery(self):
        self.browser = ServiceBrowser(self.zeroconf, SERVICE_TYPE, self.listener)
        self.zeroconf.register_service(self.service_info)
        print(f"Announcing self: {self.username} at {self.my_ip}:{self.port}")
        threading.Thread(target=self.run_tls_server, daemon=True).start()
    def stop(self):
        self.running = False
        try:
            if self.browser: self.browser.cancel()
            self.zeroconf.unregister_service(self.service_info); self.zeroconf.close()
        except Exception as e: print(f"Error while stopping Zeroconf: {e}")
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s: s.connect((self.my_ip, self.port))
        except: pass
    def _recvall(self, sock, n):
        data = bytearray()
        while len(data) < n:
            packet = sock.recv(n - len(data))
            if not packet: return None
            data.extend(packet)
        return data
    def run_tls_server(self):
        if not os.path.exists(CERTFILE) or not os.path.exists(KEYFILE): return
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        try: context.load_cert_chain(certfile=CERTFILE, keyfile=KEYFILE)
        except Exception as e: print(f"Failed to load certificate: {e}"); return
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1.0)
            try: sock.bind((self.my_ip, self.port))
            except OSError as e: print(f"Failed to bind to port {self.port}: {e}"); return
            sock.listen(5)
            while self.running:
                try:
                    newsocket, fromaddr = sock.accept()
                    with context.wrap_socket(newsocket, server_side=True) as ssock:
                        raw_msglen = self._recvall(ssock, 4)
                        if not raw_msglen: continue
                        msglen = struct.unpack('>I', raw_msglen)[0]
                        full_data = self._recvall(ssock, msglen)
                        if not full_data: continue
                        self.private_message_received.emit(json.loads(full_data.decode('utf-8')))
                except socket.timeout: continue
                except Exception as e:
                    if self.running: print(f"TLS server error: {e}")
    def send_tcp_message(self, peer_info, message_dict):
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.check_hostname = False; context.verify_mode = ssl.CERT_NONE
        try:
            with socket.create_connection((peer_info['address'], peer_info['port']), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=peer_info['address']) as ssock:
                    message_bytes = json.dumps(message_dict).encode('utf-8')
                    ssock.sendall(struct.pack('>I', len(message_bytes)))
                    ssock.sendall(message_bytes)
        except Exception as e:
            print(f"Failed to send message to {peer_info['username']}: {e}")
            self.user_went_offline.emit(peer_info['name'])

# --- Main Application Window ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Tambahkan icon aplikasi bm.png
        icon_path = os.path.join(os.path.dirname(__file__), "bm.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            tray_icon = QIcon(icon_path)
        else:
            tray_icon = self.windowIcon()
        # Fitur tray icon
        self.tray = QSystemTrayIcon(tray_icon, self)
        self.tray.setToolTip("B Messenger")
        tray_menu = QTrayMenu()
        show_action = tray_menu.addAction("Show")
        quit_action = tray_menu.addAction("Quit")
        show_action.triggered.connect(self.showNormal)
        quit_action.triggered.connect(QApplication.instance().quit)
        self.tray.setContextMenu(tray_menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()
        self.chat_widgets = {}
        self.active_transfers = {} # Untuk melacak transfer file yang sedang berjalan
        self.setup_ui()
        self.setup_network()
        self.shake_timer = QTimer(self); self.shake_timer.timeout.connect(self._shake_step); self.shake_counter = 0
        self.ping_sound_path = os.path.join(os.path.dirname(__file__), "ping.wav")

    def setup_ui(self):
        self.setWindowTitle("B Messenger"); self.setFont(QFont("Segoe UI", 10))
        # Tampilkan list dan chat bersamaan (normal desktop layout)
        self.setMinimumSize(900, 600)
        self.setGeometry(100, 100, 900, 600)
        self.setStyleSheet(f"background-color: {APP_COLORS['sidebar_bg']};")
        main_widget = QWidget(); self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget); main_layout.setContentsMargins(0, 0, 0, 0); main_layout.setSpacing(0)
        # Panel kiri: daftar chat
        self.left_panel = QWidget(); self.left_panel.setMinimumWidth(260); self.left_panel.setMaximumWidth(400)
        self.left_panel.setStyleSheet(f"background-color: {APP_COLORS['sidebar_bg']}; border-right: 1px solid {APP_COLORS['input_border']};")
        left_layout = QVBoxLayout(self.left_panel); left_layout.setContentsMargins(0, 0, 0, 0)
        self.chat_list_widget = QListWidget()
        self.chat_list_widget.setStyleSheet(f"""QListWidget {{ border: none; }} QListWidget::item {{ border-bottom: 1px solid {APP_COLORS['input_border']}; }} QListWidget::item:selected, QListWidget::item:hover {{ background-color: {APP_COLORS['active_chat']}; }}""")
        self.chat_list_widget.itemClicked.connect(self.on_chat_selected)
        left_layout.addWidget(self.chat_list_widget)
        # Panel kanan: area chat
        self.right_panel = QWidget(); self.right_panel.setStyleSheet(f"background-color: {APP_COLORS['chat_bg']};")
        right_layout = QVBoxLayout(self.right_panel); right_layout.setContentsMargins(0, 0, 0, 0)
        self.chat_area = QStackedWidget()
        self.placeholder_widget = QLabel(f"""<div style='text-align:center;color:{APP_COLORS['timestamp']};'><h2 style='color:{APP_COLORS['text_primary']};'>B-Messenger</h2><p>Select a friend to start chatting.<br/>Waiting for users...</p></div>""")
        self.placeholder_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chat_area.addWidget(self.placeholder_widget)
        right_layout.addWidget(self.chat_area)
        # Tampilkan kedua panel bersamaan
        main_layout.addWidget(self.left_panel)
        main_layout.addWidget(self.right_panel)

    def _create_chat_page(self, username, service_name):
        page = QWidget()
        layout = QVBoxLayout(page); layout.setContentsMargins(0,0,0,0); layout.setSpacing(0)
        header_widget = QWidget(); header_widget.setFixedHeight(60)
        header_widget.setStyleSheet(f"background-color: {APP_COLORS['header_bg']}; border-bottom: 1px solid {APP_COLORS['input_border']}; padding: 0 10px;")
        header_layout = QHBoxLayout(header_widget); header_layout.setContentsMargins(0,0,0,0)
        header_label = QLabel(f"{username}"); header_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold)); header_label.setStyleSheet(f"color: {APP_COLORS['text_primary']};")
        ping_button = QPushButton(); ping_button.setIcon(create_icon_from_svg(ICONS['ping'], APP_COLORS['icon_color'])); ping_button.setIconSize(QSize(24, 24)); ping_button.setFixedSize(40, 40)
        ping_button.setCursor(Qt.CursorShape.PointingHandCursor); ping_button.setToolTip("Send a Ping!"); ping_button.setStyleSheet("QPushButton { background-color: transparent; border-radius: 20px; border: none; } QPushButton:hover { background-color: #E0E0E0; }")
        ping_button.clicked.connect(lambda: self.send_ping(service_name))
        header_layout.addWidget(header_label); header_layout.addStretch(); header_layout.addWidget(ping_button)
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(f"QScrollArea {{ border: none; background-color: {APP_COLORS['chat_bg']}; }}")
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_content_widget = QWidget()
        scroll_area.setWidget(scroll_content_widget)
        scroll_layout = QVBoxLayout(scroll_content_widget)
        scroll_layout.addStretch()
        input_toolbar = QWidget(); input_toolbar.setMinimumHeight(62)
        # Perbaiki tampilan panel bawah input_field agar lebih rapi dan modern
        input_toolbar.setStyleSheet(
            f"""
            QWidget {{
                background-color: {APP_COLORS['header_bg']};
                border-top: 1px solid {APP_COLORS['input_border']};
                padding: 0px 16px;
            }}
            """
        )
        it_layout = QHBoxLayout(input_toolbar); it_layout.setSpacing(15)
        it_layout.setContentsMargins(0, 0, 0, 0)
        # Hapus tombol attach
        emoji_button = QPushButton()
        emoji_button.setText("😊")
        emoji_button.setFixedSize(48, 48)
        emoji_button.setCursor(Qt.CursorShape.PointingHandCursor)
        emoji_button.setToolTip("Insert Emoji")
        # Gunakan font emoji-aware dan font-size besar agar emoji berwarna & tidak terpotong
        emoji_font = QFont()
        for fname in ["Segoe UI Emoji", "Noto Color Emoji", "Apple Color Emoji"]:
            emoji_font.setFamily(fname)
            if QFont(fname).exactMatch():
                break
        else:
            emoji_font.setFamily("Segoe UI")
        emoji_font.setPointSize(28)
        emoji_button.setFont(emoji_font)
        # StyleSheet tanpa color, tambahkan padding agar tidak terpotong
        emoji_button.setStyleSheet(
            "QPushButton {background-color: transparent; border-radius: 24px; border: none; font-size: 28px; padding: 2px;} "
            "QPushButton:hover {background-color: #E9EDEF;}"
        )
        input_field = QLineEdit(placeholderText="Type a message...")
        # Set font emoji-aware agar emoji tetap berwarna di QLineEdit
        emoji_font = QFont()
        for fname in ["Segoe UI Emoji", "Noto Color Emoji", "Apple Color Emoji"]:
            emoji_font.setFamily(fname)
            if QFont(fname).exactMatch():
                break
        else:
            emoji_font.setFamily("Segoe UI")
        emoji_font.setPointSize(11)
        input_field.setFont(emoji_font)
        # Jangan set warna font agar emoji tetap native color
        # Tambah padding atas dan bawah agar placeholder tidak terpotong
        input_field.setStyleSheet(
            f"""QLineEdit {{
            background-color: {APP_COLORS['incoming_bg']};
            border: none;
            border-radius: 24px;
            padding-left: 18px;
            padding-right: 18px;
            padding-top: 16px;
            padding-bottom: 16px;
            font-size: 16px;
            color: {APP_COLORS['text_primary']};
            box-shadow: 0 1px 2px rgba(0,0,0,0.04);
            }}"""
        )
        send_button = QPushButton(); send_button.setIcon(create_icon_from_svg(ICONS['send'], APP_COLORS['icon_color'])); send_button.setIconSize(QSize(28, 28)); send_button.setFixedSize(40, 40)
        send_button.setCursor(Qt.CursorShape.PointingHandCursor); send_button.setToolTip("Send Message"); send_button.setStyleSheet("QPushButton {background-color: transparent; border-radius: 20px; border: none;} QPushButton:hover {background-color: #E9EDEF;}")

        # Fungsi popup emoji dengan tab kategori
        def show_emoji_popup():
            from PySide6.QtWidgets import QDialog, QTabWidget, QWidget, QGridLayout, QPushButton, QVBoxLayout
            # Kategori emoji
            emoji_categories = {
                "Smileys": [
                    "😀", "😁", "😂", "🤣", "😃", "😄", "😅", "😆", "😉", "😊", "😋", "😎", "😍", "😘", "🥰", "😗", "😙", "😚", "🙂", "🤗",
                    "🤩", "🤔", "🤨", "😐", "😑", "😶", "🙄", "😏", "😣", "😥", "😮", "🤐", "😯", "😪", "😫", "🥱", "😴", "😌", "😛", "😜",
                    "😝", "🤤", "😒", "😓", "😔", "😕", "🙃", "🤑", "😲", "☹️", "🙁", "😖", "😞", "😟", "😤", "😢", "😭", "😦", "😧", "😨",
                    "😩", "🤯", "😬", "😰", "😱", "🥵", "🥶", "😳", "🤪", "😵", "😡", "😠", "🤬", "😷", "🤒", "🤕", "🤢", "🤮", "🥴", "😇",
                    "🥳", "🥺", "🤠", "🤡", "🤥", "🤫", "🤭", "🧐", "🤓"
                ],
                "Gestures": [
                    "👋", "🤚", "🖐️", "✋", "🖖", "👌", "🤌", "🤏", "✌️", "🤞", "🫰", "🤟", "🤘", "🤙", "🫵", "🫱", "🫲", "🫳", "🫴", "👈",
                    "👉", "👆", "🖕", "👇", "☝️", "👍", "👎", "✊", "👊", "🤛", "🤜", "👏", "🙌", "👐", "🤲", "🙏", "🫶", "💅", "🤳", "💪"
                ],
                "Animals": [
                    "🐵", "🐶", "🐱", "🐭", "🐹", "🐰", "🦊", "🐻", "🐼", "🐨", "🐯", "🦁", "🐮", "🐷", "🐸", "🐔", "🐧", "🐦", "🐤", "🐣",
                    "🐥", "🦆", "🦅", "🦉", "🦇", "🐺", "🐗", "🐴", "🦄", "🐝", "🐛", "🦋", "🐌", "🐞", "🐜", "🦟", "🦗", "🕷️", "🦂",
                    "🐢", "🐍", "🦎", "🦖", "🦕", "🐙", "🦑", "🦐", "🦞", "🦀"
                ],
                "Food": [
                    "🍏", "🍎", "🍐", "🍊", "🍋", "🍌", "🍉", "🍇", "🍓", "🫐", "🍈", "🍒", "🍑", "🥭", "🍍", "🥥", "🥝", "🍅", "🍆", "🥑",
                    "🥦", "🥬", "🥒", "🌶️", "🫑", "🌽", "🥕", "🫒", "🧄", "🧅", "🥔", "🍠", "🥐", "🥯", "🍞", "🥖", "🥨", "🧀", "🥚", "🍳"
                ],
                "Activity": [
                    "⚽", "🏀", "🏈", "⚾", "🎾", "🏐", "🏉", "🥏", "🎱", "🏓", "🏸", "🥅", "🏒", "🏑", "🏏", "🥍", "🏹", "🎣", "🤿", "🥊",
                    "🥋", "🎽", "🛹", "🛷", "⛸️", "🥌", "🎿", "⛷️", "🏂", "🪂", "🏋️", "🤼", "🤸", "⛹️", "🤺", "🤾", "🏌️", "🏇", "🧘"
                ],
                "Travel": [
                    "🚗", "🚕", "🚙", "🚌", "🚎", "🏎️", "🚓", "🚑", "🚒", "🚐", "🚚", "🚛", "🚜", "🦽", "🦼", "🛺", "🚲", "🛴", "🛹", "🛼",
                    "🛶", "⛵", "🚤", "🛳️", "⛴️", "🛥️", "🚢", "✈️", "🛩️", "🛫", "🛬", "🪂", "🚁", "🚟", "🚠", "🚡", "🛰️", "🚀", "🛸"
                ],
                "Objects": [
                    "⌛", "⏳", "⌚", "⏰", "⏱️", "⏲️", "🕰️", "🕛", "🕧", "🕐", "🕜", "🕑", "🕝", "🕒", "🕞", "🕓", "🕟", "🕔", "🕠",
                    "🕕", "🕡", "🕖", "🕢", "🕗", "🕣", "🕘", "🕤", "🕙", "🕥", "🕚", "🕦", "💡", "🔦", "🕯️", "🛢️", "💸", "💵", "💴", "💶"
                ],
                "Symbols": [
                    "❤️", "🧡", "💛", "💚", "💙", "💜", "🤎", "🖤", "🤍", "💯", "💢", "💥", "💫", "💦", "💨", "🕳️", "💣", "💬", "💭", "🗯️",
                    "♠️", "♥️", "♦️", "♣️", "🃏", "🀄", "🎴", "🔔", "🔕", "🔒", "🔓", "🔏", "🔐", "🔑", "🗝️", "🔨", "⛏️", "⚒️", "🛠️"
                ],
                "Flags": [
"🇮🇩", "🇺🇸", "🇬🇧", "🇯🇵", "🇰🇷", "🇨🇳", "🇸🇬", "🇲🇾", "🇹🇭", "🇻🇳", "🇫🇷", "🇩🇪", "🇮🇹", "🇪🇸", "🇷🇺", "🇧🇷", "🇦🇺", "🇨🇦", "🇸🇦", "🇹🇷", "🇮🇳", "🇵🇰", "🇧🇩", "🇳🇬", "🇪🇬", "🇿🇦", "🇲🇽", "🇦🇷", "🇨🇱", "🇵🇪", "🇨🇴", "🇳🇱", "🇧🇪", "🇨🇭", "🇸🇪", "🇳🇴", "🇩🇰", "🇫🇮", "🇵🇱", "🇺🇦", "🇦🇹", "🇬🇷", "🇵🇹", "🇮🇪", "🇳🇿", "🇵🇭", "🇮🇷", "🇮🇶", "🇦🇪", "🇶🇦", "🇰🇼", "🇴🇲", "🇧🇭", "🇯🇴", "🇱🇧", "🇸🇾", "🇪🇹", "🇰🇪", "🇹🇿", "🇲🇦", "🇩🇿", "🇹🇳", "🇳🇵", "🇱🇰", "🇲🇲", "🇰🇭", "🇱🇦"]
            }
            dialog = QDialog(self)
            dialog.setWindowFlags(Qt.Popup)
            dialog.setMinimumWidth(37 * 10 + 32)
            layout = QVBoxLayout(dialog)
            tabs = QTabWidget(dialog)
            for cat, emojis in emoji_categories.items():
                tab = QWidget()
                grid = QGridLayout(tab)
                grid.setSpacing(2)
                grid.setContentsMargins(4, 4, 4, 4)
                cols = 10
                for idx, emoji in enumerate(emojis):
                    btn = QPushButton(emoji)
                    btn.setFixedSize(32, 32)
                    emoji_font = QFont()
                    for fname in ["Segoe UI Emoji", "Noto Color Emoji", "Apple Color Emoji"]:
                        emoji_font.setFamily(fname)
                        if QFont(fname).exactMatch():
                            break
                    else:
                        emoji_font.setFamily("Segoe UI")
                    emoji_font.setPointSize(18)
                    btn.setFont(emoji_font)
                    btn.setStyleSheet("font-size:20px; border:none; background:transparent;")
                    btn.clicked.connect(lambda checked=False, e=emoji: (input_field.insert(e), dialog.accept()))
                    grid.addWidget(btn, idx // cols, idx % cols)
                tab.setLayout(grid)
                tabs.addTab(tab, cat)
            layout.addWidget(tabs)
            dialog.setLayout(layout)
            # --- Ubah posisi popup ke atas input_field ---
            input_rect = input_field.rect()
            input_global = input_field.mapToGlobal(input_rect.bottomLeft())
            dialog_height = dialog.sizeHint().height()
            # Geser ke atas setinggi dialog
            dialog.move(input_global.x(), input_global.y() - dialog_height)
            dialog.exec()
        emoji_button.clicked.connect(show_emoji_popup)

        it_layout.addWidget(emoji_button)
        it_layout.addWidget(input_field, 1)
        it_layout.addWidget(send_button)
        layout.addWidget(header_widget); layout.addWidget(scroll_area, 1); layout.addWidget(input_toolbar)
        return page, {"scroll_area": scroll_area, "scroll_layout": scroll_layout, "input_field": input_field, "send_button": send_button}

    def add_message_to_history(self, scroll_area, scroll_layout, msg_dict, is_sent):
        stretch_item = scroll_layout.takeAt(scroll_layout.count() - 1)
        msg_type = msg_dict.get("type", "text")
        is_event = msg_type == "ping"
        content_widget = None
        if msg_type == "text":
            text = msg_dict['content']
            import re
            # Deteksi dan ubah url menjadi tautan HTML (mendukung domain multi-level, angka, dan karakter khusus)
            def linkify(match):
                url = match.group(0)
                if not url.startswith("http"):
                    url = "https://" + url
                # Hindari spasi di dalam link
                return f"<a href='{url}' style='color:#2196F3;text-decoration:underline;'>{html.escape(match.group(0))}</a>"
            # Regex: domain multi-level, subdomain, angka, path, query, port
            url_pattern = re.compile(
                r'(?<![\w@])'  # Hindari email dan kata
                r'(?:https?://)?(?:www\.)?'
                r'[a-zA-Z0-9\-]+(?:\.[a-zA-Z0-9\-]+)+'
                r'(?:\:\d+)?(?:/[^\s<]*)?(?:\?[^\s<]*)?'
                r'(?![\w])'  # Hindari gabung dengan kata lain
            )
            # Proses link dulu, lalu emoji
            linked_text = url_pattern.sub(linkify, text)
            emoji_pattern = re.compile(
                "["
                "\U0001F600-\U0001F64F"
                "\U0001F300-\U0001F5FF"
                "\U0001F680-\U0001F6FF"
                "\U0001F1E0-\U0001F1FF"
                "\U00002700-\U000027BF"
                "\U0001F900-\U0001F9FF"
                "\U00002600-\U000026FF"
                "\U00002B50"
                "\U00002B06"
                "]+", flags=re.UNICODE)
            # Jangan ubah emoji di dalam tag <a>
            def repl(m):
                # Cek apakah emoji berada di dalam tag <a>
                before = linked_text[max(0, m.start()-10):m.start()]
                after = linked_text[m.end():m.end()+10]
                if '<a' in before and '</a>' in after:
                    return m.group(0)
                return f"<span style='font-size:2em; vertical-align:middle;'>{m.group(0)}</span>"
            html_text = emoji_pattern.sub(repl, linked_text)
            display_text = f"<div style='color:{APP_COLORS['text_primary']};'>{html_text}</div>"
            content_widget = QLabel(display_text)
            content_widget.setWordWrap(True)
            emoji_font = QFont()
            for fname in ["Segoe UI Emoji", "Noto Color Emoji", "Apple Color Emoji"]:
                emoji_font.setFamily(fname)
                if QFont(fname).exactMatch():
                    break
            else:
                emoji_font.setFamily("Segoe UI")
            emoji_font.setPointSize(11)
            content_widget.setFont(emoji_font)
            content_widget.setTextFormat(Qt.TextFormat.RichText)
            content_widget.setOpenExternalLinks(True)
        elif is_event:
            from_user = msg_dict.get("from_user")
            text = "PING!!! sent" if is_sent else f"PING!!! from {from_user}"
            escaped_text = html.escape(text)
            # Tampilkan ping seperti bubble chat biasa, bukan di tengah
            content_widget = QLabel(f"<span style='color:{APP_COLORS['ping_color']}; font-weight:bold;'>PING!!!</span>")
            content_widget.setWordWrap(True)
            content_widget.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        if not content_widget:
             scroll_layout.addStretch(); return
        bubble_widget = QWidget()
        bubble_layout = QVBoxLayout(bubble_widget); bubble_layout.setContentsMargins(12, 8, 12, 8); bubble_layout.addWidget(content_widget)
        if not is_event:
            ts_label = QLabel(datetime.fromtimestamp(msg_dict['timestamp']).strftime('%H:%M')); ts_label.setFont(QFont("Segoe UI", 9)); ts_label.setStyleSheet(f"color: {APP_COLORS['timestamp']}; background: transparent;")
            bubble_layout.addWidget(ts_label, 0, Qt.AlignmentFlag.AlignRight)
        bg_color = APP_COLORS["outgoing_bg"] if is_sent else APP_COLORS["incoming_bg"]
        bubble_widget.setStyleSheet(f"background-color: {'transparent' if is_event else bg_color}; border-radius: 12px;")
        container_widget = QWidget()
        container_layout = QHBoxLayout(container_widget); container_layout.setContentsMargins(10, 5, 10, 5)
        bubble_widget.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        # Ubah: ping mengikuti bubble biasa, bukan di tengah
        if is_event:
            if is_sent:
                container_layout.addStretch(); container_layout.addWidget(bubble_widget)
            else:
                container_layout.addWidget(bubble_widget); container_layout.addStretch()
        elif is_sent:
            container_layout.addStretch(); container_layout.addWidget(bubble_widget)
        else:
            container_layout.addWidget(bubble_widget); container_layout.addStretch()
        scroll_layout.addWidget(container_widget); scroll_layout.addStretch()
        QTimer.singleShot(50, lambda: scroll_area.verticalScrollBar().setValue(scroll_area.verticalScrollBar().maximum()))

    def setup_network(self):
        self.network_thread = QThread(); self.network_manager = AdvancedNetworkManager()
        self.network_manager.moveToThread(self.network_thread)
        self.network_manager.user_discovered.connect(self.add_user)
        self.network_manager.user_went_offline.connect(self.remove_user)
        self.network_manager.private_message_received.connect(self.handle_incoming_message)
        self.network_thread.started.connect(self.network_manager.start_discovery); self.network_thread.start()

    def add_user(self, peer_data):
        service_name = peer_data['name']
        if service_name in self.chat_widgets: return
        username = peer_data['username']
        page, widgets = self._create_chat_page(username, service_name)
        self.chat_area.addWidget(page)
        item = QListWidgetItem(); item_widget = ChatListItem(username); item.setSizeHint(item_widget.sizeHint()); item.setData(Qt.UserRole, peer_data)
        self.chat_list_widget.addItem(item); self.chat_list_widget.setItemWidget(item, item_widget)
        widgets["send_button"].clicked.connect(lambda _, s=service_name: self.send_private_message(s))
        widgets["input_field"].returnPressed.connect(lambda s=service_name: self.send_private_message(s))
        self.chat_widgets[service_name] = {"page": page, "item": item, "widgets": widgets, "peer_data": peer_data}
        if self.chat_list_widget.count() == 1: self.chat_list_widget.setCurrentItem(item); self.on_chat_selected(item)

    def on_chat_selected(self, item):
        peer_data = item.data(Qt.UserRole)
        if peer_data and peer_data['name'] in self.chat_widgets:
            self.chat_area.setCurrentWidget(self.chat_widgets[peer_data['name']]["page"])
            # Jangan sembunyikan sidebar, biarkan tampil bersamaan

    def show_chat_list(self):
        # Tidak perlu sembunyikan/tampilkan panel, biarkan layout tetap
        self.chat_area.setCurrentWidget(self.placeholder_widget)

    def remove_user(self, service_name):
        if service_name in self.chat_widgets:
            if self.chat_area.currentWidget() == self.chat_widgets[service_name]['page']: self.chat_area.setCurrentWidget(self.placeholder_widget)
            data = self.chat_widgets.pop(service_name); self.chat_list_widget.takeItem(self.chat_list_widget.row(data['item'])); data['page'].deleteLater()

    def send_private_message(self, target_service_name):
        data = self.chat_widgets.get(target_service_name)
        if not data: return
        widgets = data['widgets']
        input_field = widgets['input_field']
        message = input_field.text().strip()
        if not message: return
        if message.lower() == 'p':
            self.send_ping(target_service_name)
            input_field.clear()
            return
        timestamp = time.time()
        msg_dict = {"type": "text", "content": message, "timestamp": timestamp, "from_user": self.network_manager.username}
        self.network_manager.send_tcp_message(data['peer_data'], msg_dict)
        self.add_message_to_history(widgets['scroll_area'], widgets['scroll_layout'], msg_dict, True)
        input_field.clear()

    def handle_incoming_message(self, msg):
        msg_type = msg.get("type")
        from_user = msg.get("from_user")
        target_widget_info = None
        for service_name, data in self.chat_widgets.items():
            if data['peer_data']['username'] == from_user:
                target_widget_info = data
                break
        if not target_widget_info and msg_type not in ['ping']:
            return

        if msg_type == "ping":
            self.handle_incoming_ping(msg)
        elif target_widget_info:
            self.add_message_to_history(target_widget_info['widgets']['scroll_area'], target_widget_info['widgets']['scroll_layout'], msg, False)

    def send_ping(self, target_service_name):
        # Kirim pesan ping ke lawan bicara
        data = self.chat_widgets.get(target_service_name)
        if not data: return
        timestamp = time.time()
        msg_dict = {"type": "ping", "timestamp": timestamp, "from_user": self.network_manager.username}
        self.network_manager.send_tcp_message(data['peer_data'], msg_dict)
        self.add_message_to_history(data['widgets']['scroll_area'], data['widgets']['scroll_layout'], msg_dict, True)
        self.play_ping_sound()

    def handle_incoming_ping(self, msg):
        from_user = msg.get("from_user")
        print(f"PING!!! received from {from_user}")
        self.shake_window()
        self.play_ping_sound()
        for service_name, data in self.chat_widgets.items():
            if data['peer_data']['username'] == from_user:
                widgets = data['widgets']
                self.add_message_to_history(widgets['scroll_area'], widgets['scroll_layout'], msg, False)
                break

    def play_ping_sound(self):
        # Mainkan suara ping.wav jika ada
        if os.path.exists(self.ping_sound_path):
            self.ping_sound = QSoundEffect()
            self.ping_sound.setSource(QUrl.fromLocalFile(self.ping_sound_path))
            self.ping_sound.setVolume(1.0)
            self.ping_sound.play()
        else:
            # fallback: tidak ada file, tidak mainkan suara
            pass

    def shake_window(self):
        if self.shake_timer.isActive(): return
        self.original_pos = self.pos(); self.shake_counter = 0; self.shake_timer.start(20)
    def _shake_step(self):
        if self.shake_counter > 15: self.shake_timer.stop(); self.move(self.original_pos); return
        offset_x = (random.randint(0, 1) * 2 - 1) * 5; offset_y = (random.randint(0, 1) * 2 - 1) * 5
        self.move(self.original_pos.x() + offset_x, self.original_pos.y() + offset_y); self.shake_counter += 1

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.showNormal()
            self.raise_()
            self.activateWindow()
            # Tambahkan fokus dan pastikan window di depan
            self.setWindowState(self.windowState() & ~Qt.WindowMinimized | Qt.WindowActive)
            self.show()
            QApplication.processEvents()

    def closeEvent(self, event):
        # Sembunyikan window, tetap jalan di tray
        event.ignore()
        self.hide()
        self.tray.showMessage("B Messenger", "The application is still running in the tray.", QSystemTrayIcon.Information, 2000)
        for transfer_id, transfer_data in list(self.active_transfers.items()):
            try:
                transfer_data['file_handle'].close()
                print(f"Closed dangling file handle for transfer {transfer_id}")
            except Exception as e:
                print(f"Error closing file on exit: {e}")
        self.network_manager.stop(); self.network_thread.quit(); self.network_thread.wait(2000)

def ensure_certificates():
    # Jangan overwrite jika sudah ada
    if os.path.exists(CERTFILE) and os.path.exists(KEYFILE):
        return True
    try:
        print("Generating TLS certificate and key in home directory...")
        subprocess.run([
            "openssl", "req", "-new", "-x509", "-days", "3650", "-nodes",
            "-out", CERTFILE, "-keyout", KEYFILE,
            "-subj", "/CN=b-messenger-p2p"
        ], check=True)
        print(f"Certificate and key generated: {CERTFILE}, {KEYFILE}")
    except Exception as e:
        print(f"Failed to generate certificates: {e}")
        return False
    return True

if __name__ == "__main__":
    if not ensure_certificates():
        app_temp = QApplication(sys.argv)
        error_box = QMessageBox(); error_box.setIcon(QMessageBox.Icon.Critical); error_box.setText(f"Could not create certificate files: '{CERTFILE}' & '{KEYFILE}'"); error_box.setInformativeText("Check OpenSSL installation and permissions."); error_box.setWindowTitle("Configuration Error"); error_box.exec()
        sys.exit(1)
    app = QApplication(sys.argv)
    # Set theme KDE jika tersedia di sistem
    if QStyleFactory:
        if "breeze" in QStyleFactory.keys():
            app.setStyle(QStyleFactory.create("breeze"))
        elif "oxygen" in QStyleFactory.keys():
            app.setStyle(QStyleFactory.create("oxygen"))
        # Jika tidak ada, biarkan default
    main_win = MainWindow(); main_win.show(); sys.exit(app.exec())
