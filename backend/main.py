import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from models import SubmitRequest
import queue_manager

DOWNLOADS_DIR = Path("/app/downloads")
STATIC_DIR = Path("/app/static")

VALID_URL_PREFIXES = ("youtube.com/watch", "youtu.be/", "youtube.com/playlist")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await queue_manager.start_workers(n=2)
    yield


app = FastAPI(title="YTVenger", lifespan=lifespan)

app.mount("/downloads", StaticFiles(directory=str(DOWNLOADS_DIR)), name="downloads")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.post("/api/jobs", status_code=201)
async def submit_job(req: SubmitRequest):
    if not any(p in req.url for p in VALID_URL_PREFIXES):
        raise HTTPException(status_code=422, detail="Only YouTube URLs are accepted")

    if queue_manager.is_playlist_url(req.url):
        loop = asyncio.get_running_loop()
        try:
            urls = await loop.run_in_executor(None, queue_manager.extract_playlist_videos, req.url)
        except Exception as exc:
            raise HTTPException(status_code=422, detail=f"Failed to read playlist: {exc}")
        if not urls:
            raise HTTPException(status_code=422, detail="No videos found in playlist")
        jobs = queue_manager.create_jobs_from_urls(urls)
        return jobs

    return [queue_manager.create_job(req.url)]


@app.get("/api/jobs")
def list_jobs():
    return queue_manager.list_jobs()


@app.post("/api/jobs/cancel-all", status_code=200)
async def cancel_all_jobs():
    await queue_manager.cancel_all()
    return {"ok": True}


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    job = queue_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/")
def index():
    return FileResponse(str(STATIC_DIR / "index.html"))
