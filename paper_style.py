"""Portable publication typography, with the manuscript's Palatino family."""
from pathlib import Path
import importlib.util


def serif_family():
    return 'Palatino Linotype' if (Path('C:/Windows/Fonts')/'pala.ttf').exists() else 'STIXGeneral'


def register_fonts():
    from PySide6.QtGui import QFontDatabase
    for name in ['pala.ttf','palab.ttf','palai.ttf','palabi.ttf']:
        path=Path('C:/Windows/Fonts')/name
        if path.exists():QFontDatabase.addApplicationFont(str(path))
    spec=importlib.util.find_spec('matplotlib')
    if spec and spec.origin:
        folder=Path(spec.origin).parent/'mpl-data/fonts/ttf'
        for path in folder.glob('STIXGeneral*.ttf'):QFontDatabase.addApplicationFont(str(path))
    return serif_family()
