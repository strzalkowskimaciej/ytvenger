import asyncio
import uuid
import yt_dlp
from datetime import datetime, timezone
from pathlib import Path
from models import Job, JobStatus

_jobs: dict[str, Job] = {}
_queue: asyncio.Queue[str] = asyncio.Queue()
_jobs_to_cancel: set[str] = set()

DOWNLOADS_DIR = Path("/app/downloads")
MAX_CONCURRENT_WORKERS = 2


class _DownloadCancelled(Exception):
    pass


def _make_job(url: str) -> Job:
    job = Job(
        id=str(uuid.uuid4()),
        url=url,
        status=JobStatus.QUEUED,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    _jobs[job.id] = job
    _queue.put_nowait(job.id)
    return job


def create_job(url: str) -> Job:
    return _make_job(url)


def is_playlist_url(url: str) -> bool:
    return "list=" in url


def extract_playlist_videos(url: str) -> list[str]:
    """Extract individual video URLs from a playlist (no download). Blocking — run in executor."""
    ydl_opts = {
        "quiet": True,
        "extract_flat": "in_playlist",
        "noplaylist": False,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if info.get("_type") == "playlist":
        return [
            f"https://www.youtube.com/watch?v={entry['id']}"
            for entry in info.get("entries", [])
            if entry and entry.get("id")
        ]
    return [url]


def create_jobs_from_urls(urls: list[str]) -> list[Job]:
    return [_make_job(url) for url in urls]


def get_job(job_id: str) -> Job | None:
    return _jobs.get(job_id)


def list_jobs() -> list[Job]:
    return sorted(_jobs.values(), key=lambda j: j.created_at, reverse=True)


async def _process_job(job_id: str):
    job = _jobs[job_id]
    job.status = JobStatus.DOWNLOADING
    job.updated_at = datetime.now(timezone.utc)

    loop = asyncio.get_running_loop()
    try:
        await loop.run_in_executor(None, _download_sync, job)
    except _DownloadCancelled:
        job.status = JobStatus.CANCELLED
        job.updated_at = datetime.now(timezone.utc)
    except Exception as exc:
        job.status = JobStatus.ERROR
        job.error = str(exc)
        job.updated_at = datetime.now(timezone.utc)
    finally:
        _jobs_to_cancel.discard(job.id)


def _download_sync(job: Job):
    output_template = str(DOWNLOADS_DIR / "%(title)s.%(ext)s")
    pre_download_path: list[Path] = []

    def progress_hook(info: dict):
        if job.id in _jobs_to_cancel:
            raise _DownloadCancelled()
        if info.get("status") == "finished" and info.get("filename"):
            pre_download_path.append(Path(info["filename"]))

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "progress_hooks": [progress_hook],
        "quiet": False,
        "no_warnings": False,
        "noplaylist": True,
        "windowsfilenames": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(job.url, download=True)
        job.title = info.get("title", "Unknown")

    if not pre_download_path:
        raise FileNotFoundError("MP3 file not found after download")

    mp3_path = pre_download_path[-1].with_suffix(".mp3")
    if not mp3_path.exists():
        raise FileNotFoundError(f"Expected MP3 not found: {mp3_path.name}")

    job.filename = mp3_path.name
    job.status = JobStatus.DONE
    job.updated_at = datetime.now(timezone.utc)


async def worker():
    while True:
        job_id = await _queue.get()
        try:
            await _process_job(job_id)
        finally:
            _queue.task_done()


async def start_workers(n: int = MAX_CONCURRENT_WORKERS):
    for _ in range(n):
        asyncio.create_task(worker())


async def cancel_all():
    now = datetime.now(timezone.utc)

    # Cancel jobs waiting in queue
    while not _queue.empty():
        try:
            job_id = _queue.get_nowait()
            _queue.task_done()
            job = _jobs.get(job_id)
            if job and job.status == JobStatus.QUEUED:
                job.status = JobStatus.CANCELLED
                job.updated_at = now
        except asyncio.QueueEmpty:
            break

    # Signal active downloads to stop
    for job in _jobs.values():
        if job.status == JobStatus.DOWNLOADING:
            _jobs_to_cancel.add(job.id)
