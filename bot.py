import asyncio
import logging
import os
import re
import tempfile

import yt_dlp
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO
)
log = logging.getLogger("tiktok-bot")

# ቶከኑ ከ Railway Variables ይነበባል (በኮድ ውስጥ አትጻፈው)
TOKEN = os.environ["9264557363:AAFs404U3AJkvjPaLFNo0UqO1NGMqvDOAvQ"]

# ቴሌግራም ቦቶች መላክ የሚችሉት ከፍተኛ መጠን: 50 MB
MAX_BYTES = 50 * 1024 * 1024

# የ TikTok ሊንክ መለያ
URL_RE = re.compile(r"https?://(?:[\w-]+\.)?tiktok\.com/\S+", re.I)


def download_video(url: str, outdir: str) -> tuple[str, str]:
    """ቪዲዮውን አውርዶ የፋይሉን አድራሻና መግለጫ ይመልሳል"""
    opts = {
        "outtmpl": os.path.join(outdir, "%(id)s.%(ext)s"),
        "format": "best[ext=mp4][filesize<50M]/best[ext=mp4]/best",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "socket_timeout": 30,
        "max_filesize": MAX_BYTES,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return ydl.prepare_filename(info), (info.get("description") or "")[:900]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start ሲላክ የሚሰጥ ምላሽ"""
    await update.message.reply_text(
        "👋 ሰላም! የ TikTok ሊንክ ላክልኝ፤ ቪዲዮውን አወርድልሃለሁ።"
    )


async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """የተላከውን ሊንክ ፈልጎ ቪዲዮውን ያወርዳል"""
    match = URL_RE.search(update.message.text or "")
    if not match:
        await update.message.reply_text("⚠️ እባክህ ትክክለኛ የ TikTok ሊንክ ላክ።")
        return

    status = await update.message.reply_text("⏳ በማውረድ ላይ…")
    await update.message.chat.send_action(ChatAction.UPLOAD_VIDEO)

    try:
        with tempfile.TemporaryDirectory() as tmp:
            path, caption = await asyncio.to_thread(
                download_video, match.group(0), tmp
            )
            if not os.path.exists(path) or os.path.getsize(path) > MAX_BYTES:
                raise ValueError("ፋይሉ የለም ወይም ከ 50 MB በላይ ነው")
            with open(path, "rb") as f:
                await update.message.reply_video(
                    video=f,
                    caption=caption or None,
                    supports_streaming=True,
                    read_timeout=120,
                    write_timeout=120,
                )
        await status.delete()
    except Exception as e:
        log.exception("ማውረድ አልተሳካም: %s", e)
        await status.edit_text(
            "❌ ይህን ቪዲዮ ማውረድ አልተቻለም። ቪዲዮው የግል (private)፣ የተሰረዘ ወይም በጣም ትልቅ ሊሆን ይችላል።"
        )


def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
    log.info("ቦቱ ተነስቷል")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
