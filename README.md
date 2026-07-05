# Teledown - Telegram Stream Downloader

A lightweight, multi-threaded Telegram file streaming application. It lets you stream files from Telegram directly into your web browser without saving intermediate files on the backend disk.

## Prerequisites

- **Python 3.8+**
- **Modern Web Browser** (Chrome, Firefox, Safari, Edge) supporting Web Streams API

---

## One-Click Startup Automation

We provide cross-platform scripts in the root directory to automate virtual environment setup, package installations, and booting the server on port 8000:

- **Windows**:
  Simply double-click the **`start.bat`** file in the project root, or execute:
  ```cmd
  start.bat
  ```

- **macOS / Linux**:
  Make the shell script executable first, then run it:
  ```bash
  chmod +x start.sh
  ./start.sh
  ```

### Startup Handshake & Verification Flow
On the first server launch:
- The script automatically checks for and creates a Python virtual environment (`venv/`), installs dependencies, and boots the FastAPI server on port 8000.
- If a session does not exist, the startup lifespan handler will ask you for your **phone number** (including country code) and the **Telegram login OTP** directly in the terminal to authorize the Telethon connection.
- After login, a persistent `.session` file is saved inside `/backend` and subsequent launches will bypass authentication.

---

## Frontend Testing Step

1. To test the frontend locally:
   - Open `/frontend/index.html` directly in your web browser, or
   - Start a simple HTTP server in the `/frontend` directory:
     ```bash
     cd frontend
     python -m http.server 8080
     ```
     Then navigate to `http://localhost:8080`.

2. The top-right corner of the UI card will display a status badge:
   - **`● Local Engine Connected` (Green)**: The local FastAPI server is online and responding.
   - **`● Local Engine Offline` (Red)**: The local FastAPI server is offline. Run the `start` script to launch it.

3. Paste a valid Telegram channel or message link (e.g., `https://t.me/channel/101`) into the input field and click **Stream Download**. The browser will request the file from the backend and initiate a direct browser stream download.

---

## Stream Path Architecture

During execution, the stream flows entirely in-memory:
- **No Backend Disk Writing**: The backend processes chunks of the file as an asynchronous iterator generator and pipes it directly into the HTTP response stream. No temporary files are written to the backend disk.
- **Frontend Stream Redirection**: The frontend updates the button to a success state and redirects the browser window location to the `/stream` endpoint. The browser's native download manager intercepts the stream chunk-by-chunk and saves it to disk with zero JS RAM overhead, avoiding tab crashes on large (>2GB) downloads.
