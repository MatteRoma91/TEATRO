"""QSS scuro in stile TeatroApp."""

from teatro.constants import BG, DIM, GOLD, PANEL, TXT


def rgb_css(t: tuple[float, float, float]) -> str:
    r, g, b = (int(255 * x) for x in t)
    return f"rgb({r},{g},{b})"


def app_stylesheet() -> str:
    return f"""
    QWidget {{
        background-color: {rgb_css(BG)};
        color: {rgb_css(TXT)};
        font-size: 13px;
    }}
    QPushButton {{
        background-color: {rgb_css(PANEL)};
        color: {rgb_css(TXT)};
        border: 1px solid #333;
        padding: 6px 10px;
        border-radius: 4px;
    }}
    QPushButton:hover {{
        border-color: {rgb_css(GOLD)};
    }}
    QPushButton:pressed {{
        background-color: #1a1b22;
    }}
    QListWidget {{
        background-color: {rgb_css(PANEL)};
        color: {rgb_css(TXT)};
        border: 1px solid #333;
        font-size: 14px;
    }}
    QListWidget::item:selected {{
        background-color: #2a3140;
        color: {rgb_css(GOLD)};
    }}
    QLabel.title {{
        font-size: 20px;
        font-weight: bold;
        color: {rgb_css(GOLD)};
    }}
    QLabel.hint {{
        color: {rgb_css(DIM)};
        font-size: 11px;
    }}
    QLineEdit, QTextEdit, QPlainTextEdit {{
        background-color: {rgb_css(PANEL)};
        color: {rgb_css(TXT)};
        border: 1px solid #333;
        padding: 4px;
    }}
    QDialog {{
        background-color: {rgb_css(BG)};
    }}
    """
