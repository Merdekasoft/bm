#!/usr/bin/env python3
# Description: Professional P2P Chat Application with Auto-Discovery (NSD) and Encryption (TLS)
# Version: 2.0 - Professional UI

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
    QScrollArea, QStatusBar, QGridLayout, QTabWidget, QDialog, QFrame
)
from PySide6.QtCore import QThread, Signal, QObject, Qt, QUrl, QTimer, QSize, QPoint
from PySide6.QtGui import (
    QIcon, QFont, QDesktopServices, QAction, QPalette, QPixmap, QPainter, QColor,
    QPainterPath, QFontMetrics
)
from PySide6.QtMultimedia import QSoundEffect
from PySide6.QtSvg import QSvgRenderer

# KDE theme support
try:
    from PySide6.QtWidgets import QStyleFactory
except ImportError:
    QStyleFactory = None

# --- Application Configuration ---
HOME_DIR = str(Path.home())
APP_COLORS = {
    "primary": "#2A5C8D",          # Professional blue
    "primary_dark": "#1E3F66",     # Darker blue
    "secondary": "#4A90E2",        # Light blue
    "chat_bg": "#F5F7FA",          # Chat background
    "incoming_bg": "#FFFFFF",      # Incoming message bg
    "outgoing_bg": "#E1F0FF",      # Outgoing message bg
    "text_primary": "#2D3748",     # Main text color
    "text_secondary": "#4A5568",   # Secondary text
    "timestamp": "#718096",        # Timestamp color
    "header_bg": "#FFFFFF",        # Header background
    "sidebar_bg": "#F8FAFC",       # Sidebar background
    "active_chat": "#EBF4FF",      # Active chat highlight
    "notification": "#4299E1",     # Notification color
    "icon_color": "#4A5568",       # Icon color
    "input_border": "#E2E8F0",     # Input border
    "divider": "#E2E8F0",          # Divider lines
    "ping_color": "#E53E3E",       # Ping notification
    "online_status": "#48BB78",    # Online status
    "offline_status": "#A0AEC0",   # Offline status
    "success": "#38A169",          # Success messages
    "warning": "#DD6B20",          # Warning messages
    "error": "#E53E3E"             # Error messages
}

ICONS = {
    "user": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>""",
    "send": """<svg viewBox="0 0 24 24" height="24" width="24"><path fill="currentColor" d="M1.101,21.757L23.8,12.028L1.101,2.3l0.011,7.912l13.623,1.816L1.112,13.845 L1.101,21.757z"></path></svg>""",
    "ping": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path></svg>""",
    "attach": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path></svg>""",
    "file": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>""",
    "menu": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>""",
    "search": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>"""
}

SERVICE_TYPE = "_b-messenger._tcp.local."
CERTFILE = os.path.join(HOME_DIR, ".cert.pem")
KEYFILE = os.path.join(HOME_DIR, ".key.pem")
CHUNK_SIZE = 4096  # File transfer chunk size in bytes

# --- Helper Functions & UI Components ---
def make_circular_pixmap(source_pixmap):
    """Create a circular pixmap from source pixmap"""
    size = source_pixmap.size()
    mask = QPixmap(size)
    mask.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(mask)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    path = QPainterPath()
    path.addEllipse(0, 0, size.width(), size.height())
    painter.fillPath(path, Qt.GlobalColor.white)
    painter.end()
    
    result = QPixmap(size)
    result.fill(Qt.GlobalColor.transparent)
    painter.begin(result)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setClipPath(path)
    painter.drawPixmap(0, 0, source_pixmap)
    painter.end()
    
    return result

def create_icon_from_svg(svg_string, color="currentColor", size=QSize(24, 24)):
    """Create QIcon from SVG string with custom color"""
    colored_svg = svg_string.replace('currentColor', color)
    renderer = QSvgRenderer(colored_svg.encode('utf-8'))
    pixmap = QPixmap(size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return QIcon(pixmap)

class ChatListItem(QWidget):
    """Custom widget for chat list items with rich display"""
    def __init__(self, username, last_message=None, unread=False, is_online=False):
        super().__init__()
        self.setStyleSheet(f"""
            background: transparent;
            border-bottom: 1px solid {APP_COLORS['divider']};
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        
        # Profile picture with status indicator
        profile_container = QWidget()
        profile_container.setFixedSize(48, 48)
        profile_layout = QVBoxLayout(profile_container)
        profile_layout.setContentsMargins(0, 0, 0, 0)
        
        self.profile_pic_label = QLabel()
        icon_pixmap = create_icon_from_svg(
            ICONS['user'], 
            color=APP_COLORS["icon_color"], 
            size=QSize(42, 42)
        ).pixmap(QSize(42, 42))
        self.profile_pic_label.setPixmap(make_circular_pixmap(icon_pixmap))
        profile_layout.addWidget(self.profile_pic_label, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Status indicator
        self.status_indicator = QLabel()
        self.status_indicator.setFixedSize(10, 10)
        self.set_online_status(is_online)
        profile_layout.addWidget(
            self.status_indicator, 
            0, 
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom
        )
        
        layout.addWidget(profile_container)
        
        # Text content
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        
        # Top row (username and time)
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        
        self.username_label = QLabel(username)
        self.username_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Medium))
        self.username_label.setStyleSheet(f"color: {APP_COLORS['text_primary']};")
        top_row.addWidget(self.username_label)
        
        top_row.addStretch()
        
        self.time_label = QLabel("")
        self.time_label.setFont(QFont("Segoe UI", 10))
        self.time_label.setStyleSheet(f"color: {APP_COLORS['timestamp']};")
        top_row.addWidget(self.time_label)
        
        text_layout.addLayout(top_row)
        
        # Bottom row (message preview)
        self.message_preview = QLabel(last_message or "No messages yet")
        self.message_preview.setFont(QFont("Segoe UI", 10))
        self.message_preview.setStyleSheet(f"color: {APP_COLORS['text_secondary']};")
        self.message_preview.setWordWrap(True)
        self.message_preview.setMaximumWidth(220)
        self.message_preview.setSizePolicy(
            QSizePolicy.Policy.Expanding, 
            QSizePolicy.Policy.Preferred
        )
        text_layout.addWidget(self.message_preview)
        
        layout.addLayout(text_layout, 1)
        
        # Unread indicator
        self.unread_indicator = QLabel()
        self.unread_indicator.setFixedSize(16, 16)
        self.unread_indicator.setVisible(unread)
        self.unread_indicator.setStyleSheet(f"""
            background-color: {APP_COLORS['notification']};
            border-radius: 8px;
            border: none;
        """)
        layout.addWidget(self.unread_indicator)
        
        self.setMinimumHeight(72)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    
    def set_online_status(self, is_online):
        """Update the online status indicator"""
        color = APP_COLORS["online_status"] if is_online else APP_COLORS["offline_status"]
        self.status_indicator.setStyleSheet(f"""
            background-color: {color};
            border-radius: 5px;
            border: 2px solid {APP_COLORS['sidebar_bg']};
        """)
    
    def update_last_message(self, message, timestamp, is_unread=False):
        """Update the last message preview"""
        # Truncate long messages
        metrics = QFontMetrics(self.message_preview.font())
        elided_text = metrics.elidedText(
            message, 
            Qt.TextElideMode.ElideRight, 
            self.message_preview.maximumWidth()
        )
        self.message_preview.setText(elided_text)
        
        # Update timestamp
        if timestamp:
            self.time_label.setText(datetime.fromtimestamp(timestamp).strftime('%H:%M'))
        
        # Update unread indicator
        self.unread_indicator.setVisible(is_unread)

class FileBubbleWidget(QWidget):
    """Widget for displaying file transfer information"""
    def __init__(self, filename, filesize, status="", is_sent=False):
        super().__init__()
        self.filename = filename
        self.filesize = filesize
        self.setStyleSheet("background: transparent;")
        
        layout = QHBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(12, 8, 12, 8)
        
        # File icon
        file_icon_label = QLabel()
        file_icon = create_icon_from_svg(
            ICONS['file'], 
            APP_COLORS['icon_color'], 
            QSize(36, 36)
        )
        file_icon_label.setPixmap(file_icon.pixmap(QSize(36, 36)))
        layout.addWidget(file_icon_label)
        
        # File info
        text_layout = QVBoxLayout()
        text_layout.setSpacing(4)
        
        # Filename
        filename_label = QLabel(self.filename)
        filename_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
        filename_label.setStyleSheet(f"color: {APP_COLORS['text_primary']};")
        text_layout.addWidget(filename_label)
        
        # Filesize and progress
        filesize_layout = QHBoxLayout()
        filesize_layout.setContentsMargins(0, 0, 0, 0)
        filesize_layout.setSpacing(8)
        
        # Filesize text
        if self.filesize < 1024:
            filesize_str = f"{self.filesize} B"
        elif self.filesize < 1024 * 1024:
            filesize_str = f"{self.filesize / 1024:.1f} KB"
        else:
            filesize_str = f"{self.filesize / (1024 * 1024):.1f} MB"
            
        self.filesize_label = QLabel(filesize_str)
        self.filesize_label.setFont(QFont("Segoe UI", 9))
        self.filesize_label.setStyleSheet(f"color: {APP_COLORS['timestamp']};")
        filesize_layout.addWidget(self.filesize_label)
        
        filesize_layout.addStretch()
        text_layout.addLayout(filesize_layout)
        
        # Status and progress
        self.status_label = QLabel(status)
        status_font = QFont("Segoe UI", 9)
        status_font.setItalic(True)
        self.status_label.setFont(status_font)
        self.status_label.setStyleSheet(f"""
            color: {APP_COLORS['success'] if is_sent else APP_COLORS['primary']};
        """)
        text_layout.addWidget(self.status_label)
        
        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(4)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background: {APP_COLORS['divider']};
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background: {APP_COLORS['primary']};
                border-radius: 2px;
            }}
        """)
        self.progress_bar.setVisible(False)
        text_layout.addWidget(self.progress_bar)
        
        layout.addLayout(text_layout, 1)
    
    def set_status(self, text, is_success=False):
        """Update the status text"""
        color = APP_COLORS["success"] if is_success else APP_COLORS["primary"]
        self.status_label.setStyleSheet(f"color: {color};")
        self.status_label.setText(text)
    
    def update_progress(self, percent):
        """Update the progress bar"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(percent)
        if percent >= 100:
            self.progress_bar.setVisible(False)

class EmojiPicker(QDialog):
    """Popup emoji picker with categorized emojis"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup)
        self.setMinimumSize(400, 400)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Search bar
        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("Search emojis...")
        self.search_field.setStyleSheet(f"""
            QLineEdit {{
                background: white;
                border: 1px solid {APP_COLORS['input_border']};
                border-radius: 4px;
                padding: 8px;
            }}
        """)
        layout.addWidget(self.search_field)
        
        # Tab widget for categories
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Emoji categories
        emoji_categories = {
            "Smileys": [
                "😀", "😁", "😂", "🤣", "😃", "😄", "😅", "😆", "😉", "😊", 
                "😋", "😎", "😍", "😘", "🥰", "😗", "😙", "😚", "🙂", "🤗",
                "🤩", "🤔", "🤨", "😐", "😑", "😶", "🙄", "😏", "😣", "😥",
                "😮", "🤐", "😯", "😪", "😫", "🥱", "😴", "😌", "😛", "😜",
                "😝", "🤤", "😒", "😓", "😔", "😕", "🙃", "🤑", "😲", "☹️",
                "🙁", "😖", "😞", "😟", "😤", "😢", "😭", "😦", "😧", "😨",
                "😩", "🤯", "😬", "😰", "😱", "🥵", "🥶", "😳", "🤪", "😵",
                "😡", "😠", "🤬", "😷", "🤒", "🤕", "🤢", "🤮", "🥴", "😇",
                "🥳", "🥺", "🤠", "🤡", "🤥", "🤫", "🤭", "🧐", "🤓"
            ],
            "People": [
                "👋", "🤚", "🖐️", "✋", "🖖", "👌", "🤌", "🤏", "✌️", "🤞",
                "🫰", "🤟", "🤘", "🤙", "🫵", "🫱", "🫲", "🫳", "🫴", "👈",
                "👉", "👆", "🖕", "👇", "☝️", "👍", "👎", "✊", "👊", "🤛",
                "🤜", "👏", "🙌", "👐", "🤲", "🙏", "🫶", "💅", "🤳", "💪"
            ],
            "Nature": [
                "🐵", "🐶", "🐱", "🐭", "🐹", "🐰", "🦊", "🐻", "🐼", "🐨",
                "🐯", "🦁", "🐮", "🐷", "🐸", "🐔", "🐧", "🐦", "🐤", "🐣",
                "🐥", "🦆", "🦅", "🦉", "🦇", "🐺", "🐗", "🐴", "🦄", "🐝",
                "🐛", "🦋", "🐌", "🐞", "🐜", "🦟", "🦗", "🕷️", "🦂", "🐢"
            ],
            "Food": [
                "🍏", "🍎", "🍐", "🍊", "🍋", "🍌", "🍉", "🍇", "🍓", "🫐",
                "🍈", "🍒", "🍑", "🥭", "🍍", "🥥", "🥝", "🍅", "🍆", "🥑",
                "🥦", "🥬", "🥒", "🌶️", "🫑", "🌽", "🥕", "🫒", "🧄", "🧅"
            ],
            "Activity": [
                "⚽", "🏀", "🏈", "⚾", "🎾", "🏐", "🏉", "🥏", "🎱", "🏓",
                "🏸", "🥅", "🏒", "🏑", "🏏", "🥍", "🏹", "🎣", "🤿", "🥊",
                "🥋", "🎽", "🛹", "🛷", "⛸️", "🥌", "🎿", "⛷️", "🏂", "🪂"
            ],
            "Objects": [
                "⌛", "⏳", "⌚", "⏰", "⏱️", "⏲️", "🕰️", "🕛", "🕧", "🕐",
                "🕜", "🕑", "🕝", "🕒", "🕞", "🕓", "🕟", "🕔", "🕠", "🕕",
                "🕡", "🕖", "🕢", "🕗", "🕣", "🕘", "🕤", "🕙", "🕥", "🕚"
            ],
            "Symbols": [
                "❤️", "🧡", "💛", "💚", "💙", "💜", "🤎", "🖤", "🤍", "💯",
                "💢", "💥", "💫", "💦", "💨", "🕳️", "💣", "💬", "💭", "🗯️",
                "♠️", "♥️", "♦️", "♣️", "🃏", "🀄", "🎴", "🔔", "🔕", "🔒"
            ]
        }
        
        # Create emoji grids for each category
        for category, emojis in emoji_categories.items():
            tab = QWidget()
            grid = QGridLayout(tab)
            grid.setSpacing(4)
            grid.setContentsMargins(4, 4, 4, 4)
            
            # Add emoji buttons
            cols = 8
            for idx, emoji in enumerate(emojis):
                btn = QPushButton(emoji)
                btn.setFixedSize(36, 36)
                
                # Use emoji-aware font
                emoji_font = QFont()
                for fname in ["Segoe UI Emoji", "Noto Color Emoji", "Apple Color Emoji"]:
                    emoji_font.setFamily(fname)
                    if QFont(fname).exactMatch():
                        break
                else:
                    emoji_font.setFamily("Segoe UI")
                emoji_font.setPointSize(20)
                btn.setFont(emoji_font)
                
                btn.setStyleSheet("""
                    QPushButton {
                        font-size: 20px;
                        border: none;
                        background: transparent;
                    }
                    QPushButton:hover {
                        background: #E2E8F0;
                        border-radius: 4px;
                    }
                """)
                
                btn.clicked.connect(lambda checked=False, e=emoji: self.emoji_selected(e))
                grid.addWidget(btn, idx // cols, idx % cols)
            
            self.tabs.addTab(tab, category)
        
        self.selected_emoji = None
    
    def emoji_selected(self, emoji):
        """Handle emoji selection"""
        self.selected_emoji = emoji
        self.accept()
    
    def get_emoji(self):
        """Get the selected emoji"""
        return self.selected_emoji

# --- Network Logic ---
class ZeroconfListener:
    """Listener for Zeroconf service discovery"""
    def __init__(self, network_manager):
        self.network_manager = network_manager
    
    def remove_service(self, zeroconf, type, name):
        """Handle service removal"""
        self.network_manager.user_went_offline.emit(name)
    
    def add_service(self, zeroconf, type, name):
        """Handle new service discovery"""
        info = zeroconf.get_service_info(type, name)
        try:
            my_hostname = socket.gethostname()
            if info and info.server not in [f"{my_hostname}.local.", f"{my_hostname}."]:
                peer_data = {
                    "name": name,
                    "username": info.properties.get(b'username', b'unknown').decode('utf-8'),
                    "address": socket.inet_ntoa(info.addresses[0]),
                    "port": info.port,
                    "is_online": True
                }
                self.network_manager.user_discovered.emit(peer_data)
        except Exception as e:
            print(f"Error processing service {name}: {e}")
    
    def update_service(self, zeroconf, type, name):
        """Handle service updates"""
        self.add_service(zeroconf, type, name)

class AdvancedNetworkManager(QObject):
    """Network manager handling discovery and communication"""
    user_discovered = Signal(dict)          # Emitted when a new user is discovered
    user_went_offline = Signal(str)        # Emitted when a user goes offline
    private_message_received = Signal(dict) # Emitted when a message is received
    
    def __init__(self):
        super().__init__()
        self.username = getpass.getuser()
        self.my_ip = self._get_local_ip()
        self.port = self._get_free_port()
        self.running = True
        self.zeroconf = Zeroconf()
        self.listener = ZeroconfListener(self)
        self.browser = None
        
        # Create service info for announcing ourselves
        self.service_info = ServiceInfo(
            SERVICE_TYPE,
            f"{self.username}._S.{SERVICE_TYPE}",
            addresses=[socket.inet_aton(self.my_ip)],
            port=self.port,
            properties={'username': self.username.encode('utf-8')}
        )
    
    def _get_local_ip(self):
        """Get the local IP address"""
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            try:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
            except OSError:
                return "127.0.0.1"
    
    def _get_free_port(self):
        """Find a free port to use"""
        with socket.socket() as s:
            s.bind(('', 0))
            return s.getsockname()[1]
    
    def start_discovery(self):
        """Start service discovery and announce ourselves"""
        self.browser = ServiceBrowser(self.zeroconf, SERVICE_TYPE, self.listener)
        self.zeroconf.register_service(self.service_info)
        print(f"Announcing self: {self.username} at {self.my_ip}:{self.port}")
        
        # Start TLS server in a separate thread
        threading.Thread(target=self.run_tls_server, daemon=True).start()
    
    def stop(self):
        """Clean up network resources"""
        self.running = False
        try:
            if self.browser:
                self.browser.cancel()
            self.zeroconf.unregister_service(self.service_info)
            self.zeroconf.close()
        except Exception as e:
            print(f"Error while stopping Zeroconf: {e}")
        
        # Connect to our own port to unblock the accept() call
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect((self.my_ip, self.port))
        except:
            pass
    
    def _recvall(self, sock, n):
        """Receive exactly n bytes from socket"""
        data = bytearray()
        while len(data) < n:
            packet = sock.recv(n - len(data))
            if not packet:
                return None
            data.extend(packet)
        return data
    
    def run_tls_server(self):
        """Run TLS server to receive messages"""
        if not os.path.exists(CERTFILE) or not os.path.exists(KEYFILE):
            return
        
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        try:
            context.load_cert_chain(certfile=CERTFILE, keyfile=KEYFILE)
        except Exception as e:
            print(f"Failed to load certificate: {e}")
            return
        
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(1.0)
            try:
                sock.bind((self.my_ip, self.port))
            except OSError as e:
                print(f"Failed to bind to port {self.port}: {e}")
                return
            
            sock.listen(5)
            
            while self.running:
                try:
                    newsocket, fromaddr = sock.accept()
                    
                    with context.wrap_socket(newsocket, server_side=True) as ssock:
                        # Read message length (first 4 bytes)
                        raw_msglen = self._recvall(ssock, 4)
                        if not raw_msglen:
                            continue
                        
                        msglen = struct.unpack('>I', raw_msglen)[0]
                        
                        # Read the message data
                        full_data = self._recvall(ssock, msglen)
                        if not full_data:
                            continue
                        
                        # Emit the received message
                        self.private_message_received.emit(json.loads(full_data.decode('utf-8')))
                
                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        print(f"TLS server error: {e}")
    
    def send_tcp_message(self, peer_info, message_dict):
        """Send a message to a peer over TLS"""
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        try:
            with socket.create_connection(
                (peer_info['address'], peer_info['port']), 
                timeout=10
            ) as sock:
                with context.wrap_socket(sock, server_hostname=peer_info['address']) as ssock:
                    # Convert message to JSON and encode
                    message_bytes = json.dumps(message_dict).encode('utf-8')
                    
                    # Send message length (4 bytes) followed by the message
                    ssock.sendall(struct.pack('>I', len(message_bytes)))
                    ssock.sendall(message_bytes)
        except Exception as e:
            print(f"Failed to send message to {peer_info['username']}: {e}")
            self.user_went_offline.emit(peer_info['name'])

# --- Main Application Window ---
class MainWindow(QMainWindow):
    """Main application window with professional UI"""
    def __init__(self):
        super().__init__()
        self.chat_widgets = {}          # Active chat sessions
        self.active_transfers = {}       # Ongoing file transfers
        self.message_history = {}        # Message history per user
        self.unread_counts = {}         # Unread message counts
        
        # Setup UI and network
        self.setup_ui()
        self.setup_network()
        
        # Window shake animation for ping
        self.shake_timer = QTimer(self)
        self.shake_timer.timeout.connect(self._shake_step)
        self.shake_counter = 0
        self.original_pos = self.pos()
    
    def setup_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("B Messenger")
        self.setFont(QFont("Segoe UI", 10))
        
        # Window size and minimums
        self.setMinimumSize(800, 600)
        self.resize(1000, 700)
        
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Custom title bar
        self.setup_title_bar()
        main_layout.addWidget(self.title_bar)
        
        # Content area (below title bar)
        content_widget = QWidget()
        content_layout = QHBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # Sidebar
        self.setup_sidebar()
        content_layout.addWidget(self.sidebar)
        
        # Main chat area
        self.setup_chat_area()
        content_layout.addWidget(self.chat_area, 1)
        
        main_layout.addWidget(content_widget, 1)
        
        # Status bar
        self.setup_status_bar()
    
    def setup_title_bar(self):
        """Create custom title bar with window controls"""
        self.title_bar = QWidget()
        self.title_bar.setStyleSheet(f"""
            background-color: {APP_COLORS['primary']};
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        """)
        self.title_bar.setFixedHeight(40)
        
        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(12, 0, 12, 0)
        
        # Window title
        self.title_label = QLabel("B Messenger")
        self.title_label.setStyleSheet("""
            color: white;
            font-size: 14px;
            font-weight: medium;
        """)
        title_layout.addWidget(self.title_label)
        
        title_layout.addStretch()
        
        # Window controls
        self.setup_window_controls(title_layout)
    
    def setup_window_controls(self, layout):
        """Add window control buttons to title bar"""
        # Minimize button
        self.minimize_button = QPushButton("−")
        self.minimize_button.setFixedSize(30, 30)
        self.minimize_button.setStyleSheet("""
            QPushButton {
                color: white;
                background: transparent;
                border: none;
                font-size: 16px;
                qproperty-alignment: AlignCenter;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.2);
            }
        """)
        self.minimize_button.clicked.connect(self.showMinimized)
        layout.addWidget(self.minimize_button)
        
        # Maximize/Restore button
        self.maximize_button = QPushButton("□")
        self.maximize_button.setFixedSize(30, 30)
        self.maximize_button.setStyleSheet("""
            QPushButton {
                color: white;
                background: transparent;
                border: none;
                font-size: 16px;
                qproperty-alignment: AlignCenter;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.2);
            }
        """)
        self.maximize_button.clicked.connect(self.toggle_maximize)
        layout.addWidget(self.maximize_button)
        
        # Close button
        self.close_button = QPushButton("×")
        self.close_button.setFixedSize(30, 30)
        self.close_button.setStyleSheet("""
            QPushButton {
                color: white;
                background: transparent;
                border: none;
                font-size: 18px;
                qproperty-alignment: AlignCenter;
            }
            QPushButton:hover {
                background: #E53E3E;
            }
        """)
        self.close_button.clicked.connect(self.close)
        layout.addWidget(self.close_button)
    
    def toggle_maximize(self):
        """Toggle between maximized and normal window state"""
        if self.isMaximized():
            self.showNormal()
            self.maximize_button.setText("□")
        else:
            self.showMaximized()
            self.maximize_button.setText("❐")
    
    def setup_sidebar(self):
        """Setup the sidebar with chat list and search"""
        self.sidebar = QWidget()
        self.sidebar.setMinimumWidth(280)
        self.sidebar.setMaximumWidth(350)
        self.sidebar.setStyleSheet(f"""
            background-color: {APP_COLORS['sidebar_bg']};
            border-right: 1px solid {APP_COLORS['divider']};
        """)
        
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)
        
        # Search bar
        search_bar = QWidget()
        search_bar.setFixedHeight(60)
        search_bar.setStyleSheet(f"background-color: {APP_COLORS['header_bg']};")
        
        search_layout = QHBoxLayout(search_bar)
        search_layout.setContentsMargins(12, 12, 12, 12)
        
        self.search_field = QLineEdit()
        self.search_field.setPlaceholderText("Search contacts...")
        self.search_field.setStyleSheet(f"""
            QLineEdit {{
                background-color: white;
                border: 1px solid {APP_COLORS['input_border']};
                border-radius: 18px;
                padding: 8px 15px;
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border: 1px solid {APP_COLORS['primary']};
            }}
        """)
        
        # Add search icon
        search_icon = QLabel()
        search_icon.setPixmap(
            create_icon_from_svg(
                ICONS['search'], 
                APP_COLORS['icon_color']
            ).pixmap(QSize(16, 16))
        )
        search_icon.setStyleSheet("margin-left: 8px;")
        
        search_layout.addWidget(search_icon)
        search_layout.addWidget(self.search_field)
        sidebar_layout.addWidget(search_bar)
        
        # Chat list
        self.chat_list_widget = QListWidget()
        self.chat_list_widget.setStyleSheet(f"""
            QListWidget {{
                border: none;
                background-color: {APP_COLORS['sidebar_bg']};
            }}
            QListWidget::item {{
                border-bottom: 1px solid {APP_COLORS['divider']};
            }}
            QListWidget::item:selected {{
                background-color: {APP_COLORS['active_chat']};
            }}
            QListWidget::item:hover {{
                background-color: {APP_COLORS['active_chat']};
            }}
            QScrollBar:vertical {{
                border: none;
                background: {APP_COLORS['sidebar_bg']};
                width: 8px;
                margin: 0px 0px 0px 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {APP_COLORS['divider']};
                min-height: 20px;
                border-radius: 4px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                background: none;
            }}
        """)
        self.chat_list_widget.itemClicked.connect(self.on_chat_selected)
        sidebar_layout.addWidget(self.chat_list_widget)
    
    def setup_chat_area(self):
        """Setup the main chat area"""
        self.chat_area = QStackedWidget()
        self.chat_area.setStyleSheet(f"background-color: {APP_COLORS['chat_bg']};")
        
        # Placeholder widget when no chat is selected
        self.placeholder_widget = QWidget()
        placeholder_layout = QVBoxLayout(self.placeholder_widget)
        placeholder_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        placeholder_icon = QLabel()
        icon_pixmap = create_icon_from_svg(
            ICONS['user'], 
            color=APP_COLORS["icon_color"], 
            size=QSize(120, 120)
        ).pixmap(QSize(120, 120))
        placeholder_icon.setPixmap(icon_pixmap)
        placeholder_layout.addWidget(placeholder_icon, 0, Qt.AlignmentFlag.AlignHCenter)
        
        placeholder_text = QLabel("Select a contact to start chatting")
        placeholder_text.setFont(QFont("Segoe UI", 14))
        placeholder_text.setStyleSheet(f"""
            color: {APP_COLORS['text_secondary']}; 
            margin-top: 20px;
        """)
        placeholder_layout.addWidget(placeholder_text, 0, Qt.AlignmentFlag.AlignHCenter)
        
        placeholder_hint = QLabel("Users on your network will appear here automatically")
        placeholder_hint.setFont(QFont("Segoe UI", 11))
        placeholder_hint.setStyleSheet(f"""
            color: {APP_COLORS['timestamp']}; 
            margin-top: 8px;
        """)
        placeholder_layout.addWidget(placeholder_hint, 0, Qt.AlignmentFlag.AlignHCenter)
        
        self.chat_area.addWidget(self.placeholder_widget)
    
    def setup_status_bar(self):
        """Setup the status bar at the bottom"""
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet(f"""
            QStatusBar {{
                background-color: {APP_COLORS['sidebar_bg']};
                border-top: 1px solid {APP_COLORS['divider']};
                color: {APP_COLORS['text_secondary']};
                font-size: 11px;
                padding: 4px 12px;
            }}
        """)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
    
    def _create_chat_page(self, username, service_name):
        """Create a new chat page for a user"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        header_widget = QWidget()
        header_widget.setFixedHeight(70)
        header_widget.setStyleSheet(f"""
            background-color: {APP_COLORS['header_bg']};
            border-bottom: 1px solid {APP_COLORS['divider']};
        """)
        
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(16, 0, 16, 0)
        header_layout.setSpacing(12)
        
        # Back button (visible only in mobile mode)
        self.back_button = QPushButton()
        self.back_button.setIcon(create_icon_from_svg(ICONS['user'], APP_COLORS['icon_color']))
        self.back_button.setIconSize(QSize(24, 24))
        self.back_button.setFixedSize(40, 40)
        self.back_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.back_button.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
            }
            QPushButton:hover {
                background: #E2E8F0;
                border-radius: 20px;
            }
        """)
        self.back_button.clicked.connect(self.show_chat_list)
        self.back_button.hide()  # Hidden by default (visible in mobile mode)
        header_layout.addWidget(self.back_button)
        
        # User info
        user_info_widget = QWidget()
        user_info_layout = QHBoxLayout(user_info_widget)
        user_info_layout.setContentsMargins(0, 0, 0, 0)
        user_info_layout.setSpacing(12)
        
        # Profile picture
        profile_pic = QLabel()
        icon_pixmap = create_icon_from_svg(
            ICONS['user'], 
            color=APP_COLORS["icon_color"], 
            size=QSize(36, 36)
        ).pixmap(QSize(36, 36))
        profile_pic.setPixmap(make_circular_pixmap(icon_pixmap))
        user_info_layout.addWidget(profile_pic)
        
        # Name and status
        name_status_layout = QVBoxLayout()
        name_status_layout.setSpacing(2)
        
        self.chat_header_label = QLabel(username)
        self.chat_header_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Medium))
        self.chat_header_label.setStyleSheet(f"color: {APP_COLORS['text_primary']};")
        name_status_layout.addWidget(self.chat_header_label)
        
        self.status_label = QLabel("Offline")
        self.status_label.setFont(QFont("Segoe UI", 10))
        self.status_label.setStyleSheet(f"color: {APP_COLORS['timestamp']};")
        name_status_layout.addWidget(self.status_label)
        
        user_info_layout.addLayout(name_status_layout, 1)
        header_layout.addWidget(user_info_info_widget, 1)
        
        # Header buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(8)
        
        # Ping button
        ping_button = QPushButton()
        ping_button.setIcon(create_icon_from_svg(ICONS['ping'], APP_COLORS['icon_color']))
        ping_button.setIconSize(QSize(24, 24))
        ping_button.setFixedSize(40, 40)
        ping_button.setCursor(Qt.CursorShape.PointingHandCursor)
        ping_button.setToolTip("Send Ping")
        ping_button.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
            }
            QPushButton:hover {
                background: #E2E8F0;
                border-radius: 20px;
            }
        """)
        ping_button.clicked.connect(lambda: self.send_ping(service_name))
        button_layout.addWidget(ping_button)
        
        header_layout.addLayout(button_layout)
        layout.addWidget(header_widget)
        
        # Chat messages area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: {APP_COLORS['chat_bg']};
            }}
            QScrollBar:vertical {{
                border: none;
                background: {APP_COLORS['chat_bg']};
                width: 8px;
                margin: 0px 0px 0px 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {APP_COLORS['divider']};
                min-height: 20px;
                border-radius: 4px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                background: none;
            }}
        """)
        
        scroll_content_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_content_widget)
        scroll_layout.addStretch()  # Add stretch to push content to top
        
        scroll_area.setWidget(scroll_content_widget)
        layout.addWidget(scroll_area, 1)
        
        # Input area
        input_widget = QWidget()
        input_widget.setMinimumHeight(80)
        input_widget.setStyleSheet(f"""
            background-color: {APP_COLORS['header_bg']};
            border-top: 1px solid {APP_COLORS['divider']};
        """)
        
        input_layout = QHBoxLayout(input_widget)
        input_layout.setContentsMargins(16, 12, 16, 12)
        input_layout.setSpacing(12)
        
        # Attachment button
        attach_button = QPushButton()
        attach_button.setIcon(create_icon_from_svg(ICONS['attach'], APP_COLORS['icon_color']))
        attach_button.setIconSize(QSize(24, 24))
        attach_button.setFixedSize(40, 40)
        attach_button.setCursor(Qt.CursorShape.PointingHandCursor)
        attach_button.setToolTip("Attach File")
        attach_button.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
            }
            QPushButton:hover {
                background: #E2E8F0;
                border-radius: 20px;
            }
        """)
        attach_button.clicked.connect(lambda: self.prompt_send_file(service_name))
        input_layout.addWidget(attach_button)
        
        # Emoji button
        emoji_button = QPushButton("😊")
        emoji_button.setFixedSize(40, 40)
        emoji_button.setCursor(Qt.CursorShape.PointingHandCursor)
        emoji_button.setToolTip("Insert Emoji")
        
        # Use emoji-aware font
        emoji_font = QFont()
        for fname in ["Segoe UI Emoji", "Noto Color Emoji", "Apple Color Emoji"]:
            emoji_font.setFamily(fname)
            if QFont(fname).exactMatch():
                break
        else:
            emoji_font.setFamily("Segoe UI")
        emoji_font.setPointSize(20)
        emoji_button.setFont(emoji_font)
        
        emoji_button.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                padding: 0px;
            }
            QPushButton:hover {
                background: #E2E8F0;
                border-radius: 20px;
            }
        """)
        emoji_button.clicked.connect(lambda: self.show_emoji_popup(service_name))
        input_layout.addWidget(emoji_button)
        
        # Input field
        input_field = QLineEdit()
        input_field.setPlaceholderText("Type a message...")
        input_field.setStyleSheet(f"""
            QLineEdit {{
                background-color: white;
                border: 1px solid {APP_COLORS['input_border']};
                border-radius: 18px;
                padding: 8px 16px;
                font-size: 14px;
            }}
            QLineEdit:focus {{
                border: 1px solid {APP_COLORS['primary']};
            }}
        """)
        input_layout.addWidget(input_field, 1)
        
        # Send button
        send_button = QPushButton()
        send_button.setIcon(create_icon_from_svg(ICONS['send'], APP_COLORS['primary']))
        send_button.setIconSize(QSize(24, 24))
        send_button.setFixedSize(40, 40)
        send_button.setCursor(Qt.CursorShape.PointingHandCursor)
        send_button.setToolTip("Send Message")
        send_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {APP_COLORS['primary']};
                border-radius: 20px;
                border: none;
            }}
            QPushButton:hover {{
                background-color: {APP_COLORS['primary_dark']};
            }}
        """)
        input_layout.addWidget(send_button)
        
        layout.addWidget(input_widget)
        
        return page, {
            "scroll_area": scroll_area,
            "scroll_layout": scroll_layout,
            "input_field": input_field,
            "send_button": send_button
        }
    
    def show_emoji_popup(self, service_name):
        """Show emoji picker popup"""
        if service_name not in self.chat_widgets:
            return
            
        widgets = self.chat_widgets[service_name]["widgets"]
        input_field = widgets["input_field"]
        
        emoji_picker = EmojiPicker(self)
        emoji_picker.move(
            self.mapToGlobal(
                input_field.pos() + QPoint(0, -emoji_picker.height())
            )
        )
        
        if emoji_picker.exec() == QDialog.DialogCode.Accepted:
            emoji = emoji_picker.get_emoji()
            if emoji:
                input_field.insert(emoji)
    
    def add_message_to_history(self, scroll_area, scroll_layout, msg_dict, is_sent):
        """Add a message to the chat history"""
        # Remove the stretch at the end temporarily
        stretch_item = scroll_layout.takeAt(scroll_layout.count() - 1)
        
        msg_type = msg_dict.get("type", "text")
        is_event = msg_type == "ping"
        content_widget = None
        
        if msg_type == "text":
            # Format text message with emoji support
            text = msg_dict['content']
            escaped = html.escape(text)
            
            # Create label with emoji support
            content_widget = QLabel(escaped)
            content_widget.setWordWrap(True)
            content_widget.setStyleSheet(f"""
                color: {APP_COLORS['text_primary']};
                font-size: 14px;
            """)
            
            # Use emoji-aware font
            emoji_font = QFont()
            for fname in ["Segoe UI Emoji", "Noto Color Emoji", "Apple Color Emoji"]:
                emoji_font.setFamily(fname)
                if QFont(fname).exactMatch():
                    break
            else:
                emoji_font.setFamily("Segoe UI")
            
            emoji_font.setPointSize(12)
            content_widget.setFont(emoji_font)
            content_widget.setTextFormat(Qt.TextFormat.RichText)
        
        elif is_event:
            # Format ping notification
            from_user = msg_dict.get("from_user")
            text = "PING!!! sent" if is_sent else f"PING!!! from {from_user}"
            content_widget = QLabel(f"<span style='color:{APP_COLORS['ping_color']}; font-weight:bold;'>PING!!!</span>")
            content_widget.setWordWrap(True)
            content_widget.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        
        elif msg_type == "file_header":
            # Format file transfer message
            status = "Sending..." if is_sent else "Receiving..."
            content_widget = FileBubbleWidget(
                msg_dict['filename'], 
                msg_dict['filesize'], 
                status,
                is_sent
            )
            
            if not is_sent and 'transfer_id' in msg_dict:
                if msg_dict['transfer_id'] in self.active_transfers:
                    self.active_transfers[msg_dict['transfer_id']]['bubble'] = content_widget
        
        if not content_widget:
            scroll_layout.addStretch()
            return
        
        # Create message bubble
        bubble_widget = QWidget()
        bubble_layout = QVBoxLayout(bubble_widget)
        bubble_layout.setContentsMargins(12, 8, 12, 8)
        bubble_layout.addWidget(content_widget)
        
        if not is_event:
            # Add timestamp for regular messages
            ts_label = QLabel(
                datetime.fromtimestamp(msg_dict['timestamp']).strftime('%H:%M')
            )
            ts_label.setFont(QFont("Segoe UI", 9))
            ts_label.setStyleSheet(f"""
                color: {APP_COLORS['timestamp']}; 
                background: transparent;
            """)
            bubble_layout.addWidget(ts_label, 0, Qt.AlignmentFlag.AlignRight)
        
        # Set bubble background color
        bg_color = APP_COLORS["outgoing_bg"] if is_sent else APP_COLORS["incoming_bg"]
        bubble_widget.setStyleSheet(f"""
            background-color: {'transparent' if is_event else bg_color};
            border-radius: 12px;
        """)
        
        # Container for proper alignment
        container_widget = QWidget()
        container_layout = QHBoxLayout(container_widget)
        container_layout.setContentsMargins(10, 5, 10, 5)
        bubble_widget.setSizePolicy(
            QSizePolicy.Policy.Maximum, 
            QSizePolicy.Policy.Preferred
        )
        
        # Align message based on sender and type
        if is_event:
            if is_sent:
                container_layout.addStretch()
                container_layout.addWidget(bubble_widget)
            else:
                container_layout.addWidget(bubble_widget)
                container_layout.addStretch()
        elif is_sent:
            container_layout.addStretch()
            container_layout.addWidget(bubble_widget)
        else:
            container_layout.addWidget(bubble_widget)
            container_layout.addStretch()
        
        scroll_layout.addWidget(container_widget)
        scroll_layout.addStretch()  # Add stretch back
        
        # Scroll to bottom
        QTimer.singleShot(
            50, 
            lambda: scroll_area.verticalScrollBar().setValue(
                scroll_area.verticalScrollBar().maximum()
            )
        )
    
    def setup_network(self):
        """Setup network components"""
        self.network_thread = QThread()
        self.network_manager = AdvancedNetworkManager()
        self.network_manager.moveToThread(self.network_thread)
        
        # Connect signals
        self.network_manager.user_discovered.connect(self.add_user)
        self.network_manager.user_went_offline.connect(self.remove_user)
        self.network_manager.private_message_received.connect(
            self.handle_incoming_message
        )
        
        # Start network thread
        self.network_thread.started.connect(self.network_manager.start_discovery)
        self.network_thread.start()
    
    def add_user(self, peer_data):
        """Add a new user to the chat list"""
        service_name = peer_data['name']
        if service_name in self.chat_widgets:
            return
            
        username = peer_data['username']
        
        # Create chat page and list item
        page, widgets = self._create_chat_page(username, service_name)
        self.chat_area.addWidget(page)
        
        # Create list item
        item = QListWidgetItem()
        item_widget = ChatListItem(
            username,
            is_online=peer_data.get('is_online', False)
        )
        item.setSizeHint(item_widget.sizeHint())
        item.setData(Qt.ItemDataRole.UserRole, peer_data)
        
        self.chat_list_widget.addItem(item)
        self.chat_list_widget.setItemWidget(item, item_widget)
        
        # Connect signals
        widgets["send_button"].clicked.connect(
            lambda _, s=service_name: self.send_private_message(s)
        )
        widgets["input_field"].returnPressed.connect(
            lambda s=service_name: self.send_private_message(s)
        )
        
        # Store references
        self.chat_widgets[service_name] = {
            "page": page,
            "item": item,
            "widgets": widgets,
            "peer_data": peer_data,
            "item_widget": item_widget
        }
        
        # Initialize message history
        if service_name not in self.message_history:
            self.message_history[service_name] = []
        
        # Initialize unread count
        if service_name not in self.unread_counts:
            self.unread_counts[service_name] = 0
        
        # Select first user automatically
        if self.chat_list_widget.count() == 1:
            self.chat_list_widget.setCurrentItem(item)
            self.on_chat_selected(item)
    
    def on_chat_selected(self, item):
        """Handle chat selection from the list"""
        peer_data = item.data(Qt.ItemDataRole.UserRole)
        if not peer_data or peer_data['name'] not in self.chat_widgets:
            return
            
        service_name = peer_data['name']
        chat_data = self.chat_widgets[service_name]
        
        # Mark messages as read
        self.unread_counts[service_name] = 0
        chat_data["item_widget"].unread_indicator.setVisible(False)
        
        # Show chat page
        self.chat_area.setCurrentWidget(chat_data["page"])
        
        # In mobile mode, hide sidebar and show chat
        if self.width() < 800:
            self.sidebar.hide()
            self.back_button.show()
    
    def show_chat_list(self):
        """Show the chat list (sidebar)"""
        self.sidebar.show()
        self.back_button.hide()
        self.chat_area.setCurrentWidget(self.placeholder_widget)
    
    def remove_user(self, service_name):
        """Remove a user who went offline"""
        if service_name not in self.chat_widgets:
            return
            
        chat_data = self.chat_widgets[service_name]
        
        # If we're currently viewing this chat, switch to placeholder
        if self.chat_area.currentWidget() == chat_data['page']:
            self.chat_area.setCurrentWidget(self.placeholder_widget)
        
        # Remove from chat list
        self.chat_list_widget.takeItem(self.chat_list_widget.row(chat_data['item']))
        
        # Clean up
        chat_data['page'].deleteLater()
        del self.chat_widgets[service_name]
        del self.message_history[service_name]
        del self.unread_counts[service_name]
    
    def send_private_message(self, target_service_name):
        """Send a text message to a user"""
        if target_service_name not in self.chat_widgets:
            return
            
        chat_data = self.chat_widgets[target_service_name]
        widgets = chat_data['widgets']
        input_field = widgets['input_field']
        
        message = input_field.text().strip()
        if not message:
            return
            
        # Handle ping shortcut
        if message.lower() == 'p':
            self.send_ping(target_service_name)
            input_field.clear()
            return
            
        timestamp = time.time()
        msg_dict = {
            "type": "text",
            "content": message,
            "timestamp": timestamp,
            "from_user": self.network_manager.username
        }
        
        # Send message
        self.network_manager.send_tcp_message(chat_data['peer_data'], msg_dict)
        
        # Add to message history
        self.message_history[target_service_name].append((msg_dict, True))
        
        # Update UI
        self.add_message_to_history(
            widgets['scroll_area'],
            widgets['scroll_layout'],
            msg_dict,
            True
        )
        
        # Update last message preview
        chat_data["item_widget"].update_last_message(message, timestamp)
        
        input_field.clear()
    
    def _send_file_in_thread(self, file_path, transfer_id, peer_data):
        """Thread function for sending file chunks"""
        try:
            total_size = os.path.getsize(file_path)
            sent_bytes = 0
            
            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    
                    # Send chunk
                    b64_chunk = base64.b64encode(chunk).decode('ascii')
                    chunk_msg = {
                        "type": "file_chunk",
                        "transfer_id": transfer_id,
                        "data": b64_chunk
                    }
                    self.network_manager.send_tcp_message(peer_data, chunk_msg)
                    
                    # Update progress
                    sent_bytes += len(chunk)
                    percent = int((sent_bytes / total_size) * 100)
                    
                    # Update UI via signal if needed
                    # (In a real app, you'd use signals to update the UI)
                    
            # Send completion message
            end_msg = {
                "type": "file_end",
                "transfer_id": transfer_id,
                "from_user": self.network_manager.username
            }
            self.network_manager.send_tcp_message(peer_data, end_msg)
            
            print(f"File transfer {transfer_id} completed.")
        except Exception as e:
            print(f"Error during file sending thread: {e}")
    
    def prompt_send_file(self, target_service_name):
        """Prompt user to select and send a file"""
        if target_service_name not in self.chat_widgets:
            return
            
        chat_data = self.chat_widgets[target_service_name]
        
        # Open file dialog
        dialog = QFileDialog(self, "Select File to Send")
        dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        
        if not dialog.exec():
            return
            
        file_path = dialog.selectedFiles()[0]
        if not file_path:
            return
            
        try:
            filename = os.path.basename(file_path)
            filesize = os.path.getsize(file_path)
            transfer_id = str(uuid.uuid4())
            
            # Create file header message
            header_msg = {
                "type": "file_header",
                "filename": filename,
                "filesize": filesize,
                "transfer_id": transfer_id,
                "timestamp": time.time(),
                "from_user": self.network_manager.username
            }
            
            # Send header
            self.network_manager.send_tcp_message(chat_data['peer_data'], header_msg)
            
            # Add to message history
            self.message_history[target_service_name].append((header_msg, True))
            
            # Update UI
            widgets = chat_data['widgets']
            self.add_message_to_history(
                widgets['scroll_area'],
                widgets['scroll_layout'],
                header_msg,
                True
            )
            
            # Update last message preview
            chat_data["item_widget"].update_last_message(f"File: {filename}", time.time())
            
            # Start file transfer thread
            thread = threading.Thread(
                target=self._send_file_in_thread,
                args=(file_path, transfer_id, chat_data['peer_data'])
            )
            thread.daemon = True
            thread.start()
            
        except Exception as e:
            print(f"Error preparing file send: {e}")
            QMessageBox.critical(
                self,
                "File Error",
                f"Could not read or send file:\n{e}"
            )
    
    def send_ping(self, target_service_name):
        """Send a ping notification to a user"""
        if target_service_name not in self.chat_widgets:
            return
            
        chat_data = self.chat_widgets[target_service_name]
        widgets = chat_data['widgets']
        
        print(f"Sending PING! to {chat_data['peer_data']['username']}")
        
        msg_dict = {
            "type": "ping",
            "timestamp": time.time(),
            "from_user": self.network_manager.username
        }
        
        # Send ping
        self.network_manager.send_tcp_message(chat_data['peer_data'], msg_dict)
        
        # Add to message history
        self.message_history[target_service_name].append((msg_dict, True))
        
        # Update UI
        self.add_message_to_history(
            widgets['scroll_area'],
            widgets['scroll_layout'],
            msg_dict,
            True
        )
    
    def handle_incoming_message(self, msg):
        """Handle incoming message from network"""
        msg_type = msg.get("type")
        from_user = msg.get("from_user")
        
        # Find the target chat widget
        target_widget_info = None
        for service_name, data in self.chat_widgets.items():
            if data['peer_data']['username'] == from_user:
                target_widget_info = data
                break
        
        # If we don't have a chat open for this user and it's not a file/ping
        if not target_widget_info and msg_type not in ['file_header', 'file_chunk', 'file_end', 'ping']:
            return
            
        if msg_type == 'file_header':
            # Handle incoming file transfer
            try:
                transfer_id = msg['transfer_id']
                filename = msg['filename']
                
                # Create downloads directory if it doesn't exist
                downloads_path = str(Path.home() / "Downloads")
                if not os.path.exists(downloads_path):
                    os.makedirs(downloads_path)
                
                # Create unique filename if needed
                base, extension = os.path.splitext(filename)
                save_path = os.path.join(downloads_path, filename)
                counter = 1
                
                while os.path.exists(save_path):
                    save_path = os.path.join(
                        downloads_path, 
                        f"{base}_{counter}{extension}"
                    )
                    counter += 1
                
                # Open file for writing
                file_handle = open(save_path, 'wb')
                
                # Store transfer info
                self.active_transfers[transfer_id] = {
                    'file_handle': file_handle,
                    'path': save_path,
                    'bubble': None,
                    'bytes_received': 0,
                    'total_size': msg['filesize']
                }
                
                print(f"Receiving file {filename} ({transfer_id}), saving to {save_path}")
                
                # Add to message history if we have the chat open
                if target_widget_info:
                    self.message_history[target_widget_info['peer_data']['name']].append((msg, False))
                    self.add_message_to_history(
                        target_widget_info['widgets']['scroll_area'],
                        target_widget_info['widgets']['scroll_layout'],
                        msg,
                        False
                    )
                    
                    # Update unread count if not viewing this chat
                    if self.chat_area.currentWidget() != target_widget_info['page']:
                        service_name = target_widget_info['peer_data']['name']
                        self.unread_counts[service_name] += 1
                        target_widget_info["item_widget"].unread_indicator.setVisible(True)
                        
                    # Update last message preview
                    target_widget_info["item_widget"].update_last_message(
                        f"File: {filename}",
                        msg['timestamp']
                    )
            
            except Exception as e:
                print(f"Error handling file header: {e}")
        
        elif msg_type == 'file_chunk':
            # Handle file chunk
            transfer_id = msg.get('transfer_id')
            transfer = self.active_transfers.get(transfer_id)
            
            if transfer:
                try:
                    # Write chunk to file
                    chunk_data = base64.b64decode(msg['data'])
                    transfer['file_handle'].write(chunk_data)
                    
                    # Update progress
                    transfer['bytes_received'] += len(chunk_data)
                    percent = int((transfer['bytes_received'] / transfer['total_size']) * 100)
                    
                    # Update progress in UI if bubble exists
                    if transfer['bubble']:
                        transfer['bubble'].update_progress(percent)
                
                except Exception as e:
                    print(f"Error writing chunk for {transfer_id}: {e}")
        
        elif msg_type == 'file_end':
            # Handle file transfer completion
            transfer_id = msg.get('transfer_id')
            transfer = self.active_transfers.pop(transfer_id, None)
            
            if transfer:
                try:
                    # Close file
                    transfer['file_handle'].close()
                    
                    # Update UI
                    if transfer['bubble']:
                        transfer['bubble'].set_status("Saved to Downloads", True)
                    
                    print(f"File transfer {transfer_id} finished. Saved to {transfer['path']}")
                
                except Exception as e:
                    print(f"Error finishing transfer for {transfer_id}: {e}")
        
        elif msg_type == "ping":
            # Handle ping notification
            self.handle_incoming_ping(msg)
        
        elif target_widget_info:
            # Handle regular text message
            self.message_history[target_widget_info['peer_data']['name']].append((msg, False))
            
            # Add to chat history
            self.add_message_to_history(
                target_widget_info['widgets']['scroll_area'],
                target_widget_info['widgets']['scroll_layout'],
                msg,
                False
            )
            
            # Update unread count if not viewing this chat
            if self.chat_area.currentWidget() != target_widget_info['page']:
                service_name = target_widget_info['peer_data']['name']
                self.unread_counts[service_name] += 1
                target_widget_info["item_widget"].unread_indicator.setVisible(True)
            
            # Update last message preview
            target_widget_info["item_widget"].update_last_message(
                msg['content'],
                msg['timestamp']
            )
    
    def handle_incoming_ping(self, msg):
        """Handle incoming ping notification"""
        from_user = msg.get("from_user")
        print(f"PING!!! received from {from_user}")
        
        # Play sound if available
        if os.path.exists("ping.wav"):
            self.ping_sound = QSoundEffect()
            self.ping_sound.setSource(QUrl.fromLocalFile("ping.wav"))
            self.ping_sound.play()
        
        # Shake window
        self.shake_window()
        
        # Find the chat for this user
        for service_name, data in self.chat_widgets.items():
            if data['peer_data']['username'] == from_user:
                # Add to message history
                self.message_history[service_name].append((msg, False))
                
                # Add to chat UI
                widgets = data['widgets']
                self.add_message_to_history(
                    widgets['scroll_area'],
                    widgets['scroll_layout'],
                    msg,
                    False
                )
                
                # Update unread count if not viewing this chat
                if self.chat_area.currentWidget() != data['page']:
                    self.unread_counts[service_name] += 1
                    data["item_widget"].unread_indicator.setVisible(True)
                
                # Update last message preview
                data["item_widget"].update_last_message(
                    "Ping received",
                    msg['timestamp']
                )
                
                break
    
    def shake_window(self):
        """Animate window shake for ping notification"""
        if self.shake_timer.isActive():
            return
            
        self.original_pos = self.pos()
        self.shake_counter = 0
        self.shake_timer.start(20)
    
    def _shake_step(self):
        """Animation step for window shake"""
        if self.shake_counter > 15:
            self.shake_timer.stop()
            self.move(self.original_pos)
            return
            
        offset_x = (random.randint(0, 1) * 2 - 1) * 5
        offset_y = (random.randint(0, 1) * 2 - 1) * 5
        
        self.move(
            self.original_pos.x() + offset_x,
            self.original_pos.y() + offset_y
        )
        self.shake_counter += 1
    
    def closeEvent(self, event):
        """Clean up resources on window close"""
        # Close any open file transfers
        for transfer_id, transfer_data in list(self.active_transfers.items()):
            try:
                transfer_data['file_handle'].close()
                print(f"Closed dangling file handle for transfer {transfer_id}")
            except Exception as e:
                print(f"Error closing file on exit: {e}")
        
        # Stop network services
        self.network_manager.stop()
        self.network_thread.quit()
        self.network_thread.wait(2000)
        
        event.accept()

def ensure_certificates():
    """Generate TLS certificates if they don't exist"""
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
        return True
    except Exception as e:
        print(f"Failed to generate certificates: {e}")
        return False

if __name__ == "__main__":
    # Ensure we have TLS certificates
    if not ensure_certificates():
        app_temp = QApplication(sys.argv)
        error_box = QMessageBox()
        error_box.setIcon(QMessageBox.Icon.Critical)
        error_box.setText(f"Could not create certificate files: '{CERTFILE}' & '{KEYFILE}'")
        error_box.setInformativeText("Check OpenSSL installation and permissions.")
        error_box.setWindowTitle("Configuration Error")
        error_box.exec()
        sys.exit(1)
    
    # Create and run application
    app = QApplication(sys.argv)
    
    # Apply KDE theme if available
    if QStyleFactory:
        if "breeze" in QStyleFactory.keys():
            app.setStyle(QStyleFactory.create("breeze"))
        elif "oxygen" in QStyleFactory.keys():
            app.setStyle(QStyleFactory.create("oxygen"))
    
    # Create and show main window
    main_win = MainWindow()
    main_win.show()
    
    sys.exit(app.exec())
