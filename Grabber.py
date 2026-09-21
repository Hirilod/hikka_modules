# SPDX-License-Identifier: AGPL-3.0-or-later
# Safe Hikka/Heroku YouTube downloader.
# Inspired by i-execute/Modules Grabber (AGPLv3), rewritten to avoid global
# herokutl patches, public BotFather handlers, third-party uploaders and arbitrary URLs.
# meta developer: @Hirilod

__version__ = (2, 0, 0)

import asyncio
import html
import importlib.util
import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.parse import urlparse

from telethon.tl.types import Message

from .. import loader, utils

logger = logging.getLogger(__name__)

_ALLOWED_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "music.youtube.com",
    "youtu.be",
    "www.youtu.be",
    "youtube-nocookie.com",
    "www.youtube-nocookie.com",
}
_URL_RE = re.compile(r"https?://[^\s<>\"']+", re.I)
_MEDIA_EXTENSIONS = {".mp4", ".mkv", ".webm", ".mov", ".m4a", ".mp3", ".opus", ".ogg"}


def _human_bytes(value):
    if not value:
        return "—"
    value = float(value)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024 or unit == "GB":
            return f"{value:.1f} {unit}"
        value /= 1024


def _human_time(seconds):
    if seconds is None:
        return "—"
    try:
        seconds = max(0, int(seconds))
    except (TypeError, ValueError):
        return "—"
    minutes, sec = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{sec:02d}"
    return f"{minutes}:{sec:02d}"


def _parse_version(text):
    nums = re.findall(r"\d+", text or "")
    return tuple(int(x) for x in nums[:3]) if nums else ()


def _runtime_version(binary):
    path = shutil.which(binary)
    if not path:
        return None, None
    try:
        proc = subprocess.run(
            [path, "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=5,
            check=False,
        )
        line = (proc.stdout or "").splitlines()[0].strip()
        return path, line
    except Exception:
        return path, "unknown"


def _detect_js_runtimes():
    runtimes = {}
    details = []

    deno_path, deno_ver = _runtime_version("deno")
    if deno_path:
        ok = _parse_version(deno_ver) >= (2, 3)
        details.append(f"Deno: {deno_ver} ({'OK' if ok else 'too old'})")
        if ok:
            runtimes["deno"] = {"path": deno_path}

    node_path, node_ver = _runtime_version("node")
    if node_path:
        ok = _parse_version(node_ver) >= (22,)
        details.append(f"Node: {node_ver} ({'OK' if ok else 'too old'})")
        if ok:
            runtimes["node"] = {"path": node_path}

    qjs_path, qjs_ver = _runtime_version("qjs")
    if not qjs_path:
        qjs_path, qjs_ver = _runtime_version("quickjs")
    if qjs_path:
        details.append(f"QuickJS: {qjs_ver} (detected)")
        runtimes["quickjs"] = {"path": qjs_path}

    return runtimes, details


def _extract_url(text):
    match = _URL_RE.search(text or "")
    return match.group(0).rstrip(".,);]}") if match else None


def _validate_youtube_url(url):
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    if parsed.scheme not in {"http", "https"}:
        return False
    host = (parsed.hostname or "").lower().rstrip(".")
    return host in _ALLOWED_HOSTS


@loader.tds
class Grabber(loader.Module):
    """Safe YouTube downloader for Hikka/Heroku using yt-dlp."""

    strings = {
        "name": "Grabber",
        "usage": (
            "<b>Использование:</b> <code>.grab &lt;YouTube URL&gt;</code> — видео\n"
            "<code>.graba &lt;YouTube URL&gt;</code> — MP3\n"
            "URL также можно взять из сообщения, на которое отвечаете."
        ),
        "bad_url": "<b>Разрешены только ссылки YouTube / youtu.be.</b>",
        "no_ytdlp": (
            "<b>Не установлен yt-dlp.</b>\n"
            "Установи в окружение: <code>pip install -U yt-dlp yt-dlp-ejs</code>"
        ),
        "no_ffmpeg": "<b>Для этого режима нужен ffmpeg.</b>",
        "starting": "<b>Подготовка загрузки…</b>",
        "downloading": (
            "<b>Скачивание YouTube…</b>\n"
            "Прогресс: <code>{percent}</code>\n"
            "Скорость: <code>{speed}</code>\n"
            "Осталось: <code>{eta}</code>"
        ),
        "uploading": "<b>Загрузка в Telegram…</b> <code>{percent}</code>",
        "done": "<b>Готово.</b> <code>{name}</code> — {size}",
        "too_big": "<b>Файл превышает безопасный лимит {limit} МБ.</b>",
        "failed": "<b>Ошибка Grabber:</b> <code>{error}</code>",
        "diag": (
            "<b>Grabber diagnostics</b>\n"
            "yt-dlp: <code>{ytdlp}</code>\n"
            "yt-dlp-ejs: <code>{ejs}</code>\n"
            "ffmpeg: <code>{ffmpeg}</code>\n"
            "JS runtime:\n{runtime}"
        ),
    }

    def __init__(self):
        self.config = loader.ModuleConfig(
            loader.ConfigValue(
                "max_file_mb",
                1900,
                "Максимальный размер итогового файла в МБ",
                validator=loader.validators.Integer(minimum=50, maximum=3900),
            ),
            loader.ConfigValue(
                "concurrent_fragments",
                4,
                "Количество параллельно скачиваемых фрагментов",
                validator=loader.validators.Integer(minimum=1, maximum=16),
            ),
        )

    async def _get_url(self, message):
        raw = utils.get_args_raw(message)
        url = _extract_url(raw)
        if url:
            return url
        reply = await message.get_reply_message()
        if reply:
            return _extract_url(getattr(reply, "raw_text", "") or "")
        return None

    def _load_ytdlp(self):
        try:
            import yt_dlp
            return yt_dlp
        except ImportError:
            return None

    def _find_result_file(self, directory, audio):
        files = []
        for path in Path(directory).iterdir():
            if not path.is_file():
                continue
            if path.suffix.lower() not in _MEDIA_EXTENSIONS:
                continue
            if path.name.endswith((".part", ".ytdl")):
                continue
            files.append(path)
        if not files:
            return None
        if audio:
            mp3 = [p for p in files if p.suffix.lower() == ".mp3"]
            if mp3:
                return max(mp3, key=lambda p: p.stat().st_size)
        preferred = [p for p in files if p.suffix.lower() == ".mp4"]
        if preferred:
            return max(preferred, key=lambda p: p.stat().st_size)
        return max(files, key=lambda p: p.stat().st_size)

    def _download_sync(self, url, audio, directory, state):
        yt_dlp = self._load_ytdlp()
        if yt_dlp is None:
            raise RuntimeError("yt-dlp is not installed")

        max_bytes = int(self.config["max_file_mb"]) * 1024 * 1024
        js_runtimes, _ = _detect_js_runtimes()

        def progress_hook(data):
            if data.get("status") != "downloading":
                return
            downloaded = data.get("downloaded_bytes") or 0
            total = data.get("total_bytes") or data.get("total_bytes_estimate") or 0
            if downloaded > max_bytes:
                raise yt_dlp.utils.DownloadError("file exceeds configured size limit")
            state["downloaded"] = downloaded
            state["total"] = total
            state["speed"] = data.get("speed")
            state["eta"] = data.get("eta")

        common = {
            "outtmpl": os.path.join(directory, "%(title).160B [%(id)s].%(ext)s"),
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "cachedir": False,
            "retries": 5,
            "fragment_retries": 5,
            "socket_timeout": 30,
            "concurrent_fragment_downloads": int(self.config["concurrent_fragments"]),
            "max_filesize": max_bytes,
            "progress_hooks": [progress_hook],
            "windowsfilenames": True,
        }
        if js_runtimes:
            common["js_runtimes"] = js_runtimes

        if audio:
            common.update(
                {
                    "format": "bestaudio/best",
                    "postprocessors": [
                        {
                            "key": "FFmpegExtractAudio",
                            "preferredcodec": "mp3",
                            "preferredquality": "0",
                        }
                    ],
                }
            )
        else:
            if shutil.which("ffmpeg"):
                common.update(
                    {
                        "format": "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b",
                        "merge_output_format": "mp4",
                    }
                )
            else:
                common["format"] = "b[ext=mp4]/best"

        with yt_dlp.YoutubeDL(common) as ydl:
            info = ydl.extract_info(url, download=True)

        result = self._find_result_file(directory, audio)
        if result is None:
            raise RuntimeError("yt-dlp finished but output file was not found")
        if result.stat().st_size > max_bytes:
            raise RuntimeError("file exceeds configured size limit")
        return {
            "path": str(result),
            "title": info.get("title") or result.stem,
            "uploader": info.get("uploader") or info.get("channel") or "",
        }

    async def _run(self, message, audio):
        url = await self._get_url(message)
        if not url:
            return await utils.answer(message, self.strings("usage"))
        if not _validate_youtube_url(url):
            return await utils.answer(message, self.strings("bad_url"))

        yt_dlp = self._load_ytdlp()
        if yt_dlp is None:
            return await utils.answer(message, self.strings("no_ytdlp"))
        if audio and not shutil.which("ffmpeg"):
            return await utils.answer(message, self.strings("no_ffmpeg"))

        await utils.answer(message, self.strings("starting"))
        state = {"downloaded": 0, "total": 0, "speed": None, "eta": None}

        try:
            with tempfile.TemporaryDirectory(prefix="hikka_grabber_") as tmp:
                loop = asyncio.get_running_loop()
                job = loop.run_in_executor(None, self._download_sync, url, audio, tmp, state)
                last_update = 0.0

                while not job.done():
                    await asyncio.sleep(1)
                    now = time.monotonic()
                    if now - last_update < 4:
                        continue
                    total = state.get("total") or 0
                    downloaded = state.get("downloaded") or 0
                    percent = f"{downloaded / total * 100:.1f}%" if total else _human_bytes(downloaded)
                    await utils.answer(
                        message,
                        self.strings("downloading").format(
                            percent=percent,
                            speed=(f"{_human_bytes(state.get('speed'))}/s" if state.get("speed") else "—"),
                            eta=_human_time(state.get("eta")),
                        ),
                    )
                    last_update = now

                result = await job
                path = result["path"]
                size = os.path.getsize(path)
                limit = int(self.config["max_file_mb"])
                if size > limit * 1024 * 1024:
                    return await utils.answer(message, self.strings("too_big").format(limit=limit))

                upload_state = {"last": 0.0}

                async def upload_progress(current, total):
                    now = time.monotonic()
                    if now - upload_state["last"] < 4 and current != total:
                        return
                    upload_state["last"] = now
                    percent = f"{current / total * 100:.1f}%" if total else "—"
                    try:
                        await utils.answer(message, self.strings("uploading").format(percent=percent))
                    except Exception:
                        pass

                caption = html.escape(result["title"])
                if result.get("uploader"):
                    caption += f"\n{html.escape(result['uploader'])}"

                await self._client.send_file(
                    message.peer_id,
                    path,
                    caption=caption,
                    reply_to=message.reply_to_msg_id or message.id,
                    force_document=audio,
                    supports_streaming=not audio,
                    progress_callback=upload_progress,
                )

                await utils.answer(
                    message,
                    self.strings("done").format(
                        name=html.escape(os.path.basename(path)),
                        size=_human_bytes(size),
                    ),
                )
        except Exception as exc:
            logger.exception("Grabber failed")
            text = str(exc).replace("<", "&lt;").replace(">", "&gt;")
            if "size limit" in text.lower() or "max-filesize" in text.lower():
                return await utils.answer(
                    message,
                    self.strings("too_big").format(limit=int(self.config["max_file_mb"])),
                )
            return await utils.answer(message, self.strings("failed").format(error=text[:800]))

    @loader.command(ru_doc="<YouTube URL> — скачать видео")
    async def grab(self, message: Message):
        """<YouTube URL> - download video"""
        await self._run(message, audio=False)

    @loader.command(ru_doc="<YouTube URL> — скачать MP3")
    async def graba(self, message: Message):
        """<YouTube URL> - download MP3"""
        await self._run(message, audio=True)

    @loader.command(ru_doc="Проверить зависимости Grabber")
    async def grabdiag(self, message: Message):
        """Show yt-dlp/ffmpeg/JS runtime diagnostics"""
        yt_dlp = self._load_ytdlp()
        ytdlp_ver = getattr(getattr(yt_dlp, "version", None), "__version__", None) if yt_dlp else None
        ejs = "installed" if importlib.util.find_spec("yt_dlp_ejs") else "missing"
        ffmpeg = shutil.which("ffmpeg") or "missing"
        _, runtime_details = _detect_js_runtimes()
        runtime = "\n".join(f"• <code>{html.escape(x)}</code>" for x in runtime_details) or "• <code>missing</code>"
        await utils.answer(
            message,
            self.strings("diag").format(
                ytdlp=html.escape(ytdlp_ver or "missing"),
                ejs=ejs,
                ffmpeg=html.escape(ffmpeg),
                runtime=runtime,
            ),
        )
