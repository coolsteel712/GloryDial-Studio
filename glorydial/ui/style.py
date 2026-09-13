"""A clean, modern dark theme (with a light variant) for GloryDial Studio.

Deliberately not a Java-Swing-style look: flat surfaces, a single
accent color, generous spacing, and system-native fonts.
"""

from __future__ import annotations

ACCENT = "#5B8DEF"
ACCENT_HOVER = "#7BA3F5"

DARK_QSS = f"""
QMainWindow, QDialog {{
    background-color: #1e1f24;
    color: #e6e6e9;
}}
QWidget {{
    background-color: #1e1f24;
    color: #e6e6e9;
    font-family: "Segoe UI", "Inter", "Helvetica Neue", sans-serif;
    font-size: 13px;
}}
QDockWidget {{
    titlebar-close-icon: none;
    color: #b8b9c0;
}}
QDockWidget::title {{
    background-color: #26272e;
    padding: 6px 8px;
    font-weight: 600;
    border-bottom: 1px solid #33343c;
}}
QToolBar {{
    background-color: #23242a;
    border: none;
    padding: 4px;
    spacing: 4px;
}}
QToolBar QToolButton {{
    background: transparent;
    border-radius: 6px;
    padding: 6px;
}}
QToolBar QToolButton:hover {{
    background-color: #33343c;
}}
QToolBar QToolButton:pressed, QToolBar QToolButton:checked {{
    background-color: {ACCENT};
}}
QMenuBar {{
    background-color: #23242a;
    color: #e6e6e9;
}}
QMenuBar::item:selected {{
    background-color: #33343c;
}}
QMenu {{
    background-color: #26272e;
    border: 1px solid #33343c;
    padding: 4px;
}}
QMenu::item {{
    padding: 5px 24px 5px 12px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background-color: {ACCENT};
}}
QStatusBar {{
    background-color: #23242a;
    color: #9a9ba3;
    border-top: 1px solid #33343c;
}}
QTreeWidget, QListWidget, QTableWidget {{
    background-color: #26272e;
    border: 1px solid #33343c;
    border-radius: 6px;
    alternate-background-color: #2a2b32;
}}
QTreeWidget::item, QListWidget::item {{
    padding: 4px;
    border-radius: 4px;
}}
QTreeWidget::item:selected, QListWidget::item:selected {{
    background-color: {ACCENT};
    color: white;
}}
QHeaderView::section {{
    background-color: #26272e;
    color: #9a9ba3;
    padding: 4px;
    border: none;
    border-bottom: 1px solid #33343c;
}}
QGroupBox {{
    border: 1px solid #33343c;
    border-radius: 8px;
    margin-top: 12px;
    padding-top: 12px;
    font-weight: 600;
    color: #b8b9c0;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}}
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTimeEdit, QDateEdit {{
    background-color: #26272e;
    border: 1px solid #3a3b44;
    border-radius: 6px;
    padding: 4px 8px;
    selection-background-color: {ACCENT};
}}
QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
    border: 1px solid {ACCENT};
}}
QPushButton {{
    background-color: #33343c;
    border: 1px solid #3f4049;
    border-radius: 6px;
    padding: 6px 14px;
}}
QPushButton:hover {{
    background-color: #3a3b44;
}}
QPushButton:pressed {{
    background-color: {ACCENT};
}}
QPushButton#primary {{
    background-color: {ACCENT};
    border: none;
    font-weight: 600;
}}
QPushButton#primary:hover {{
    background-color: {ACCENT_HOVER};
}}
QSlider::groove:horizontal {{
    height: 4px;
    background: #3a3b44;
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {ACCENT};
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border-radius: 4px;
    border: 1px solid #4a4b54;
    background: #26272e;
}}
QCheckBox::indicator:checked {{
    background: {ACCENT};
    border: 1px solid {ACCENT};
}}
QTabWidget::pane {{
    border: 1px solid #33343c;
    border-radius: 6px;
}}
QTabBar::tab {{
    background: #26272e;
    padding: 6px 14px;
    margin-right: 2px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
}}
QTabBar::tab:selected {{
    background: {ACCENT};
    color: white;
}}
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
}}
QScrollBar::handle:vertical {{
    background: #3f4049;
    border-radius: 5px;
    min-height: 24px;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
}}
QScrollBar::handle:horizontal {{
    background: #3f4049;
    border-radius: 5px;
    min-width: 24px;
}}
QSplitter::handle {{
    background-color: #1e1f24;
}}
"""
