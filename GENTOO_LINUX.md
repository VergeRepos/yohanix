# Yohanix on Gentoo Linux & Linux

This guide provides specific instructions for setting up, running, and accessing **Yohanix** on **Gentoo Linux** and other Linux distributions — including access from your phone over local Wi-Fi.

---

## 1. Prerequisites on Gentoo Linux

Since Gentoo is a source-based distribution, ensure you have Python 3.12+, GCC, Python development headers, and Node.js installed via Portage:

```bash
# 1. Install Python 3.12+ and build tools
emerge --ask dev-lang/python dev-python/pip sys-devel/gcc dev-python/wheel

# 2. Install Node.js (with npm) for the web UI dashboard
emerge --ask net-libs/nodejs
```

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

## 4. Running Yohanix & Accessing from Your Phone

To access StockPulse from your phone while your laptop is running on the same Wi-Fi network:

1. **Find your laptop's local IP address**:
   - On Linux / Gentoo: `ip addr show` or `hostname -I` (e.g. `192.168.1.50`)
   - On Windows: `ipconfig`

2. **Start the Backend API (Port 18000)**:
   ```bash
   make api
   ```
   *(Binds to `0.0.0.0`, accessible across your local network).*

3. **Start the Web UI Dashboard (Port 3003)**:
   ```bash
   make ui
   ```
   *(Configured to bind to `0.0.0.0` and automatically route API requests to your laptop's local IP).*

4. **Open on your Phone**:
   - Connect your phone to the same Wi-Fi network.
   - Open your mobile browser and go to:
     ```text
     http://<YOUR_LAPTOP_IP>:3003
     ```
     *(Example: `http://192.168.1.50:3003`)*

---

## 5. Running as a Gentoo OpenRC Service

Yohanix includes built-in OpenRC support for Gentoo Linux.

1. Generate the OpenRC init script template:
   ```bash
   make install-service
   ```
2. Copy it to `/etc/init.d/` and make it executable:
   ```bash
   sudo cp yohanix.initd /etc/init.d/yohanix
   sudo chmod +x /etc/init.d/yohanix
   ```
3. Add Yohanix to the default runlevel and start the service:
   ```bash
   sudo rc-update add yohanix default
   sudo rc-service yohanix start
   ```

---

## Troubleshooting

- **Python Command Missing**: If `python` command is not found on your Gentoo system, `make setup` automatically tries `python3`, `python3.12`, or `python3.13`.
- **Phone Connection Issues**: Ensure both your laptop and phone are on the same Wi-Fi network, and that your laptop's firewall (e.g., `iptables`, `nftables`, `ufw`, or Gentoo `iptables-services`) allows inbound connections on ports `3003` and `18000`.
