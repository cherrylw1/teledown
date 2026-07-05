import os
import re
import asyncio
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from telethon import TelegramClient, utils
from telethon.errors import SessionPasswordNeededError
from parallel_transfer import ParallelTransferrer

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

def parse_telegram_link(link: str):
    """Parses public and private Telegram message links to extract entity and message ID."""
    # Match private channel links like t.me/c/123456789/101
    private_match = re.search(r"t\.me/c/(\d+)/(\d+)", link)
    if private_match:
        channel_id = int(private_match.group(1))
        message_id = int(private_match.group(2))
        # MTProto private channels require -100 prefix
        entity_id = int(f"-100{channel_id}")
        return entity_id, message_id

    # Match public channel links like t.me/username/101
    public_match = re.search(r"t\.me/([^/]+)/(\d+)", link)
    if public_match:
        entity = public_match.group(1)
        message_id = int(public_match.group(2))
        return entity, message_id
        
    raise ValueError("Invalid Telegram link format. Expected format: t.me/c/channel_id/message_id or t.me/username/message_id")

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

# Enable Cross-Origin Resource Sharing (CORS) for local and web frontend requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    """Health check endpoint to indicate local engine is running."""
    return {"status": "online"}

@app.get("/stream")
async def stream_file(link: str):
    """Streams a file from Telegram directly to the client without disk writing."""
    if not await client.is_user_authorized():
        raise HTTPException(
            status_code=401,
            detail="Telegram client is not authorized. Please log in first."
        )

    try:
        entity, message_id = parse_telegram_link(link)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        # Fetch the message
        message = await client.get_messages(entity, ids=message_id)
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Failed to fetch message from Telegram: {e}"
        )

    if not message or not message.media:
        raise HTTPException(
            status_code=404,
            detail="The specified message does not exist or does not contain any media file."
        )

    # Check if the media is a file/document we can download
    if not message.file:
        raise HTTPException(
            status_code=400,
            detail="The message media is not a downloadable file."
        )

    file_size = message.file.size
    file_name = message.file.name
    mime_type = message.file.mime_type or "application/octet-stream"

    if not file_name:
        ext = message.file.ext or "bin"
        file_name = f"telegram_file_{message_id}.{ext}"

    # Get the input location of the file and DC ID
    dc_id, input_location = utils.get_input_location(message.media)

    # Initialize parallel downloader connection pool
    downloader = ParallelTransferrer(client, dc_id)

    # Asynchronous generator to stream file chunks from Telegram in parallel
    async def file_sender():
        try:
            async for chunk in downloader.download(
                input_location,
                file_size
            ):
                yield chunk
        except Exception as e:
            print(f"Error while streaming media in parallel: {e}")
            raise e

    # Expose custom headers for browser downloads
    headers = {
        "Content-Length": str(file_size),
        "Content-Disposition": f'attachment; filename="{file_name}"',
        "Accept-Ranges": "bytes"
    }

    return StreamingResponse(
        file_sender(),
        media_type=mime_type,
        headers=headers
    )

@app.get("/")
async def root():
    return {"status": "ok", "authorized": await client.is_user_authorized()}
