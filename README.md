# YTVenger

A local web app to convert YouTube videos to MP3 files using [yt-dlp](https://github.com/yt-dlp/yt-dlp).

## Features

- Paste a YouTube URL and get an MP3 download link
- Add multiple URLs while previous ones are still converting
- 2 concurrent downloads running in parallel
- MP3 files named after the video title (Windows-safe characters)
- Dark themed UI with live status updates

## Requirements

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)

## Usage

**First run (builds the Docker image):**
```bash
docker compose up --build
```

**Subsequent runs:**
```bash
docker compose up -d
```

Open **http://localhost:8000** in your browser.

**Stop the app:**
```bash
docker compose down
```

## Downloaded files

MP3 files are saved to the `downloads/` folder in the project directory.

## Updating yt-dlp

YouTube occasionally changes its internals and requires a newer version of yt-dlp. If downloads start failing, update in `backend/requirements.txt` and rebuild:

```bash
docker compose up --build
```

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12 + FastAPI |
| Downloader | yt-dlp + ffmpeg |
| Frontend | Vanilla HTML / CSS / JS |
| Deployment | Docker Compose |
