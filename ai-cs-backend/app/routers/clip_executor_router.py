"""Clip Executor Router — Real video clipping endpoints.

Endpoints for downloading, processing, and managing video clips:
- Download Twitch clips
- Process clips with FFmpeg (vertical, overlays, effects)
- Generate test clips
- Batch process streamer clips
- Serve processed files
- Set Twitch API credentials
"""

import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
import aiosqlite

from app.database import get_db
from app.services.clip_executor import (
    download_twitch_clip,
    process_clip,
    generate_test_clip,
    execute_clip_from_moment,
    batch_process_streamer,
    get_twitch_clips,
    get_executor_status,
    CLIPS_DIR,
)

router = APIRouter(prefix="/api/clip-executor", tags=["clip-executor"])


# ─── Schemas ─────────────────────────────────────────────────────────
class DownloadRequest(BaseModel):
    url: str
    output_name: Optional[str] = None


class ProcessRequest(BaseModel):
    source_path: str
    hook_text: Optional[str] = None
    hook_duration: float = 3.0
    cta_text: Optional[str] = None
    cta_start_offset: float = 4.0
    subtitle_text: Optional[str] = None
    color_grade: str = "none"
    max_duration: float = 60.0
    target_width: int = 1080
    target_height: int = 1920
    fps: int = 30
    volume_boost: float = 1.2


class TestClipRequest(BaseModel):
    twitch_url: str
    hook_text: str = "WAIT FOR IT..."
    cta_text: str = "Follow for daily CS2 highlights!"
    subtitle_text: str = "Insane play"
    color_grade: str = "cinematic"
    max_duration: float = 30.0


class MomentClipRequest(BaseModel):
    moment_id: int
    template_format: str = "highlight_subtitles"
    hook_text: Optional[str] = None
    cta_text: Optional[str] = None


class BatchRequest(BaseModel):
    broadcaster_name: str
    limit: int = 5
    period: str = "7d"
    template: str = "highlight_subtitles"


class TwitchCredentials(BaseModel):
    client_id: str
    client_secret: str


class TwitchClipsRequest(BaseModel):
    broadcaster_name: str
    period: str = "24h"
    limit: int = 20


# ─── Status ──────────────────────────────────────────────────────────
@router.get("/status")
async def executor_status():
    """Get clip executor status: available tools, configured APIs, file counts."""
    return get_executor_status()


# ─── Set Twitch API Credentials ──────────────────────────────────────
@router.post("/set-twitch-credentials")
async def set_twitch_credentials(creds: TwitchCredentials):
    """Set Twitch API credentials for clip discovery."""
    import app.services.clip_executor as ce

    ce.TWITCH_CLIENT_ID = creds.client_id
    ce.TWITCH_CLIENT_SECRET = creds.client_secret
    ce._twitch_token_cache.clear()
    os.environ["TWITCH_CLIENT_ID"] = creds.client_id
    os.environ["TWITCH_CLIENT_SECRET"] = creds.client_secret

    # Persist to SQLite
    from app.database import DB_PATH
    db = await aiosqlite.connect(DB_PATH)
    await db.execute(
        "INSERT INTO settings (key, value, updated_at) VALUES ('twitch_client_id', ?, datetime('now')) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=datetime('now')",
        (creds.client_id,),
    )
    await db.execute(
        "INSERT INTO settings (key, value, updated_at) VALUES ('twitch_client_secret', ?, datetime('now')) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=datetime('now')",
        (creds.client_secret,),
    )
    await db.commit()
    await db.close()

    return {"success": True, "message": "Twitch credentials saved and activated"}


# ─── Discover Clips from Twitch ─────────────────────────────────────
@router.post("/discover-clips")
async def discover_clips(req: TwitchClipsRequest):
    """Get top clips from a Twitch channel (requires Twitch API credentials)."""
    clips = await get_twitch_clips(
        broadcaster_name=req.broadcaster_name,
        period=req.period,
        limit=req.limit,
    )
    if not clips:
        raise HTTPException(
            status_code=400,
            detail="No clips found. Check streamer name or configure Twitch API credentials first.",
        )
    return {"clips": clips, "total": len(clips), "broadcaster": req.broadcaster_name}


# ─── Download ────────────────────────────────────────────────────────
@router.post("/download")
async def download_clip(req: DownloadRequest):
    """Download a video from Twitch URL using yt-dlp."""
    result = await download_twitch_clip(req.url, req.output_name)
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Download failed"))
    return result


# ─── Process ─────────────────────────────────────────────────────────
@router.post("/process")
async def process_clip_endpoint(req: ProcessRequest):
    """Process a downloaded video: crop to vertical, add overlays, effects."""
    if not os.path.exists(req.source_path):
        raise HTTPException(status_code=404, detail="Source file not found")

    result = await process_clip(
        source_path=req.source_path,
        hook_text=req.hook_text,
        hook_duration=req.hook_duration,
        cta_text=req.cta_text,
        cta_start_offset=req.cta_start_offset,
        subtitle_text=req.subtitle_text,
        color_grade=req.color_grade,
        max_duration=req.max_duration,
        target_width=req.target_width,
        target_height=req.target_height,
        fps=req.fps,
        volume_boost=req.volume_boost,
    )
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Processing failed"))
    return result


# ─── Test Clip (one-shot: URL → processed clip) ─────────────────────
@router.post("/test-clip")
async def test_clip(req: TestClipRequest):
    """
    Quick test: download a Twitch clip URL and process it into a vertical clip.
    Returns the processed file path and metadata.
    """
    result = await generate_test_clip(
        twitch_url=req.twitch_url,
        hook_text=req.hook_text,
        cta_text=req.cta_text,
        subtitle_text=req.subtitle_text,
        color_grade=req.color_grade,
        max_duration=req.max_duration,
    )
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Test clip generation failed"))
    return result


# ─── Execute from Moment (DB-driven) ────────────────────────────────
@router.post("/execute-moment")
async def execute_moment_clip(
    req: MomentClipRequest,
    db: aiosqlite.Connection = Depends(get_db),
):
    """
    Execute full clipping pipeline for a detected moment:
    Download source → Process → Save to DB → Return clip.
    """
    result = await execute_clip_from_moment(
        db=db,
        moment_id=req.moment_id,
        template_format=req.template_format,
        hook_text=req.hook_text,
        cta_text=req.cta_text,
    )
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Clip execution failed"))
    return result


# ─── Batch Process ───────────────────────────────────────────────────
@router.post("/batch-process")
async def batch_process(req: BatchRequest):
    """
    Batch process: get top clips from a Twitch streamer, download and process all.
    Requires Twitch API credentials.
    """
    result = await batch_process_streamer(
        broadcaster_name=req.broadcaster_name,
        limit=req.limit,
        period=req.period,
        template=req.template,
    )
    return result


# ─── File Serving ────────────────────────────────────────────────────
@router.get("/files/{file_type}/{filename}")
async def serve_clip_file(file_type: str, filename: str):
    """Serve a clip file (source/processed/thumbnails)."""
    if file_type not in ("source", "processed", "thumbnails"):
        raise HTTPException(status_code=400, detail="Invalid file type")

    file_path = CLIPS_DIR / file_type / filename
    if not file_path.resolve().is_relative_to((CLIPS_DIR / file_type).resolve()):
        raise HTTPException(status_code=400, detail="Invalid filename")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    media_types = {
        "source": "video/mp4",
        "processed": "video/mp4",
        "thumbnails": "image/jpeg",
    }

    return FileResponse(str(file_path), media_type=media_types.get(file_type, "application/octet-stream"))


# ─── List Processed Clips ───────────────────────────────────────────
@router.get("/processed-clips")
async def list_processed_clips():
    """List all processed clip files."""
    clips = []
    processed_dir = CLIPS_DIR / "processed"
    if processed_dir.exists():
        for f in sorted(processed_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
            if f.is_file() and f.suffix == ".mp4":
                # Check for thumbnail
                thumb = CLIPS_DIR / "thumbnails" / f"{f.stem}.jpg"
                clips.append({
                    "filename": f.name,
                    "file_path": str(f),
                    "size_bytes": f.stat().st_size,
                    "created_at": f.stat().st_mtime,
                    "video_url": f"/api/clip-executor/files/processed/{f.name}",
                    "thumbnail_url": f"/api/clip-executor/files/thumbnails/{f.stem}.jpg" if thumb.exists() else None,
                })
    return {"clips": clips, "total": len(clips)}
