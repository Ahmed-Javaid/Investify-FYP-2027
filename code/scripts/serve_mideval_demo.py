"""Launch the local mid-eval demo without installing training/UI dependencies."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from investify.demo_server import main

if __name__ == "__main__":
    main()
