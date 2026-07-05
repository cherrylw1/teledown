# Teledown - Telegram Stream Downloader

A lightweight, multi-threaded Telegram file streaming application. It lets you stream files from Telegram directly into your web browser without saving intermediate files on the backend disk.

## Prerequisites

- **Python 3.8+** (Tested with Python 3.13)
- **Modern Web Browser** (Chrome, Firefox, Safari, Edge) supporting Web Streams API

---

## Backend Startup Sequence

1. Navigate to the `/backend` directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment and activate it:
   - **Windows (CMD/PowerShell)**:
     ```powershell
     python -m venv venv
     .\venv\Scripts\activate
     ```
   - **macOS/Linux**:
     ```bash
     python3 -m venv venv
     source venv/bin/activate
     ```

3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the `/backend` folder with your Telegram credentials:
   ```env
   TELEGRAM_API_ID=your_api_id
   TELEGRAM_API_HASH=your_api_hash
   ```
   *(Note: You can get your API ID and HASH from [my.telegram.org](https://my.telegram.org/))*

5. Launch the FastAPI server:
   ```bash
   uvicorn main:app --reload --port 8000
   ```

### Initial Terminal Verification Flow
Upon the very first server launch (when there is no authorized session):
- The FastAPI lifespan startup handler connects to Telegram and detects an unauthorized state.
- In your terminal, you will be prompted to enter your phone number (e.g. `+1234567890`).
- Telegram will send you a login OTP code. Enter the code in the terminal when prompted.
- If two-step verification (2FA) is enabled, you will also be prompted for your password.
- Once completed, a persistent `fast_streamer_session.session` file is saved inside `/backend` and subsequent launches will bypass authentication.

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

2. Paste a valid Telegram channel or message link (e.g., `https://t.me/channel/101`) into the input field and click **Stream Download**.
3. The frontend makes loopback requests to the backend server running at `http://localhost:8000`.

---

## Stream Path Architecture & Verification

During execution, the stream flows entirely in-memory:
- **No Backend Disk Writing**: The backend processes chunks of the file as an asynchronous iterator generator and pipes it directly into the HTTP response stream. No temporary files are written to the backend disk.
- **Frontend Array Buffers**: The frontend receives incoming chunks via `response.body.getReader()`, collects them sequentially into a JavaScript array buffer in memory, compiles them into a native `Blob`, and simulates a click to download the complete file to the user's default downloads directory.
