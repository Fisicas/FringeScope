"""Writable per-user state is separate from immutable installed resources."""
import os
from pathlib import Path

def user_dir():
    folder=Path(os.environ.get('LOCALAPPDATA',Path.home()/'AppData/Local'))/'FringeScope'
    folder.mkdir(parents=True,exist_ok=True)
    return folder

def export_parent():
    folder=user_dir()/'exports';folder.mkdir(exist_ok=True)
    return folder
