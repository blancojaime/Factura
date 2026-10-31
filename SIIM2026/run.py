import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from siim.main import run
sys.exit(run())
