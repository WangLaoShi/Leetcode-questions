import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from qb.inventory import build_inventory

if __name__ == "__main__":
    build_inventory()
