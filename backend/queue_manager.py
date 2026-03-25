import asyncio
import uuid
import yt_dlp
from datetime import datetime, timezone
from pathlib import Path
from models import Job, JobStatus

_jobs: dict[str, Job] = {}
_queue: asyncio.Queue[str] = asyncio.Queue()

DOWNLOADS_DIR = Path("/app/downloads")
MAX_CONCURRENT_WORKERS = 2


def create_job(url: str) -> Job:
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
    except Exception as exc:
        job.status = JobStatus.ERROR
        job.error = str(exc)
        job.updated_at = datetime.now(timezone.utc)


def _download_sync(job: Job):
    job_dir = DOWNLOADS_DIR / job.id
    job_dir.mkdir(parents=True, exist_ok=True)
    output_template = str(job_dir / "%(title)s.%(ext)s")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "quiet": False,
        "no_warnings": False,
        "noplaylist": True,
        "windowsfilenames": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(job.url, download=True)
        job.title = info.get("title", "Unknown")

    matches = list(job_dir.glob("*.mp3"))
    if not matches:
        raise FileNotFoundError("MP3 file not found after download")

    # Store as relative path: {job_id}/{filename.mp3}
    job.filename = f"{job.id}/{matches[0].name}"
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
