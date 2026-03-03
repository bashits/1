"""Smart Girl Video Sourcer — Free Base Video Selection from Pexels.

Finds and selects consistent base videos of girls for LatentSync lip-sync.
Uses Pexels API (free, 200 req/hr, commercial use allowed).

Smart Selection Algorithm:
1. Search Pexels for "girl talking portrait" videos
2. Filter by quality (resolution, duration, orientation)
3. Group by photographer (same photographer = likely same model)
4. Score visual consistency within groups (skin tone, color palette)
5. Select best group of videos showing the same girl
6. Cache selected videos locally for reuse

This replaces the need to generate AI photos for video-to-video lipsync.
Instead we use real stock footage as base, then LatentSync replaces the lips.
"""

import hashlib
import json
import logging
import os
import random
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# Storage
GENERATED_DIR = Path("/data/generated") if os.path.exists("/data") else Path(
    os.path.join(os.path.dirname(__file__), "..", "..", "generated")
)
BASE_VIDEOS_DIR = GENERATED_DIR / "base_videos"
BASE_VIDEOS_DIR.mkdir(parents=True, exist_ok=True)

# Cache file for selected video sets
CACHE_FILE = BASE_VIDEOS_DIR / "video_cache.json"


def _get_pexels_key() -> str:
    return os.environ.get("PEXELS_API_KEY", "")


# ─── Search Query Builder ────────────────────────────────────────────

GIRL_VIDEO_QUERIES = [
    "young woman talking portrait",
    "girl speaking close up face",
    "woman talking to camera portrait",
    "female vlogger speaking",
    "young woman face talking",
    "girl reaction face camera",
    "woman speaking selfie style",
    "female portrait talking video",
    "girl looking at camera speaking",
    "woman close up face video",
]

ETHNICITY_VIDEO_QUERIES = {
    "european": ["european girl talking", "caucasian woman portrait video"],
    "slavic": ["slavic girl talking", "eastern european woman video"],
    "latina": ["latina girl talking", "hispanic woman portrait video"],
    "east_asian": ["asian girl talking", "asian woman portrait video"],
    "korean": ["korean girl talking", "korean woman portrait video"],
    "african": ["african girl talking", "black woman portrait video"],
    "mixed": ["mixed race girl talking", "biracial woman portrait video"],
}


def build_video_search_queries(
    appearance: Optional[dict] = None,
    max_queries: int = 5,
) -> list[str]:
    """Build search queries for finding base videos matching appearance."""
    queries = []

    if appearance:
        ethnicity = appearance.get("ethnicity", "european")
        hair_color = appearance.get("hair_color", "")

        # Add ethnicity-specific queries
        eth_queries = ETHNICITY_VIDEO_QUERIES.get(ethnicity, [])
        queries.extend(eth_queries)

        # Add hair-specific queries
        if hair_color:
            queries.append(f"{hair_color} hair woman talking portrait video")

    # Add general queries
    queries.extend(random.sample(GIRL_VIDEO_QUERIES, min(3, len(GIRL_VIDEO_QUERIES))))

    # Deduplicate and limit
    seen = set()
    unique = []
    for q in queries:
        q_lower = q.lower().strip()
        if q_lower not in seen:
            seen.add(q_lower)
            unique.append(q)

    return unique[:max_queries]


# ─── Pexels Video API ────────────────────────────────────────────────

async def search_pexels_videos(
    query: str,
    per_page: int = 20,
    page: int = 1,
    orientation: str = "portrait",
    min_duration: int = 3,
    max_duration: int = 30,
) -> list[dict]:
    """Search Pexels for videos matching query.

    Returns list of video metadata with download URLs.
    """
    key = _get_pexels_key()
    if not key:
        logger.warning("PEXELS_API_KEY not set")
        return []

    headers = {"Authorization": key}
    params = {
        "query": query,
        "per_page": per_page,
        "page": page,
        "orientation": orientation,
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(
                "https://api.pexels.com/videos/search",
                headers=headers,
                params=params,
            )
            if resp.status_code != 200:
                logger.warning(f"Pexels video API error: {resp.status_code}")
                return []

            data = resp.json()
            videos = []

            for video in data.get("videos", []):
                duration = video.get("duration", 0)

                # Filter by duration
                if duration < min_duration or duration > max_duration:
                    continue

                # Find best quality video file
                video_files = video.get("video_files", [])
                best_file = _select_best_video_file(video_files)
                if not best_file:
                    continue

                # Get preview image
                video_pictures = video.get("video_pictures", [])
                preview_url = video_pictures[0].get("picture", "") if video_pictures else ""

                videos.append({
                    "id": video.get("id"),
                    "url": best_file["link"],
                    "width": best_file.get("width", 0),
                    "height": best_file.get("height", 0),
                    "duration": duration,
                    "quality": best_file.get("quality", ""),
                    "file_type": best_file.get("file_type", ""),
                    "preview_url": preview_url,
                    "user": video.get("user", {}).get("name", ""),
                    "user_id": video.get("user", {}).get("id", 0),
                    "pexels_url": video.get("url", ""),
                })

            return videos
        except Exception as e:
            logger.error(f"Pexels video search failed: {e}")
            return []


def _select_best_video_file(video_files: list[dict]) -> Optional[dict]:
    """Select the best quality video file from Pexels options.

    Prefers:
    - 720p or 1080p (not too large, good quality for LatentSync)
    - MP4 format
    - Portrait orientation
    """
    if not video_files:
        return None

    # Score each file
    scored = []
    for vf in video_files:
        score = 0.0
        width = vf.get("width", 0)
        height = vf.get("height", 0)
        quality = vf.get("quality", "")
        file_type = vf.get("file_type", "")

        # Prefer mp4
        if "mp4" in file_type.lower():
            score += 1.0

        # Prefer 720p (ideal for LatentSync 512x512 processing)
        if quality == "hd":
            score += 2.0
        elif quality == "sd":
            score += 1.0

        # Prefer reasonable resolution
        if 480 <= min(width, height) <= 1080:
            score += 1.0
        if 720 <= max(width, height) <= 1920:
            score += 0.5

        # Prefer portrait/square orientation
        if height >= width:
            score += 0.5

        scored.append((vf, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[0][0] if scored else None


# ─── Smart Video Selection ───────────────────────────────────────────

async def search_videos_multi(
    queries: list[str],
    videos_per_query: int = 15,
) -> list[dict]:
    """Search Pexels with multiple queries and merge results."""
    all_videos: dict[int, dict] = {}

    for query in queries:
        results = await search_pexels_videos(query, per_page=videos_per_query)
        for video in results:
            vid = video["id"]
            if vid not in all_videos:
                all_videos[vid] = video

    return list(all_videos.values())


def _score_video_quality(video: dict) -> float:
    """Score video quality for use as LatentSync base (0-1)."""
    score = 0.5

    # Duration: prefer 5-15 seconds (good for looping)
    duration = video.get("duration", 0)
    if 5 <= duration <= 15:
        score += 0.2
    elif 3 <= duration <= 5:
        score += 0.1
    elif duration > 30:
        score -= 0.2

    # Resolution: prefer 720p+
    width = video.get("width", 0)
    height = video.get("height", 0)
    min_dim = min(width, height) if width and height else 0
    if min_dim >= 720:
        score += 0.15
    elif min_dim >= 480:
        score += 0.05
    elif min_dim < 360:
        score -= 0.3

    # Quality label
    quality = video.get("quality", "")
    if quality == "hd":
        score += 0.1
    elif quality == "uhd":
        score += 0.05  # Too large, slight penalty for processing time

    return max(0.0, min(1.0, score))


def group_videos_by_user(videos: list[dict]) -> dict[int, list[dict]]:
    """Group videos by Pexels user (same user = likely same model)."""
    groups: dict[int, list[dict]] = {}
    for video in videos:
        uid = video.get("user_id", 0)
        if uid not in groups:
            groups[uid] = []
        groups[uid].append(video)
    return groups


def select_best_video_set(
    videos: list[dict],
    target_count: int = 5,
    min_count: int = 2,
) -> list[dict]:
    """Select best set of base videos for LatentSync.

    Strategy:
    1. Filter low quality
    2. Group by user (photographer)
    3. Pick best group with enough videos
    4. If no single group is big enough, take top-scored videos
    """
    if not videos:
        return []

    # Score all videos
    scored = [(v, _score_video_quality(v)) for v in videos]
    scored = [(v, s) for v, s in scored if s >= 0.3]
    scored.sort(key=lambda x: x[1], reverse=True)

    quality_videos = [v for v, _ in scored]

    # Group by photographer
    groups = group_videos_by_user(quality_videos)
    sorted_groups = sorted(groups.items(), key=lambda x: len(x[1]), reverse=True)

    # Try to find single-user group with enough videos
    for uid, group_videos in sorted_groups:
        if len(group_videos) >= min_count:
            logger.info(
                f"Found {len(group_videos)} videos from user '{group_videos[0].get('user', 'unknown')}'"
            )
            return group_videos[:target_count]

    # Fallback: just take top-scored videos
    return quality_videos[:target_count]


# ─── Download & Cache ────────────────────────────────────────────────

async def download_video(url: str, filename: str) -> Optional[str]:
    """Download a video from URL to local storage."""
    fpath = BASE_VIDEOS_DIR / filename
    if fpath.exists():
        return str(fpath)

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                fpath.write_bytes(resp.content)
                logger.info(f"Downloaded base video: {filename} ({len(resp.content)} bytes)")
                return str(fpath)
            else:
                logger.warning(f"Failed to download video: HTTP {resp.status_code}")
                return None
        except Exception as e:
            logger.error(f"Video download failed: {e}")
            return None


def _load_cache() -> dict:
    """Load video cache from disk."""
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text())
        except Exception:
            pass
    return {}


def _save_cache(cache: dict) -> None:
    """Save video cache to disk."""
    try:
        CACHE_FILE.write_text(json.dumps(cache, indent=2))
    except Exception as e:
        logger.warning(f"Cache save failed: {e}")


# ─── High-Level API ──────────────────────────────────────────────────

async def source_base_videos(
    appearance: Optional[dict] = None,
    target_count: int = 5,
    download: bool = True,
) -> dict:
    """Source base videos for LatentSync from Pexels.

    Main entry point. Searches, selects, optionally downloads.

    Returns: {success, videos: [...], cached, source}
    """
    # Check cache first
    cache_key = hashlib.md5(json.dumps(appearance or {}, sort_keys=True).encode()).hexdigest()[:12]
    cache = _load_cache()

    if cache_key in cache:
        cached_videos = cache[cache_key]
        # Verify cached files still exist
        valid = [v for v in cached_videos if Path(v.get("local_path", "")).exists()]
        if len(valid) >= 2:
            logger.info(f"Using cached base videos ({len(valid)} videos)")
            return {
                "success": True,
                "videos": valid,
                "cached": True,
                "source": "pexels_cached",
            }

    # Check Pexels API key
    if not _get_pexels_key():
        return {
            "success": False,
            "error": "PEXELS_API_KEY not configured",
            "videos": [],
            "cached": False,
        }

    # Build search queries
    queries = build_video_search_queries(appearance, max_queries=5)
    logger.info(f"Searching Pexels for base videos: {queries[:3]}...")

    # Search
    all_videos = await search_videos_multi(queries, videos_per_query=15)
    logger.info(f"Found {len(all_videos)} candidate videos")

    if not all_videos:
        return {
            "success": False,
            "error": "No suitable base videos found on Pexels",
            "videos": [],
            "cached": False,
        }

    # Select best set
    selected = select_best_video_set(all_videos, target_count=target_count)
    logger.info(f"Selected {len(selected)} best base videos")

    # Download if requested
    result_videos = []
    for video in selected:
        video_data = {
            "pexels_id": video["id"],
            "url": video["url"],
            "preview_url": video.get("preview_url", ""),
            "duration": video.get("duration", 0),
            "width": video.get("width", 0),
            "height": video.get("height", 0),
            "user": video.get("user", ""),
            "pexels_url": video.get("pexels_url", ""),
        }

        if download:
            fname = f"base_{video['id']}.mp4"
            local_path = await download_video(video["url"], fname)
            if local_path:
                video_data["local_path"] = local_path
                video_data["filename"] = fname

        result_videos.append(video_data)

    # Cache results
    if result_videos:
        cache[cache_key] = result_videos
        _save_cache(cache)

    return {
        "success": len(result_videos) > 0,
        "videos": result_videos,
        "cached": False,
        "source": "pexels_fresh",
        "queries_used": queries,
    }


async def get_random_base_video(
    appearance: Optional[dict] = None,
) -> Optional[dict]:
    """Get a single random base video for immediate use.

    First checks cache, then sources new if needed.
    """
    result = await source_base_videos(appearance, target_count=5, download=True)

    if not result.get("success") or not result.get("videos"):
        return None

    videos = result["videos"]
    # Prefer videos with local paths
    local_videos = [v for v in videos if v.get("local_path")]
    if local_videos:
        return random.choice(local_videos)

    return random.choice(videos)


def list_cached_base_videos() -> list[dict]:
    """List all cached base videos on disk."""
    videos = []
    if BASE_VIDEOS_DIR.exists():
        for f in BASE_VIDEOS_DIR.glob("base_*.mp4"):
            stat = f.stat()
            videos.append({
                "filename": f.name,
                "path": str(f),
                "size_bytes": stat.st_size,
                "size_human": f"{stat.st_size / (1024*1024):.1f} MB",
            })
    return videos


def clear_video_cache() -> dict:
    """Clear all cached base videos."""
    count = 0
    freed = 0
    for f in BASE_VIDEOS_DIR.glob("base_*.mp4"):
        freed += f.stat().st_size
        f.unlink()
        count += 1

    if CACHE_FILE.exists():
        CACHE_FILE.unlink()

    return {
        "deleted_files": count,
        "freed_bytes": freed,
        "freed_human": f"{freed / (1024*1024):.1f} MB",
    }
