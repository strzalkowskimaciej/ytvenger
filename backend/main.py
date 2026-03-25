from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from models import SubmitRequest
import queue_manager

DOWNLOADS_DIR = Path("/app/downloads")
STATIC_DIR = Path("/app/static")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await queue_manager.start_workers(n=2)
    yield


app = FastAPI(title="YTVenger", lifespan=lifespan)

app.mount("/downloads", StaticFiles(directory=str(DOWNLOADS_DIR)), name="downloads")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.post("/api/jobs", status_code=201)
def submit_job(req: SubmitRequest):
    if "youtube.com/watch" not in req.url and "youtu.be/" not in req.url:
        raise HTTPException(status_code=422, detail="Only YouTube URLs are accepted")
    job = queue_manager.create_job(req.url)
    return job


@app.get("/api/jobs")
def list_jobs():
    return queue_manager.list_jobs()


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str):
    job = queue_manager.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/")
def index():
    return FileResponse(str(STATIC_DIR / "index.html"))
