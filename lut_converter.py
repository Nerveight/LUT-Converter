"""
LUT Converter
Turn .cube LUT files into PNG LUT textures for Unreal Engine, Unity and other engines.

Run:  python lut_converter.py [file.cube ...]
Needs: pip install PySide6 pillow numpy
"""

import os
import sys
import traceback
from datetime import datetime

import numpy as np
from PySide6.QtCore import Qt, QPoint, QRect, QRectF, QSettings, QSize, QTimer, QUrl, Signal
from PySide6.QtGui import (QAction, QColor, QDesktopServices, QFont, QIcon, QImage, QKeySequence, QPainter,
                           QPainterPath, QPen, QPixmap, QShortcut)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QButtonGroup, QCheckBox, QComboBox, QFileDialog,
                               QFrame, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMainWindow, QMenu,
                               QMessageBox, QProgressDialog, QPushButton, QSizePolicy, QSlider, QSpinBox,
                               QStackedWidget, QToolButton, QVBoxLayout, QWidget)

import lut_core as core

APP_NAME = "LUT Converter"
APP_VERSION = "1.0"
IMAGE_EXTS = (".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp", ".tga")


def resource(name):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, name)


def log_dir():
    root = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    path = os.path.join(root, APP_NAME)
    os.makedirs(path, exist_ok=True)
    return path


# ==========================================================================
# Look and feel
# ==========================================================================

C = {
    "bg": "#0e0e12", "panel": "#15151c", "raised": "#1c1c26", "hover": "#252532",
    "border": "#262634", "border_hi": "#3a3a50", "text": "#e6e6f0", "muted": "#8b8ba7",
    "faint": "#5c5c75", "accent": "#7c6fff", "accent_hi": "#8f84ff", "accent_lo": "#6a5ee6",
    "accent_bg": "#221f3f", "danger": "#f87171", "ok": "#4ade80", "well": "#0a0a0d",
}

STYLE = f"""
* {{ color: {C['text']}; outline: 0; }}
QMainWindow, #root {{ background: {C['bg']}; }}
QToolTip {{ background: {C['raised']}; color: {C['text']}; border: 1px solid {C['border_hi']};
            padding: 6px 8px; border-radius: 6px; }}

#panel {{ background: {C['panel']}; border: 1px solid {C['border']}; border-radius: 12px; }}
#well {{ background: {C['well']}; border: 1px solid {C['border']}; border-radius: 10px; }}

QLabel#h1 {{ font-size: 15pt; font-weight: 600; }}
QLabel#section {{ color: {C['muted']}; font-size: 8pt; font-weight: 600; letter-spacing: 1px; }}
QLabel#muted {{ color: {C['muted']}; }}
QLabel#hint {{ color: {C['muted']}; font-size: 9pt; background: {C['well']}; border: 1px solid {C['border']};
               border-radius: 8px; padding: 9px 11px; }}
QLabel#value {{ color: {C['text']}; font-family: "Cascadia Mono", Consolas, "DejaVu Sans Mono", monospace; font-size: 9pt; }}
QLabel#status {{ color: {C['muted']}; font-size: 9pt; }}
QLabel#status a {{ color: {C['accent_hi']}; }}

QPushButton, QToolButton {{
    background: {C['raised']}; border: 1px solid {C['border']}; border-radius: 8px;
    padding: 7px 14px; font-weight: 500;
}}
QPushButton:hover, QToolButton:hover {{ background: {C['hover']}; border-color: {C['border_hi']}; }}
QPushButton:pressed, QToolButton:pressed {{ background: {C['border']}; }}
QPushButton:disabled, QToolButton:disabled {{ color: {C['faint']}; background: {C['panel']}; border-color: {C['border']}; }}
QToolButton::menu-indicator {{ image: none; width: 0; }}

QPushButton#primary {{ background: {C['accent']}; border: 1px solid {C['accent']}; color: white; font-weight: 600; padding: 10px 14px; }}
QPushButton#primary:hover {{ background: {C['accent_hi']}; border-color: {C['accent_hi']}; }}
QPushButton#primary:pressed {{ background: {C['accent_lo']}; }}
QPushButton#primary:disabled {{ background: {C['raised']}; border-color: {C['border']}; color: {C['faint']}; }}

QPushButton#seg {{ background: transparent; border: none; border-radius: 6px; padding: 5px 14px; color: {C['muted']}; }}
QPushButton#seg:hover {{ color: {C['text']}; }}
QPushButton#seg:checked {{ background: {C['hover']}; color: {C['text']}; }}
#segbar {{ background: {C['well']}; border: 1px solid {C['border']}; border-radius: 8px; }}

QPushButton#ghost, QToolButton#ghost {{ background: transparent; border: 1px solid transparent; padding: 6px 8px; }}
QPushButton#ghost:hover, QToolButton#ghost:hover {{ background: {C['hover']}; }}

QComboBox, QSpinBox {{
    background: {C['raised']}; border: 1px solid {C['border']}; border-radius: 8px; padding: 6px 10px; min-height: 20px;
}}
QComboBox:hover, QSpinBox:hover {{ border-color: {C['border_hi']}; }}
QComboBox:focus, QSpinBox:focus {{ border-color: {C['accent']}; }}
QComboBox::drop-down {{ border: none; width: 26px; }}
QComboBox::down-arrow {{ image: url(__CHEVRON__); width: 12px; height: 12px; }}
QComboBox QAbstractItemView {{
    background: {C['raised']}; border: 1px solid {C['border_hi']}; border-radius: 8px; padding: 4px;
    selection-background-color: {C['accent_bg']}; selection-color: {C['text']};
}}
QSpinBox::up-button, QSpinBox::down-button {{ width: 0; border: none; }}

QSlider::groove:horizontal {{ height: 4px; background: {C['border']}; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {C['accent']}; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: white; width: 16px; height: 16px; margin: -6px 0; border-radius: 8px; }}
QSlider::handle:horizontal:hover {{ background: {C['accent_hi']}; }}
QSlider:disabled {{ }}
QSlider::sub-page:horizontal:disabled {{ background: {C['faint']}; }}

QCheckBox {{ spacing: 8px; color: {C['muted']}; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 4px; border: 1px solid {C['border_hi']}; background: {C['raised']}; }}
QCheckBox::indicator:checked {{ background: {C['accent']}; border-color: {C['accent']}; image: url(__CHECK__); }}

QListWidget {{ background: transparent; border: none; padding: 2px; }}
QListWidget::item {{ border-radius: 8px; padding: 0; margin: 1px 0; }}
QListWidget::item:hover {{ background: {C['raised']}; }}
QListWidget::item:selected {{ background: {C['accent_bg']}; }}

QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {C['border_hi']}; border-radius: 3px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line, QScrollBar::add-page, QScrollBar::sub-page {{ background: none; height: 0; }}

QMenu {{ background: {C['raised']}; border: 1px solid {C['border_hi']}; border-radius: 10px; padding: 6px; }}
QMenu::item {{ padding: 7px 28px 7px 12px; border-radius: 6px; }}
QMenu::item:selected {{ background: {C['accent_bg']}; }}
QMenu::item:disabled {{ color: {C['faint']}; }}
QMenu::separator {{ height: 1px; background: {C['border']}; margin: 5px 8px; }}

QMessageBox, QProgressDialog, QDialog {{ background: {C['panel']}; }}
QProgressBar {{ background: {C['well']}; border: 1px solid {C['border']}; border-radius: 5px; height: 10px; text-align: center; }}
QProgressBar::chunk {{ background: {C['accent']}; border-radius: 4px; }}
"""

ICONS = {
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "image": '<rect x="3" y="4" width="18" height="16" rx="2.5"/><circle cx="8.5" cy="9.5" r="1.8"/><path d="M21 16l-5-5-9 9"/>',
    "download": '<path d="M12 4v11M7 10l5 5 5-5M5 20h14"/>',
    "folder": '<path d="M3 7.5A1.5 1.5 0 0 1 4.5 6H9l2 2h8.5A1.5 1.5 0 0 1 21 9.5v8A1.5 1.5 0 0 1 19.5 19h-15A1.5 1.5 0 0 1 3 17.5z"/>',
    "more": '<circle cx="5" cy="12" r="1.3"/><circle cx="12" cy="12" r="1.3"/><circle cx="19" cy="12" r="1.3"/>',
    "x": '<path d="M6 6l12 12M18 6L6 18"/>',
    "copy": '<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5.5A1.5 1.5 0 0 0 14.5 4h-9A1.5 1.5 0 0 0 4 5.5v9A1.5 1.5 0 0 0 5.5 16H8"/>',
    "cube": '<path d="M12 3l8 4.5v9L12 21l-8-4.5v-9z"/><path d="M4 7.5l8 4.5 8-4.5M12 12v9"/>',
    "chevron": '<path d="M6 9l6 6 6-6"/>',
    "check": '<path d="M5 12.5l4.5 4.5L19 7"/>',
    "upload": '<path d="M12 16V5M7 10l5-5 5 5M5 20h14"/>',
}


def svg(name, color=C["text"], stroke=1.8):
    body = ICONS[name]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" '
            f'stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round">{body}</svg>')


def icon(name, color=C["text"], size=18):
    renderer = QSvgRenderer(svg(name, color).encode())
    pm = QPixmap(QSize(size, size) * 3)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    renderer.render(p)
    p.end()
    pm.setDevicePixelRatio(3)
    return QIcon(pm)


def write_svg_file(name, color, stroke=2.4):
    path = os.path.join(log_dir(), f"ui_{name}.svg")
    with open(path, "w", encoding="utf-8") as f:
        f.write(svg(name, color, stroke))
    return path.replace("\\", "/")


def to_qimage(arr):
    arr = np.ascontiguousarray(arr)
    h, w, _ = arr.shape
    return QImage(arr.data, w, h, 3 * w, QImage.Format_RGB888).copy()


# ==========================================================================
# Widgets
# ==========================================================================

class Panel(QFrame):
    def __init__(self, name="panel"):
        super().__init__()
        self.setObjectName(name)


def section(text):
    lbl = QLabel(text.upper())
    lbl.setObjectName("section")
    return lbl


class DropZone(QWidget):
    """Big friendly empty state shown before any LUT is loaded."""
    clicked = Signal()

    def __init__(self, title, subtitle, icon_name="upload"):
        super().__init__()
        self.title, self.subtitle, self.icon_name = title, subtitle, icon_name
        self.hot = False
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(200)

    def set_hot(self, hot):
        self.hot = hot
        self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.clicked.emit()

    def enterEvent(self, e):
        self.set_hot(True)

    def leaveEvent(self, e):
        self.set_hot(False)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(14, 14, -14, -14)
        pen = QPen(QColor(C["accent"] if self.hot else C["border_hi"]), 1.5, Qt.DashLine)
        pen.setDashPattern([4, 4])
        p.setPen(pen)
        p.setBrush(QColor(C["accent_bg"]) if self.hot else Qt.NoBrush)
        p.drawRoundedRect(r, 14, 14)

        cy = r.center().y()
        badge = QRectF(r.center().x() - 28, cy - 70, 56, 56)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(C["accent_bg"]))
        p.drawRoundedRect(badge, 16, 16)
        QSvgRenderer(svg(self.icon_name, C["accent_hi"], 1.6).encode()).render(p, badge.adjusted(14, 14, -14, -14))

        p.setPen(QColor(C["text"]))
        f = QFont(self.font())
        f.setPointSizeF(f.pointSizeF() * 1.25)
        f.setWeight(QFont.DemiBold)
        p.setFont(f)
        p.drawText(QRectF(r.left(), cy - 2, r.width(), 30), Qt.AlignHCenter | Qt.AlignTop, self.title)
        p.setPen(QColor(C["muted"]))
        p.setFont(self.font())
        p.drawText(QRectF(r.left() + 20, cy + 30, r.width() - 40, 60), Qt.AlignHCenter | Qt.AlignTop | Qt.TextWordWrap,
                   self.subtitle)


class TextureView(QWidget):
    """Shows the LUT texture big and pixel-sharp."""

    def __init__(self):
        super().__init__()
        self.image = None
        self.setMinimumSize(300, 200)

    def set_image(self, qimg):
        self.image = qimg
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        if self.image is None:
            return
        avail = QRectF(self.rect()).adjusted(24, 24, -24, -24)
        iw, ih = self.image.width(), self.image.height()
        scale = min(avail.width() / iw, avail.height() / ih)
        w, h = round(iw * scale), round(ih * scale)
        target = QRectF(round(avail.center().x() - w / 2), round(avail.center().y() - h / 2), w, h)
        p.setRenderHint(QPainter.SmoothPixmapTransform, scale < 1)   # blocky when zoomed in, like a pixel editor
        p.drawImage(target, self.image)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor(255, 255, 255, 28), 1))
        p.setBrush(Qt.NoBrush)
        p.drawRect(target.adjusted(-0.5, -0.5, 0.5, 0.5))


class CompareView(QWidget):
    """Before / after split view with a draggable divider."""
    image_dropped = Signal(str)

    def __init__(self):
        super().__init__()
        self.before = self.after = None
        self.split = 0.5
        self.dragging = False
        self.setMouseTracking(True)
        self.setMinimumSize(300, 200)

    def set_images(self, before, after):
        self.before, self.after = before, after
        self.update()

    def image_rect(self):
        if self.before is None:
            return QRectF()
        avail = QRectF(self.rect()).adjusted(20, 20, -20, -20)
        iw, ih = self.before.width(), self.before.height()
        s = min(avail.width() / iw, avail.height() / ih)
        w, h = iw * s, ih * s
        return QRectF(avail.center().x() - w / 2, avail.center().y() - h / 2, w, h)

    def _set_split_from(self, x):
        r = self.image_rect()
        if r.width() > 0:
            self.split = min(1, max(0, (x - r.left()) / r.width()))
            self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton and self.image_rect().contains(e.position()):
            self.dragging = True
            self._set_split_from(e.position().x())

    def mouseMoveEvent(self, e):
        r = self.image_rect()
        if self.dragging:
            self._set_split_from(e.position().x())
        self.setCursor(Qt.SplitHCursor if r.contains(e.position()) else Qt.ArrowCursor)

    def mouseReleaseEvent(self, e):
        self.dragging = False

    def paintEvent(self, e):
        if self.before is None:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setRenderHint(QPainter.SmoothPixmapTransform)
        r = self.image_rect()
        clip = QPainterPath()
        clip.addRoundedRect(r, 8, 8)
        p.setClipPath(clip)
        p.drawImage(r, self.after if self.after is not None else self.before)
        sx = r.left() + r.width() * self.split
        p.save()
        p.setClipRect(QRectF(r.left(), r.top(), sx - r.left(), r.height()), Qt.IntersectClip)
        p.drawImage(r, self.before)
        p.restore()
        p.setClipping(False)

        # Divider and handle
        p.setPen(QPen(QColor(255, 255, 255, 230), 2))
        p.drawLine(QPoint(round(sx), round(r.top())), QPoint(round(sx), round(r.bottom())))
        handle = QRectF(sx - 15, r.center().y() - 15, 30, 30)
        p.setBrush(QColor("white"))
        p.setPen(Qt.NoPen)
        p.drawEllipse(handle)
        p.setPen(QPen(QColor(C["bg"]), 1.8, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        cx, cy = handle.center().x(), handle.center().y()
        for d in (-1, 1):
            p.drawLine(QPoint(round(cx + d * 3), round(cy - 4)), QPoint(round(cx + d * 7), round(cy)))
            p.drawLine(QPoint(round(cx + d * 7), round(cy)), QPoint(round(cx + d * 3), round(cy + 4)))

        # Labels
        f = QFont(self.font())
        f.setPointSizeF(f.pointSizeF() * 0.8)
        f.setWeight(QFont.DemiBold)
        f.setLetterSpacing(QFont.AbsoluteSpacing, 1)
        p.setFont(f)
        for text, left in (("BEFORE", True), ("AFTER", False)):
            tw = p.fontMetrics().horizontalAdvance(text) + 18
            x = r.left() + 10 if left else r.right() - tw - 10
            pill = QRectF(x, r.top() + 10, tw, 22)
            visible = (pill.right() < sx) if left else (pill.left() > sx)
            if not visible:
                continue
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(0, 0, 0, 150))
            p.drawRoundedRect(pill, 11, 11)
            p.setPen(QColor("white"))
            p.drawText(pill, Qt.AlignCenter, text)


class ResetSlider(QSlider):
    """A slider that jumps back to its default value on double-click."""

    def __init__(self, orientation, default):
        super().__init__(orientation)
        self.default = default

    def mouseDoubleClickEvent(self, e):
        self.setValue(self.default)


class LutItem(QWidget):
    """One row in the LUT list."""

    def __init__(self, lut):
        super().__init__()
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(10)
        self.swatch = QLabel()
        self.swatch.setFixedSize(34, 34)
        lay.addWidget(self.swatch)
        col = QVBoxLayout()
        col.setSpacing(1)
        name = QLabel(lut.name)
        name.setToolTip(lut.path or "")
        f = name.font()
        f.setWeight(QFont.Medium)
        name.setFont(f)
        self.name = name
        meta = QLabel(lut.description + (f" · {lut.title}" if lut.title and lut.title != lut.name else ""))
        meta.setObjectName("muted")
        mf = meta.font()
        mf.setPointSizeF(mf.pointSizeF() * 0.88)
        meta.setFont(mf)
        self.meta = meta
        col.addWidget(name)
        col.addWidget(meta)
        lay.addLayout(col, 1)
        self._full_name = lut.name
        self._full_meta = meta.text()
        self.set_swatch(lut)

    def set_swatch(self, lut):
        # A tiny preview: a gray ramp (top) and hue sweep (bottom) through the LUT
        n = 34
        t = np.linspace(0, 1, n, dtype=np.float32)
        gray = np.repeat(np.stack([t, t, t], -1)[None], n // 2, 0)
        hue = core._hsv_to_rgb(np.tile(t, (n - n // 2, 1)), np.full((n - n // 2, n), 0.85, np.float32),
                               np.full((n - n // 2, n), 0.9, np.float32))
        img = core.to_uint8(lut.apply(np.concatenate([gray, hue], 0)))
        pm = QPixmap.fromImage(to_qimage(img))
        rounded = QPixmap(pm.size())
        rounded.fill(Qt.transparent)
        p = QPainter(rounded)
        p.setRenderHint(QPainter.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(rounded.rect()), 7, 7)
        p.setClipPath(path)
        p.drawPixmap(0, 0, pm)
        p.end()
        self.swatch.setPixmap(rounded)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        w = max(40, self.width() - 70)
        self.name.setText(self.name.fontMetrics().elidedText(self._full_name, Qt.ElideMiddle, w))
        self.meta.setText(self.meta.fontMetrics().elidedText(self._full_meta, Qt.ElideRight, w))


# ==========================================================================
# Main window
# ==========================================================================

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("LUT Converter", "LUT Converter")
        self.luts = []
        self.graded_cache = {}            # id(lut) -> graded preview image (float)
        self.texture_cache = {}           # (id(lut), target, strip) -> graded texture (float)
        self.preview_src = core.sample_image()
        self.preview_name = "Built-in color chart"

        self.setWindowTitle(APP_NAME)
        if os.path.exists(resource("lut_icon.ico")):
            self.setWindowIcon(QIcon(resource("lut_icon.ico")))
        self.setAcceptDrops(True)
        self.setMinimumSize(980, 620)

        self._render_timer = QTimer(self, singleShot=True, interval=16, timeout=self._render_now)
        self._build()
        self._restore_settings()
        self._shortcuts()
        self.refresh()

    # ---- layout ----------------------------------------------------------
    def _build(self):
        root = QWidget(objectName="root")
        self.setCentralWidget(root)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(16, 12, 16, 10)
        outer.setSpacing(12)

        # Header
        head = QHBoxLayout()
        head.setSpacing(10)
        logo = QLabel()
        if os.path.exists(resource("lut_icon.ico")):
            logo.setPixmap(QIcon(resource("lut_icon.ico")).pixmap(28, 28))
        head.addWidget(logo)
        title = QLabel(APP_NAME, objectName="h1")
        head.addWidget(title)
        sub = QLabel(".cube  →  PNG LUT textures", objectName="muted")
        head.addWidget(sub)
        head.addStretch(1)
        self.add_btn = QPushButton(icon("plus"), "  Add LUTs")
        self.add_btn.setToolTip("Add .cube files (Ctrl+O). You can also drop them anywhere on the window.")
        self.add_btn.clicked.connect(self.browse_luts)
        head.addWidget(self.add_btn)
        more = QToolButton(objectName="ghost")
        more.setIcon(icon("more"))
        more.setIconSize(QSize(18, 18))
        more.setPopupMode(QToolButton.InstantPopup)
        more.setToolTip("More")
        menu = QMenu(more)
        self.act_preview_img = menu.addAction(icon("image"), "Preview on my own image…", self.browse_preview_image)
        self.act_reset_img = menu.addAction("Use the built-in color chart", self.reset_preview_image)
        menu.addSeparator()
        menu.addAction(icon("download"), "Save a neutral LUT texture…", self.save_neutral)
        self.act_copy = menu.addAction(icon("copy"), "Copy texture to clipboard", self.copy_texture, "Ctrl+C")
        menu.addSeparator()
        menu.addAction(icon("folder"), "Open error log folder", lambda: self._open_folder(log_dir()))
        menu.addAction(f"About {APP_NAME}", self.about)
        more.setMenu(menu)
        head.addWidget(more)
        outer.addLayout(head)

        body = QHBoxLayout()
        body.setSpacing(12)
        outer.addLayout(body, 1)

        # Left: LUT list
        left = Panel()
        left.setFixedWidth(270)
        ll = QVBoxLayout(left)
        ll.setContentsMargins(12, 14, 12, 12)
        ll.setSpacing(8)
        lh = QHBoxLayout()
        self.list_title = section("LUTs")
        lh.addWidget(self.list_title)
        lh.addStretch(1)
        self.clear_btn = QPushButton("Clear", objectName="ghost")
        self.clear_btn.setToolTip("Remove all LUTs from the list")
        self.clear_btn.clicked.connect(self.clear_luts)
        lh.addWidget(self.clear_btn)
        ll.addLayout(lh)
        self.list = QListWidget()
        self.list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.list.currentRowChanged.connect(lambda _: self.refresh())
        self.list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list.customContextMenuRequested.connect(self._list_menu)
        self.list_drop = QLabel("No LUTs yet", objectName="muted", alignment=Qt.AlignCenter)
        self.list_stack = QStackedWidget()
        self.list_stack.addWidget(self.list_drop)
        self.list_stack.addWidget(self.list)
        ll.addWidget(self.list_stack, 1)
        self.remove_btn = QPushButton(icon("x", C["muted"]), "  Remove selected")
        self.remove_btn.setObjectName("ghost")
        self.remove_btn.clicked.connect(self.remove_selected)
        ll.addWidget(self.remove_btn)
        body.addWidget(left)

        # Center: preview
        center = Panel()
        cl = QVBoxLayout(center)
        cl.setContentsMargins(14, 12, 14, 12)
        cl.setSpacing(10)
        ch = QHBoxLayout()
        segbar = QFrame(objectName="segbar")
        sl = QHBoxLayout(segbar)
        sl.setContentsMargins(3, 3, 3, 3)
        sl.setSpacing(2)
        self.seg = QButtonGroup(self)
        for i, (text, tip) in enumerate((("Texture", "The PNG you'll export"),
                                         ("On image", "See the LUT applied to an image, with a before / after split"))):
            b = QPushButton(text, objectName="seg", checkable=True)
            b.setToolTip(tip)
            b.setCursor(Qt.PointingHandCursor)
            self.seg.addButton(b, i)
            sl.addWidget(b)
        self.seg.idClicked.connect(self._set_view)
        self.segbar = segbar
        ch.addWidget(segbar)
        ch.addStretch(1)
        self.preview_caption = QLabel(objectName="muted")
        ch.addWidget(self.preview_caption)
        self.img_btn = QPushButton(icon("image", C["muted"]), "  Change image…", objectName="ghost")
        self.img_btn.setToolTip("Preview the LUT on one of your own screenshots or photos.\nYou can also drop an image on the window.")
        self.img_btn.clicked.connect(self.browse_preview_image)
        ch.addWidget(self.img_btn)
        cl.addLayout(ch)

        well = Panel("well")
        wl = QVBoxLayout(well)
        wl.setContentsMargins(0, 0, 0, 0)
        self.view_stack = QStackedWidget()
        self.texture_view = TextureView()
        self.compare_view = CompareView()
        self.center_drop = DropZone("Drop .cube LUT files here",
                                    "or click to browse. Convert them to PNG textures for Unreal Engine, Unity and more.")
        self.center_drop.clicked.connect(self.browse_luts)
        self.view_stack.addWidget(self.texture_view)
        self.view_stack.addWidget(self.compare_view)
        self.view_stack.addWidget(self.center_drop)
        wl.addWidget(self.view_stack)
        cl.addWidget(well, 1)
        body.addWidget(center, 1)

        # Right: export settings
        right = Panel()
        right.setFixedWidth(300)
        rl = QVBoxLayout(right)
        rl.setContentsMargins(16, 14, 16, 16)
        rl.setSpacing(8)

        rl.addWidget(section("Export for"))
        self.target_box = QComboBox()
        for t in core.TARGETS:
            self.target_box.addItem(t.label, t.key)
        self.target_box.currentIndexChanged.connect(lambda _: self.refresh())
        rl.addWidget(self.target_box)
        self.hint = QLabel(objectName="hint", wordWrap=True)
        self.hint.setTextFormat(Qt.RichText)
        self.hint.setTextInteractionFlags(Qt.TextSelectableByMouse)
        rl.addWidget(self.hint)

        self.strip_box = QWidget()
        sb = QHBoxLayout(self.strip_box)
        sb.setContentsMargins(0, 4, 0, 0)
        sb.setSpacing(8)
        self.strip_w = self._spin(2, 8192, 512, "Width")
        self.strip_h = self._spin(1, 2048, 32, "Height")
        for lab, spin in (("W", self.strip_w), ("H", self.strip_h)):
            l = QLabel(lab, objectName="muted")
            sb.addWidget(l)
            sb.addWidget(spin, 1)
        rl.addWidget(self.strip_box)

        rl.addSpacing(10)
        sh = QHBoxLayout()
        sh.addWidget(section("Strength"))
        sh.addStretch(1)
        self.strength_lbl = QLabel("100%", objectName="value")
        sh.addWidget(self.strength_lbl)
        rl.addLayout(sh)
        self.strength = ResetSlider(Qt.Horizontal, 100)
        self.strength.setRange(0, 100)
        self.strength.setValue(100)
        self.strength.setToolTip("Blend between no change (0%) and the full LUT (100%).\nDouble-click to reset.")
        self.strength.valueChanged.connect(self._strength_changed)
        rl.addWidget(self.strength)

        rl.addSpacing(10)
        rl.addWidget(section("Output"))
        info = QFrame(objectName="well")
        il = QVBoxLayout(info)
        il.setContentsMargins(12, 10, 12, 10)
        il.setSpacing(6)
        self.out_size = self._info_row(il, "Size")
        self.out_name = self._info_row(il, "File")
        rl.addWidget(info)

        rl.addStretch(1)
        self.export_btn = QPushButton(icon("download", "white"), "  Export PNG", objectName="primary")
        self.export_btn.setToolTip("Save the selected LUT as a PNG texture (Ctrl+S)")
        self.export_btn.setCursor(Qt.PointingHandCursor)
        self.export_btn.clicked.connect(self.export_current)
        rl.addWidget(self.export_btn)
        self.export_all_btn = QPushButton(icon("folder"), "  Export all to folder…")
        self.export_all_btn.setToolTip("Save every LUT in the list with these settings (Ctrl+Shift+S)")
        self.export_all_btn.clicked.connect(self.export_all)
        rl.addWidget(self.export_all_btn)
        self.open_after = QCheckBox("Show in folder after export")
        rl.addWidget(self.open_after)
        body.addWidget(right)

        # Status line
        self.status = QLabel(objectName="status")
        self.status.setTextFormat(Qt.RichText)
        self.status.linkActivated.connect(self._open_link)
        outer.addWidget(self.status)
        self._status_timer = QTimer(self, singleShot=True, timeout=lambda: self.set_status(""))

    def _spin(self, lo, hi, val, tip):
        s = QSpinBox()
        s.setRange(lo, hi)
        s.setValue(val)
        s.setSuffix(" px")
        s.setToolTip(tip)
        s.valueChanged.connect(lambda _: self.refresh())
        return s

    def _info_row(self, layout, label):
        row = QHBoxLayout()
        l = QLabel(label, objectName="muted")
        l.setFixedWidth(36)
        v = QLabel("—", objectName="value")
        v.setTextInteractionFlags(Qt.TextSelectableByMouse)
        row.addWidget(l)
        row.addWidget(v, 1)
        layout.addLayout(row)
        return v

    def _shortcuts(self):
        QShortcut(QKeySequence.Open, self, self.browse_luts)
        QShortcut(QKeySequence("Ctrl+S"), self, self.export_current)
        QShortcut(QKeySequence("Ctrl+Shift+S"), self, self.export_all)
        QShortcut(QKeySequence.Delete, self.list, self.remove_selected)
        QShortcut(QKeySequence("Ctrl+C"), self, self.copy_texture)
        QShortcut(QKeySequence("Ctrl+Tab"), self, lambda: self._set_view(1 - self.seg.checkedId()))

    # ---- settings --------------------------------------------------------
    def _restore_settings(self):
        s = self.settings
        geo = s.value("geometry")
        if geo is not None:
            self.restoreGeometry(geo)
        else:
            self.resize(1240, 760)
        key = s.value("target", "ue")
        idx = self.target_box.findData(key)
        self.target_box.setCurrentIndex(max(0, idx))
        self.strip_w.setValue(int(s.value("strip_w", 512)))
        self.strip_h.setValue(int(s.value("strip_h", 32)))
        self.open_after.setChecked(s.value("open_after", "false") in (True, "true"))
        view = int(s.value("view", 1))
        self.seg.button(view if view in (0, 1) else 0).setChecked(True)

    def closeEvent(self, e):
        s = self.settings
        s.setValue("geometry", self.saveGeometry())
        s.setValue("target", self.target.key)
        s.setValue("strip_w", self.strip_w.value())
        s.setValue("strip_h", self.strip_h.value())
        s.setValue("open_after", self.open_after.isChecked())
        s.setValue("view", self.seg.checkedId())
        super().closeEvent(e)

    # ---- state helpers ---------------------------------------------------
    @property
    def target(self):
        return core.TARGETS_BY_KEY[self.target_box.currentData()]

    @property
    def strength_value(self):
        return self.strength.value() / 100

    def current_lut(self):
        row = self.list.currentRow()
        return self.luts[row] if 0 <= row < len(self.luts) else None

    def set_status(self, html, ms=0):
        self.status.setText(html)
        if ms:
            self._status_timer.start(ms)

    # ---- loading ---------------------------------------------------------
    def browse_luts(self):
        start = self.settings.value("open_dir", os.path.expanduser("~"))
        paths, _ = QFileDialog.getOpenFileNames(self, "Add LUT files", start, "Cube LUTs (*.cube);;All files (*)")
        if paths:
            self.settings.setValue("open_dir", os.path.dirname(paths[0]))
            self.add_luts(paths)

    def add_luts(self, paths):
        errors, added, first_new = [], 0, None
        known = {os.path.normcase(os.path.abspath(l.path)): i for i, l in enumerate(self.luts)}
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            for path in paths:
                key = os.path.normcase(os.path.abspath(path))
                if key in known:
                    first_new = known[key] if first_new is None else first_new
                    continue
                try:
                    lut = core.parse_cube(path)
                except core.LUTError as e:
                    errors.append(f"<b>{os.path.basename(path)}</b><br>{e}")
                    continue
                except Exception as e:
                    errors.append(f"<b>{os.path.basename(path)}</b><br>Unexpected error: {e}")
                    log_exception(e)
                    continue
                self.luts.append(lut)
                item = QListWidgetItem()
                item.setSizeHint(QSize(0, 52))
                item.setToolTip(path)
                self.list.addItem(item)
                self.list.setItemWidget(item, LutItem(lut))
                known[key] = len(self.luts) - 1
                first_new = len(self.luts) - 1 if first_new is None else first_new
                added += 1
        finally:
            QApplication.restoreOverrideCursor()

        if first_new is not None:
            self.list.setCurrentRow(first_new)
        if added:
            self.set_status(f"Added {added} LUT{'s' if added > 1 else ''}.", 4000)
        if errors:
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Warning)
            box.setWindowTitle("Some files couldn't be opened")
            box.setText(f"{len(errors)} file{'s' if len(errors) > 1 else ''} couldn't be read as a LUT:")
            box.setInformativeText("<br><br>".join(errors[:8]) + ("<br><br>…" if len(errors) > 8 else ""))
            box.exec()
        self.refresh()

    def remove_selected(self):
        rows = sorted({self.list.row(i) for i in self.list.selectedItems()}, reverse=True)
        if not rows and self.list.currentRow() >= 0:
            rows = [self.list.currentRow()]
        for r in rows:
            lut = self.luts.pop(r)
            self._forget(lut)
            self.list.takeItem(r)
        self.refresh()

    def clear_luts(self):
        if len(self.luts) > 3 and QMessageBox.question(
                self, "Clear list", f"Remove all {len(self.luts)} LUTs from the list?\n(Your files aren't deleted.)"
        ) != QMessageBox.Yes:
            return
        self.luts.clear()
        self.list.clear()
        self.graded_cache.clear()
        self.texture_cache.clear()
        self.refresh()

    def _forget(self, lut):
        self.graded_cache.pop(id(lut), None)
        for k in [k for k in self.texture_cache if k[0] == id(lut)]:
            del self.texture_cache[k]

    def _list_menu(self, pos):
        item = self.list.itemAt(pos)
        if not item:
            return
        lut = self.luts[self.list.row(item)]
        m = QMenu(self)
        m.addAction(icon("download"), "Export PNG…", self.export_current)
        m.addAction(icon("folder"), "Show .cube in folder", lambda: self._open_folder(os.path.dirname(lut.path)))
        m.addSeparator()
        m.addAction(icon("x"), "Remove from list", self.remove_selected)
        m.exec(self.list.mapToGlobal(pos))

    # ---- preview image ---------------------------------------------------
    def browse_preview_image(self):
        start = self.settings.value("image_dir", os.path.expanduser("~"))
        exts = " ".join(f"*{e}" for e in IMAGE_EXTS)
        path, _ = QFileDialog.getOpenFileName(self, "Choose a preview image", start, f"Images ({exts})")
        if path:
            self.settings.setValue("image_dir", os.path.dirname(path))
            self.set_preview_image(path)

    def set_preview_image(self, path):
        try:
            self.preview_src = core.load_image(path)
        except Exception as e:
            QMessageBox.warning(self, "Couldn't open image", f"{os.path.basename(path)} couldn't be opened.\n\n{e}")
            return
        self.preview_name = os.path.basename(path)
        self.graded_cache.clear()
        self._set_view(1)
        self.set_status(f"Previewing on <b>{self.preview_name}</b>.", 4000)

    def reset_preview_image(self):
        self.preview_src = core.sample_image()
        self.preview_name = "Built-in color chart"
        self.graded_cache.clear()
        self.refresh()

    # ---- drag and drop ---------------------------------------------------
    def _dropped_files(self, mime):
        if not mime.hasUrls():
            return [], []
        files = [u.toLocalFile() for u in mime.urls() if u.isLocalFile()]
        cubes, images = [], []
        for f in files:
            if os.path.isdir(f):
                cubes += [os.path.join(f, n) for n in sorted(os.listdir(f)) if n.lower().endswith(".cube")]
            elif f.lower().endswith(".cube"):
                cubes.append(f)
            elif f.lower().endswith(IMAGE_EXTS):
                images.append(f)
        return cubes, images

    def _drop_targets(self):
        return (self.center_drop,)

    def dragEnterEvent(self, e):
        cubes, images = self._dropped_files(e.mimeData())
        if cubes or images:
            e.acceptProposedAction()
            for z in self._drop_targets():
                z.set_hot(True)
            self.set_status("Drop to add LUTs" if cubes else "Drop to preview the LUT on this image")

    def dragLeaveEvent(self, e):
        for z in self._drop_targets():
            z.set_hot(False)
        self.set_status("")

    def dropEvent(self, e):
        self.dragLeaveEvent(e)
        cubes, images = self._dropped_files(e.mimeData())
        if cubes:
            self.add_luts(cubes)
        if images:
            self.set_preview_image(images[0])

    # ---- rendering -------------------------------------------------------
    def _set_view(self, i):
        self.seg.button(i).setChecked(True)
        self.refresh()

    def _strength_changed(self, v):
        self.strength_lbl.setText(f"{v}%")
        self.refresh()

    def refresh(self):
        self._render_timer.start()

    def _texture_float(self, lut, target):
        key = (id(lut), target.key, self.strip_w.value(), self.strip_h.value()) if lut else None
        grid = core.neutral_grid(target, self.strip_w.value(), self.strip_h.value())
        if lut is None:
            return grid, grid
        if key not in self.texture_cache:
            self.texture_cache[key] = lut.apply(grid)
        return grid, self.texture_cache[key]

    def build_texture(self, lut):
        grid, graded = self._texture_float(lut, self.target)
        return core.to_uint8(core.blend(grid, graded, self.strength_value))

    def _render_now(self):
        lut = self.current_lut()
        has = lut is not None
        n = len(self.luts)
        t = self.target

        self.list_stack.setCurrentIndex(1 if n else 0)
        self.list_title.setText(f"LUTS  ·  {n}" if n else "LUTS")
        self.clear_btn.setVisible(n > 0)
        self.remove_btn.setVisible(n > 0)
        for w in (self.export_btn, self.strength, self.target_box, self.strip_w, self.strip_h):
            w.setEnabled(has)
        self.export_all_btn.setEnabled(n > 0)
        self.export_all_btn.setText(f"  Export all {n} to folder…" if n > 1 else "  Export all to folder…")
        self.act_copy.setEnabled(has)
        self.strip_box.setVisible(t.is_strip)
        self.hint.setText(t.hint)
        view = self.seg.checkedId()
        self.img_btn.setVisible(has and view == 1)
        self.segbar.setVisible(has)

        if not has:
            self.view_stack.setCurrentWidget(self.center_drop)
            self.preview_caption.setText("")
            self.out_size.setText("—")
            self.out_name.setText("—")
            return

        tex = self.build_texture(lut)
        h, w, _ = tex.shape
        self.out_size.setText(f"{w} × {h} px")
        name = core.output_name(lut, t, self.strength_value)
        self.out_name.setText(self.out_name.fontMetrics().elidedText(name, Qt.ElideMiddle, 200))
        self.out_name.setToolTip(name)

        if view == 0:
            self.texture_view.set_image(to_qimage(tex))
            self.view_stack.setCurrentWidget(self.texture_view)
            self.preview_caption.setText(f"{w} × {h} px")
        else:
            if id(lut) not in self.graded_cache:
                QApplication.setOverrideCursor(Qt.WaitCursor)
                try:
                    self.graded_cache[id(lut)] = lut.apply(self.preview_src)
                finally:
                    QApplication.restoreOverrideCursor()
            after = core.blend(self.preview_src, self.graded_cache[id(lut)], self.strength_value)
            self.compare_view.set_images(to_qimage(core.to_uint8(self.preview_src)), to_qimage(core.to_uint8(after)))
            self.view_stack.setCurrentWidget(self.compare_view)
            self.preview_caption.setText(self.preview_name)

    # ---- exporting -------------------------------------------------------
    def _export_dir(self, lut=None):
        d = self.settings.value("export_dir")
        if d and os.path.isdir(d):
            return d
        return os.path.dirname(lut.path) if lut and lut.path else os.path.expanduser("~")

    def _save_png(self, arr, path):
        from PIL import Image
        Image.fromarray(arr, "RGB").save(path)

    def export_current(self):
        lut = self.current_lut()
        if not lut:
            return
        name = core.output_name(lut, self.target, self.strength_value)
        path, _ = QFileDialog.getSaveFileName(self, "Export LUT texture", os.path.join(self._export_dir(lut), name),
                                              "PNG image (*.png)")
        if not path:
            return
        if not path.lower().endswith(".png"):
            path += ".png"
        try:
            self._save_png(self.build_texture(lut), path)
        except Exception as e:
            QMessageBox.critical(self, "Couldn't save", f"The PNG couldn't be saved:\n{path}\n\n{e}")
            return
        self.settings.setValue("export_dir", os.path.dirname(path))
        self._after_export(os.path.dirname(path), f"Saved <b>{os.path.basename(path)}</b>")

    def export_all(self):
        if not self.luts:
            return
        folder = QFileDialog.getExistingDirectory(self, "Export all LUTs to…", self._export_dir(self.current_lut()))
        if not folder:
            return
        self.settings.setValue("export_dir", folder)
        jobs = [(lut, os.path.join(folder, core.output_name(lut, self.target, self.strength_value))) for lut in self.luts]

        existing = [p for _, p in jobs if os.path.exists(p)]
        if existing:
            box = QMessageBox(self)
            box.setIcon(QMessageBox.Question)
            box.setWindowTitle("Files already exist")
            box.setText(f"{len(existing)} of these files already exist in that folder.")
            replace = box.addButton("Replace them", QMessageBox.AcceptRole)
            skip = box.addButton("Skip them", QMessageBox.ActionRole)
            box.addButton(QMessageBox.Cancel)
            box.exec()
            if box.clickedButton() == skip:
                jobs = [j for j in jobs if not os.path.exists(j[1])]
                if not jobs:
                    self.set_status("Nothing to export: every file already existed.", 6000)
                    return
            elif box.clickedButton() != replace:
                return

        progress = QProgressDialog("Exporting…", "Cancel", 0, len(jobs), self)
        progress.setWindowTitle("Export all")
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(400)
        failed, done = [], 0
        for i, (lut, path) in enumerate(jobs):
            if progress.wasCanceled():
                break
            progress.setLabelText(f"Exporting {lut.name}…")
            progress.setValue(i)
            QApplication.processEvents()
            try:
                self._save_png(self.build_texture(lut), path)
                done += 1
            except Exception as e:
                failed.append(f"{os.path.basename(path)}: {e}")
        progress.setValue(len(jobs))

        if failed:
            QMessageBox.warning(self, "Some exports failed", "\n".join(failed[:10]))
        self._after_export(folder, f"Exported <b>{done}</b> texture{'s' if done != 1 else ''}")

    def save_neutral(self):
        t = self.target
        name = core.output_name(None, t)
        path, _ = QFileDialog.getSaveFileName(self, "Save neutral LUT texture", os.path.join(self._export_dir(), name),
                                              "PNG image (*.png)")
        if not path:
            return
        try:
            core.render_texture(None, t, 1, self.strip_w.value(), self.strip_h.value()).save(path)
        except Exception as e:
            QMessageBox.critical(self, "Couldn't save", str(e))
            return
        self._after_export(os.path.dirname(path), f"Saved neutral texture <b>{os.path.basename(path)}</b>")

    def _after_export(self, folder, msg):
        url = QUrl.fromLocalFile(folder).toString()
        self.set_status(f'<span style="color:{C["ok"]}">✓</span>&nbsp; {msg} &nbsp;·&nbsp; '
                        f'<a href="{url}">Show in folder</a>', 12000)
        if self.open_after.isChecked():
            self._open_folder(folder)

    def copy_texture(self):
        lut = self.current_lut()
        if not lut:
            return
        QApplication.clipboard().setImage(to_qimage(self.build_texture(lut)))
        self.set_status("Texture copied to the clipboard.", 3000)

    def _open_link(self, url):
        QDesktopServices.openUrl(QUrl(url))

    def _open_folder(self, folder):
        QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

    def about(self):
        QMessageBox.about(
            self, f"About {APP_NAME}",
            f"<h3 style='margin-bottom:4px'>{APP_NAME} {APP_VERSION}</h3>"
            "<p>Turns .cube LUT files into PNG LUT textures for game engines.</p>"
            "<p><b>Quick start</b><br>"
            "1. Drop .cube files on the window.<br>"
            "2. Pick your engine under <i>Export for</i>.<br>"
            "3. Click <i>Export PNG</i>.</p>"
            "<p><b>Shortcuts</b><br>"
            "Ctrl+O add LUTs · Ctrl+S export · Ctrl+Shift+S export all<br>"
            "Ctrl+C copy texture · Ctrl+Tab switch preview · Delete remove</p>"
            "<p>Drop any image on the window to preview a LUT on it.</p>")


# ==========================================================================
# Startup
# ==========================================================================

def log_exception(exc):
    try:
        with open(os.path.join(log_dir(), "error.log"), "a", encoding="utf-8") as f:
            f.write(f"\n--- {datetime.now():%Y-%m-%d %H:%M:%S} · {APP_NAME} {APP_VERSION}\n")
            f.write("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
    except OSError:
        pass


def excepthook(exc_type, exc, tb):
    log_exception(exc)
    try:
        QMessageBox.critical(None, "Something went wrong",
                             f"{APP_NAME} ran into an unexpected problem:\n\n{exc}\n\n"
                             f"Details were saved to:\n{os.path.join(log_dir(), 'error.log')}")
    except Exception:
        pass


def main():
    sys.excepthook = excepthook
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("LUTConverter.App")
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setStyle("Fusion")
    font = QFont()
    font.setFamilies(["Segoe UI Variable Text", "Segoe UI", "Inter", "DejaVu Sans"])
    font.setPointSizeF(9.5)
    app.setFont(font)
    style = STYLE.replace("__CHEVRON__", write_svg_file("chevron", C["muted"])) \
                 .replace("__CHECK__", write_svg_file("check", "white", 3))
    app.setStyleSheet(style)

    win = MainWindow()
    win.show()
    files = [a for a in sys.argv[1:] if os.path.isfile(a)]
    cubes = [f for f in files if f.lower().endswith(".cube")]
    if cubes:
        QTimer.singleShot(50, lambda: win.add_luts(cubes))
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
