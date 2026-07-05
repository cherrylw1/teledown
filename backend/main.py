import os
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

# Resolve paths
BACKEND_DIR = Path(__file__).resolve().parent
ENV_PATH = BACKEND_DIR / ".env"
SESSION_PATH = BACKEND_DIR / "fast_streamer_session"

# Load env variables
load_dotenv(dotenv_path=ENV_PATH)

API_ID_STR = os.getenv("TELEGRAM_API_ID")
API_HASH = os.getenv("TELEGRAM_API_HASH")

if not API_ID_STR or not API_HASH:
    raise RuntimeError(
        "Missing configuration: TELEGRAM_API_ID and TELEGRAM_API_HASH "
        "must be set in the .env file."
    )

try:
    API_ID = int(API_ID_STR)
except ValueError as e:
    raise RuntimeError(
        f"Invalid TELEGRAM_API_ID: '{API_ID_STR}' is not an integer."
    ) from e

# Initialize Telethon TelegramClient
# Session path specifies where the .session file will be written
client = TelegramClient(str(SESSION_PATH), API_ID, API_HASH)

async def interactive_auth():
    """Handles terminal-based interactive authentication with Telethon."""
    # Ensure client is connected
    if not client.is_connected():
        await client.connect()

    if not await client.is_user_authorized():
        print("\n--- Telegram Authentication Required ---")
        # Prompt for phone number
        phone = await asyncio.to_thread(
            input, "Please enter your Telegram phone number (with country code): "
        )
        phone = phone.strip()
        
        # Request verification code
        print(f"Requesting login code for {phone}...")
        try:
            await client.send_code_request(phone)
        except Exception as e:
            print(f"Failed to send code: {e}")
            raise e

        # Prompt for verification code
        code = await asyncio.to_thread(
            input, "Please enter the OTP verification code sent by Telegram: "
        )
        code = code.strip()

        try:
            await client.sign_in(phone, code)
            print("Successfully signed in!")
        except SessionPasswordNeededError:
            # Handle 2FA password if enabled
            password = await asyncio.to_thread(
                input, "Two-step verification (2FA) is enabled. Please enter your password: "
            )
            await client.sign_in(password=password)
            print("Successfully signed in with 2FA!")
        except Exception as e:
            print(f"Authentication failed: {e}")
            raise e
    else:
        print("Telegram client is already authorized.")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Connect and authenticate client on startup
    print("Starting up FastAPI application...")
    await client.connect()
    await interactive_auth()
    
    yield
    
    # Disconnect client on shutdown
    print("Shutting down FastAPI application...")
    await client.disconnect()

app = FastAPI(lifespan=lifespan)

@app.get("/")
async def root():
    return {"status": "ok", "authorized": await client.is_user_authorized()}
