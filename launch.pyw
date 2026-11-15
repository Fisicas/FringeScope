"""Windows entry point: open a new log, then show the early Qt splash."""
from pathlib import Path
from datetime import datetime
import sys,traceback

from runtime_paths import user_dir
logs=user_dir()/'logs';logs.mkdir(exist_ok=True)
log=(logs/('session_'+datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'.log')).open('w',encoding='utf-8',buffering=1)
sys.stdout=log;sys.stderr=log
try:
    from startup import main
    sys.exit(main())
except Exception:
    traceback.print_exc()
    raise
