"""FringeScope identity; importable before NumPy, SciPy and Matplotlib."""
from pathlib import Path
import importlib.util

NAME = 'FringeScope'
SUBTITLE = 'Time-resolved step-scan FTIR artifact simulator'
VERSION = '0.11.0'
ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / 'assets'
BG, PANEL, LINE = '#1d242c', '#13171c', '#2f3843'
TEXT, MUTED, AMBER = '#dde3ea', '#8e9aa8', '#f2b24c'
BLUE, GREEN, CORAL = '#6fa8ff', '#6cc58a', '#ff7a66'
FONT = 'DejaVu Sans'


def ensure_fonts():
    """Find bundled fonts without importing Matplotlib during early startup."""
    from PySide6.QtGui import QFontDatabase
    spec = importlib.util.find_spec('matplotlib')
    if spec and spec.origin:
        folder = Path(spec.origin).parent / 'mpl-data/fonts/ttf'
        for name in ('DejaVuSans.ttf', 'DejaVuSans-Bold.ttf'):
            QFontDatabase.addApplicationFont(str(folder / name))


def icon():
    from PySide6.QtGui import QIcon
    from PySide6.QtCore import QSize
    result = QIcon()
    for size in (16,20,24,32,48,64,128,256):
        result.addFile(str(ASSETS / f'fringescope_{size}.png'), QSize(size,size))
    return result
