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

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QListWidget, QListWidgetItem, QTextBrowser, QLineEdit, QPushButton, QStackedWidget,
    QLabel, QFileDialog, QProgressBar, QMenu, QMessageBox, QSizePolicy, QSpacerItem,
    QScrollArea
)
from PyQt6.QtCore import QThread, pyqtSignal, QObject, Qt, QUrl, QTimer, QSize
from PyQt6.QtGui import (
    QIcon, QFont, QDesktopServices, QAction, QPalette, QPixmap, QPainter, QColor,
    QPainterPath
)
from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtSvg import QSvgRenderer

# --- Application Configuration ---
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
CERTFILE = "cert.pem"
KEYFILE = "key.pem"
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

class FileBubbleWidget(QWidget):
    def __init__(self, filename, filesize, status=""):
        super().__init__()
        self.filename = filename
        self.filesize = filesize
        self.setStyleSheet("background: transparent;")
        layout = QHBoxLayout(self); layout.setSpacing(10); layout.setContentsMargins(0,0,0,0)
        file_icon_label = QLabel()
        file_icon = create_icon_from_svg(ICONS['file'], APP_COLORS['icon_color'], QSize(36, 36))
        file_icon_label.setPixmap(file_icon.pixmap(QSize(36, 36)))
        layout.addWidget(file_icon_label)
        text_layout = QVBoxLayout(); text_layout.setSpacing(2)
        filename_label = QLabel(self.filename); filename_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold)); filename_label.setStyleSheet(f"color: {APP_COLORS['text_primary']};")
        if self.filesize < 1024 * 1024: filesize_str = f"{self.filesize / 1024:.1f} KB"
        else: filesize_str = f"{self.filesize / (1024 * 1024):.1f} MB"
        self.filesize_label = QLabel(filesize_str); self.filesize_label.setFont(QFont("Segoe UI", 9)); self.filesize_label.setStyleSheet(f"color: {APP_COLORS['timestamp']};")
        text_layout.addWidget(filename_label); text_layout.addWidget(self.filesize_label)
        self.status_label = QLabel(status)
        status_font = QFont("Segoe UI", 9)
        status_font.setItalic(True) # Cara yang benar untuk membuat font miring
        self.status_label.setFont(status_font)
        text_layout.addWidget(self.status_label)
        layout.addLayout(text_layout, 1)

    def set_status(self, text):
        self.status_label.setText(text)

# --- Network Logic ---
class ZeroconfListener:
    def __init__(self, network_manager): self.network_manager = network_manager
    def remove_service(self, zeroconf, type, name): self.network_manager.user_went_offline.emit(name)
    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        try:
            my_hostname = socket.gethostname()
            if info and info.server not in [f"{my_hostname}.local.", f"{my_hostname}."]:
                peer_data = {"name": name, "username": info.properties.get(b'username', b'unknown').decode('utf-8'), "address": socket.inet_ntoa(info.addresses[0]), "port": info.port}
                self.network_manager.user_discovered.emit(peer_data)
        except Exception as e: print(f"Error processing service {name}: {e}")
    def update_service(self, zeroconf, type, name): self.add_service(zeroconf, type, name)

class AdvancedNetworkManager(QObject):
    user_discovered = pyqtSignal(dict); user_went_offline = pyqtSignal(str); private_message_received = pyqtSignal(dict)
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
        self.chat_widgets = {}
        self.active_transfers = {} # Untuk melacak transfer file yang sedang berjalan
        self.setup_ui()
        self.setup_network()
        self.shake_timer = QTimer(self); self.shake_timer.timeout.connect(self._shake_step); self.shake_counter = 0

    def setup_ui(self):
        self.setWindowTitle("B-Messenger (NSD Version)"); self.setFont(QFont("Segoe UI", 10))
        self.setMinimumSize(900, 600); self.setGeometry(100, 100, 1200, 800)
        self.setStyleSheet(f"background-color: {APP_COLORS['sidebar_bg']};")
        main_widget = QWidget(); self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget); main_layout.setContentsMargins(0, 0, 0, 0); main_layout.setSpacing(0)
        left_panel = QWidget(); left_panel.setMinimumWidth(380); left_panel.setMaximumWidth(420)
        left_panel.setStyleSheet(f"background-color: {APP_COLORS['sidebar_bg']}; border-right: 1px solid {APP_COLORS['input_border']};")
        left_layout = QVBoxLayout(left_panel); left_layout.setContentsMargins(0, 0, 0, 0)
        self.chat_list_widget = QListWidget()
        self.chat_list_widget.setStyleSheet(f"""QListWidget {{ border: none; }} QListWidget::item {{ border-bottom: 1px solid {APP_COLORS['input_border']}; }} QListWidget::item:selected, QListWidget::item:hover {{ background-color: {APP_COLORS['active_chat']}; }}""")
        self.chat_list_widget.itemClicked.connect(self.on_chat_selected)
        left_layout.addWidget(self.chat_list_widget)
        right_panel = QWidget(); right_panel.setStyleSheet(f"background-color: {APP_COLORS['chat_bg']};")
        right_layout = QVBoxLayout(right_panel); right_layout.setContentsMargins(0, 0, 0, 0)
        self.chat_area = QStackedWidget()
        self.placeholder_widget = QLabel(f"""<div style='text-align:center;color:{APP_COLORS['timestamp']};'><h2 style='color:{APP_COLORS['text_primary']};'>B-Messenger</h2><p>Select a friend to start chatting.<br/>Waiting for users...</p></div>""")
        self.placeholder_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chat_area.addWidget(self.placeholder_widget)
        right_layout.addWidget(self.chat_area)
        main_layout.addWidget(left_panel); main_layout.addWidget(right_panel)

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
        input_toolbar.setStyleSheet(f"background-color: {APP_COLORS['header_bg']}; border-top: 1px solid {APP_COLORS['input_border']}; padding: 8px 16px;")
        it_layout = QHBoxLayout(input_toolbar); it_layout.setSpacing(15)
        attach_button = QPushButton(); attach_button.setIcon(create_icon_from_svg(ICONS['attach'], APP_COLORS['icon_color'])); attach_button.setIconSize(QSize(28, 28)); attach_button.setFixedSize(40, 40)
        attach_button.setCursor(Qt.CursorShape.PointingHandCursor); attach_button.setToolTip("Send File"); attach_button.setStyleSheet("QPushButton {background-color: transparent; border-radius: 20px; border: none;} QPushButton:hover {background-color: #E9EDEF;}")
        attach_button.clicked.connect(lambda: self.prompt_send_file(service_name))
        input_field = QLineEdit(placeholderText="Type a message..."); input_field.setFont(QFont("Segoe UI", 11))
        input_field.setStyleSheet(f"""QLineEdit {{ background-color: #FFFFFF; border: 1px solid {APP_COLORS['input_border']}; border-radius: 18px; padding: 8px 15px; color: {APP_COLORS['text_primary']};}}""")
        send_button = QPushButton(); send_button.setIcon(create_icon_from_svg(ICONS['send'], APP_COLORS['icon_color'])); send_button.setIconSize(QSize(28, 28)); send_button.setFixedSize(40, 40)
        send_button.setCursor(Qt.CursorShape.PointingHandCursor); send_button.setToolTip("Send Message"); send_button.setStyleSheet("QPushButton {background-color: transparent; border-radius: 20px; border: none;} QPushButton:hover {background-color: #E9EDEF;}")
        it_layout.addWidget(attach_button); it_layout.addWidget(input_field, 1); it_layout.addWidget(send_button)
        layout.addWidget(header_widget); layout.addWidget(scroll_area, 1); layout.addWidget(input_toolbar)
        return page, {"scroll_area": scroll_area, "scroll_layout": scroll_layout, "input_field": input_field, "send_button": send_button}

    def add_message_to_history(self, scroll_area, scroll_layout, msg_dict, is_sent):
        stretch_item = scroll_layout.takeAt(scroll_layout.count() - 1)
        msg_type = msg_dict.get("type", "text")
        is_event = msg_type == "ping"
        content_widget = None
        if msg_type == "text":
            escaped_text = html.escape(msg_dict['content'])
            display_text = f"<div style='color:{APP_COLORS['text_primary']};'>{escaped_text}</div>"
            content_widget = QLabel(display_text)
            content_widget.setWordWrap(True)
            content_widget.setFont(QFont("Segoe UI", 11))
        elif is_event:
            from_user = msg_dict.get("from_user")
            text = "PING!!! sent" if is_sent else f"PING!!! from {from_user}"
            escaped_text = html.escape(text)
            content_widget = QLabel(f"<div style='text-align:center; color:{APP_COLORS['ping_color']}; font-weight:bold;'>{escaped_text}</div>")
        elif msg_type == "file_header":
             status = "Mengirim..." if is_sent else "Menerima..."
             content_widget = FileBubbleWidget(msg_dict['filename'], msg_dict['filesize'], status)
             if not is_sent and 'transfer_id' in msg_dict:
                 # Pastikan transfer ada sebelum mencoba mengaksesnya
                 if msg_dict['transfer_id'] in self.active_transfers:
                    self.active_transfers[msg_dict['transfer_id']]['bubble'] = content_widget
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
        if is_event: container_layout.addWidget(bubble_widget, 0, Qt.AlignmentFlag.AlignCenter)
        elif is_sent: container_layout.addStretch(); container_layout.addWidget(bubble_widget)
        else: container_layout.addWidget(bubble_widget); container_layout.addStretch()
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
        item = QListWidgetItem(); item_widget = ChatListItem(username); item.setSizeHint(item_widget.sizeHint()); item.setData(Qt.ItemDataRole.UserRole, peer_data)
        self.chat_list_widget.addItem(item); self.chat_list_widget.setItemWidget(item, item_widget)
        widgets["send_button"].clicked.connect(lambda _, s=service_name: self.send_private_message(s))
        widgets["input_field"].returnPressed.connect(lambda s=service_name: self.send_private_message(s))
        self.chat_widgets[service_name] = {"page": page, "item": item, "widgets": widgets, "peer_data": peer_data}
        if self.chat_list_widget.count() == 1: self.chat_list_widget.setCurrentItem(item); self.on_chat_selected(item)

    def on_chat_selected(self, item):
        peer_data = item.data(Qt.ItemDataRole.UserRole)
        if peer_data and peer_data['name'] in self.chat_widgets: self.chat_area.setCurrentWidget(self.chat_widgets[peer_data['name']]["page"])

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

    def _send_file_in_thread(self, file_path, transfer_id, peer_data):
        try:
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    b64_chunk = base64.b64encode(chunk).decode('ascii')
                    chunk_msg = { "type": "file_chunk", "transfer_id": transfer_id, "data": b64_chunk }
                    self.network_manager.send_tcp_message(peer_data, chunk_msg)
            end_msg = { "type": "file_end", "transfer_id": transfer_id, "from_user": self.network_manager.username }
            self.network_manager.send_tcp_message(peer_data, end_msg)
            print(f"File transfer {transfer_id} completed.")
        except Exception as e:
            print(f"Error during file sending thread: {e}")

    def prompt_send_file(self, target_service_name):
        data = self.chat_widgets.get(target_service_name)
        if not data: return
        dialog = QFileDialog(self, "Pilih File untuk Dikirim")
        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        if not dialog.exec(): return
        file_path = dialog.selectedFiles()[0]
        if not file_path: return
        try:
            filename = os.path.basename(file_path)
            filesize = os.path.getsize(file_path)
            transfer_id = str(uuid.uuid4())
            header_msg = {
                "type": "file_header", "filename": filename, "filesize": filesize,
                "transfer_id": transfer_id, "timestamp": time.time(),
                "from_user": self.network_manager.username
            }
            self.network_manager.send_tcp_message(data['peer_data'], header_msg)
            widgets = data['widgets']
            self.add_message_to_history(widgets['scroll_area'], widgets['scroll_layout'], header_msg, True)
            thread = threading.Thread(target=self._send_file_in_thread, args=(file_path, transfer_id, data['peer_data']))
            thread.daemon = True
            thread.start()
        except Exception as e:
            print(f"Error preparing file send: {e}")
            QMessageBox.critical(self, "File Error", f"Tidak dapat membaca atau mengirim file:\n{e}")

    def send_ping(self, target_service_name):
        data = self.chat_widgets.get(target_service_name)
        if not data: return
        widgets = data['widgets']
        print(f"Sending PING! to {data['peer_data']['username']}")
        msg_dict = {"type": "ping", "timestamp": time.time(), "from_user": self.network_manager.username}
        self.network_manager.send_tcp_message(data['peer_data'], msg_dict)
        self.add_message_to_history(widgets['scroll_area'], widgets['scroll_layout'], msg_dict, True)

    def handle_incoming_message(self, msg):
        msg_type = msg.get("type")
        from_user = msg.get("from_user")
        target_widget_info = None
        for service_name, data in self.chat_widgets.items():
            if data['peer_data']['username'] == from_user:
                target_widget_info = data
                break
        if not target_widget_info and msg_type not in ['file_header', 'ping']:
            return

        if msg_type == 'file_header':
            try:
                transfer_id = msg['transfer_id']
                downloads_path = str(Path.home() / "Downloads")
                if not os.path.exists(downloads_path): os.makedirs(downloads_path)
                base, extension = os.path.splitext(msg['filename'])
                save_path = os.path.join(downloads_path, msg['filename'])
                counter = 1
                while os.path.exists(save_path):
                    save_path = os.path.join(downloads_path, f"{base}_{counter}{extension}")
                    counter += 1
                file_handle = open(save_path, 'wb')
                self.active_transfers[transfer_id] = {
                    'file_handle': file_handle, 'path': save_path, 'bubble': None
                }
                print(f"Receiving file {msg['filename']} ({transfer_id}), saving to {save_path}")
                if target_widget_info:
                    self.add_message_to_history(target_widget_info['widgets']['scroll_area'], target_widget_info['widgets']['scroll_layout'], msg, False)
            except Exception as e:
                print(f"Error handling file header: {e}")
        elif msg_type == 'file_chunk':
            transfer_id = msg.get('transfer_id')
            transfer = self.active_transfers.get(transfer_id)
            if transfer:
                try:
                    chunk_data = base64.b64decode(msg['data'])
                    transfer['file_handle'].write(chunk_data)
                except Exception as e:
                    print(f"Error writing chunk for {transfer_id}: {e}")
        elif msg_type == 'file_end':
            transfer_id = msg.get('transfer_id')
            transfer = self.active_transfers.pop(transfer_id, None)
            if transfer:
                try:
                    transfer['file_handle'].close()
                    if transfer['bubble']:
                        transfer['bubble'].set_status(f"Disimpan di Downloads")
                    print(f"File transfer {transfer_id} finished. Saved to {transfer['path']}")
                except Exception as e:
                    print(f"Error finishing transfer for {transfer_id}: {e}")
        elif msg_type == "ping":
            self.handle_incoming_ping(msg)
        elif target_widget_info:
            self.add_message_to_history(target_widget_info['widgets']['scroll_area'], target_widget_info['widgets']['scroll_layout'], msg, False)

    def handle_incoming_ping(self, msg):
        from_user = msg.get("from_user"); print(f"PING!!! received from {from_user}")
        self.shake_window()
        if os.path.exists("ping.wav"):
            self.ping_sound = QSoundEffect(); self.ping_sound.setSource(QUrl.fromLocalFile("ping.wav")); self.ping_sound.play()
        for service_name, data in self.chat_widgets.items():
            if data['peer_data']['username'] == from_user:
                widgets = data['widgets']
                self.add_message_to_history(widgets['scroll_area'], widgets['scroll_layout'], msg, False)
                break
    
    def shake_window(self):
        if self.shake_timer.isActive(): return
        self.original_pos = self.pos(); self.shake_counter = 0; self.shake_timer.start(20)
    def _shake_step(self):
        if self.shake_counter > 15: self.shake_timer.stop(); self.move(self.original_pos); return
        offset_x = (random.randint(0, 1) * 2 - 1) * 5; offset_y = (random.randint(0, 1) * 2 - 1) * 5
        self.move(self.original_pos.x() + offset_x, self.original_pos.y() + offset_y); self.shake_counter += 1

    def closeEvent(self, event):
        for transfer_id, transfer_data in list(self.active_transfers.items()):
            try:
                transfer_data['file_handle'].close()
                print(f"Closed dangling file handle for transfer {transfer_id}")
            except Exception as e:
                print(f"Error closing file on exit: {e}")
        self.network_manager.stop(); self.network_thread.quit(); self.network_thread.wait(2000); event.accept()

if __name__ == "__main__":
    if not os.path.exists(CERTFILE) or not os.path.exists(KEYFILE):
        print("="*60 + f"\n!!! ERROR: File '{CERTFILE}' or '{KEYFILE}' not found.\n" + 'openssl req -new -x509 -days 3650 -nodes -out cert.pem -keyout key.pem -subj "/CN=b-messenger-p2p"' + "\n" + "="*60)
        app_temp = QApplication(sys.argv)
        error_box = QMessageBox(); error_box.setIcon(QMessageBox.Icon.Critical); error_box.setText(f"Certificate files not found: '{CERTFILE}' & '{KEYFILE}'"); error_box.setInformativeText("Run the openssl command in the console before running the application."); error_box.setWindowTitle("Configuration Error"); error_box.exec()
        sys.exit(1)
    app = QApplication(sys.argv); main_win = MainWindow(); main_win.show(); sys.exit(app.exec())