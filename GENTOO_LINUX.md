# Yohanix on Gentoo Linux & Linux

This guide provides specific instructions for setting up and running **Yohanix** on **Gentoo Linux** and other Linux distributions.

---

## 1. Prerequisites on Gentoo Linux

Since Gentoo is a source-based distribution, ensure you have Python 3.12+, GCC, Python development headers, and Node.js installed via Portage:

```bash
# 1. Install Python 3.12+ and build tools
emerge --ask dev-lang/python dev-python/pip sys-devel/gcc dev-python/wheel

# 2. Install Node.js (with npm) for the web UI dashboard
emerge --ask net-libs/nodejs
```

*Note: Ensure your Python use flags include `sqlite` and `ssl` (enabled by default in Gentoo profiles).*

---

## 2. Automated Setup

Clone the repository and run `make setup`:

```bash
git clone https://github.com/NightBaRron1412/yohanix.git
cd yohanix

# Create virtual environment, install Python dependencies, and set up config/directories
make setup

# Install Node.js dependencies for the web UI
make all
```

---

## 3. Configuration

1. Copy or edit `.env`:
   ```bash
   cp .env.example .env
   ```
2. Get a free API key at [Finnhub](https://finnhub.io).
3. Set your API key in `.env`:
   ```env
   FINNHUB_API_KEY=your_actual_finnhub_key_here
   ```
4. Validate your setup:
   ```bash
   make check
   ```

---

## 4. Running Yohanix on Linux / Gentoo

### Run a One-Shot S&P 500 Scan
```bash
make run
```

### Start the FastAPI Backend & Web UI
- **Backend API (Port 18000):**
  ```bash
  make api
  ```
- **Web UI Dashboard (Port 3003):**
  ```bash
  make ui
  ```

---

## 5. Running as a Gentoo OpenRC Service

Yohanix includes built-in OpenRC support for Gentoo Linux.

1. Generate the OpenRC init script template:
   ```bash
   make install-service
   ```
2. This creates `yohanix.initd` in your project directory. Copy it to `/etc/init.d/` and make it executable:
   ```bash
   sudo cp yohanix.initd /etc/init.d/yohanix
   sudo chmod +x /etc/init.d/yohanix
   ```
3. Edit `/etc/init.d/yohanix` if needed to point to your absolute project directory and virtualenv python path.
4. Add Yohanix to the default runlevel and start the service:
   ```bash
   sudo rc-update add yohanix default
   sudo rc-service yohanix start
   ```
5. Check service status:
   ```bash
   sudo rc-service yohanix status
   ```

---

## Troubleshooting

- **Python Command Missing**: If `python` command is not found on your Gentoo system, `make setup` automatically tries `python3`, `python3.12`, or `python3.13`.
- **C Extension Compilation Errors**: If `scipy` or `pandas-ta` fail to build from source via pip, ensure `sys-devel/gcc`, `dev-python/wheel`, and Python dev headers (`dev-lang/python:3.12`) are installed on your Gentoo system.
