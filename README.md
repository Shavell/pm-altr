# PM-ALTR 🚀

A feature-rich, open-source **Postman alternative** built entirely in Python + PyQt6.

---

## Features

| Category | Detail |
|---|---|
| **Tabbed interface** | Open unlimited request tabs, reorder/close freely |
| **HTTP methods** | GET · POST · PUT · PATCH · DELETE · HEAD · OPTIONS |
| **Query params** | Add/remove/toggle rows in a dedicated Params table |
| **Request headers** | Fully editable key-value table per tab |
| **Body types** | `none` · `json` · `form-data` · `x-www-form-urlencoded` · `text/plain` |
| **Authentication** | None · Basic Auth · Bearer Token |
| **SSL verify toggle** | Per-tab checkbox (default in Settings) |
| **Follow redirects toggle** | Per-tab checkbox (default in Settings) |
| **Proxy support** | HTTP/HTTPS proxy config in Settings; per-tab on/off toggle |
| **cURL import** | Paste any cURL command → automatically populates all fields |
| **cURL export** | Serialises current request to cURL → copies to clipboard |
| **Response body** | Auto-prettify + syntax highlight when JSON (Pygments/Monokai) |
| **Response headers** | Dedicated Headers tab in response panel |
| **Response metrics** | Status code · response time (ms) · response size |
| **Raw view** | Full HTTP response headers + body as plain text |
| **Request history** | SQLite-backed; dockable sidebar; search; double-click to restore |
| **Network diagnostics** | DNS resolution · TCP connect time · ping RTT · packet loss |

---

## Quick Start

### 1. Clone / Download
```bash
git clone https://github.com/Shavell/pm-altr.git
cd pm-altr
```

### 2. Create virtual environment & install deps
```bash
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Run
```bash
python main.py
```

---

## Usage Guide

### Sending a request
1. Open the app — a **New Request** tab appears automatically.
2. Select the HTTP method from the dropdown.
3. Type or paste the URL.
4. Add query params in the **Params** sub-tab.
5. Add/modify headers in the **Headers** sub-tab.
6. Choose a body type in **Body** and enter your payload.
7. Click **Send**.

### Multiple tabs
Use **File → New Tab** (`Ctrl+T`) to open another request in parallel. Tabs are independent.

### Importing a cURL command
1. **cURL → Import cURL…** (`Ctrl+I`)
2. Paste your `curl` command and click OK.
3. All fields (URL, method, headers, cookies, body, auth) are populated automatically.

**Example cURL commands you can paste:**

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"name": "John Doe", "age": 30}' \
  "https://echo.free.beeceptor.com/sample-request"
```

```bash
curl "https://echo.free.beeceptor.com/sample-request?author=beeceptor"
```

```bash
curl 'https://app.beeceptor.com/api/v1/whoami' \
  -H 'accept: */*' \
  -H 'cache-control: no-cache' \
  -H 'user-agent: Mozilla/5.0'
```

### Exporting a cURL command
**cURL → Export cURL (copy)** (`Ctrl+E`) — the cURL representation of the current tab is copied to your clipboard.

### Authentication
Select the **Auth** sub-tab in the request panel:
- **Basic** — username + password (sent as `Authorization: Basic …`)
- **Bearer** — paste your token (sent as `Authorization: Bearer …`)

### Proxy
1. Open **File → Settings…** (`Ctrl+,`).
2. Configure `HTTP proxy` and/or `HTTPS proxy` URLs (e.g. `http://127.0.0.1:8080`).
3. Tick **Enable proxy** and click OK.
4. Toggle proxy per-tab with the **Use Proxy** checkbox in the request bar.

### SSL & Redirects
- **SSL Verify** — uncheck to skip certificate verification (useful for self-signed certs).
- **Follow Redirects** — uncheck to stop at the first redirect.

### History
The left **History** dock shows all past requests. Double-click any entry to restore it in a new tab. Use the search box to filter by URL or method. **Clear All** wipes the database.

Toggle visibility with **View → Toggle History** (`Ctrl+H`).

### Network Diagnostics
Every tab has a **Network Diagnostics** panel on the right side of the request area.
Click **▶ Run Diagnostics** after setting a URL (or after sending a request) to see:
- Resolved IP addresses
- DNS lookup time
- TCP connect latency
- Ping avg / min / max (ICMP if available, TCP fallback otherwise)
- Packet loss %

---

## Project Structure

```
pm-altr/
├── main.py                        # Entry point
├── requirements.txt
├── README.md
└── src/
    ├── core/
    │   ├── http_client.py         # HTTP execution, metrics, proxy, auth
    │   ├── curl_parser.py         # cURL ↔ request model conversion
    │   ├── history_manager.py     # SQLite history (stored in ~/.pm-altr/)
    │   └── network_diagnostics.py # DNS/TCP/ping diagnostics
    └── ui/
        ├── main_window.py         # QMainWindow, tab management, menus
        ├── request_panel.py       # URL bar, params, headers, body, auth
        ├── response_panel.py      # Metrics, prettified body, headers, raw
        ├── network_debug_panel.py # Diagnostics runner
        ├── history_panel.py       # Dockable history list
        └── settings_dialog.py     # Proxy + default settings
```

---

## Dependencies

| Package | Purpose |
|---|---|
| `PyQt6` | GUI framework |
| `requests` | HTTP client |
| `pygments` | Syntax highlighting for JSON responses |
| `ping3` | ICMP ping for network diagnostics |
| `dnspython` | Advanced DNS utilities |

Install all with:
```bash
pip install -r requirements.txt
```

---

## Building a Single Binary

You can package PM-ALTR into a standalone executable using [PyInstaller](https://pyinstaller.org/).

### 1. Install PyInstaller
```bash
source venv/bin/activate
pip install pyinstaller
```

### 2. Build
```bash
# macOS
pyinstaller pm-altr.spec --clean --noconfirm

# Windows
pyinstaller pm-altr-win.spec --clean --noconfirm
```

### 3. Output

| Platform | Output | Description |
|---|---|---|
| macOS | `dist/pm-altr` | Single executable binary |
| macOS | `dist/PM-ALTR.app` | macOS app bundle (Finder) |
| Windows | `dist/pm-altr.exe` | Single executable (.exe) |

### 4. Run
```bash
# macOS — standalone binary
./dist/pm-altr

# macOS — app bundle
open dist/PM-ALTR.app

# Windows
dist\pm-altr.exe
```

> **Note:** The `pm-altr.spec` file is pre-configured with `console=False` (no terminal window) and `upx=True` (compression enabled). The `dist/` and `build/` directories are excluded via `.gitignore`.

---

## CI/CD

Two GitHub Actions workflows are included:

| Workflow | Trigger | What it does |
|---|---|---|
| **CI** (`ci.yml`) | Push/PR to `main` | Lint (flake8), verify imports, test cURL parser — on Python 3.11/3.12/3.13 |
| **Release** (`release.yml`) | Push a tag `v*` | Build binaries for macOS + Windows + Linux, create GitHub Release with artifacts |

### Creating a release

```bash
git tag v1.0.0
git push origin v1.0.0
```

This automatically builds all three platforms and publishes the binaries as a GitHub Release.

---

## Data Storage

History and settings are persisted at:
```
~/.pm-altr/
├── history.db       # Request/response history (SQLite)
├── settings.json    # Proxy, SSL, redirect preferences
└── tabs.json        # Last open tabs (restored on startup)
```

---

## License

MIT
