"""Cross-platform setup helper for Yohanix."""
import os
import subprocess
import sys
from pathlib import Path

def main():
    root = Path(__file__).resolve().parent.parent.parent
    os.chdir(root)
    print("Setting up Yohanix...")

    venv_dir = root / ".venv"
    if not venv_dir.exists():
        print("Creating virtual environment (.venv)...")
        subprocess.check_call([sys.executable, "-m", "venv", ".venv"])

    # Determine python/pip executable inside venv
    if os.name == "nt":
        pip_exe = venv_dir / "Scripts" / "pip.exe"
    else:
        pip_exe = venv_dir / "bin" / "pip"

    print("Installing dependencies...")
    subprocess.check_call([str(pip_exe), "install", "--upgrade", "pip"])
    subprocess.check_call([str(pip_exe), "install", "-e", ".[dev]"])

    env_file = root / ".env"
    env_example = root / ".env.example"
    if not env_file.exists() and env_example.exists():
        print("Creating .env from .env.example...")
        env_file.write_text(env_example.read_text())

    for d in ["reports", "json", "logs", ".cache/data"]:
        (root / "outputs" / d).mkdir(parents=True, exist_ok=True)

    print("\nSetup complete! Next steps:")
    print("  1. Get a free API key at https://finnhub.io")
    print("  2. Edit .env and set FINNHUB_API_KEY=your_key")
    print("  3. Run 'make check' (or python -m stockpulse.utils.validate_setup) to validate your setup")
    print("  4. Run 'make run' for a one-shot scan")

if __name__ == "__main__":
    main()
