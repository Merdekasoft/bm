#!/usr/bin/env python3
# Description: P2P Chat Application with Auto-Discovery (NSD) and Encryption (TLS)
# Enhanced Version with all fixes and improvements

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
import re
from pathlib import Path
from datetime import datetime
from zeroconf import ServiceInfo, Zeroconf, ServiceBrowser
import subprocess

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QListWidget, QListWidgetItem, QTextBrowser, QLineEdit, QPushButton, QStackedWidget,
    QLabel, QFileDialog, QProgressBar, QMenu, QMessageBox, QSizePolicy, QSpacerItem,
    QScrollArea, QSystemTrayIcon, QMenu as QTrayMenu, QDialog, QTabWidget, QGridLayout,
    QStyleFactory
)
from PySide6.QtCore import QThread, Signal, QObject, Qt, QUrl, QTimer, QSize
from PySide6.QtGui import (
    QIcon, QFont, QDesktopServices, QAction, QPalette, QPixmap, QPainter, QColor,
    QPainterPath
)
from PySide6.QtMultimedia import QSoundEffect
from PySide6.QtSvg import QSvgRenderer

# --- Application Configuration ---
HOME_DIR = str(Path.home())
APP_DATA_DIR = os.path.join(HOME_DIR, ".b-messenger")
os.makedirs(APP_DATA_DIR, exist_ok=True)

APP_COLORS = {
    "primary_green": "#00A884", "primary_green_dark": "#075E54", "secondary_green": "#25D366",
    "chat_bg": "#EFEAE2", "incoming_bg": "#FFFFFF", "outgoing_bg": "#D9FDD3",
    "text_primary": "#303030", "timestamp": "#667781", "header_bg": "#F0F2F5",
    "sidebar_bg": "#F0F2F5", "active_chat": "#E9EDEF", "notification": "#25D366",
    "icon_color": "#54656F", "input_border": "#DEE2E6", "ping_color": "#D32F2F"
}

ICONS = {
    "user": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>""",
    "send": """<svg viewBox="0 0 24 24" height="24" width="24"><path fill="currentColor" d="M1.101,21.757L23.8,12.028L1.101,2.3l0.011,7.912l13.623,1.816L1.112,13.845 L1.101,21.757z"></path></svg>""",
    "ping": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path></svg>""",
    "attach": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path></svg>""",
    "file": """<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>"""
}

SERVICE_TYPE = "_b-messenger._tcp.local."
CERTFILE = os.path.join(APP_DATA_DIR, "cert.pem")
KEYFILE = os.path.join(APP_DATA_DIR, "key.pem")
CHUNK_SIZE = 4096
PING_SOUND_FILE = os.path.join(APP_DATA_DIR, "ping.wav")

# --- Helper Functions ---
def make_circular_pixmap(source_pixmap):
    """Create a circular pixmap from the source pixmap"""
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
    """Create a QIcon from SVG string with specified color"""
    try:
        colored_svg = svg_string.replace('currentColor', color)
        renderer = QSvgRenderer(colored_svg.encode('utf-8'))
        pixmap = QPixmap(size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        return QIcon(pixmap)
    except Exception:
        return QIcon()

def ensure_certificates():
    """Ensure TLS certificates exist or generate new ones"""
    if os.path.exists(CERTFILE) and os.path.exists(KEYFILE):
        return True
    
    try:
        print("Generating TLS certificate and key...")
        subprocess.run([
            "openssl", "req", "-new", "-x509", "-days", "3650", "-nodes",
            "-out", CERTFILE, "-keyout", KEYFILE,
            "-subj", "/CN=b-messenger-p2p"
        ], check=True)
        os.chmod(CERTFILE, 0o600)
        os.chmod(KEYFILE, 0o600)
        print(f"Certificate and key generated: {CERTFILE}, {KEYFILE}")
        return True
    except Exception as e:
        print(f"Failed to generate certificates: {e}")
        return False

def get_system_avatar_path():
    """Get system avatar paths from common locations"""
    avatar_dirs = [
        "/usr/share/plasma/avatars/photos/",
        "/usr/share/pixmaps/faces/",
        "/var/lib/AccountsService/icons/"
    ]
    
    for dir_path in avatar_dirs:
        if os.path.exists(dir_path):
            try:
                files = [os.path.join(dir_path, f) for f in os.listdir(dir_path) 
                        if f.lower().endswith(('.png', '.jpg', '.jpeg'))]
                if files:
                    return files
            except Exception:
                continue
    return []

class ChatListItem(QWidget):
    """Custom widget for chat list items"""
    def __init__(self, user_label, avatar_path=None):
        super().__init__()
        self.setStyleSheet("background: transparent;")
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self.profile_pic_label = QLabel()
        self.profile_pic_label.setFixedSize(42, 42)
        
        if avatar_path and os.path.exists(avatar_path):
            try:
                pixmap = QPixmap(avatar_path).scaled(42, 42, 
                    Qt.AspectRatioMode.KeepAspectRatio, 
                    Qt.TransformationMode.SmoothTransformation)
                self.profile_pic_label.setPixmap(make_circular_pixmap(pixmap))
            except Exception:
                icon = create_icon_from_svg(ICONS['user'], 
                    color=APP_COLORS["icon_color"], size=QSize(42, 42))
                self.profile_pic_label.setPixmap(icon.pixmap(QSize(42, 42)))
        else:
            icon = create_icon_from_svg(ICONS['user'], 
                color=APP_COLORS["icon_color"], size=QSize(42, 42))
            self.profile_pic_label.setPixmap(icon.pixmap(QSize(42, 42)))

        layout.addWidget(self.profile_pic_label)

        text_layout = QVBoxLayout()
        text_layout.setContentsMargins(0, 0, 0, 0)
        text_layout.setSpacing(0)

        self.username_label = QLabel(user_label)
        self.username_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.username_label.setStyleSheet(f"color: {APP_COLORS['text_primary']};")

        text_layout.addWidget(self.username_label)
        layout.addLayout(text_layout, 1)

        self.setMinimumHeight(68)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

class ZeroconfListener:
    """Listener for Zeroconf service discovery"""
    def __init__(self, network_manager):
        self.network_manager = network_manager

    def remove_service(self, zeroconf, type, name):
        self.network_manager.user_went_offline.emit(name)

    def add_service(self, zeroconf, type, name):
        try:
            info = zeroconf.get_service_info(type, name)
            if not info:
                return
                
            my_hostname = socket.gethostname()
            if info.server in [f"{my_hostname}.local.", f"{my_hostname}."]:
                return
                
            if not info.addresses:
                return
                
            peer_data = {
                "name": name,
                "username": info.properties.get(b'username', b'unknown').decode('utf-8'),
                "address": socket.inet_ntoa(info.addresses[0]),
                "port": info.port
            }
            self.network_manager.user_discovered.emit(peer_data)
        except Exception as e:
            print(f"Error processing service {name}: {e}")

    def update_service(self, zeroconf, type, name):
        self.add_service(zeroconf, type, name)

class AdvancedNetworkManager(QObject):
    """Network manager handling discovery and communication"""
    user_discovered = Signal(dict)
    user_went_offline = Signal(str)
    private_message_received = Signal(dict)
    
    def __init__(self):
        super().__init__()
        self.username = getpass.getuser()
        self.my_ip = self._get_local_ip()
        self.port = self._get_free_port()
        self.running = True
        self.zeroconf = Zeroconf(ip_version=socket.AF_INET)
        self.listener = ZeroconfListener(self)
        self.browser = None
        
        self.service_info = ServiceInfo(
            SERVICE_TYPE,
            f"{self.username}._S.{SERVICE_TYPE}",
            addresses=[socket.inet_aton(self.my_ip)],
            port=self.port,
            properties={'username': self.username.encode('utf-8')}
        )

    def _get_local_ip(self):
        """Get local IP address that can reach the internet"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except OSError:
            try:
                return socket.gethostbyname(socket.gethostname())
            except socket.gaierror:
                return "127.0.0.1"

    def _get_free_port(self):
        """Find a free port to use"""
        with socket.socket() as s:
            s.bind(('', 0))
            return s.getsockname()[1]

    def start_discovery(self):
        """Start service discovery"""
        QTimer.singleShot(0, self._start_zeroconf)

    def _start_zeroconf(self):
        """Initialize Zeroconf service browser and registration"""
        try:
            self.browser = ServiceBrowser(self.zeroconf, SERVICE_TYPE, self.listener)
            self._register_service()
            threading.Thread(target=self.run_tls_server, daemon=True).start()
        except Exception as e:
            print(f"Failed to start Zeroconf: {e}")

    def _register_service(self):
        """Register our service with Zeroconf"""
        try:
            self.zeroconf.register_service(self.service_info)
            print(f"Announcing self: {self.username} at {self.my_ip}:{self.port}")
        except Exception as e:
            print(f"Zeroconf register_service error: {e}")
            if "NonUniqueNameException" in str(e):
                unique_id = uuid.uuid4().hex[:8]
                self.service_info.name = f"{self.username}-{unique_id}._S.{SERVICE_TYPE}"
                try:
                    self.zeroconf.register_service(self.service_info)
                except Exception as e2:
                    print(f"Failed to register service after renaming: {e2}")

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

        # Wake up the server socket if it's blocked on accept()
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                s.connect((self.my_ip, self.port))
        except:
            pass

    def _recvall(self, sock, n):
        """Receive exactly n bytes from socket"""
        data = bytearray()
        while len(data) < n:
            try:
                packet = sock.recv(n - len(data))
                if not packet:
                    return None
                data.extend(packet)
            except (socket.timeout, ConnectionResetError):
                continue
            except Exception:
                return None
        return data

    def run_tls_server(self):
        """Run TLS server to receive messages"""
        if not os.path.exists(CERTFILE) or not os.path.exists(KEYFILE):
            print("Error: Certificate or key file missing!")
            return

        print(f"Starting TLS server on {self.my_ip}:{self.port}")
        
        context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        try:
            context.load_cert_chain(certfile=CERTFILE, keyfile=KEYFILE)
        except Exception as e:
            print(f"Failed to load certificate: {e}")
            return

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(1.0)
            
            try:
                sock.bind((self.my_ip, self.port))
                sock.listen(5)
            except OSError as e:
                print(f"Failed to bind to port {self.port}: {e}")
                return

            while self.running:
                try:
                    newsocket, fromaddr = sock.accept()
                    with context.wrap_socket(newsocket, server_side=True) as ssock:
                        # Get message length (first 4 bytes)
                        raw_msglen = self._recvall(ssock, 4)
                        if not raw_msglen:
                            continue
                            
                        msglen = struct.unpack('>I', raw_msglen)[0]
                        if msglen > 10 * 1024 * 1024:  # 10MB limit
                            continue
                            
                        # Get the actual message data
                        full_data = self._recvall(ssock, msglen)
                        if not full_data:
                            continue
                            
                        try:
                            message = json.loads(full_data.decode('utf-8'))
                            self.private_message_received.emit(message)
                        except (json.JSONDecodeError, UnicodeDecodeError) as e:
                            print(f"Failed to decode message: {e}")
                except socket.timeout:
                    continue
                except ssl.SSLError as e:
                    print(f"SSL error: {e}")
                except Exception as e:
                    if self.running:
                        print(f"TLS server error: {e}")

    def send_tcp_message(self, peer_info, message_dict):
        """Send a TCP message to a peer"""
        if not peer_info or 'address' not in peer_info or 'port' not in peer_info:
            print(f"Invalid peer_info: {peer_info}")
            return

        print(f"Attempting to connect to {peer_info.get('username')} at {peer_info.get('address')}:{peer_info.get('port')}")
        
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        
        try:
            address = peer_info.get('address')
            port = peer_info.get('port')
            
            if not address or not port:
                print(f"Invalid peer info: {peer_info}")
                return
                
            with socket.create_connection((address, port), timeout=5) as sock:
                with context.wrap_socket(sock, server_hostname=address) as ssock:
                    message_bytes = json.dumps(message_dict).encode('utf-8')
                    # Prefix message with its length (4-byte big-endian)
                    ssock.sendall(struct.pack('>I', len(message_bytes)))
                    ssock.sendall(message_bytes)
        except ConnectionRefusedError:
            print(f"Peer {peer_info['username']} is offline or firewall is blocking port {peer_info['port']}")
            self.user_went_offline.emit(peer_info['name'])
        except socket.timeout:
            print(f"Peer {peer_info['username']} is not responding (timeout)")
        except OSError as e:
            print(f"Failed to send message to {peer_info.get('username')}: {e}")
        except Exception as e:
            print(f"Unexpected error sending to {peer_info.get('username')}: {e}")

    def is_peer_reachable(self, address, port):
        """Check if a peer is reachable"""
        try:
            with socket.create_connection((address, port), timeout=2):
                return True
        except:
            return False

class EmojiDialog(QDialog):
    """Dialog for emoji selection"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Popup)
        self.setMinimumWidth(37 * 10 + 32)
        
        # Emoji categories
        self.emoji_categories = {
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
            "Flags": [
                "🇮🇩", "🇺🇸", "🇬🇧", "🇯🇵", "🇰🇷", "🇨🇳", "🇸🇬", "🇲🇾", "🇹🇭", "🇻🇳", "🇫🇷", "🇩🇪", "🇮🇹", "🇪🇸", "🇷🇺", "🇧🇷", "🇦🇺", "🇨🇦", "🇸🇦", "🇹🇷"
            ]
        }
        
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        
        for cat, emojis in self.emoji_categories.items():
            tab = QWidget()
            grid = QGridLayout(tab)
            grid.setSpacing(2)
            grid.setContentsMargins(4, 4, 4, 4)
            
            cols = 10
            for idx, emoji in enumerate(emojis):
                btn = QPushButton(emoji)
                btn.setFixedSize(32, 32)
                
                # Find best emoji font
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
                btn.clicked.connect(lambda checked=False, e=emoji: self._emoji_selected(e))
                grid.addWidget(btn, idx // cols, idx % cols)
                
            tab.setLayout(grid)
            tabs.addTab(tab, cat)
            
        layout.addWidget(tabs)
        self.setLayout(layout)
        
    def _emoji_selected(self, emoji):
        """Handle emoji selection"""
        self.parent().insert_emoji(emoji)
        self.accept()

class MainWindow(QMainWindow):
    """Main application window"""
    def __init__(self):
        super().__init__()
        self._setup_resources()
        self._setup_ui()
        self._setup_network()
        
        # Animation timers
        self.shake_timer = QTimer(self)
        self.shake_timer.timeout.connect(self._shake_step)
        self.shake_counter = 0
        
    def _setup_resources(self):
        """Setup application resources"""
        # Create application data directory
        os.makedirs(APP_DATA_DIR, exist_ok=True)
        
        # Set window icon
        icon_path = os.path.join(os.path.dirname(__file__), "bm.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            tray_icon = QIcon(icon_path)
        else:
            # Fallback to default icon
            tray_icon = create_icon_from_svg(ICONS['user'])
            
        # Setup system tray
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = QSystemTrayIcon(tray_icon, self)
            self.tray.setToolTip("B Messenger")
            
            tray_menu = QTrayMenu()
            show_action = tray_menu.addAction("Show")
            hide_action = tray_menu.addAction("Hide")
            quit_action = tray_menu.addAction("Quit")
            
            show_action.triggered.connect(self.showNormal)
            hide_action.triggered.connect(self.hide)
            quit_action.triggered.connect(self.quit_app)
            
            self.tray.setContextMenu(tray_menu)
            self.tray.activated.connect(self._on_tray_activated)
            self.tray.show()
            
        # Get available avatars
        self.avatar_files = get_system_avatar_path()
        self.my_avatar = self.avatar_files[0] if self.avatar_files else None
        
        # Initialize chat data structures
        self.chat_widgets = {}
        self.active_transfers = {}
        
    def _setup_ui(self):
        """Setup the main UI"""
        self.setWindowTitle("B Messenger")
        self.setFont(QFont("Segoe UI", 10))
        self.setMinimumSize(900, 600)
        self.setGeometry(100, 100, 900, 600)
        self.setStyleSheet(f"background-color: {APP_COLORS['sidebar_bg']};")
        
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Left panel - chat list
        self._setup_left_panel(main_layout)
        
        # Right panel - chat area
        self._setup_right_panel(main_layout)
        
    def _setup_left_panel(self, main_layout):
        """Setup the left chat list panel"""
        self.left_panel = QWidget()
        self.left_panel.setMinimumWidth(260)
        self.left_panel.setMaximumWidth(400)
        self.left_panel.setStyleSheet(f"background-color: {APP_COLORS['sidebar_bg']};")
        
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        self.chat_list_widget = QListWidget()
        self.chat_list_widget.setStyleSheet(f"""
            QListWidget {{
                border: none;
                background: {APP_COLORS['sidebar_bg']};
                font-size: 15px;
            }}
            QListWidget::item {{
                padding: 8px 0;
                margin: 0;
            }}
            QListWidget::item:selected, QListWidget::item:hover {{
                background-color: {APP_COLORS['active_chat']};
                border-radius: 8px;
                padding: 8px;
            }}
            QScrollBar:vertical {{
                width: 7px;
                background: {APP_COLORS['sidebar_bg']};
                margin: 0px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: #d1d7db;
                min-height: 24px;
                border-radius: 4px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
                background: none;
                border: none;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)
        
        self.chat_list_widget.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self.chat_list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.chat_list_widget.itemClicked.connect(self.on_chat_selected)
        
        left_layout.addWidget(self.chat_list_widget)
        main_layout.addWidget(self.left_panel)
        
    def _setup_right_panel(self, main_layout):
        """Setup the right chat area panel"""
        self.right_panel = QWidget()
        self.right_panel.setStyleSheet(f"background-color: {APP_COLORS['chat_bg']};")
        
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        self.chat_area = QStackedWidget()
        self.placeholder_widget = QLabel(
            f"""<div style='text-align:center;color:{APP_COLORS['timestamp']};'>
                <h2 style='color:{APP_COLORS['text_primary']};'>B-Messenger</h2>
                <p>Select a friend to start chatting.<br/>Waiting for users...</p>
            </div>"""
        )
        self.placeholder_widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chat_area.addWidget(self.placeholder_widget)
        
        right_layout.addWidget(self.chat_area)
        main_layout.addWidget(self.right_panel)
        
    def _setup_network(self):
        """Setup network components"""
        self.network_thread = QThread()
        self.network_manager = AdvancedNetworkManager()
        self.network_manager.moveToThread(self.network_thread)
        
        # Connect signals
        self.network_manager.user_discovered.connect(self.add_user)
        self.network_manager.user_went_offline.connect(self.remove_user)
        self.network_manager.private_message_received.connect(self.handle_incoming_message)
        
        self.network_thread.started.connect(self.network_manager.start_discovery)
        self.network_thread.start()
        
    def _create_chat_page(self, username, service_name):
        """Create a chat page for a user"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        header_widget = QWidget()
        header_widget.setFixedHeight(60)
        header_widget.setStyleSheet(
            f"background-color: {APP_COLORS['header_bg']}; "
            f"border-bottom: 1px solid {APP_COLORS['input_border']}; "
            "padding: 0 10px;"
        )
        
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        header_label = QLabel(username)
        header_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        header_label.setStyleSheet(f"color: {APP_COLORS['text_primary']};")
        
        ping_button = QPushButton()
        ping_button.setIcon(create_icon_from_svg(ICONS['ping'], APP_COLORS['icon_color']))
        ping_button.setIconSize(QSize(24, 24))
        ping_button.setFixedSize(40, 40)
        ping_button.setCursor(Qt.CursorShape.PointingHandCursor)
        ping_button.setToolTip("Send a Ping!")
        ping_button.setStyleSheet("""
            QPushButton { 
                background-color: transparent; 
                border-radius: 20px; 
                border: none; 
            } 
            QPushButton:hover { 
                background-color: #E0E0E0; 
            }
        """)
        ping_button.clicked.connect(lambda: self.send_ping(service_name))
        
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        header_layout.addWidget(ping_button)
        
        # Chat area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet(f"""
            QScrollArea {{
                border: none;
                background-color: {APP_COLORS['chat_bg']};
            }}
            QScrollBar:vertical {{
                width: 8px;
                background: #F0F2F5;
                margin: 0px;
                border-radius: 4px;
            }}
            QScrollBar::handle:vertical {{
                background: #d1d7db;
                min-height: 24px;
                border-radius: 4px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
                background: none;
                border: none;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        scroll_content_widget = QWidget()
        scroll_area.setWidget(scroll_content_widget)
        
        scroll_layout = QVBoxLayout(scroll_content_widget)
        scroll_layout.addStretch()
        
        # Input toolbar
        input_toolbar = QWidget()
        input_toolbar.setMinimumHeight(62)
        input_toolbar.setStyleSheet(f"""
            QWidget {{
                background-color: {APP_COLORS['header_bg']};
                border-top: 1px solid {APP_COLORS['input_border']};
                padding: 0px 16px;
            }}
        """)
        
        it_layout = QHBoxLayout(input_toolbar)
        it_layout.setSpacing(15)
        it_layout.setContentsMargins(0, 0, 0, 0)
        
        # Emoji button
        emoji_button = QPushButton("😊")
        emoji_button.setFixedSize(48, 48)
        emoji_button.setCursor(Qt.CursorShape.PointingHandCursor)
        emoji_button.setToolTip("Insert Emoji")
        
        emoji_font = QFont()
        for fname in ["Segoe UI Emoji", "Noto Color Emoji", "Apple Color Emoji"]:
            emoji_font.setFamily(fname)
            if QFont(fname).exactMatch():
                break
        else:
            emoji_font.setFamily("Segoe UI")
            
        emoji_font.setPointSize(28)
        emoji_button.setFont(emoji_font)
        emoji_button.setStyleSheet("""
            QPushButton {
                background-color: transparent; 
                border-radius: 24px; 
                border: none; 
                font-size: 28px; 
                padding: 2px;
            }
            QPushButton:hover {
                background-color: #E9EDEF;
            }
        """)
        emoji_button.clicked.connect(self._show_emoji_dialog)
        
        # Input field
        input_field = QLineEdit(placeholderText="Type a message...")
        input_field.setFont(emoji_font)
        input_field.setStyleSheet(f"""
            QLineEdit {{
                background-color: {APP_COLORS['incoming_bg']};
                border: 1.5px solid {APP_COLORS['input_border']};
                border-radius: 24px;
                padding-left: 20px;
                padding-right: 20px;
                padding-top: 14px;
                padding-bottom: 14px;
                color: {APP_COLORS['text_primary']};
                font-size: 15px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.07);
                transition: border-color 0.2s;
            }}
            QLineEdit:focus {{
                border: 1.5px solid {APP_COLORS['primary_green']};
                background-color: #fff;
                outline: none;
            }}
            QLineEdit:hover {{
                border: 1.5px solid {APP_COLORS['secondary_green']};
            }}
        """)
        
        # Send button
        send_button = QPushButton()
        send_button.setIcon(create_icon_from_svg(ICONS['send'], APP_COLORS['icon_color']))
        send_button.setIconSize(QSize(28, 28))
        send_button.setFixedSize(40, 40)
        send_button.setCursor(Qt.CursorShape.PointingHandCursor)
        send_button.setToolTip("Send Message")
        send_button.setStyleSheet("""
            QPushButton {
                background-color: #e8f5e9; 
                border-radius: 20px; 
                border: none;
            }
            QPushButton:hover {
                background-color: #c8e6c9;
            }
        """)
        
        # Connect send functionality
        send_button.clicked.connect(lambda: self.send_private_message(service_name))
        input_field.returnPressed.connect(lambda: self.send_private_message(service_name))
        
        # Add widgets to layout
        it_layout.addWidget(emoji_button)
        it_layout.addWidget(input_field, 1)
        it_layout.addWidget(send_button)
        
        # Add all to main layout
        layout.addWidget(header_widget)
        layout.addWidget(scroll_area, 1)
        layout.addWidget(input_toolbar)
        
        return page, {
            "scroll_area": scroll_area,
            "scroll_layout": scroll_layout,
            "input_field": input_field,
            "send_button": send_button
        }
        
    def _show_emoji_dialog(self):
        """Show emoji selection dialog"""
        dialog = EmojiDialog(self)
        input_field = self.sender().parent().findChild(QLineEdit)
        if input_field:
            input_rect = input_field.rect()
            input_global = input_field.mapToGlobal(input_rect.bottomLeft())
            dialog_height = dialog.sizeHint().height()
            dialog.move(input_global.x(), input_global.y() - dialog_height)
            dialog.exec()
            
    def insert_emoji(self, emoji):
        """Insert emoji into current input field"""
        current_page = self.chat_area.currentWidget()
        if not current_page:
            return
            
        input_field = current_page.findChild(QLineEdit)
        if input_field:
            input_field.insert(emoji)
            
    def add_message_to_history(self, scroll_area, scroll_layout, msg_dict, is_sent):
        """Add a message to chat history"""
        stretch_item = scroll_layout.takeAt(scroll_layout.count() - 1)
        msg_type = msg_dict.get("type", "text")
        is_event = msg_type == "ping"
        
        content_widget = None
        
        if msg_type == "text":
            text = msg_dict['content']
            
            # URL detection pattern
            url_pattern = re.compile(
                r'(?<![\w@])'  # Not preceded by word character or @
                r'(?:https?://)?(?:www\.)?'
                r'(?:[a-zA-Z0-9\-]+\.)+[a-zA-Z]{2,}'  # domain
                r'(?::\d+)?(?:/[^\s<]*)?(?:\?[^\s<]*)?'  # port/path/query
                r'(?![\w])'  # Not followed by word character
            )
            
            # Make URLs clickable
            def linkify(match):
                url = match.group(0)
                if not url.startswith("http"):
                    url = "https://" + url
                return f"<a href='{url}' style='color:#2196F3;text-decoration:underline;'>{html.escape(match.group(0))}</a>"
                
            linked_text = url_pattern.sub(linkify, text)
            
            # Emoji pattern
            emoji_pattern = re.compile(
                "["
                "\U0001F600-\U0001F64F"  # emoticons
                "\U0001F300-\U0001F5FF"  # symbols & pictographs
                "\U0001F680-\U0001F6FF"  # transport & map symbols
                "\U0001F1E0-\U0001F1FF"  # flags (iOS)
                "\U00002700-\U000027BF"  # dingbats
                "\U0001F900-\U0001F9FF"  # supplemental symbols
                "\U00002600-\U000026FF"  # miscellaneous symbols
                "\U00002B50"             # star
                "\U00002B06"             # up arrow
                "]+", flags=re.UNICODE)
            
            # Don't modify emojis inside links
            def repl(m):
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
            content_widget = QLabel(f"<span style='color:{APP_COLORS['ping_color']}; font-weight:bold;'>PING!!!</span>")
            content_widget.setWordWrap(True)
            content_widget.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            
        if not content_widget:
            scroll_layout.addStretch()
            return
            
        # Create message bubble
        bubble_widget = QWidget()
        bubble_layout = QVBoxLayout(bubble_widget)
        bubble_layout.setContentsMargins(12, 8, 12, 8)
        bubble_layout.addWidget(content_widget)
        
        if not is_event:
            ts_label = QLabel(datetime.fromtimestamp(msg_dict['timestamp']).strftime('%H:%M'))
            ts_label.setFont(QFont("Segoe UI", 9))
            ts_label.setStyleSheet(f"color: {APP_COLORS['timestamp']}; background: transparent;")
            bubble_layout.addWidget(ts_label, 0, Qt.AlignmentFlag.AlignRight)
            
        bg_color = APP_COLORS["outgoing_bg"] if is_sent else APP_COLORS["incoming_bg"]
        bubble_widget.setStyleSheet(f"background-color: {'transparent' if is_event else bg_color}; border-radius: 12px;")
        
        # Container for proper alignment
        container_widget = QWidget()
        container_layout = QHBoxLayout(container_widget)
        container_layout.setContentsMargins(10, 5, 10, 5)
        bubble_widget.setSizePolicy(QSizePolicy.Policy.Maximum, QSizePolicy.Policy.Preferred)
        
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
        scroll_layout.addStretch()
        
        # Auto-scroll to bottom
        def safe_scroll():
            try:
                if scroll_area and scroll_area.verticalScrollBar():
                    scroll_area.verticalScrollBar().setValue(
                        scroll_area.verticalScrollBar().maximum()
                    )
            except RuntimeError:
                pass  # Widget already deleted
                
        QTimer.singleShot(50, safe_scroll)
        
    def add_user(self, peer_data):
        """Add a discovered user to the chat list"""
        service_name = peer_data['name']
        if service_name in self.chat_widgets:
            return
            
        username = peer_data['username']
        try:
            local_hostname = socket.gethostname()
            if username == getpass.getuser():
                host = local_hostname
            else:
                host = peer_data.get('address', '')
        except Exception:
            host = peer_data.get('address', '')
            
        user_label = f"{username}@{host}"
        
        # Select avatar based on username hash
        avatar_path = None
        if self.avatar_files:
            idx = abs(hash(username)) % len(self.avatar_files)
            avatar_path = self.avatar_files[idx]
            
        # Create chat page
        page, widgets = self._create_chat_page(username, service_name)
        self.chat_area.addWidget(page)
        
        # Create list item
        item = QListWidgetItem()
        item_widget = ChatListItem(user_label, avatar_path)
        item.setSizeHint(item_widget.sizeHint())
        item.setData(Qt.ItemDataRole.UserRole, peer_data)
        
        self.chat_list_widget.addItem(item)
        self.chat_list_widget.setItemWidget(item, item_widget)
        
        # Connect send functionality
        widgets["send_button"].clicked.connect(lambda _, s=service_name: self.send_private_message(s))
        widgets["input_field"].returnPressed.connect(lambda s=service_name: self.send_private_message(s))
        
        # Store widget references
        self.chat_widgets[service_name] = {
            "page": page,
            "item": item,
            "widgets": widgets,
            "peer_data": peer_data
        }
        
        # Select first user automatically
        if self.chat_list_widget.count() == 1:
            self.chat_list_widget.setCurrentItem(item)
            self.on_chat_selected(item)
            
    def on_chat_selected(self, item):
        """Handle chat selection from list"""
        peer_data = item.data(Qt.ItemDataRole.UserRole)
        if peer_data and peer_data['name'] in self.chat_widgets:
            self.chat_area.setCurrentWidget(self.chat_widgets[peer_data['name']]["page"])
            
    def remove_user(self, service_name):
        """Remove a user who went offline"""
        if service_name in self.chat_widgets:
            if self.chat_area.currentWidget() == self.chat_widgets[service_name]['page']:
                self.chat_area.setCurrentWidget(self.placeholder_widget)
                
            data = self.chat_widgets.pop(service_name)
            self.chat_list_widget.takeItem(self.chat_list_widget.row(data['item']))
            data['page'].deleteLater()
            
    def send_private_message(self, target_service_name):
        """Send a private message to a user"""
        data = self.chat_widgets.get(target_service_name)
        if not data:
            return
            
        widgets = data['widgets']
        input_field = widgets['input_field']
        message = input_field.text().strip()
        
        if not message:
            return
            
        timestamp = time.time()
        msg_dict = {
            "type": "text",
            "content": message,
            "timestamp": timestamp,
            "from_user": self.network_manager.username
        }
        
        self.network_manager.send_tcp_message(data['peer_data'], msg_dict)
        self.add_message_to_history(
            widgets['scroll_area'],
            widgets['scroll_layout'],
            msg_dict,
            True
        )
        input_field.clear()
        
    def handle_incoming_message(self, msg):
        """Handle incoming message from network"""
        msg_type = msg.get("type")
        from_user = msg.get("from_user")
        
        # Find target chat
        target_widget_info = None
        for service_name, data in self.chat_widgets.items():
            if data['peer_data']['username'] == from_user:
                target_widget_info = data
                break
                
        if not target_widget_info and msg_type != 'ping':
            return
            
        if msg_type == "ping":
            self.handle_incoming_ping(msg)
        elif target_widget_info:
            self.add_message_to_history(
                target_widget_info['widgets']['scroll_area'],
                target_widget_info['widgets']['scroll_layout'],
                msg,
                False
            )
            
    def send_ping(self, target_service_name):
        """Send a ping notification to a user"""
        data = self.chat_widgets.get(target_service_name)
        if not data:
            return
            
        timestamp = time.time()
        msg_dict = {
            "type": "ping",
            "timestamp": timestamp,
            "from_user": self.network_manager.username
        }
        
        self.network_manager.send_tcp_message(data['peer_data'], msg_dict)
        self.add_message_to_history(
            data['widgets']['scroll_area'],
            data['widgets']['scroll_layout'],
            msg_dict,
            True
        )
        
    def handle_incoming_ping(self, msg):
        """Handle incoming ping notification"""
        from_user = msg.get("from_user")
        print(f"PING!!! received from {from_user}")
        
        # Visual and sound effects
        self.shake_window()
        self.play_ping_sound()
        self.raise_()
        self.activateWindow()
        
        # Show tray notification
        if hasattr(self, 'tray'):
            self.tray.showMessage("B Messenger", f"PING!!! from {from_user}", 
                                QSystemTrayIcon.MessageIcon.Information, 2500)
                                
        # Find and highlight the sender's chat
        for service_name, data in self.chat_widgets.items():
            if data['peer_data']['username'] == from_user:
                widgets = data['widgets']
                self.add_message_to_history(
                    widgets['scroll_area'],
                    widgets['scroll_layout'],
                    msg,
                    False
                )
                
                # Blink the chat list item
                item = data['item']
                self._blink_chat_item(item)
                break
                
    def _blink_chat_item(self, item, blink_count=6, interval=180):
        """Blink a chat list item to draw attention"""
        item_widget = self.chat_list_widget.itemWidget(item)
        if not item_widget:
            return
            
        blink_color = "#FFD600"
        
        def do_blink(step=[0]):
            if step[0] >= blink_count:
                item_widget.setStyleSheet("background: transparent;")
                return
                
            if step[0] % 2 == 0:
                item_widget.setStyleSheet(f"background-color: {blink_color}; border-radius: 12px;")
            else:
                item_widget.setStyleSheet("background: transparent;")
                
            step[0] += 1
            QTimer.singleShot(interval, lambda: do_blink(step))
            
        do_blink()
        
    def play_ping_sound(self):
        """Play ping notification sound"""
        if os.path.exists(PING_SOUND_FILE):
            try:
                self.ping_sound = QSoundEffect()
                self.ping_sound.setSource(QUrl.fromLocalFile(PING_SOUND_FILE))
                self.ping_sound.setVolume(1.0)
                self.ping_sound.play()
            except Exception as e:
                print(f"Failed to play ping sound: {e}")
                
    def shake_window(self):
        """Shake the window to get attention"""
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
        self.move(self.original_pos.x() + offset_x, self.original_pos.y() + offset_y)
        self.shake_counter += 1
        
    def _on_tray_activated(self, reason):
        """Handle tray icon activation"""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.showNormal()
                self.raise_()
                self.activateWindow()
                self.setWindowState(
                    (self.windowState() & ~Qt.WindowState.WindowMinimized) | 
                    Qt.WindowState.WindowActive
                )
                QApplication.processEvents()
                self.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
                QTimer.singleShot(0, self.raise_)
                QTimer.singleShot(0, self.activateWindow)
                
    def closeEvent(self, event):
        """Handle window close event"""
        event.ignore()
        self.hide()
        
    def quit_app(self):
        """Clean up and quit application"""
        self.network_manager.stop()
        self.network_thread.quit()
        self.network_thread.wait(2000)
        
        if hasattr(self, 'tray'):
            self.tray.hide()
            
        QApplication.instance().quit()

def main():
    """Main application entry point"""
    # Ensure certificates exist
    if not ensure_certificates():
        print("Failed to generate TLS certificates. Exiting.")
        return 1
        
    # Create application
    app = QApplication(sys.argv)
    
    # Check for system tray
    if not QSystemTrayIcon.isSystemTrayAvailable():
        print("System tray not available!")
        return 1
        
    # Set application style
    if QStyleFactory:
        available_styles = QStyleFactory.keys()
        for style_name in ["breeze", "oxygen", "fusion", "windows", "gtk"]:
            if style_name in available_styles:
                app.setStyle(QStyleFactory.create(style_name))
                break
                
    # Create and show main window
    main_win = MainWindow()
    main_win.show()
    
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())
