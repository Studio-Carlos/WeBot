# Webot

**Webot** is a smart, minimalist desktop application designed to monitor ticket availability on websites that use Cloudflare protection. It uses your real browser (Arc) in the background to bypass bot detection, ensuring you never miss a ticket drop.

![Status](https://img.shields.io/badge/Status-Active-green)
![Python](https://img.shields.io/badge/Python-3.11+-blue)

## Features

- **Real Browser Automation**: Uses your installed Arc browser to bypass Cloudflare and bot detection naturally.
- **Background Operation**: Runs silently in the background without stealing focus or interrupting your work.
- **Modern Interface**: Clean, dark-mode GUI built with `customtkinter`.
- **Smart Detection**: automatically pauses for manual intervention if Cloudflare challenges appear.
- **Multi-Channel Alerts**:
    - Mobile Push Notifications (via [ntfy.sh](https://ntfy.sh))
    - Native macOS Desktop Notifications
    - System Sound Alerts
- **Configurable**: Easily change target URLs, notification topics, and refresh intervals.

## Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/yourusername/webot.git
    cd webot
    ```

2.  **Install requirements**:
    ```bash
    pip install -r requirements.txt
    ```

3.  **System Permissions**:
    - Grant **Accessibility** permissions to your Terminal/IDE (VS Code, Cursor, iTerm) to allow AppleScript to control the browser.
    - Go to `System Settings` > `Privacy & Security` > `Accessibility`.

## Usage

1.  Run the application:
    ```bash
    python Webot.py
    ```

2.  **Configure**:
    - Enter the **Target URL** of the ticket page.
    - Set your **Ntfy Topic** (e.g., `mytickets123`).
    - Adjust **Min/Max Delay** to randomize check intervals.

3.  **Start**:
    - Click **START MONITOR**.
    - If Arc is not open, it will launch in the background.
    - **Important**: If prompted by Cloudflare, switch to Arc, click the checkbox, and the bot will resume automatically.

## Requirements

- macOS
- Arc Browser
- Python 3.11+
- `customtkinter`, `requests`

## License

MIT License
