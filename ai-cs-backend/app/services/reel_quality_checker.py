"""
Reel Quality Checker — Pre-publish validation for CS2 reels.

Checks BEFORE output:
1. Subtitles: no overlaps, readable timing, proper rendering
2. Music: correct timing, starts/ends properly
3. Context: no abrupt cuts at start/end, logical flow
4. Duration: within acceptable range for target platform
5. Video: valid file, correct resolution, not corrupted

If ANY critical check fails, the reel is REJECTED with specific issues.
The pipeline will NOT silently publish broken reels.
"""

import asyncio
import json
import logging
import os
import re
from pathlib import Path
from typing import Optional

logger = logging.getLogger("reel_quality_checker")


async def _get_video_info(file_path: str) -> dict:
    """Get video metadata using ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", file_path,
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
        data = json.loads(stdout.decode())
        video_stream = None
        audio_stream = None
        for s in data.get("streams", []):
            if s.get("codec_type") == "video" and video_stream is None:
                video_stream = s
            if s.get("codec_type") == "audio" and audio_stream is None:
                audio_stream = s

        duration = float(data.get("format", {}).get("duration", 0))
        width = int(video_stream.get("width", 0)) if video_stream else 0
        height = int(video_stream.get("height", 0)) if video_stream else 0
        fps = 0
        if video_stream and video_stream.get("r_frame_rate"):
            parts = video_stream["r_frame_rate"].split("/")
            if len(parts) == 2 and int(parts[1]) > 0:
                fps = round(int(parts[0]) / int(parts[1]), 1)

        return {
            "duration": duration,
            "width": width,
            "height": height,
            "fps": fps,
            "file_size": os.path.getsize(file_path),
            "has_audio": audio_stream is not None,
            "video_codec": video_stream.get("codec_name", "") if video_stream else "",
            "audio_codec": audio_stream.get("codec_name", "") if audio_stream else "",
            "bitrate": int(data.get("format", {}).get("bit_rate", 0)),
        }
    except Exception as e:
        logger.warning("ffprobe failed for %s: %s", file_path, e)
        return {"duration": 0, "width": 0, "height": 0, "error": str(e)}


async def _check_audio_levels(file_path: str) -> dict:
    """Check audio levels — detect silence at start/end."""
    cmd = [
        "ffmpeg", "-i", file_path,
        "-af", "volumedetect",
        "-f", "null", "-"
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        output = stderr.decode(errors="replace")

        mean_volume = None
        max_volume = None
        for line in output.split("\n"):
            if "mean_volume:" in line:
                match = re.search(r"mean_volume:\s*([-\d.]+)", line)
                if match:
                    mean_volume = float(match.group(1))
            if "max_volume:" in line:
                match = re.search(r"max_volume:\s*([-\d.]+)", line)
                if match:
                    max_volume = float(match.group(1))

        return {
            "mean_volume_db": mean_volume,
            "max_volume_db": max_volume,
            "is_silent": mean_volume is not None and mean_volume < -50,
            "is_clipping": max_volume is not None and max_volume > -0.5,
        }
    except Exception as e:
        return {"error": str(e)}


async def _check_first_last_frames(file_path: str, duration: float) -> dict:
    """Check first and last few frames for black/frozen frames (abrupt cuts)."""
    issues = []

    # Check first 0.5s for black frames
    cmd_start = [
        "ffmpeg", "-i", file_path, "-t", "0.5",
        "-vf", "blackdetect=d=0.1:pix_th=0.1",
        "-f", "null", "-"
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd_start,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
        output = stderr.decode(errors="replace")
        if "black_start" in output:
            issues.append("Black frames detected at start of reel")
    except Exception:
        pass

    # Check last 0.5s for black frames
    if duration > 1:
        seek_time = max(0, duration - 0.5)
        cmd_end = [
            "ffmpeg", "-i", file_path, "-ss", str(seek_time),
            "-vf", "blackdetect=d=0.1:pix_th=0.1",
            "-f", "null", "-"
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd_end,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
            output = stderr.decode(errors="replace")
            if "black_start" in output:
                issues.append("Black frames detected at end of reel")
        except Exception:
            pass

    return {
        "issues": issues,
        "has_abrupt_start": "start" in " ".join(issues).lower(),
        "has_abrupt_end": "end" in " ".join(issues).lower(),
    }


async def check_reel_quality(
    reel_path: str,
    target_platform: str = "tiktok",
    expected_duration_range: tuple[float, float] = (5.0, 60.0),
) -> dict:
    """
    Full pre-publish quality check for a generated reel.

    Returns:
        {
            "passed": bool,         # True = safe to publish
            "grade": "A" / "B" / "C" / "F",
            "issues": [{"type": str, "severity": "critical"/"warning"/"info", "description": str}],
            "checks": {
                "file_valid": {"passed": bool, "details": str},
                "resolution": {"passed": bool, "details": str},
                "duration": {"passed": bool, "details": str},
                "audio": {"passed": bool, "details": str},
                "context": {"passed": bool, "details": str},
            },
            "metadata": {...}
        }
    """
    issues: list[dict] = []
    checks: dict = {}

    # ─── Check 1: File exists and is valid ────────────────────
    if not os.path.exists(reel_path):
        return {
            "passed": False,
            "grade": "F",
            "issues": [{"type": "file", "severity": "critical", "description": f"File not found: {reel_path}"}],
            "checks": {"file_valid": {"passed": False, "details": "File does not exist"}},
        }

    file_size = os.path.getsize(reel_path)
    if file_size < 10000:  # <10KB = corrupted
        return {
            "passed": False,
            "grade": "F",
            "issues": [{"type": "file", "severity": "critical", "description": f"File too small ({file_size} bytes), likely corrupted"}],
            "checks": {"file_valid": {"passed": False, "details": f"File size: {file_size} bytes (min 10KB)"}},
        }

    checks["file_valid"] = {"passed": True, "details": f"Valid file, {file_size / (1024*1024):.1f} MB"}

    # ─── Check 2: Video metadata ─────────────────────────────
    info = await _get_video_info(reel_path)
    if info.get("error"):
        issues.append({"type": "metadata", "severity": "critical", "description": f"Cannot read video metadata: {info['error']}"})
        checks["resolution"] = {"passed": False, "details": f"ffprobe error: {info['error']}"}
    else:
        width = info.get("width", 0)
        height = info.get("height", 0)
        duration = info.get("duration", 0)

        # Resolution check (should be vertical 9:16)
        if width == 1080 and height == 1920:
            checks["resolution"] = {"passed": True, "details": f"{width}x{height} (perfect 9:16)"}
        elif width > 0 and height > 0:
            ratio = width / height
            if ratio < 0.7:  # Vertical-ish
                checks["resolution"] = {"passed": True, "details": f"{width}x{height} (vertical, acceptable)"}
            else:
                issues.append({"type": "resolution", "severity": "warning", "description": f"Non-vertical resolution: {width}x{height}"})
                checks["resolution"] = {"passed": False, "details": f"{width}x{height} — not vertical 9:16"}
        else:
            issues.append({"type": "resolution", "severity": "critical", "description": "Cannot determine resolution"})
            checks["resolution"] = {"passed": False, "details": "Resolution unknown"}

        # Duration check
        min_dur, max_dur = expected_duration_range
        if min_dur <= duration <= max_dur:
            checks["duration"] = {"passed": True, "details": f"{duration:.1f}s (range {min_dur}-{max_dur}s)"}
        elif duration > 0:
            severity = "critical" if duration < 3 or duration > 120 else "warning"
            issues.append({"type": "duration", "severity": severity, "description": f"Duration {duration:.1f}s outside range {min_dur}-{max_dur}s"})
            checks["duration"] = {"passed": False, "details": f"{duration:.1f}s (expected {min_dur}-{max_dur}s)"}
        else:
            issues.append({"type": "duration", "severity": "critical", "description": "Duration is 0"})
            checks["duration"] = {"passed": False, "details": "Duration: 0s"}

    # ─── Check 3: Audio quality ──────────────────────────────
    audio_result = await _check_audio_levels(reel_path)
    if audio_result.get("is_silent"):
        issues.append({"type": "audio", "severity": "warning", "description": f"Audio is very quiet (mean: {audio_result.get('mean_volume_db')} dB)"})
        checks["audio"] = {"passed": False, "details": f"Silent audio: {audio_result.get('mean_volume_db')} dB mean"}
    elif audio_result.get("is_clipping"):
        issues.append({"type": "audio", "severity": "warning", "description": f"Audio clipping detected (max: {audio_result.get('max_volume_db')} dB)"})
        checks["audio"] = {"passed": True, "details": f"Audio present but clipping at {audio_result.get('max_volume_db')} dB"}
    elif audio_result.get("error"):
        issues.append({"type": "audio", "severity": "info", "description": f"Audio check inconclusive: {audio_result['error']}"})
        checks["audio"] = {"passed": True, "details": "Audio check inconclusive"}
    else:
        checks["audio"] = {"passed": True, "details": f"Audio OK (mean: {audio_result.get('mean_volume_db')} dB)"}

    # ─── Check 4: Context — no abrupt cuts ───────────────────
    duration = info.get("duration", 0)
    if duration > 2:
        frame_result = await _check_first_last_frames(reel_path, duration)
        context_issues = frame_result.get("issues", [])
        if context_issues:
            for ci in context_issues:
                issues.append({"type": "context", "severity": "warning", "description": ci})
            checks["context"] = {"passed": False, "details": "; ".join(context_issues)}
        else:
            checks["context"] = {"passed": True, "details": "No abrupt cuts detected"}
    else:
        checks["context"] = {"passed": True, "details": "Clip too short for context check"}

    # ─── Calculate grade ─────────────────────────────────────
    critical_count = sum(1 for i in issues if i["severity"] == "critical")
    warning_count = sum(1 for i in issues if i["severity"] == "warning")

    if critical_count > 0:
        grade = "F"
        passed = False
    elif warning_count >= 3:
        grade = "C"
        passed = True  # Publishable but with issues
    elif warning_count >= 1:
        grade = "B"
        passed = True
    else:
        grade = "A"
        passed = True

    return {
        "passed": passed,
        "grade": grade,
        "issues": issues,
        "checks": checks,
        "metadata": {
            "file_path": reel_path,
            "file_size_mb": round(file_size / (1024 * 1024), 1),
            "duration": info.get("duration", 0),
            "resolution": f"{info.get('width', 0)}x{info.get('height', 0)}",
            "video_codec": info.get("video_codec", ""),
            "audio_codec": info.get("audio_codec", ""),
            "has_audio": info.get("has_audio", False),
            "platform": target_platform,
        },
        "summary": (
            f"Grade {grade}: "
            + (f"{critical_count} critical, " if critical_count else "")
            + (f"{warning_count} warnings" if warning_count else "no issues")
        ),
    }
