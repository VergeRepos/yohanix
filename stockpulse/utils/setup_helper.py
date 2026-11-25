"""Cross-platform setup helper for Yohanix (supports Linux, Gentoo, macOS, Windows)."""
import os
import subprocess
import sys
from pathlib import Path

def main():
    root = Path(__file__).resolve().parent.parent.parent
    os.chdir(root)
    print("Setting up Yohanix...")

    # Ensure Python 3.12+
    v = sys.version_info
    if v < (3, 12):
        print(f"Warning: Python {v.major}.{v.minor} detected. Python 3.12+ is recommended.")

    venv_dir = root / ".venv"
    if not venv_dir.exists():
        print("Creating virtual environment (.venv)...")
        py_executable = sys.executable
        try:
            subprocess.check_call([py_executable, "-m", "venv", ".venv"])
        except Exception:
            try:
                subprocess.check_call(["python3", "-m", "venv", ".venv"])
                py_executable = "python3"
            except Exception:
                subprocess.check_call(["python", "-m", "venv", ".venv"])
                py_executable = "python"

    # Determine python/pip executable inside venv
    if os.name == "nt":
        pip_exe = venv_dir / "Scripts" / "pip.exe"
        python_exe = venv_dir / "Scripts" / "python.exe"
    else:
        pip_exe = venv_dir / "bin" / "pip"
        python_exe = venv_dir / "bin" / "python"

    print("Upgrading pip and installing dependencies...")
    try:
        subprocess.check_call([str(pip_exe), "install", "--upgrade", "pip", "setuptools", "wheel"])
        subprocess.check_call([str(pip_exe), "install", "-e", ".[dev]"])
    except Exception as e:
        print("\n[ERROR] Dependency installation failed.")
        print("On Linux / Gentoo Linux, ensure build tools and C compiler are installed:")
        print("  Gentoo: emerge --ask sys-devel/gcc dev-python/wheel dev-python/setuptools")
        print("  Ubuntu/Debian: apt-get install python3-dev build-essential")
        raise e

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
