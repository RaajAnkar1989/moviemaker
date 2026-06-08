import subprocess
import sys
from pathlib import Path


def create_bundle():
    script = Path(__file__).resolve().parent / "scripts" / "build_dmg.sh"
    subprocess.check_call(["bash", str(script)])


if __name__ == "__main__":
    create_bundle()
