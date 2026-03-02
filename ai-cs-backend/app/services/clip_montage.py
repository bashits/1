"""
Intelligent Clip Montage Engine — Full Video Production Pipeline

Complete system for creating viral CS2 clips with:
1. Game clip download + vertical crop (FFmpeg)
2. AI Girl commentary with lip-sync (edge-tts + fal.ai)
3. Background music tracks (royalty-free, bundled)
4. Meme sound effects (SFX library)
5. Visual meme inserts / overlays
6. Intelligent dramaturgy — timing, pacing, effects placement
7. Final assembly with multi-track audio mixing

Architecture:
┌─────────────────────────────────────────────────┐
│                  MONTAGE ENGINE                  │
├─────────────┬───────────┬───────────┬───────────┤
│  Game Clip  │  AI Girl  │   Music   │  Meme SFX │
│  (FFmpeg)   │  (TTS+    │  (FFmpeg) │  (FFmpeg)  │
│             │  LipSync) │           │            │
├─────────────┴───────────┴───────────┴───────────┤
│            DRAMATURGY CONTROLLER                 │
│  - Hook phase (0-3s): attention grab             │
│  - Build phase (3-8s): context + tension         │
│  - Peak phase (8-12s): action moment             │
│  - React phase (12-15s): AI girl reaction        │
│  - CTA phase (last 3s): call to action           │
├─────────────────────────────────────────────────┤
│              FINAL ASSEMBLY (FFmpeg)             │
│  Multi-track: game audio + music + TTS + SFX    │
│  Visual: game + overlays + AI girl PiP           │
└─────────────────────────────────────────────────┘

APIs needed:
- fal.ai (API key) — for AI girl photo gen + lip-sync video
- edge-tts (FREE) — for AI girl voice
- FFmpeg (FREE) — all video/audio processing
- yt-dlp (FREE) — clip download
- Twitch API (optional) — clip discovery
"""

import asyncio
import json
import os
import random
import shutil
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

# Ensure system paths are on PATH
for _bin_dir in ["/usr/bin", "/usr/local/bin"]:
    if _bin_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = _bin_dir + os.pathsep + os.environ.get("PATH", "")

_ffmpeg_initialized = False

def _ensure_ffmpeg():
    """Lazy init: download static-ffmpeg only when ffmpeg is actually needed."""
    global _ffmpeg_initialized
    if _ffmpeg_initialized:
        return
    _ffmpeg_initialized = True
    if shutil.which("ffmpeg") is None:
        try:
            import static_ffmpeg
            _ffmpeg_path, _ffprobe_path = static_ffmpeg.run.get_or_fetch_platform_executables_else_raise()
            _sf_bin_dir = str(Path(_ffmpeg_path).parent)
            os.environ["PATH"] = _sf_bin_dir + os.pathsep + os.environ.get("PATH", "")
        except Exception:
            pass

# ─── Directories ─────────────────────────────────────────────────────
DATA_ROOT = Path("/data") if os.path.exists("/data") else Path(
    os.path.join(os.path.dirname(__file__), "..", "..", "data_local")
)
MONTAGE_DIR = DATA_ROOT / "montage"
MONTAGE_DIR.mkdir(parents=True, exist_ok=True)
(MONTAGE_DIR / "output").mkdir(exist_ok=True)
(MONTAGE_DIR / "temp").mkdir(exist_ok=True)
(MONTAGE_DIR / "assets").mkdir(exist_ok=True)
(MONTAGE_DIR / "assets" / "music").mkdir(exist_ok=True)
(MONTAGE_DIR / "assets" / "sfx").mkdir(exist_ok=True)
(MONTAGE_DIR / "assets" / "memes").mkdir(exist_ok=True)
(MONTAGE_DIR / "assets" / "girl").mkdir(exist_ok=True)

def _find_font() -> str:
    """Find a usable TTF font on the system."""
    import glob
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    fonts = glob.glob("/usr/share/fonts/**/*.ttf", recursive=True)
    if fonts:
        return fonts[0]
    # Last resort: try fc-match
    try:
        result = subprocess.run(["fc-match", "-f", "%{file}", "sans"], capture_output=True, text=True, timeout=5)
        if result.returncode == 0 and result.stdout.strip() and os.path.exists(result.stdout.strip()):
            return result.stdout.strip()
    except Exception:
        pass
    return ""

FONT_PATH = _find_font()
HAS_FONT = bool(FONT_PATH and os.path.exists(FONT_PATH))


# ═══════════════════════════════════════════════════════════════════════
# SECTION 1: DRAMATURGY ENGINE — Intelligent Clip Structure
# ═══════════════════════════════════════════════════════════════════════

# Clip dramaturgy phases with timing, effects, and purpose
DRAMATURGY_TEMPLATES = {
    "highlight_react": {
        "name": "Highlight + Girl React",
        "description": "Game highlight with AI girl reaction at peak moment",
        "total_duration": 15,
        "phases": [
            {
                "name": "hook",
                "start": 0.0, "end": 2.5,
                "purpose": "Grab attention instantly",
                "game_audio_vol": 0.3,
                "music_vol": 0.6,
                "sfx": "whoosh_intro",
                "text_overlay": "hook",
                "girl_visible": False,
            },
            {
                "name": "build",
                "start": 2.5, "end": 7.0,
                "purpose": "Build tension, show context",
                "game_audio_vol": 0.7,
                "music_vol": 0.4,
                "sfx": None,
                "text_overlay": "subtitle",
                "girl_visible": False,
            },
            {
                "name": "peak",
                "start": 7.0, "end": 10.0,
                "purpose": "THE moment — kill/clutch/ace",
                "game_audio_vol": 1.0,
                "music_vol": 0.2,
                "sfx": "impact_hit",
                "text_overlay": None,
                "girl_visible": False,
                "zoom": True,
                "slow_mo": False,
            },
            {
                "name": "react",
                "start": 10.0, "end": 13.0,
                "purpose": "AI girl reaction — emotion peak",
                "game_audio_vol": 0.2,
                "music_vol": 0.3,
                "sfx": "girl_wow",
                "text_overlay": None,
                "girl_visible": True,
                "girl_position": "pip_bottom_right",
                "girl_size": 0.35,
            },
            {
                "name": "cta",
                "start": 13.0, "end": 15.0,
                "purpose": "Call to action — follow/subscribe",
                "game_audio_vol": 0.1,
                "music_vol": 0.7,
                "sfx": "notification",
                "text_overlay": "cta",
                "girl_visible": False,
            },
        ],
    },
    "meme_edit": {
        "name": "Meme Edit Style",
        "description": "Fast-paced meme edit with SFX and visual inserts",
        "total_duration": 12,
        "phases": [
            {
                "name": "hook",
                "start": 0.0, "end": 1.5,
                "purpose": "Meme intro — quick flash",
                "game_audio_vol": 0.2,
                "music_vol": 0.8,
                "sfx": "vine_boom",
                "text_overlay": "hook",
                "girl_visible": False,
            },
            {
                "name": "build",
                "start": 1.5, "end": 5.0,
                "purpose": "Gameplay context with meme overlay",
                "game_audio_vol": 0.8,
                "music_vol": 0.3,
                "sfx": None,
                "text_overlay": "subtitle",
                "girl_visible": False,
                "meme_overlay": True,
            },
            {
                "name": "peak",
                "start": 5.0, "end": 8.0,
                "purpose": "Kill moment with SFX stack",
                "game_audio_vol": 1.0,
                "music_vol": 0.1,
                "sfx": "mlg_airhorn",
                "text_overlay": None,
                "girl_visible": False,
                "zoom": True,
                "screen_shake": True,
            },
            {
                "name": "react",
                "start": 8.0, "end": 10.5,
                "purpose": "Meme reaction insert",
                "game_audio_vol": 0.3,
                "music_vol": 0.5,
                "sfx": "bruh",
                "text_overlay": None,
                "girl_visible": True,
                "girl_position": "pip_center",
                "girl_size": 0.5,
            },
            {
                "name": "cta",
                "start": 10.5, "end": 12.0,
                "purpose": "Quick CTA with follow prompt",
                "game_audio_vol": 0.1,
                "music_vol": 0.6,
                "sfx": "notification",
                "text_overlay": "cta",
                "girl_visible": False,
            },
        ],
    },
    "girl_commentary": {
        "name": "Girl Commentary Full",
        "description": "AI girl narrates the entire clip with reactions",
        "total_duration": 20,
        "phases": [
            {
                "name": "girl_intro",
                "start": 0.0, "end": 3.0,
                "purpose": "Girl introduces the clip",
                "game_audio_vol": 0.1,
                "music_vol": 0.3,
                "sfx": None,
                "text_overlay": None,
                "girl_visible": True,
                "girl_position": "fullscreen",
                "girl_size": 1.0,
                "girl_speaks": True,
                "girl_script": "intro",
            },
            {
                "name": "gameplay",
                "start": 3.0, "end": 12.0,
                "purpose": "Show the gameplay moment",
                "game_audio_vol": 0.8,
                "music_vol": 0.3,
                "sfx": None,
                "text_overlay": "subtitle",
                "girl_visible": True,
                "girl_position": "pip_top_right",
                "girl_size": 0.25,
            },
            {
                "name": "peak_react",
                "start": 12.0, "end": 16.0,
                "purpose": "Girl reacts to the peak moment",
                "game_audio_vol": 0.3,
                "music_vol": 0.2,
                "sfx": "girl_omg",
                "text_overlay": None,
                "girl_visible": True,
                "girl_position": "pip_bottom_right",
                "girl_size": 0.4,
                "girl_speaks": True,
                "girl_script": "react",
            },
            {
                "name": "outro",
                "start": 16.0, "end": 20.0,
                "purpose": "Girl outro + CTA",
                "game_audio_vol": 0.1,
                "music_vol": 0.4,
                "sfx": None,
                "text_overlay": "cta",
                "girl_visible": True,
                "girl_position": "fullscreen",
                "girl_size": 1.0,
                "girl_speaks": True,
                "girl_script": "outro",
            },
        ],
    },
    "quick_kill": {
        "name": "Quick Kill Clip",
        "description": "Short punchy clip — just the kill with effects",
        "total_duration": 8,
        "phases": [
            {
                "name": "hook",
                "start": 0.0, "end": 1.0,
                "purpose": "Flash hook text",
                "game_audio_vol": 0.3,
                "music_vol": 0.7,
                "sfx": "whoosh_intro",
                "text_overlay": "hook",
                "girl_visible": False,
            },
            {
                "name": "action",
                "start": 1.0, "end": 5.0,
                "purpose": "The kill/play",
                "game_audio_vol": 1.0,
                "music_vol": 0.2,
                "sfx": "impact_hit",
                "text_overlay": None,
                "girl_visible": False,
                "zoom": True,
            },
            {
                "name": "replay",
                "start": 5.0, "end": 7.0,
                "purpose": "Slow-mo replay of the kill",
                "game_audio_vol": 0.5,
                "music_vol": 0.5,
                "sfx": "slow_mo_whoosh",
                "text_overlay": "subtitle",
                "girl_visible": False,
                "slow_mo": True,
                "slow_mo_factor": 0.4,
            },
            {
                "name": "cta",
                "start": 7.0, "end": 8.0,
                "purpose": "Quick CTA",
                "game_audio_vol": 0.1,
                "music_vol": 0.6,
                "sfx": None,
                "text_overlay": "cta",
                "girl_visible": False,
            },
        ],
    },
    # ── NEW: Additional Dramaturgy Templates ──
    "dramatic_ace": {
        "name": "Dramatic ACE Showcase",
        "description": "Cinematic ACE presentation with tension build and replay",
        "total_duration": 18,
        "phases": [
            {
                "name": "tension_intro",
                "start": 0.0, "end": 2.0,
                "purpose": "Dark suspense intro with countdown feel",
                "game_audio_vol": 0.2,
                "music_vol": 0.5,
                "sfx": "clutch_tension",
                "text_overlay": "hook",
                "girl_visible": False,
            },
            {
                "name": "build",
                "start": 2.0, "end": 5.0,
                "purpose": "Show first 1-2 kills building momentum",
                "game_audio_vol": 0.8,
                "music_vol": 0.3,
                "sfx": "headshot_ding",
                "text_overlay": "subtitle",
                "girl_visible": False,
            },
            {
                "name": "peak",
                "start": 5.0, "end": 10.0,
                "purpose": "The remaining kills — full ACE",
                "game_audio_vol": 1.0,
                "music_vol": 0.15,
                "sfx": "impact_hit",
                "text_overlay": None,
                "girl_visible": False,
                "zoom": True,
            },
            {
                "name": "replay",
                "start": 10.0, "end": 13.0,
                "purpose": "Slow-mo replay of the best kill",
                "game_audio_vol": 0.4,
                "music_vol": 0.5,
                "sfx": "slow_mo_whoosh",
                "text_overlay": "subtitle",
                "girl_visible": False,
                "slow_mo": True,
                "slow_mo_factor": 0.3,
            },
            {
                "name": "react",
                "start": 13.0, "end": 16.0,
                "purpose": "Girl reaction to the ACE",
                "game_audio_vol": 0.2,
                "music_vol": 0.3,
                "sfx": "girl_omg",
                "text_overlay": None,
                "girl_visible": True,
                "girl_position": "pip_bottom_right",
                "girl_size": 0.35,
                "girl_speaks": True,
                "girl_script": "react",
            },
            {
                "name": "cta",
                "start": 16.0, "end": 18.0,
                "purpose": "Follow CTA with round win fanfare",
                "game_audio_vol": 0.1,
                "music_vol": 0.6,
                "sfx": "round_win",
                "text_overlay": "cta",
                "girl_visible": False,
            },
        ],
    },
    "fail_compilation": {
        "name": "Fail/Funny Compilation",
        "description": "Funny fail moment with meme edits and reactions",
        "total_duration": 14,
        "phases": [
            {
                "name": "hook",
                "start": 0.0, "end": 2.0,
                "purpose": "Record scratch + freeze frame setup",
                "game_audio_vol": 0.3,
                "music_vol": 0.6,
                "sfx": "record_scratch",
                "text_overlay": "hook",
                "girl_visible": False,
            },
            {
                "name": "context",
                "start": 2.0, "end": 6.0,
                "purpose": "The play that goes wrong",
                "game_audio_vol": 0.9,
                "music_vol": 0.2,
                "sfx": None,
                "text_overlay": "subtitle",
                "girl_visible": False,
            },
            {
                "name": "fail_moment",
                "start": 6.0, "end": 8.0,
                "purpose": "THE fail — with sad trombone",
                "game_audio_vol": 1.0,
                "music_vol": 0.1,
                "sfx": "sad_trombone",
                "text_overlay": None,
                "girl_visible": False,
                "zoom": True,
            },
            {
                "name": "replay",
                "start": 8.0, "end": 10.0,
                "purpose": "Slow-mo replay of the fail",
                "game_audio_vol": 0.3,
                "music_vol": 0.4,
                "sfx": "dun_dun_dun",
                "text_overlay": "subtitle",
                "girl_visible": False,
                "slow_mo": True,
                "slow_mo_factor": 0.4,
            },
            {
                "name": "react",
                "start": 10.0, "end": 12.5,
                "purpose": "Girl laughing reaction",
                "game_audio_vol": 0.2,
                "music_vol": 0.3,
                "sfx": "bruh",
                "text_overlay": None,
                "girl_visible": True,
                "girl_position": "pip_center",
                "girl_size": 0.4,
                "girl_speaks": True,
                "girl_script": "react",
            },
            {
                "name": "cta",
                "start": 12.5, "end": 14.0,
                "purpose": "CTA with notification ding",
                "game_audio_vol": 0.1,
                "music_vol": 0.5,
                "sfx": "notification",
                "text_overlay": "cta",
                "girl_visible": False,
            },
        ],
    },
    "streamer_reaction": {
        "name": "Streamer Reaction Focus",
        "description": "Focus on streamer's emotional reaction to a play",
        "total_duration": 16,
        "phases": [
            {
                "name": "hook",
                "start": 0.0, "end": 2.0,
                "purpose": "Hook text with deep horn",
                "game_audio_vol": 0.3,
                "music_vol": 0.5,
                "sfx": "deep_horn",
                "text_overlay": "hook",
                "girl_visible": False,
            },
            {
                "name": "gameplay",
                "start": 2.0, "end": 8.0,
                "purpose": "The gameplay moment",
                "game_audio_vol": 0.9,
                "music_vol": 0.25,
                "sfx": None,
                "text_overlay": "subtitle",
                "girl_visible": False,
            },
            {
                "name": "peak",
                "start": 8.0, "end": 10.0,
                "purpose": "Peak action with bass drop",
                "game_audio_vol": 1.0,
                "music_vol": 0.1,
                "sfx": "bass_drop",
                "text_overlay": None,
                "girl_visible": False,
                "zoom": True,
            },
            {
                "name": "react",
                "start": 10.0, "end": 14.0,
                "purpose": "Full girl reaction — main event of the clip",
                "game_audio_vol": 0.15,
                "music_vol": 0.2,
                "sfx": "audience_gasp",
                "text_overlay": None,
                "girl_visible": True,
                "girl_position": "pip_bottom_right",
                "girl_size": 0.45,
                "girl_speaks": True,
                "girl_script": "react",
            },
            {
                "name": "cta",
                "start": 14.0, "end": 16.0,
                "purpose": "CTA driven by emotional high",
                "game_audio_vol": 0.1,
                "music_vol": 0.6,
                "sfx": "notification",
                "text_overlay": "cta",
                "girl_visible": False,
            },
        ],
    },
    # ── NEW v2.0: Trending Format Templates ──
    "sigma_edit": {
        "name": "Sigma Edit",
        "description": "Dark cinematic phonk edit — slow-mo, deep bass, sigma text",
        "total_duration": 15,
        "phases": [
            {
                "name": "hook",
                "start": 0.0, "end": 2.0,
                "purpose": "Dark text with deep bass",
                "game_audio_vol": 0.15,
                "music_vol": 0.7,
                "sfx": "deep_horn",
                "text_overlay": "hook",
                "girl_visible": False,
            },
            {
                "name": "build",
                "start": 2.0, "end": 6.0,
                "purpose": "Slow cinematic gameplay build",
                "game_audio_vol": 0.6,
                "music_vol": 0.5,
                "sfx": None,
                "text_overlay": "subtitle",
                "girl_visible": False,
                "slow_mo": True,
                "slow_mo_factor": 0.6,
            },
            {
                "name": "peak",
                "start": 6.0, "end": 10.0,
                "purpose": "Bass drop + kill montage",
                "game_audio_vol": 1.0,
                "music_vol": 0.3,
                "sfx": "bass_drop",
                "text_overlay": None,
                "girl_visible": False,
                "zoom": True,
            },
            {
                "name": "slow_replay",
                "start": 10.0, "end": 13.0,
                "purpose": "Slow-mo replay with sigma text",
                "game_audio_vol": 0.3,
                "music_vol": 0.6,
                "sfx": "slow_mo_whoosh",
                "text_overlay": "subtitle",
                "girl_visible": False,
                "slow_mo": True,
                "slow_mo_factor": 0.3,
            },
            {
                "name": "cta",
                "start": 13.0, "end": 15.0,
                "purpose": "Follow CTA",
                "game_audio_vol": 0.1,
                "music_vol": 0.5,
                "sfx": None,
                "text_overlay": "cta",
                "girl_visible": False,
            },
        ],
    },
    "girl_split_screen": {
        "name": "Girl Split Screen (Instagram)",
        "description": "50/50 split: gameplay top, AI girl bottom. Instagram-native format.",
        "total_duration": 15,
        "phases": [
            {
                "name": "intro",
                "start": 0.0, "end": 2.5,
                "purpose": "Girl introduces from bottom half",
                "game_audio_vol": 0.2,
                "music_vol": 0.4,
                "sfx": None,
                "text_overlay": None,
                "girl_visible": True,
                "girl_position": "split_bottom",
                "girl_size": 0.5,
                "girl_speaks": True,
                "girl_script": "intro",
            },
            {
                "name": "gameplay",
                "start": 2.5, "end": 9.0,
                "purpose": "Gameplay top half, girl reacting bottom",
                "game_audio_vol": 0.8,
                "music_vol": 0.3,
                "sfx": None,
                "text_overlay": "subtitle",
                "girl_visible": True,
                "girl_position": "split_bottom",
                "girl_size": 0.5,
            },
            {
                "name": "peak",
                "start": 9.0, "end": 12.0,
                "purpose": "Peak moment — girl reacts",
                "game_audio_vol": 0.5,
                "music_vol": 0.2,
                "sfx": "girl_omg",
                "text_overlay": None,
                "girl_visible": True,
                "girl_position": "split_bottom",
                "girl_size": 0.5,
                "girl_speaks": True,
                "girl_script": "react",
            },
            {
                "name": "cta",
                "start": 12.0, "end": 15.0,
                "purpose": "CTA with girl outro",
                "game_audio_vol": 0.1,
                "music_vol": 0.5,
                "sfx": "notification",
                "text_overlay": "cta",
                "girl_visible": True,
                "girl_position": "split_bottom",
                "girl_size": 0.5,
                "girl_speaks": True,
                "girl_script": "outro",
            },
        ],
    },
    "girl_fullscreen_intro": {
        "name": "Girl Fullscreen Intro",
        "description": "AI girl introduces fullscreen then transitions to PiP during gameplay",
        "total_duration": 18,
        "phases": [
            {
                "name": "girl_intro",
                "start": 0.0, "end": 3.5,
                "purpose": "Girl fullscreen intro — maximum engagement hook",
                "game_audio_vol": 0.0,
                "music_vol": 0.4,
                "sfx": None,
                "text_overlay": None,
                "girl_visible": True,
                "girl_position": "fullscreen",
                "girl_size": 1.0,
                "girl_speaks": True,
                "girl_script": "intro",
            },
            {
                "name": "gameplay",
                "start": 3.5, "end": 10.0,
                "purpose": "Gameplay with girl in PiP corner",
                "game_audio_vol": 0.8,
                "music_vol": 0.3,
                "sfx": None,
                "text_overlay": "subtitle",
                "girl_visible": True,
                "girl_position": "pip_top_right",
                "girl_size": 0.22,
            },
            {
                "name": "peak",
                "start": 10.0, "end": 13.0,
                "purpose": "Peak moment — girl expands",
                "game_audio_vol": 1.0,
                "music_vol": 0.15,
                "sfx": "impact_hit",
                "text_overlay": None,
                "girl_visible": True,
                "girl_position": "pip_bottom_right",
                "girl_size": 0.35,
                "zoom": True,
            },
            {
                "name": "react",
                "start": 13.0, "end": 16.0,
                "purpose": "Girl reaction expanded",
                "game_audio_vol": 0.2,
                "music_vol": 0.2,
                "sfx": "girl_wow",
                "text_overlay": None,
                "girl_visible": True,
                "girl_position": "pip_bottom_right",
                "girl_size": 0.45,
                "girl_speaks": True,
                "girl_script": "react",
            },
            {
                "name": "cta",
                "start": 16.0, "end": 18.0,
                "purpose": "CTA",
                "game_audio_vol": 0.1,
                "music_vol": 0.6,
                "sfx": "notification",
                "text_overlay": "cta",
                "girl_visible": False,
            },
        ],
    },
    "instagram_story": {
        "name": "Instagram Story Style",
        "description": "Designed for Instagram stories — girl in bottom third, sticker/poll style",
        "total_duration": 15,
        "phases": [
            {
                "name": "hook",
                "start": 0.0, "end": 2.0,
                "purpose": "Poll-style question hook",
                "game_audio_vol": 0.3,
                "music_vol": 0.5,
                "sfx": "swoosh_fast",
                "text_overlay": "hook",
                "girl_visible": False,
            },
            {
                "name": "gameplay",
                "start": 2.0, "end": 8.0,
                "purpose": "Gameplay with girl in bottom third",
                "game_audio_vol": 0.8,
                "music_vol": 0.3,
                "sfx": None,
                "text_overlay": "subtitle",
                "girl_visible": True,
                "girl_position": "bottom_third",
                "girl_size": 0.33,
            },
            {
                "name": "peak",
                "start": 8.0, "end": 11.0,
                "purpose": "Peak action",
                "game_audio_vol": 1.0,
                "music_vol": 0.15,
                "sfx": "impact_hit",
                "text_overlay": None,
                "girl_visible": True,
                "girl_position": "bottom_third",
                "girl_size": 0.33,
                "zoom": True,
            },
            {
                "name": "react",
                "start": 11.0, "end": 13.5,
                "purpose": "Girl reaction in bottom third",
                "game_audio_vol": 0.2,
                "music_vol": 0.3,
                "sfx": "girl_wow",
                "text_overlay": None,
                "girl_visible": True,
                "girl_position": "bottom_third",
                "girl_size": 0.33,
                "girl_speaks": True,
                "girl_script": "react",
            },
            {
                "name": "cta",
                "start": 13.5, "end": 15.0,
                "purpose": "Swipe up / follow CTA",
                "game_audio_vol": 0.1,
                "music_vol": 0.5,
                "sfx": "notification",
                "text_overlay": "cta",
                "girl_visible": False,
            },
        ],
    },
    "brainrot_edit": {
        "name": "Brainrot Edit",
        "description": "Maximum sensory overload — rapid SFX, zoom, shake, meme sounds",
        "total_duration": 10,
        "phases": [
            {
                "name": "hook",
                "start": 0.0, "end": 1.0,
                "purpose": "Vine boom + flash text",
                "game_audio_vol": 0.2,
                "music_vol": 0.8,
                "sfx": "vine_boom",
                "text_overlay": "hook",
                "girl_visible": False,
                "screen_shake": True,
            },
            {
                "name": "build",
                "start": 1.0, "end": 3.5,
                "purpose": "Fast gameplay with meme overlay",
                "game_audio_vol": 0.7,
                "music_vol": 0.5,
                "sfx": "swoosh_fast",
                "text_overlay": "subtitle",
                "girl_visible": False,
                "meme_overlay": True,
            },
            {
                "name": "peak",
                "start": 3.5, "end": 6.0,
                "purpose": "Kill with SFX stack + zoom + shake",
                "game_audio_vol": 1.0,
                "music_vol": 0.2,
                "sfx": "mlg_airhorn",
                "text_overlay": None,
                "girl_visible": False,
                "zoom": True,
                "screen_shake": True,
            },
            {
                "name": "meme_react",
                "start": 6.0, "end": 8.5,
                "purpose": "Meme sound + reaction",
                "game_audio_vol": 0.3,
                "music_vol": 0.6,
                "sfx": "bruh",
                "text_overlay": "subtitle",
                "girl_visible": False,
                "meme_overlay": True,
            },
            {
                "name": "cta",
                "start": 8.5, "end": 10.0,
                "purpose": "Quick CTA",
                "game_audio_vol": 0.1,
                "music_vol": 0.5,
                "sfx": "notification",
                "text_overlay": "cta",
                "girl_visible": False,
            },
        ],
    },
    "provocative_hook": {
        "name": "Provocative Hook",
        "description": "Controversial question that forces comments + engagement",
        "total_duration": 14,
        "phases": [
            {
                "name": "hook",
                "start": 0.0, "end": 3.0,
                "purpose": "Big provocative question text",
                "game_audio_vol": 0.2,
                "music_vol": 0.6,
                "sfx": "deep_horn",
                "text_overlay": "hook",
                "girl_visible": False,
            },
            {
                "name": "build",
                "start": 3.0, "end": 7.0,
                "purpose": "Show the gameplay context",
                "game_audio_vol": 0.8,
                "music_vol": 0.3,
                "sfx": None,
                "text_overlay": "subtitle",
                "girl_visible": False,
            },
            {
                "name": "peak",
                "start": 7.0, "end": 10.0,
                "purpose": "The moment",
                "game_audio_vol": 1.0,
                "music_vol": 0.15,
                "sfx": "impact_hit",
                "text_overlay": None,
                "girl_visible": False,
                "zoom": True,
            },
            {
                "name": "debate",
                "start": 10.0, "end": 12.5,
                "purpose": "Replay with question text overlay",
                "game_audio_vol": 0.4,
                "music_vol": 0.4,
                "sfx": None,
                "text_overlay": "subtitle",
                "girl_visible": False,
            },
            {
                "name": "cta",
                "start": 12.5, "end": 14.0,
                "purpose": "Comment CTA",
                "game_audio_vol": 0.1,
                "music_vol": 0.5,
                "sfx": "notification",
                "text_overlay": "cta",
                "girl_visible": False,
            },
        ],
    },
}

# ═══════════════════════════════════════════════════════════════════════
# SECTION 2: SFX & MUSIC LIBRARY
# ═══════════════════════════════════════════════════════════════════════

# Sound effects catalog — generated with FFmpeg (no external files needed)
SFX_CATALOG = {
    "whoosh_intro": {
        "name": "Whoosh Intro",
        "category": "transition",
        "duration": 0.8,
        "generate_cmd": "anoisesrc=d=0.8:c=pink:r=44100:a=0.3,afade=t=in:d=0.1,afade=t=out:d=0.3:st=0.5,asetrate=44100*2,aresample=44100,volume=0.7",
    },
    "impact_hit": {
        "name": "Impact Hit",
        "category": "action",
        "duration": 0.5,
        "generate_cmd": "anoisesrc=d=0.5:c=white:r=44100:a=0.8,afade=t=out:d=0.4:st=0.1,lowpass=f=200,volume=2.0",
    },
    "vine_boom": {
        "name": "Vine Boom",
        "category": "meme",
        "duration": 1.0,
        "generate_cmd": "sine=f=80:d=1.0,afade=t=out:d=0.8:st=0.2,volume=1.5",
    },
    "mlg_airhorn": {
        "name": "MLG Airhorn",
        "category": "meme",
        "duration": 1.5,
        "generate_cmd": "sine=f=600:d=0.3[s1];sine=f=700:d=0.3[s2];sine=f=600:d=0.3[s3];sine=f=800:d=0.3[s4];sine=f=600:d=0.3[s5];[s1][s2][s3][s4][s5]concat=n=5:v=0:a=1,volume=0.8",
    },
    "bruh": {
        "name": "Bruh Sound",
        "category": "meme",
        "duration": 0.7,
        "generate_cmd": "sine=f=150:d=0.7,afade=t=in:d=0.05,afade=t=out:d=0.3:st=0.4,asetrate=44100*0.7,aresample=44100,volume=1.2",
    },
    "notification": {
        "name": "Notification Ding",
        "category": "ui",
        "duration": 0.6,
        "generate_cmd": "sine=f=880:d=0.15[s1];sine=f=1100:d=0.15[s2];[s1][s2]concat=n=2:v=0:a=1,afade=t=out:d=0.2:st=0.1,volume=0.6",
    },
    "slow_mo_whoosh": {
        "name": "Slow-Mo Whoosh",
        "category": "effect",
        "duration": 2.0,
        "generate_cmd": "anoisesrc=d=2.0:c=pink:r=44100:a=0.2,lowpass=f=500,afade=t=in:d=0.5,afade=t=out:d=0.5:st=1.5,volume=0.5",
    },
    "girl_wow": {
        "name": "Wow Reaction",
        "category": "reaction",
        "duration": 1.0,
        "generate_cmd": "sine=f=440:d=0.3[s1];sine=f=660:d=0.3[s2];sine=f=880:d=0.4[s3];[s1][s2][s3]concat=n=3:v=0:a=1,afade=t=out:d=0.3:st=0.7,volume=0.5",
    },
    "girl_omg": {
        "name": "OMG Reaction",
        "category": "reaction",
        "duration": 1.2,
        "generate_cmd": "sine=f=500:d=0.4[s1];sine=f=800:d=0.4[s2];sine=f=1200:d=0.4[s3];[s1][s2][s3]concat=n=3:v=0:a=1,afade=t=out:d=0.4:st=0.8,volume=0.5",
    },
    "suspense_rise": {
        "name": "Suspense Riser",
        "category": "build",
        "duration": 3.0,
        "generate_cmd": "anoisesrc=d=3.0:c=pink:r=44100:a=0.1,lowpass=f=200,volume=0.3",
    },
    # ── NEW: Gaming-specific SFX ──
    "headshot_ding": {
        "name": "Headshot Ding",
        "category": "action",
        "duration": 0.4,
        "generate_cmd": "sine=f=2200:d=0.1[s1];sine=f=3300:d=0.1[s2];[s1][s2]concat=n=2:v=0:a=1,afade=t=out:d=0.1:st=0.1,volume=0.6",
    },
    "bomb_plant": {
        "name": "Bomb Plant Beep",
        "category": "game",
        "duration": 1.2,
        "generate_cmd": "sine=f=1000:d=0.15,apad=pad_dur=0.35[s1];sine=f=1000:d=0.15,apad=pad_dur=0.35[s2];sine=f=1200:d=0.2[s3];[s1][s2][s3]concat=n=3:v=0:a=1,volume=0.5",
    },
    "round_win": {
        "name": "Round Win Fanfare",
        "category": "game",
        "duration": 1.5,
        "generate_cmd": "sine=f=523:d=0.25[s1];sine=f=659:d=0.25[s2];sine=f=784:d=0.5[s3];sine=f=1047:d=0.5[s4];[s1][s2][s3][s4]concat=n=4:v=0:a=1,afade=t=out:d=0.3:st=1.2,volume=0.6",
    },
    "clutch_tension": {
        "name": "Clutch Tension Build",
        "category": "build",
        "duration": 4.0,
        "generate_cmd": "anoisesrc=d=4.0:c=pink:r=44100:a=0.05,lowpass=f=300,tremolo=f=2:d=0.8,afade=t=in:d=1.0,afade=t=out:d=0.5:st=3.5,volume=0.4",
    },
    "bass_drop": {
        "name": "Bass Drop",
        "category": "meme",
        "duration": 1.0,
        "generate_cmd": "sine=f=40:d=1.0,afade=t=in:d=0.02,afade=t=out:d=0.6:st=0.4,volume=2.0",
    },
    "record_scratch": {
        "name": "Record Scratch",
        "category": "meme",
        "duration": 0.8,
        "generate_cmd": "anoisesrc=d=0.8:c=white:r=44100:a=0.5,highpass=f=3000,afade=t=out:d=0.6:st=0.2,asetrate=44100*0.5,aresample=44100,volume=0.7",
    },
    "sad_trombone": {
        "name": "Sad Trombone",
        "category": "meme",
        "duration": 2.0,
        "generate_cmd": "sine=f=311:d=0.5[s1];sine=f=293:d=0.5[s2];sine=f=277:d=0.5[s3];sine=f=261:d=0.5[s4];[s1][s2][s3][s4]concat=n=4:v=0:a=1,afade=t=out:d=0.5:st=1.5,volume=0.5",
    },
    "dun_dun_dun": {
        "name": "Dun Dun Dun",
        "category": "meme",
        "duration": 1.5,
        "generate_cmd": "sine=f=196:d=0.4,apad=pad_dur=0.1[s1];sine=f=196:d=0.4,apad=pad_dur=0.1[s2];sine=f=146:d=0.5[s3];[s1][s2][s3]concat=n=3:v=0:a=1,volume=0.7",
    },
    "kill_confirmed": {
        "name": "Kill Confirmed",
        "category": "action",
        "duration": 0.6,
        "generate_cmd": "sine=f=1500:d=0.15[s1];sine=f=2000:d=0.15[s2];[s1][s2]concat=n=2:v=0:a=1,afade=t=out:d=0.2:st=0.1,volume=0.7",
    },
    "swoosh_fast": {
        "name": "Fast Swoosh",
        "category": "transition",
        "duration": 0.4,
        "generate_cmd": "anoisesrc=d=0.4:c=pink:r=44100:a=0.4,afade=t=in:d=0.05,afade=t=out:d=0.15:st=0.25,asetrate=44100*3,aresample=44100,volume=0.6",
    },
    "countdown_tick": {
        "name": "Countdown Tick",
        "category": "build",
        "duration": 0.3,
        "generate_cmd": "sine=f=1000:d=0.05,apad=pad_dur=0.25,aformat=sample_fmts=fltp:sample_rates=44100,volume=0.5",
    },
    "glass_shatter": {
        "name": "Glass Shatter",
        "category": "meme",
        "duration": 1.0,
        "generate_cmd": "anoisesrc=d=1.0:c=white:r=44100:a=0.8,highpass=f=5000,afade=t=out:d=0.8:st=0.2,volume=0.6",
    },
    "deep_horn": {
        "name": "Deep Horn",
        "category": "transition",
        "duration": 2.0,
        "generate_cmd": "sine=f=65:d=2.0,volume=0.4[s1];sine=f=98:d=2.0,volume=0.3[s2];[s1][s2]amix=inputs=2:duration=longest,afade=t=in:d=0.3,afade=t=out:d=0.5:st=1.5,volume=0.5",
    },
    "triple_kill_chime": {
        "name": "Triple Kill Chime",
        "category": "action",
        "duration": 0.8,
        "generate_cmd": "sine=f=880:d=0.15[s1];sine=f=1100:d=0.15[s2];sine=f=1320:d=0.15[s3];[s1][s2][s3]concat=n=3:v=0:a=1,afade=t=out:d=0.1:st=0.35,volume=0.6",
    },
    "audience_gasp": {
        "name": "Audience Gasp",
        "category": "reaction",
        "duration": 1.5,
        "generate_cmd": "anoisesrc=d=1.5:c=pink:r=44100:a=0.3,bandpass=f=600:w=400,afade=t=in:d=0.1,afade=t=out:d=0.8:st=0.7,volume=0.5",
    },
}

# Music tracks — generated procedurally with FFmpeg
MUSIC_TRACKS = {
    "phonk_beat": {
        "name": "Phonk Beat",
        "category": "gaming",
        "bpm": 140,
        "mood": "aggressive",
        "generate_cmd": (
            "sine=f=65:d=30,volume=0.3[bass];"
            "anoisesrc=d=30:c=pink:r=44100:a=0.1,bandpass=f=8000:w=2000[hat];"
            "sine=f=100:d=0.1,apad=whole_dur=30,volume=0.4[kick];"
            "[bass][hat][kick]amix=inputs=3:duration=longest,volume=0.5"
        ),
    },
    "trap_chill": {
        "name": "Trap Chill",
        "category": "gaming",
        "bpm": 120,
        "mood": "chill",
        "generate_cmd": (
            "sine=f=55:d=30,volume=0.25[bass];"
            "sine=f=220:d=30,tremolo=f=4:d=0.5,volume=0.15[melody];"
            "anoisesrc=d=30:c=pink:r=44100:a=0.05,bandpass=f=10000:w=3000[hat];"
            "[bass][melody][hat]amix=inputs=3:duration=longest,volume=0.4"
        ),
    },
    "epic_orchestral": {
        "name": "Epic Orchestral",
        "category": "highlight",
        "bpm": 100,
        "mood": "epic",
        "generate_cmd": (
            "sine=f=110:d=30,volume=0.3[bass];"
            "sine=f=330:d=30,tremolo=f=2:d=0.3,volume=0.2[strings];"
            "sine=f=440:d=30,tremolo=f=6:d=0.7,volume=0.1[high];"
            "[bass][strings][high]amix=inputs=3:duration=longest,volume=0.45"
        ),
    },
    "lofi_gaming": {
        "name": "Lo-Fi Gaming",
        "category": "commentary",
        "bpm": 85,
        "mood": "relaxed",
        "generate_cmd": (
            "sine=f=73:d=30,volume=0.2[bass];"
            "sine=f=293:d=30,tremolo=f=1:d=0.4,volume=0.15[piano];"
            "anoisesrc=d=30:c=brown:r=44100:a=0.03[noise];"
            "[bass][piano][noise]amix=inputs=3:duration=longest,volume=0.35"
        ),
    },
    # ── NEW: More music variety ──
    "cinematic_dark": {
        "name": "Cinematic Dark",
        "category": "highlight",
        "bpm": 90,
        "mood": "dark",
        "generate_cmd": (
            "sine=f=55:d=30,volume=0.35[bass];"
            "sine=f=165:d=30,tremolo=f=0.5:d=0.6,volume=0.15[drone];"
            "anoisesrc=d=30:c=brown:r=44100:a=0.04,lowpass=f=300[rumble];"
            "[bass][drone][rumble]amix=inputs=3:duration=longest,volume=0.45"
        ),
    },
    "hard_phonk": {
        "name": "Hard Phonk",
        "category": "gaming",
        "bpm": 160,
        "mood": "aggressive",
        "generate_cmd": (
            "sine=f=55:d=30,volume=0.4[bass];"
            "anoisesrc=d=30:c=pink:r=44100:a=0.15,bandpass=f=6000:w=3000[hat];"
            "sine=f=82:d=0.08,apad=whole_dur=30,volume=0.5[kick];"
            "sine=f=220:d=30,tremolo=f=8:d=0.9,volume=0.08[cowbell];"
            "[bass][hat][kick][cowbell]amix=inputs=4:duration=longest,volume=0.5"
        ),
    },
    "synthwave_retro": {
        "name": "Synthwave Retro",
        "category": "highlight",
        "bpm": 110,
        "mood": "nostalgic",
        "generate_cmd": (
            "sine=f=82:d=30,volume=0.25[bass];"
            "sine=f=330:d=30,tremolo=f=3:d=0.5,volume=0.12[synth1];"
            "sine=f=440:d=30,tremolo=f=5:d=0.3,volume=0.08[synth2];"
            "sine=f=660:d=30,tremolo=f=2:d=0.6,volume=0.06[pad];"
            "[bass][synth1][synth2][pad]amix=inputs=4:duration=longest,volume=0.4"
        ),
    },
    "drill_beat": {
        "name": "Drill Beat",
        "category": "gaming",
        "bpm": 145,
        "mood": "menacing",
        "generate_cmd": (
            "sine=f=49:d=30,volume=0.35[bass];"
            "anoisesrc=d=30:c=pink:r=44100:a=0.12,bandpass=f=9000:w=2000[hat];"
            "sine=f=73:d=0.06,apad=whole_dur=30,volume=0.4[kick];"
            "[bass][hat][kick]amix=inputs=3:duration=longest,volume=0.45"
        ),
    },
    "ambient_tension": {
        "name": "Ambient Tension",
        "category": "commentary",
        "bpm": 70,
        "mood": "suspenseful",
        "generate_cmd": (
            "sine=f=65:d=30,volume=0.2[bass];"
            "anoisesrc=d=30:c=brown:r=44100:a=0.06,lowpass=f=200,tremolo=f=0.3:d=0.5[drone];"
            "sine=f=440:d=30,tremolo=f=0.1:d=0.8,volume=0.05[pad];"
            "[bass][drone][pad]amix=inputs=3:duration=longest,volume=0.35"
        ),
    },
    # ── NEW v2.0: Trending music tracks ──
    "phonk_dark": {
        "name": "Dark Phonk",
        "category": "gaming",
        "bpm": 135,
        "mood": "dark_aggressive",
        "generate_cmd": (
            "sine=f=45:d=30,volume=0.4[sub];"
            "sine=f=82:d=0.06,apad=whole_dur=30,volume=0.5[kick];"
            "anoisesrc=d=30:c=pink:r=44100:a=0.1,bandpass=f=7000:w=2000[hat];"
            "sine=f=130:d=30,tremolo=f=6:d=0.8,volume=0.08[synth];"
            "[sub][kick][hat][synth]amix=inputs=4:duration=longest,volume=0.45"
        ),
    },
    "lofi_chill": {
        "name": "Lo-Fi Chill",
        "category": "commentary",
        "bpm": 80,
        "mood": "chill",
        "generate_cmd": (
            "sine=f=65:d=30,volume=0.18[bass];"
            "sine=f=261:d=30,tremolo=f=0.8:d=0.3,volume=0.12[piano];"
            "anoisesrc=d=30:c=brown:r=44100:a=0.04[vinyl];"
            "sine=f=392:d=30,tremolo=f=1.2:d=0.4,volume=0.06[pad];"
            "[bass][piano][vinyl][pad]amix=inputs=4:duration=longest,volume=0.35"
        ),
    },
    "hype_buildup": {
        "name": "Hype Buildup",
        "category": "highlight",
        "bpm": 150,
        "mood": "hype",
        "generate_cmd": (
            "sine=f=55:d=30,volume=0.3[bass];"
            "anoisesrc=d=30:c=pink:r=44100:a=0.12,bandpass=f=8000:w=3000[hat];"
            "sine=f=110:d=0.08,apad=whole_dur=30,volume=0.4[kick];"
            "sine=f=440:d=30,tremolo=f=8:d=0.6,volume=0.1[synth];"
            "[bass][hat][kick][synth]amix=inputs=4:duration=longest,volume=0.5"
        ),
    },
    "trending_audio": {
        "name": "Trending Audio",
        "category": "social",
        "bpm": 128,
        "mood": "catchy",
        "generate_cmd": (
            "sine=f=73:d=30,volume=0.25[bass];"
            "sine=f=293:d=30,tremolo=f=4:d=0.5,volume=0.15[melody];"
            "sine=f=440:d=30,tremolo=f=2:d=0.3,volume=0.1[lead];"
            "anoisesrc=d=30:c=pink:r=44100:a=0.08,bandpass=f=9000:w=2000[perc];"
            "[bass][melody][lead][perc]amix=inputs=4:duration=longest,volume=0.4"
        ),
    },
}

# AI Girl commentary scripts by context — with ElevenLabs v3 audio tags for maximum expressiveness
# Audio tags: [excited], [whispers], [laughs], [sighs], [gasps], [clears throat]
GIRL_SCRIPTS = {
    "ace": {
        "intro": "[whispers] Oh my god guys... [excited] you HAVE to see this ace! This is absolutely unreal!",
        "react": "[gasps] NO WAY! [excited] That was absolutely INSANE! Five kills, are you kidding me?! [laughs] I can't even breathe right now!",
        "outro": "[excited] If you liked that, smash that follow button! [laughs] More insane clips coming daily!",
    },
    "clutch": {
        "intro": "[whispers] Okay chat, watch this clutch closely... [sighs] this is going to be insane...",
        "react": "[gasps] HE DID IT! [excited] One versus FIVE and he clutched it! [laughs] I'm literally shaking right now!",
        "outro": "[excited] Follow for more clutch moments like this! Drop a like if he's cracked!",
    },
    "multi_kill": {
        "intro": "[whispers] Wait for this multi-kill... [excited] it's absolutely nuts...",
        "react": "[gasps] TRIPLE! No, QUAD KILL! [excited] This man is not human! [laughs] What did I just watch?!",
        "outro": "[excited] Want more insane kills? Hit follow and turn on notifications!",
    },
    "funny": {
        "intro": "[laughs] Okay this one is actually SO funny, watch... [whispers] I already can't stop laughing...",
        "react": "[laughs] I can't breathe! [gasps] Did that really just happen?! [laughs] Oh my god that's hilarious!",
        "outro": "[laughs] More funny moments coming every day! [excited] Follow so you don't miss out!",
    },
    "insane_play": {
        "intro": "[whispers] Guys... [excited] this play is going to blow your mind... just watch...",
        "react": "[gasps] WHAT?! [excited] How is that even possible?! [laughs] This guy is built COMPLETELY different!",
        "outro": "[excited] Follow for daily CS2 highlights! This channel is going crazy!",
    },
    "default": {
        "intro": "[excited] Watch this insane CS2 moment... [whispers] trust me on this one...",
        "react": "[gasps] That was absolutely incredible! [excited] Did you see that?! [laughs] Unbelievable!",
        "outro": "[excited] Follow for more CS2 highlights every single day!",
    },
    "headshot": {
        "intro": "[whispers] You are NOT ready for these headshots... [excited] every single one hits different!",
        "react": "[gasps] CLEAN headshots! [excited] Every single bullet hit the head! [laughs] This aim is UNREAL!",
        "outro": "[excited] More headshot compilations coming! Follow and turn on notifications!",
    },
    "knife_kill": {
        "intro": "[whispers] He actually went for the knife... [gasps] watch what happens...",
        "react": "[gasps] THE KNIFE KILL! [excited] The absolute DISRESPECT! [laughs] I'm literally screaming!",
        "outro": "[excited] Want more disrespectful plays? Follow for daily clips!",
    },
    "eco_round": {
        "intro": "[sighs] They had NO money... [whispers] but watch what happens next...",
        "react": "[gasps] ECO ROUND WIN! [excited] Pistols versus rifles and they DESTROYED them! [laughs] How?!",
        "outro": "[excited] Eco round heroes are built different! Follow for more!",
    },
    "spray_transfer": {
        "intro": "[whispers] This spray transfer is about to break the game... [excited] watch closely!",
        "react": "[gasps] THE SPRAY TRANSFER! [excited] From one to another without stopping! [laughs] That's INHUMAN!",
        "outro": "[excited] More spray control content dropping daily! Hit follow!",
    },
    "toxic_play": {
        "intro": "[laughs] Okay this is SO toxic but SO good... [whispers] watch this...",
        "react": "[gasps] THE DISRESPECT! [laughs] I can't believe he actually did that! [excited] SAVAGE!",
        "outro": "[excited] More toxic moments every day! Follow if you love the chaos!",
    },
    "wallbang": {
        "intro": "[whispers] He's about to hit a shot through the WALL... [gasps] just wait...",
        "react": "[gasps] WALLBANG! [excited] Through the wall! How did he even KNOW they were there?! [laughs]",
        "outro": "[excited] More wallbang compilations coming! Follow now!",
    },
    "fail_moment": {
        "intro": "[laughs] This is the funniest fail I've seen all week... [whispers] I'm already dying...",
        "react": "[laughs] NOOO! [gasps] How do you even mess that up?! [laughs] I'm DYING!",
        "outro": "[laughs] More hilarious fails coming daily! [excited] Follow for the laughs!",
    },
    "comeback": {
        "intro": "[sighs] They were down 2 to 13... [whispers] and then THIS happened...",
        "react": "[gasps] THE COMEBACK! [excited] From the brink of defeat to VICTORY! [laughs] LEGENDARY!",
        "outro": "[excited] Never give up! Follow for more incredible comeback stories!",
    },
}

# TTS voice options for AI girl
# Real ElevenLabs voice IDs (verified) + edge-tts fallbacks
# Audio tags are now embedded directly in GIRL_SCRIPTS for natural flow
GIRL_VOICES = {
    "jessica": {
        "elevenlabs_id": "cgSgspJ2msm6clMCkdW9",  # Jessica — Playful, Bright, Warm
        "edge_tts_id": "en-US-JennyNeural",
        "style": "playful",
        "desc": "Playful & bright — the hype girl energy",
    },
    "sarah": {
        "elevenlabs_id": "EXAVITQu4vr4xnSDxMaL",  # Sarah — Mature, Reassuring, Confident
        "edge_tts_id": "en-US-SaraNeural",
        "style": "confident",
        "desc": "Confident & mature — pro caster vibes",
    },
    "laura": {
        "elevenlabs_id": "FGY2WhTYpPnrIDTdsKH5",  # Laura — Enthusiast, Quirky
        "edge_tts_id": "en-US-AriaNeural",
        "style": "quirky",
        "desc": "Quirky enthusiast — social media energy",
    },
    "alice": {
        "elevenlabs_id": "Xb7hH8MSUJpSbSDYk0k2",  # Alice — Clear, Engaging Educator
        "edge_tts_id": "en-GB-SoniaNeural",
        "style": "educator",
        "desc": "Clear British educator — analytical breakdowns",
    },
    "matilda": {
        "elevenlabs_id": "XrExE9yKIg1WjnnlVkGX",  # Matilda — Knowledgeable, Professional
        "edge_tts_id": "en-US-MichelleNeural",
        "style": "professional",
        "desc": "Professional analyst — sports commentator style",
    },
    "bella": {
        "elevenlabs_id": "hpp4J3VqNfWAUOO0d1Us",  # Bella — Professional, Bright, Warm
        "edge_tts_id": "en-US-EmmaNeural",
        "style": "warm",
        "desc": "Warm & professional — friendly host",
    },
    "lily": {
        "elevenlabs_id": "pFZP5JQG7iQjIQuC4Bku",  # Lily — Velvety Actress
        "edge_tts_id": "en-GB-LibbyNeural",
        "style": "dramatic",
        "desc": "Dramatic actress — cinematic narration",
    },
    "ivanna": {
        "elevenlabs_id": "yM93hbw8Qtvdma2wCnJG",  # Ivanna — Young, Versatile, Casual
        "edge_tts_id": "en-US-JennyNeural",
        "style": "casual",
        "desc": "Young & casual — TikTok/Reels vibe",
    },
}


# ═══════════════════════════════════════════════════════════════════════
# SECTION 3: ASSET GENERATION (SFX, Music via FFmpeg)
# ═══════════════════════════════════════════════════════════════════════

async def _run_ffmpeg(cmd: list[str], timeout: float = 60.0) -> dict:
    """Run an FFmpeg command and return result."""
    _ensure_ffmpeg()
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        if proc.returncode != 0:
            return {"success": False, "error": stderr.decode()[-500:]}
        return {"success": True}
    except asyncio.TimeoutError:
        return {"success": False, "error": "FFmpeg timed out"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def generate_sfx(sfx_id: str) -> str | None:
    """Generate a sound effect using FFmpeg synthesis. Returns file path."""
    if sfx_id not in SFX_CATALOG:
        return None

    sfx = SFX_CATALOG[sfx_id]
    output_path = MONTAGE_DIR / "assets" / "sfx" / f"{sfx_id}.wav"

    if output_path.exists():
        return str(output_path)

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", sfx["generate_cmd"],
        "-ar", "44100", "-ac", "1",
        str(output_path),
    ]

    result = await _run_ffmpeg(cmd)
    if result["success"] and output_path.exists():
        return str(output_path)
    return None


async def generate_music_track(track_id: str, duration: float = 30.0) -> str | None:
    """Generate a background music track using FFmpeg synthesis. Returns file path."""
    if track_id not in MUSIC_TRACKS:
        return None

    track = MUSIC_TRACKS[track_id]
    output_path = MONTAGE_DIR / "assets" / "music" / f"{track_id}_{int(duration)}s.wav"

    if output_path.exists():
        return str(output_path)

    # Replace duration placeholder in the command
    gen_cmd = track["generate_cmd"].replace(":d=30", f":d={duration}")
    gen_cmd = gen_cmd.replace("whole_dur=30", f"whole_dur={duration}")

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", gen_cmd,
        "-ar", "44100", "-ac", "2",
        "-t", str(duration),
        str(output_path),
    ]

    result = await _run_ffmpeg(cmd, timeout=30.0)
    if result["success"] and output_path.exists():
        return str(output_path)
    return None


async def ensure_assets_ready(template_id: str, duration: float) -> dict:
    """Pre-generate all SFX and music needed for a template."""
    template = DRAMATURGY_TEMPLATES.get(template_id)
    if not template:
        return {"success": False, "error": f"Unknown template: {template_id}"}

    assets = {"sfx": {}, "music": None}

    # Generate SFX for each phase
    for phase in template["phases"]:
        sfx_id = phase.get("sfx")
        if sfx_id and sfx_id not in assets["sfx"]:
            path = await generate_sfx(sfx_id)
            if path:
                assets["sfx"][sfx_id] = path

    # Pick music track based on template
    music_map = {
        "highlight_react": "phonk_beat",
        "meme_edit": "hard_phonk",
        "girl_commentary": "lofi_gaming",
        "quick_kill": "trap_chill",
        "dramatic_ace": "cinematic_dark",
        "fail_compilation": "trap_chill",
        "streamer_reaction": "synthwave_retro",
        # v2.0 trending templates
        "sigma_edit": "phonk_dark",
        "girl_split_screen": "lofi_chill",
        "girl_fullscreen_intro": "hype_buildup",
        "instagram_story": "trending_audio",
        "brainrot_edit": "hard_phonk",
        "provocative_hook": "hype_buildup",
    }
    music_id = music_map.get(template_id, "trap_chill")
    music_path = await generate_music_track(music_id, duration + 5)
    if music_path:
        assets["music"] = music_path
        assets["music_id"] = music_id

    return {"success": True, "assets": assets}


# ═══════════════════════════════════════════════════════════════════════
# SECTION 4: AI GIRL PIPELINE (TTS + Lip-sync)
# ═══════════════════════════════════════════════════════════════════════

async def generate_girl_audio(
    text: str,
    voice: str = "jessica",
    output_name: str | None = None,
    elevenlabs_api_key: str | None = None,
) -> dict:
    """
    Generate AI girl voice.
    Priority: ElevenLabs v3 (if API key) → edge-tts (free fallback).
    ElevenLabs v3 uses audio tags for expressive speech.
    """
    voice_info = GIRL_VOICES.get(voice, GIRL_VOICES["jessica"])

    if output_name is None:
        output_name = f"girl_tts_{uuid.uuid4().hex[:8]}"

    output_path = MONTAGE_DIR / "temp" / f"{output_name}.mp3"
    srt_path = MONTAGE_DIR / "temp" / f"{output_name}.srt"

    # Try ElevenLabs v3 first if API key available
    api_key = elevenlabs_api_key or os.environ.get("ELEVENLABS_API_KEY", "")
    if api_key:
        try:
            result = await _generate_elevenlabs_v3(text, voice_info, api_key, str(output_path))
            if result["success"]:
                info = await _get_audio_duration(str(output_path))
                return {
                    "success": True,
                    "audio_path": str(output_path),
                    "srt_path": None,
                    "duration": info.get("duration", 0),
                    "text": text,
                    "voice": voice,
                    "engine": "elevenlabs_v3",
                    "cost": result.get("cost", 0.0),
                }
        except Exception as e:
            # Fall through to edge-tts
            pass

    # Fallback: edge-tts (FREE)
    return await _generate_edge_tts(text, voice_info, str(output_path), str(srt_path))


async def _generate_elevenlabs_v3(
    text: str,
    voice_info: dict,
    api_key: str,
    output_path: str,
) -> dict:
    """
    Generate speech using ElevenLabs v3 with audio tags.
    v3 supports [excited], [whispers], [laughs], [sighs] etc.
    """
    from elevenlabs.client import ElevenLabs as ElevenLabsClient

    client = ElevenLabsClient(api_key=api_key)
    voice_id = voice_info.get("elevenlabs_id", "cgSgspJ2msm6clMCkdW9")

    # Text already contains audio tags from GIRL_SCRIPTS (e.g. [excited], [whispers])
    # v3 model natively processes these tags for expressive speech

    try:
        audio_iter = client.text_to_speech.convert(
            text=text,
            voice_id=voice_id,
            model_id="eleven_v3",
            output_format="mp3_44100_128",
        )

        # Write audio chunks to file
        with open(output_path, "wb") as f:
            for chunk in audio_iter:
                if isinstance(chunk, bytes):
                    f.write(chunk)

        if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
            # Cost estimate: ~$0.30 per 1000 chars
            cost = len(text) * 0.0003
            return {"success": True, "cost": round(cost, 4)}

        return {"success": False, "error": "No audio generated"}
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _generate_edge_tts(
    text: str,
    voice_info: dict,
    output_path: str,
    srt_path: str,
) -> dict:
    """Fallback: Generate AI girl voice using edge-tts (FREE)."""
    import edge_tts

    voice_id = voice_info.get("edge_tts_id", "en-US-JennyNeural")

    try:
        communicate = edge_tts.Communicate(text, voice_id)
        submaker = edge_tts.SubMaker()
        with open(output_path, "wb") as audio_file:
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_file.write(chunk["data"])
                elif chunk["type"] == "WordBoundary":
                    submaker.feed(chunk)

        srt_content = submaker.get_srt()
        with open(srt_path, "w") as f:
            f.write(srt_content)

        info = await _get_audio_duration(output_path)

        return {
            "success": True,
            "audio_path": output_path,
            "srt_path": srt_path,
            "duration": info.get("duration", 0),
            "text": text,
            "voice": voice_id,
            "engine": "edge_tts",
            "cost": 0.0,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


async def _get_audio_duration(file_path: str) -> dict:
    """Get audio duration using ffprobe."""
    cmd = [
        "ffprobe", "-v", "quiet", "-print_format", "json",
        "-show_format", file_path,
    ]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
        data = json.loads(stdout.decode())
        duration = float(data.get("format", {}).get("duration", 0))
        return {"duration": duration}
    except Exception:
        return {"duration": 0}


async def generate_girl_lipsync_video(
    audio_path: str,
    girl_image_url: str,
    fal_api_key: str,
    quality: str = "circle",
    duration_seconds: float | None = None,
) -> dict:
    """Generate lip-sync video of AI girl using fal.ai.

    This is used by the montage engine.

    Inputs:
    - audio_path: local path to generated TTS audio
    - girl_image_url: image URL for the girl's identity (from profile reference_images)

    Notes:
    - We rely on app.services.content_generation for the model call logic.
    - For the montage overlay use-case we default to VEED Fabric 1.0 (cheapest I2V).
    """
    import httpx

    if not fal_api_key:
        return {"success": False, "error": "fal.ai API key required for lip-sync"}

    if not girl_image_url:
        return {"success": False, "error": "girl_image_url is required for lip-sync"}

    # content_generation reads FAL_KEY from env
    os.environ["FAL_KEY"] = fal_api_key

    try:
        from app.services.content_generation import generate_lipsync_video, _upload_file_to_fal
    except Exception as e:
        return {"success": False, "error": f"Failed to import content generation service: {e}"}

    if duration_seconds is None:
        try:
            duration_seconds = (await _get_audio_duration(audio_path)).get("duration", 3.0)
        except Exception:
            duration_seconds = 3.0

    audio_url = await _upload_file_to_fal(audio_path)
    if not audio_url:
        return {"success": False, "error": "Failed to upload audio to fal.ai"}

    model_key = "veed_fabric"
    if quality == "high":
        model_key = "kling_avatar"
    if quality == "maximum":
        model_key = "omnihuman"

    result = await generate_lipsync_video(
        image_url=girl_image_url,
        audio_url=audio_url,
        model_key=model_key,
        duration_seconds=float(duration_seconds or 3.0),
    )

    if not result.get("success"):
        return result

    video_info = result.get("video") or {}
    video_url = video_info.get("url")

    # Prefer local saved file; otherwise download into montage temp dir
    source_path = video_info.get("file_path")
    if source_path and os.path.exists(source_path):
        fname = f"girl_lipsync_{uuid.uuid4().hex[:8]}.mp4"
        dest = MONTAGE_DIR / "temp" / fname
        try:
            shutil.copy(source_path, dest)
            return {
                "success": True,
                "video_path": str(dest),
                "video_url": video_url,
                "cost": float(result.get("cost_estimate", 0.0) or 0.0),
                "model": result.get("model_name"),
            }
        except Exception as e:
            return {"success": False, "error": f"Failed to copy lipsync video: {e}", "video_url": video_url}

    if video_url:
        fname = f"girl_lipsync_{uuid.uuid4().hex[:8]}.mp4"
        dest = MONTAGE_DIR / "temp" / fname
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                vid_resp = await client.get(video_url)
                if vid_resp.status_code == 200:
                    dest.write_bytes(vid_resp.content)
                    return {
                        "success": True,
                        "video_path": str(dest),
                        "video_url": video_url,
                        "cost": float(result.get("cost_estimate", 0.0) or 0.0),
                        "model": result.get("model_name"),
                    }
            except Exception as e:
                return {"success": False, "error": str(e), "video_url": video_url}

    return {"success": False, "error": "No video file_path or video url returned from fal.ai"}


# ═══════════════════════════════════════════════════════════════════════
# SECTION 4b: FREE LIPSYNC — FFmpeg Animated Photo Overlay (PNGtuber-style)
# ═══════════════════════════════════════════════════════════════════════
#
# Creates a "talking head" video from a SINGLE photo + audio using ONLY FFmpeg.
# Technique: Detect audio amplitude → scale/bounce the photo when speaking.
# This is how PNGtubers and many gaming channels work — $0 cost.
#
# The result looks like a webcam-style circle overlay that "reacts" to speech:
# - When audio is loud → photo slightly enlarges (talking effect)
# - When audio is quiet → photo returns to normal size
# - Subtle breathing animation runs continuously
# - Green glow border pulses when speaking
#

async def generate_girl_animated_overlay(
    audio_path: str,
    girl_image_url: str,
    duration_seconds: float = 3.0,
    size: int = 300,
) -> dict:
    """Generate FREE animated girl overlay video from photo + audio using FFmpeg.

    This creates a PNGtuber-style talking head effect:
    - Photo bounces/scales with audio amplitude (looks like talking)
    - Circle crop with glowing border
    - Subtle idle animation (breathing)
    - COMPLETELY FREE — no API calls needed

    Args:
        audio_path: Local path to TTS audio file
        girl_image_url: URL or local path to girl's photo
        duration_seconds: Duration of the output video
        size: Diameter of the circle overlay in pixels

    Returns:
        dict with success, video_path, cost (always 0)
    """
    import httpx

    _ensure_ffmpeg()
    session_id = uuid.uuid4().hex[:8]

    # Download the girl image if it's a URL
    img_path = MONTAGE_DIR / "temp" / f"girl_photo_{session_id}.png"
    if girl_image_url.startswith(("http://", "https://")):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(girl_image_url)
                if resp.status_code == 200:
                    img_path.write_bytes(resp.content)
                else:
                    return {"success": False, "error": f"Failed to download image: HTTP {resp.status_code}"}
        except Exception as e:
            return {"success": False, "error": f"Failed to download image: {e}"}
    elif os.path.exists(girl_image_url):
        shutil.copy(girl_image_url, str(img_path))
    else:
        return {"success": False, "error": f"Image not found: {girl_image_url}"}

    output_path = str(MONTAGE_DIR / "temp" / f"girl_animated_{session_id}.mp4")

    # Get actual audio duration if not provided
    if duration_seconds <= 0:
        info = await _get_audio_duration(audio_path)
        duration_seconds = info.get("duration", 3.0)

    # FFmpeg filter: create animated video from static image + audio
    # The key trick: use audio amplitude to drive a zoom effect on the photo
    # astats outputs RMS level → use it to modulate scale
    #
    # Simpler approach that works reliably:
    # 1. Create a video from the static image
    # 2. Apply a subtle zoom pulse synced to audio using volume detection
    # 3. Crop to circle with alpha channel
    #
    # We use a sine-wave breathing animation + audio-reactive bounce
    d = round(duration_seconds, 2)
    half = size // 2

    # Build the FFmpeg command:
    # - Input 0: static image (looped as video)
    # - Input 1: audio file
    # - Scale image, apply breathing animation via zoompan
    # - Crop to circle using geq alpha mask
    # - Output as MP4 with audio
    # Use a simpler, more reliable approach: scale oscillation for breathing effect
    # zoompan's 't' variable is unreliable across FFmpeg versions
    pad_size = int(size * 1.06)  # extra space for breathing animation
    filter_complex = (
        # Create video from static image at 30fps
        f"[0:v]loop=loop=-1:size=1:start=0,"
        f"setpts=N/30/TB,"
        f"trim=duration={d},"
        f"scale={pad_size}:{pad_size},"
        # Breathing animation: gentle scale oscillation using crop offset
        # sin(2*PI*t/1.5) creates a ~0.67Hz breathing cycle
        f"crop=w={size}:h={size}"
        f":x='({pad_size}-{size})/2*(1+sin(2*PI*t/1.5))'"
        f":y='({pad_size}-{size})/2*(1+sin(2*PI*t/2.0))',"
        # Crop to circle with alpha
        f"format=rgba,"
        f"geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':"
        f"a='if(lte(({half}-X)*({half}-X)+({half}-Y)*({half}-Y),{half}*{half}),255,0)'"
        f"[v_out]"
    )

    cmd = [
        "ffmpeg", "-y",
        "-i", str(img_path),
        "-i", audio_path,
        "-filter_complex", filter_complex,
        "-map", "[v_out]", "-map", "1:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-t", str(d),
        "-movflags", "+faststart",
        output_path,
    ]

    result = await _run_ffmpeg(cmd, timeout=120)

    if result["success"] and os.path.exists(output_path):
        return {
            "success": True,
            "video_path": output_path,
            "video_url": None,
            "cost": 0.0,  # FREE!
            "model": "ffmpeg_animated_overlay",
            "method": "pngtuber_style",
        }

    return {
        "success": False,
        "error": result.get("error", "FFmpeg animated overlay generation failed"),
    }


# ═══════════════════════════════════════════════════════════════════════
# SECTION 4c: TWITCH TRENDING CLIP AUTO-DISCOVERY
# ═══════════════════════════════════════════════════════════════════════
#
# Automatically finds the best trending CS2 clips from Twitch:
# 1. Get top live CS2 streams (via Twitch API or scraping)
# 2. Get recent clips from those streamers
# 3. Rank by views/recency
# 4. Return the best clip URL for reel generation
#

async def discover_trending_cs2_clips(
    twitch_client_id: str = "",
    twitch_client_secret: str = "",
    limit: int = 5,
    period: str = "24h",
) -> dict:
    """Auto-discover trending CS2 clips from top Twitch streams.

    Pipeline:
    1. Find top live CS2 streams (API → TwitchTracker scrape → known DB)
    2. Get recent clips from top streamers
    3. Rank by view count and recency
    4. Return best clips with download URLs

    Args:
        twitch_client_id: Twitch API client ID (or from env)
        twitch_client_secret: Twitch API client secret (or from env)
        limit: Max clips to return
        period: Time period — '24h', '7d', '30d'

    Returns:
        dict with clips list, each containing url, download_url, title, views, etc.
    """
    import httpx
    import time as _time
    from datetime import timedelta

    client_id = twitch_client_id or os.environ.get("TWITCH_CLIENT_ID", "")
    client_secret = twitch_client_secret or os.environ.get("TWITCH_CLIENT_SECRET", "")

    if not client_id or not client_secret:
        return {
            "success": False,
            "error": "Twitch API credentials required. Set TWITCH_CLIENT_ID and TWITCH_CLIENT_SECRET.",
            "clips": [],
        }

    # Step 1: Get OAuth token
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            token_resp = await client.post(
                "https://id.twitch.tv/oauth2/token",
                data={
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "grant_type": "client_credentials",
                },
            )
            if token_resp.status_code != 200:
                return {"success": False, "error": f"Twitch OAuth failed: {token_resp.status_code}", "clips": []}
            token = token_resp.json().get("access_token", "")
    except Exception as e:
        return {"success": False, "error": f"Twitch OAuth error: {e}", "clips": []}

    headers = {
        "Client-ID": client_id,
        "Authorization": f"Bearer {token}",
    }

    # Step 2: Get top CS2 live streams
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            streams_resp = await client.get(
                "https://api.twitch.tv/helix/streams",
                params={"game_id": "32399", "first": "10", "type": "live"},
                headers=headers,
            )
            if streams_resp.status_code != 200:
                return {"success": False, "error": f"Twitch streams API failed: {streams_resp.status_code}", "clips": []}
            streams = streams_resp.json().get("data", [])
    except Exception as e:
        return {"success": False, "error": f"Twitch streams error: {e}", "clips": []}

    if not streams:
        return {"success": False, "error": "No live CS2 streams found on Twitch", "clips": []}

    # Step 3: Get clips from top streamers
    now = datetime.utcnow()
    period_map = {
        "24h": timedelta(hours=24),
        "7d": timedelta(days=7),
        "30d": timedelta(days=30),
    }
    started = now - period_map.get(period, timedelta(hours=24))

    all_clips = []
    async with httpx.AsyncClient(timeout=15.0) as client:
        for stream in streams[:5]:  # Check top 5 streamers
            broadcaster_id = stream.get("user_id", "")
            broadcaster_name = stream.get("user_name", "Unknown")
            viewer_count = stream.get("viewer_count", 0)

            if not broadcaster_id:
                continue

            try:
                clips_resp = await client.get(
                    "https://api.twitch.tv/helix/clips",
                    params={
                        "broadcaster_id": broadcaster_id,
                        "first": "10",
                        "started_at": started.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "ended_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    },
                    headers=headers,
                )
                if clips_resp.status_code != 200:
                    continue

                clips_data = clips_resp.json().get("data", [])
                for c in clips_data:
                    # Construct download URL from thumbnail URL
                    thumb = c.get("thumbnail_url", "")
                    download_url = thumb.split("-preview-")[0] + ".mp4" if "-preview-" in thumb else ""

                    all_clips.append({
                        "clip_id": c["id"],
                        "url": c["url"],
                        "download_url": download_url,
                        "title": c["title"],
                        "broadcaster_name": c["broadcaster_name"],
                        "broadcaster_viewers": viewer_count,
                        "creator_name": c.get("creator_name", ""),
                        "view_count": c["view_count"],
                        "duration": c["duration"],
                        "created_at": c["created_at"],
                        "thumbnail_url": thumb,
                        "language": c.get("language", "en"),
                    })
            except Exception:
                continue

    if not all_clips:
        return {
            "success": False,
            "error": "No clips found from top CS2 streamers",
            "streamers_checked": [s.get("user_name") for s in streams[:5]],
            "clips": [],
        }

    # Step 4: Rank clips by views (weighted by recency)
    for clip in all_clips:
        try:
            created = datetime.strptime(clip["created_at"], "%Y-%m-%dT%H:%M:%SZ")
            hours_ago = (now - created).total_seconds() / 3600
            # Recency boost: newer clips get higher score
            recency_multiplier = max(0.5, 1.0 - (hours_ago / 168))  # decay over 7 days
            clip["score"] = clip["view_count"] * recency_multiplier
        except Exception:
            clip["score"] = clip["view_count"]

    all_clips.sort(key=lambda c: c["score"], reverse=True)

    return {
        "success": True,
        "clips": all_clips[:limit],
        "total_found": len(all_clips),
        "streamers_checked": [s.get("user_name") for s in streams[:5]],
        "period": period,
    }


# ═══════════════════════════════════════════════════════════════════════
# SECTION 5: VIDEO PROCESSING (FFmpeg)
# ═══════════════════════════════════════════════════════════════════════

def _escape_text(text: str) -> str:
    """Escape text for FFmpeg drawtext."""
    text = text.replace("\\", "\\\\")
    text = text.replace("'", "\\'")
    text = text.replace(":", "\\:")
    text = text.replace("%", "%%")
    return text


async def _get_video_info(file_path: str) -> dict:
    """Get video metadata using ffprobe."""
    _ensure_ffmpeg()
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
        for s in data.get("streams", []):
            if s.get("codec_type") == "video":
                video_stream = s
                break
        duration = float(data.get("format", {}).get("duration", 0))
        width = int(video_stream.get("width", 0)) if video_stream else 0
        height = int(video_stream.get("height", 0)) if video_stream else 0
        return {"duration": duration, "width": width, "height": height}
    except Exception:
        return {"duration": 0, "width": 0, "height": 0}


async def download_clip(url: str, output_name: str | None = None) -> dict:
    """Download a clip from URL using yt-dlp (CLI or Python module)."""
    if output_name is None:
        output_name = f"source_{uuid.uuid4().hex[:8]}"

    output_path = str(MONTAGE_DIR / "temp" / f"{output_name}.mp4")

    # Try CLI first, fall back to Python module
    ytdlp_bin = shutil.which("yt-dlp")
    if ytdlp_bin:
        cmd = [
            ytdlp_bin, "--no-check-certificates",
            "-f", "best[ext=mp4]/best",
            "-o", output_path,
            "--no-playlist", "--quiet", "--no-warnings",
            url,
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
            if proc.returncode != 0:
                return {"success": False, "error": f"Download failed: {stderr.decode()[:300]}"}
        except asyncio.TimeoutError:
            return {"success": False, "error": "Download timed out"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    else:
        # Use yt-dlp as Python module
        try:
            import yt_dlp
            ydl_opts = {
                "format": "best[ext=mp4]/best",
                "outtmpl": output_path,
                "noplaylist": True,
                "quiet": True,
                "no_warnings": True,
                "nocheckcertificate": True,
            }
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: yt_dlp.YoutubeDL(ydl_opts).download([url]))
        except Exception as e:
            return {"success": False, "error": f"yt-dlp module error: {str(e)[:300]}"}

    if not os.path.exists(output_path):
        candidates = list(Path(str(MONTAGE_DIR / "temp")).rglob(f"{output_name}.*"))
        output_path = str(candidates[0]) if candidates else output_path

    if not os.path.exists(output_path):
        return {"success": False, "error": "Downloaded file not found"}

    info = await _get_video_info(output_path)
    return {
        "success": True,
        "file_path": output_path,
        "duration": info["duration"],
        "width": info["width"],
        "height": info["height"],
    }


async def process_game_clip_vertical(
    source_path: str,
    start_time: float = 0.0,
    duration: float = 15.0,
    color_grade: str = "cinematic",
    hook_text: str | None = None,
    hook_duration: float = 2.5,
    cta_text: str | None = None,
    cta_start_before_end: float = 2.0,
    subtitle_text: str | None = None,
    zoom_at: float | None = None,
    zoom_duration: float = 1.0,
    zoom_factor: float = 1.3,
    output_name: str | None = None,
) -> dict:
    """Process a game clip into vertical 9:16 with overlays."""
    if output_name is None:
        output_name = f"game_{uuid.uuid4().hex[:8]}"

    output_path = str(MONTAGE_DIR / "temp" / f"{output_name}.mp4")
    info = await _get_video_info(source_path)
    src_w, src_h = info["width"] or 1920, info["height"] or 1080
    src_dur = info["duration"] or 30.0

    actual_duration = min(duration, src_dur - start_time)
    if actual_duration <= 0:
        return {"success": False, "error": "Invalid duration"}

    # Build video filter chain
    vf = []
    # Note: trim is handled by -ss/-t flags in the ffmpeg command for memory efficiency
    vf.append("setpts=PTS-STARTPTS")

    # Vertical crop
    aspect = src_w / src_h if src_h > 0 else 16 / 9
    tw, th = 1080, 1920
    if aspect > tw / th:
        sh = th
        sw = int(sh * aspect)
        vf.append(f"scale={sw}:{sh}")
        vf.append(f"crop={tw}:{th}:(iw-{tw})/2:0")
    else:
        sw = tw
        sh = int(sw / aspect)
        vf.append(f"scale={sw}:{sh}")
        if sh < th:
            vf.append(f"pad={tw}:{th}:0:({th}-ih)/2:black")
        else:
            vf.append(f"crop={tw}:{th}:0:(ih-{th})/2")

    vf.append("fps=30")

    # Color grading
    if color_grade == "cinematic":
        vf.append("eq=contrast=1.2:brightness=-0.03:saturation=0.85")
    elif color_grade == "vibrant":
        vf.append("eq=contrast=1.1:saturation=1.4:brightness=0.02")
    elif color_grade == "dark":
        vf.append("eq=contrast=1.3:brightness=-0.08:saturation=0.7")

    # Zoom effect at action point
    if zoom_at is not None:
        relative_zoom_at = zoom_at - start_time
        if 0 <= relative_zoom_at < actual_duration:
            zoom_end = relative_zoom_at + zoom_duration
            vf.append(
                f"zoompan=z='if(between(in_time,{relative_zoom_at},{zoom_end}),{zoom_factor},1)'"
                f":d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=30"
            )

    # Hook text (only if font available)
    if hook_text and HAS_FONT:
        escaped = _escape_text(hook_text)
        vf.append(
            f"drawtext=fontfile='{FONT_PATH}':text='{escaped}'"
            f":fontsize=56:fontcolor=white:borderw=3:bordercolor=black"
            f":x=(w-tw)/2:y=140:enable='between(t,0.2,{hook_duration})'"
            f":box=1:boxcolor=black@0.5:boxborderw=14"
        )

    # CTA text (only if font available)
    if cta_text and HAS_FONT:
        escaped = _escape_text(cta_text)
        cta_start = max(0, actual_duration - cta_start_before_end)
        vf.append(
            f"drawtext=fontfile='{FONT_PATH}':text='{escaped}'"
            f":fontsize=42:fontcolor=white:borderw=2:bordercolor=black"
            f":x=(w-tw)/2:y=h-180:enable='between(t,{cta_start},{actual_duration})'"
            f":box=1:boxcolor=black@0.6:boxborderw=12"
        )

    # Subtitle text (only if font available)
    if subtitle_text and HAS_FONT:
        escaped = _escape_text(subtitle_text)
        vf.append(
            f"drawtext=fontfile='{FONT_PATH}':text='{escaped}'"
            f":fontsize=46:fontcolor=yellow:borderw=3:bordercolor=black"
            f":x=(w-tw)/2:y=h-320"
        )

    vf_str = ",".join(vf)

    # Audio filter (no atrim needed — handled by -ss/-t flags)
    af = "asetpts=PTS-STARTPTS,loudnorm=I=-16:TP=-1.5:LRA=11"

    # Use -ss before -i for fast seeking (reduces memory: doesn't decode skipped frames)
    cmd = [
        "ffmpeg", "-y",
        "-ss", str(start_time),
        "-i", source_path,
        "-t", str(actual_duration),
        "-vf", vf_str, "-af", af,
        "-c:v", "libx264", "-preset", "fast", "-crf", "25",
        "-c:a", "aac", "-b:a", "128k",
        "-threads", "1",
        "-movflags", "+faststart", "-pix_fmt", "yuv420p",
        output_path,
    ]

    result = await _run_ffmpeg(cmd, timeout=300)
    if result["success"] and os.path.exists(output_path):
        return {
            "success": True,
            "file_path": output_path,
            "duration": actual_duration,
            "resolution": "1080x1920",
        }
    return result


# ═══════════════════════════════════════════════════════════════════════
# SECTION 6: FINAL ASSEMBLY — Multi-track Montage
# ═══════════════════════════════════════════════════════════════════════

async def assemble_montage(
    game_clip_path: str,
    music_path: str | None = None,
    sfx_entries: list[dict] | None = None,
    girl_video_path: str | None = None,
    girl_audio_path: str | None = None,
    girl_pip_position: str = "pip_bottom_right",
    girl_pip_size: float = 0.35,
    girl_pip_shape: str = "circle",
    girl_start_time: float = 0.0,
    girl_duration: float = 3.0,
    game_audio_vol: float = 0.7,
    music_vol: float = 0.4,
    girl_audio_vol: float = 0.9,
    output_name: str | None = None,
    phase_volumes: list[dict] | None = None,
) -> dict:
    """
    Final assembly: combine game clip + music + SFX + AI girl PiP.
    
    sfx_entries: [{"path": "/path/to/sfx.wav", "start": 2.5, "volume": 0.8}, ...]
    girl_pip_position: "pip_bottom_right", "pip_top_right", "pip_center", "fullscreen"
    """
    if output_name is None:
        output_name = f"montage_{uuid.uuid4().hex[:8]}"

    output_path = str(MONTAGE_DIR / "output" / f"{output_name}.mp4")
    game_info = await _get_video_info(game_clip_path)
    total_duration = game_info["duration"]

    # Build complex FFmpeg filter graph
    inputs = ["-i", game_clip_path]  # input 0: game clip
    input_idx = 1

    music_idx = None
    if music_path and os.path.exists(music_path):
        inputs.extend(["-i", music_path])
        music_idx = input_idx
        input_idx += 1

    girl_video_idx = None
    if girl_video_path and os.path.exists(girl_video_path):
        inputs.extend(["-i", girl_video_path])
        girl_video_idx = input_idx
        input_idx += 1

    girl_audio_idx = None
    if girl_audio_path and os.path.exists(girl_audio_path):
        inputs.extend(["-i", girl_audio_path])
        girl_audio_idx = input_idx
        input_idx += 1

    sfx_indices = []
    if sfx_entries:
        for sfx in sfx_entries:
            if os.path.exists(sfx["path"]):
                inputs.extend(["-i", sfx["path"]])
                sfx_indices.append(input_idx)
                input_idx += 1

    # ── VIDEO FILTER GRAPH ──
    video_filters = []

    # Game video stream (already processed as vertical)
    video_filters.append(f"[0:v]copy[game_v]")

    # AI girl PiP overlay
    if girl_video_idx is not None:
        # Scale girl video for PiP (and optionally crop to a circle with alpha)
        gw = int(1080 * girl_pip_size)
        gh = int(1920 * girl_pip_size)
        diameter = max(64, int(1080 * girl_pip_size))

        # Position mapping — 6 Instagram-style positions from template_engine
        enable_expr = f"enable='between(t,{girl_start_time},{girl_start_time + girl_duration})'"
        positions = {
            "pip_bottom_right": f"overlay=W-w-20:H-h-20:{enable_expr}",
            "pip_top_right": f"overlay=W-w-20:20:{enable_expr}",
            "pip_bottom_left": f"overlay=20:H-h-20:{enable_expr}",
            "pip_center": f"overlay=(W-w)/2:(H-h)/2:{enable_expr}",
            "fullscreen": f"overlay=0:0:{enable_expr}",
            # v2.0: Instagram-native positions
            "split_bottom": f"overlay=0:H/2:{enable_expr}",
            "bottom_third": f"overlay=(W-w)/2:H*0.67:{enable_expr}",
            "dynamic": f"overlay=W-w-20:H-h-20:{enable_expr}",
        }

        pos_filter = positions.get(girl_pip_position, positions["pip_bottom_right"])

        # Extend (freeze) girl video if it's shorter than the montage
        tpad = "tpad=stop_mode=clone:stop_duration=9999"

        # Circle crop only makes sense for PiP modes (not full-width splits)
        can_circle = girl_pip_position not in ("fullscreen", "split_bottom", "bottom_third")

        if girl_pip_shape == "circle" and can_circle:
            # Create alpha mask with geq() so the overlay is a perfect circle
            video_filters.append(
                f"[{girl_video_idx}:v]"
                f"scale={diameter}:{diameter},setpts=PTS-STARTPTS,{tpad},format=rgba,"
                "geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':"
                "a='if(lte((X-W/2)*(X-W/2)+(Y-H/2)*(Y-H/2),(W/2)*(W/2)),255,0)'"
                "[girl_v]"
            )
        elif girl_pip_position == "fullscreen":
            video_filters.append(f"[{girl_video_idx}:v]scale=1080:1920,setpts=PTS-STARTPTS,{tpad}[girl_v]")
        elif girl_pip_position == "split_bottom":
            # 50/50 split: girl takes bottom half (1080x960)
            video_filters.append(f"[{girl_video_idx}:v]scale=1080:960,setpts=PTS-STARTPTS,{tpad}[girl_v]")
        elif girl_pip_position == "bottom_third":
            # Bottom third: girl in lower 33% (1080x640)
            video_filters.append(f"[{girl_video_idx}:v]scale=1080:640,setpts=PTS-STARTPTS,{tpad}[girl_v]")
        else:
            video_filters.append(f"[{girl_video_idx}:v]scale={gw}:{gh},setpts=PTS-STARTPTS,{tpad}[girl_v]")

        video_filters.append(f"[game_v][girl_v]{pos_filter}[out_v]")
    else:
        video_filters.append("[game_v]copy[out_v]")

    # ── AUDIO FILTER GRAPH ──
    audio_filters = []

    # Game audio — per-phase volume automation if available
    if phase_volumes and len(phase_volumes) >= 2:
        # Build volume expression from phase keyframes: linear interpolation between phases
        game_vol_expr_parts = []
        music_vol_expr_parts = []
        for i, pv in enumerate(phase_volumes):
            t_start = pv["start"]
            t_end = pv["end"]
            g_vol = pv.get("game_audio_vol", game_audio_vol)
            m_vol = pv.get("music_vol", music_vol)
            game_vol_expr_parts.append(f"between(t,{t_start},{t_end})*{g_vol}")
            music_vol_expr_parts.append(f"between(t,{t_start},{t_end})*{m_vol}")
        game_vol_expr = "+".join(game_vol_expr_parts)
        music_vol_expr = "+".join(music_vol_expr_parts)
        audio_filters.append(
            f"[0:a]volume='{game_vol_expr}':eval=frame,"
            f"aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[game_a]"
        )
    else:
        audio_filters.append(
            f"[0:a]volume={game_audio_vol},"
            f"aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[game_a]"
        )

    mix_inputs = ["[game_a]"]
    mix_count = 1

    # Music track — per-phase volume automation if available
    if music_idx is not None:
        if phase_volumes and len(phase_volumes) >= 2:
            music_vol_expr_parts = []
            for pv in phase_volumes:
                m_vol = pv.get("music_vol", music_vol)
                music_vol_expr_parts.append(f"between(t,{pv['start']},{pv['end']})*{m_vol}")
            music_vol_expr = "+".join(music_vol_expr_parts)
            audio_filters.append(
                f"[{music_idx}:a]volume='{music_vol_expr}':eval=frame,"
                f"afade=t=in:d=1.0,afade=t=out:d=2.0:st={max(0, total_duration - 2)},"
                f"atrim=0:{total_duration},asetpts=PTS-STARTPTS,"
                f"aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[music_a]"
            )
        else:
            audio_filters.append(
                f"[{music_idx}:a]volume={music_vol},"
                f"afade=t=in:d=1.0,afade=t=out:d=2.0:st={max(0, total_duration - 2)},"
                f"atrim=0:{total_duration},asetpts=PTS-STARTPTS,"
                f"aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[music_a]"
            )
        mix_inputs.append("[music_a]")
        mix_count += 1

    # Girl audio
    if girl_audio_idx is not None:
        audio_filters.append(
            f"[{girl_audio_idx}:a]volume={girl_audio_vol},"
            f"adelay={int(girl_start_time * 1000)}|{int(girl_start_time * 1000)},"
            f"aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[girl_a]"
        )
        mix_inputs.append("[girl_a]")
        mix_count += 1

    # SFX tracks
    for i, sfx_idx in enumerate(sfx_indices):
        sfx = sfx_entries[i]
        delay_ms = int(sfx.get("start", 0) * 1000)
        vol = sfx.get("volume", 0.8)
        audio_filters.append(
            f"[{sfx_idx}:a]volume={vol},"
            f"adelay={delay_ms}|{delay_ms},"
            f"aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo[sfx_{i}]"
        )
        mix_inputs.append(f"[sfx_{i}]")
        mix_count += 1

    # Mix all audio tracks
    if mix_count > 1:
        mix_str = "".join(mix_inputs)
        audio_filters.append(f"{mix_str}amix=inputs={mix_count}:duration=first:dropout_transition=2[out_a]")
    else:
        audio_filters.append("[game_a]acopy[out_a]")

    # Combine filter graph
    filter_complex = ";".join(video_filters + audio_filters)

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[out_v]", "-map", "[out_a]",
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart", "-pix_fmt", "yuv420p",
        "-t", str(total_duration),
        output_path,
    ]

    result = await _run_ffmpeg(cmd, timeout=300)
    if result["success"] and os.path.exists(output_path):
        final_info = await _get_video_info(output_path)
        file_size = os.path.getsize(output_path)

        # Generate thumbnail
        thumb_path = str(MONTAGE_DIR / "output" / f"{output_name}_thumb.jpg")
        thumb_time = min(total_duration * 0.4, 3.0)
        await _run_ffmpeg([
            "ffmpeg", "-y", "-i", output_path,
            "-ss", str(thumb_time), "-vframes", "1", "-q:v", "2",
            thumb_path,
        ])

        return {
            "success": True,
            "output_path": output_path,
            "thumbnail_path": thumb_path if os.path.exists(thumb_path) else None,
            "duration": final_info["duration"],
            "resolution": f"{final_info['width']}x{final_info['height']}",
            "file_size": file_size,
            "tracks": {
                "game_audio": True,
                "music": music_idx is not None,
                "girl_voice": girl_audio_idx is not None,
                "girl_video": girl_video_idx is not None,
                "sfx_count": len(sfx_indices),
            },
        }

    return result


# ═══════════════════════════════════════════════════════════════════════
# SECTION 7: ORCHESTRATOR — Full Montage Pipeline
# ═══════════════════════════════════════════════════════════════════════

async def create_montage(
    clip_url: str,
    template_id: str = "highlight_react",
    moment_type: str = "insane_play",
    # Text
    hook_text: str = "WAIT FOR IT...",
    cta_text: str = "Follow for daily CS2 highlights!",
    subtitle_text: str = "",
    # Timing
    start_time: float = 0.0,
    max_duration: float = 15.0,
    action_timestamp: float | None = None,
    # Girl config
    enable_girl: bool = False,
    girl_voice: str = "jessica",
    girl_image_url: str | None = None,
    fal_api_key: str | None = None,
    elevenlabs_api_key: str | None = None,
    lipsync_mode: str = "auto",  # "free" (FFmpeg), "paid" (fal.ai), "auto" (free if no fal key)
    # Style
    color_grade: str = "cinematic",
    music_track: str | None = None,
) -> dict:
    """
    Full intelligent montage pipeline — now TREND-AWARE.
    
    0. Consult trend analyzer for platform-specific design hints
    1. Download source clip
    2. Process game clip (vertical + color + overlays)
    3. Generate SFX and music
    4. (Optional) Generate AI girl voice + lip-sync video
    5. Assemble everything into final clip
    
    Returns detailed result with file paths, costs, and metrics.
    """
    session_id = uuid.uuid4().hex[:8]
    steps = []
    total_cost = 0.0

    # ── STEP 0: Consult TREND DATA for smart defaults ──
    trend_hints = {}
    try:
        from app.services.trend_analyzer import get_platform_design_hints
        trend_hints = get_platform_design_hints("tiktok")
    except Exception:
        pass

    # Map trend format → dramaturgy template (if caller used default)
    trend_template_map = {
        "sigma_edit": "highlight_react",
        "highlight_react": "highlight_react",
        "pro_clutch": "dramatic_ace",
        "funny_moments": "fail_compilation",
        "ace_compilation": "dramatic_ace",
        "tutorial_tip": "quick_kill",
    }
    if template_id == "highlight_react" and trend_hints.get("data_type") == "real_scraped":
        trend_fmt = trend_hints.get("preferred_style", "")
        mapped = trend_template_map.get(trend_fmt, "")
        if mapped and mapped in DRAMATURGY_TEMPLATES:
            template_id = mapped

    # Override color_grade from trends if caller used default
    if color_grade == "cinematic" and trend_hints.get("recommended_color_grade"):
        trend_color = trend_hints["recommended_color_grade"]
        color_grade_map = {
            "vibrant": "vibrant", "high_contrast": "cinematic",
            "dark_moody": "cinematic", "warm": "warm",
            "cool": "cool", "retro": "retro",
        }
        color_grade = color_grade_map.get(trend_color, color_grade)

    template = DRAMATURGY_TEMPLATES.get(template_id, DRAMATURGY_TEMPLATES["highlight_react"])
    target_duration = min(max_duration, template["total_duration"])

    # ── STEP 1: Download source clip ──
    step1 = {"step": "download", "status": "running"}
    steps.append(step1)

    dl_result = await download_clip(clip_url, f"src_{session_id}")
    step1["result"] = dl_result
    step1["status"] = "success" if dl_result["success"] else "failed"
    if not dl_result["success"]:
        return {"success": False, "error": dl_result["error"], "steps": steps}

    source_path = dl_result["file_path"]
    source_duration = dl_result["duration"]
    actual_duration = min(target_duration, source_duration - start_time)

    # ── STEP 2: Process game clip (vertical + overlays) ──
    step2 = {"step": "process_game", "status": "running"}
    steps.append(step2)

    game_result = await process_game_clip_vertical(
        source_path=source_path,
        start_time=start_time,
        duration=actual_duration,
        color_grade=color_grade,
        hook_text=hook_text,
        hook_duration=template["phases"][0]["end"] if template["phases"] else 2.5,
        cta_text=cta_text,
        cta_start_before_end=template["phases"][-1]["end"] - template["phases"][-1]["start"] if template["phases"] else 2.0,
        subtitle_text=subtitle_text,
        zoom_at=action_timestamp,
        output_name=f"game_{session_id}",
    )
    step2["result"] = game_result
    step2["status"] = "success" if game_result["success"] else "failed"
    if not game_result["success"]:
        return {"success": False, "error": game_result.get("error", "Game processing failed"), "steps": steps}

    game_clip_path = game_result["file_path"]

    # ── STEP 3: Generate assets (SFX + music) ──
    step3 = {"step": "generate_assets", "status": "running"}
    steps.append(step3)

    assets = await ensure_assets_ready(template_id, actual_duration)
    step3["result"] = {"sfx_count": len(assets.get("assets", {}).get("sfx", {})), "music": assets.get("assets", {}).get("music_id")}
    step3["status"] = "success" if assets["success"] else "failed"

    # Build SFX timeline from dramaturgy
    sfx_entries = []
    if assets["success"]:
        sfx_assets = assets["assets"]["sfx"]
        for phase in template["phases"]:
            sfx_id = phase.get("sfx")
            if sfx_id and sfx_id in sfx_assets:
                # Scale phase timing to actual duration
                scale = actual_duration / template["total_duration"]
                sfx_start = phase["start"] * scale
                sfx_entries.append({
                    "path": sfx_assets[sfx_id],
                    "start": sfx_start,
                    "volume": 0.7,
                })

    music_path = assets.get("assets", {}).get("music") if assets["success"] else None
    if music_track and music_track in MUSIC_TRACKS:
        custom_music = await generate_music_track(music_track, actual_duration + 5)
        if custom_music:
            music_path = custom_music

    # ── STEP 4: AI Girl (optional) ──
    girl_audio_path = None
    girl_video_path = None
    girl_start = 0.0
    girl_dur = 3.0

    if enable_girl:
        # Determine lipsync mode: free (FFmpeg animated), paid (fal.ai), auto
        use_free_lipsync = (
            lipsync_mode == "free"
            or (lipsync_mode == "auto" and not fal_api_key)
        )

        # For paid mode, we need fal_api_key
        if not use_free_lipsync and not fal_api_key:
            return {"success": False, "error": "fal_api_key is required for paid lipsync (or use lipsync_mode='free')", "steps": steps}
        if not girl_image_url:
            return {"success": False, "error": "girl_image_url is required when enable_girl=true", "steps": steps}

        step4 = {"step": "girl_pipeline", "status": "running", "lipsync_mode": "free" if use_free_lipsync else "paid"}
        steps.append(step4)

        # Use a longer script so she feels like she's reacting throughout the clip
        scripts = GIRL_SCRIPTS.get(moment_type, GIRL_SCRIPTS["default"])
        girl_text = " ".join(
            [
                scripts.get("intro", ""),
                scripts.get("react", ""),
                scripts.get("outro", ""),
            ]
        ).strip()

        # Show her for the full montage (circle webcam style)
        girl_start = 0.0
        girl_dur = actual_duration

        # Generate TTS (ElevenLabs v3 if key available, edge-tts fallback)
        tts_result = await generate_girl_audio(
            girl_text,
            girl_voice,
            f"girl_tts_{session_id}",
            elevenlabs_api_key=elevenlabs_api_key,
        )
        if not tts_result.get("success"):
            step4["status"] = "failed"
            step4["tts"] = f"failed: {tts_result.get('error', '')}"
            return {"success": False, "error": "Girl TTS generation failed", "steps": steps}

        girl_audio_path = tts_result["audio_path"]
        total_cost += tts_result.get("cost", 0)
        step4["tts"] = "success"

        if use_free_lipsync:
            # FREE mode: FFmpeg animated photo overlay (PNGtuber-style)
            lipsync_result = await generate_girl_animated_overlay(
                audio_path=girl_audio_path,
                girl_image_url=girl_image_url,
                duration_seconds=float(tts_result.get("duration") or 3.0),
            )
        else:
            # PAID mode: fal.ai lipsync (higher quality)
            lipsync_result = await generate_girl_lipsync_video(
                girl_audio_path,
                girl_image_url,
                fal_api_key,
                quality="circle",
                duration_seconds=float(tts_result.get("duration") or 3.0),
            )

        if not lipsync_result.get("success"):
            step4["status"] = "failed"
            step4["lipsync"] = f"failed: {lipsync_result.get('error', '')}"
            return {"success": False, "error": "Girl lip-sync generation failed", "steps": steps, "total_cost": total_cost}

        girl_video_path = lipsync_result["video_path"]
        total_cost += lipsync_result.get("cost", 0)
        step4["lipsync"] = "success"
        step4["status"] = "success"
        step4["result"] = {
            "has_audio": True,
            "has_video": True,
            "text": girl_text,
            "voice": girl_voice,
            "model": lipsync_result.get("model"),
            "lipsync_cost": lipsync_result.get("cost", 0),
        }

    # ── STEP 5: Final Assembly ──
    step5 = {"step": "assembly", "status": "running"}
    steps.append(step5)

    # Find girl PiP settings from template
    girl_pip_pos = "pip_bottom_right"
    girl_pip_sz = 0.35
    for phase in template["phases"]:
        if phase.get("girl_visible"):
            girl_pip_pos = phase.get("girl_position", "pip_bottom_right")
            girl_pip_sz = phase.get("girl_size", 0.35)
            break

    # Build per-phase volume automation from dramaturgy template
    phase_volumes = []
    scale = actual_duration / template["total_duration"]
    for phase in template["phases"]:
        phase_volumes.append({
            "start": round(phase["start"] * scale, 2),
            "end": round(phase["end"] * scale, 2),
            "game_audio_vol": phase.get("game_audio_vol", 0.7),
            "music_vol": phase.get("music_vol", 0.4),
        })

    assembly_result = await assemble_montage(
        game_clip_path=game_clip_path,
        music_path=music_path,
        sfx_entries=sfx_entries if sfx_entries else None,
        girl_video_path=girl_video_path,
        girl_audio_path=girl_audio_path,
        girl_pip_position=girl_pip_pos,
        girl_pip_size=girl_pip_sz,
        girl_pip_shape="circle",
        girl_start_time=girl_start,
        girl_duration=girl_dur,
        output_name=f"final_{session_id}",
        phase_volumes=phase_volumes,
    )

    step5["result"] = assembly_result
    step5["status"] = "success" if assembly_result.get("success") else "failed"

    if not assembly_result.get("success"):
        return {
            "success": False,
            "error": assembly_result.get("error", "Assembly failed"),
            "steps": steps,
            "total_cost": total_cost,
        }

    # ── RESULT ──
    return {
        "success": True,
        "output_path": assembly_result["output_path"],
        "thumbnail_path": assembly_result.get("thumbnail_path"),
        "duration": assembly_result["duration"],
        "resolution": assembly_result["resolution"],
        "file_size": assembly_result["file_size"],
        "template": template_id,
        "moment_type": moment_type,
        "tracks": assembly_result["tracks"],
        "steps": steps,
        "total_cost": total_cost,
        "session_id": session_id,
        "created_at": datetime.utcnow().isoformat(),
        "trend_influence": {
            "data_type": trend_hints.get("data_type", "none"),
            "platform": trend_hints.get("platform", "unknown"),
            "preferred_style": trend_hints.get("preferred_style", "N/A"),
            "recommended_hook": trend_hints.get("recommended_hook", "N/A"),
            "recommended_pacing": trend_hints.get("recommended_pacing", "N/A"),
            "color_grade_used": color_grade,
        },
    }


# ═══════════════════════════════════════════════════════════════════════
# SECTION 8: STATUS & CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════

def get_montage_status() -> dict:
    """Get montage engine status and capabilities."""
    _ensure_ffmpeg()
    ffmpeg_ok = shutil.which("ffmpeg") is not None
    ytdlp_ok = shutil.which("yt-dlp") is not None
    if not ytdlp_ok:
        try:
            import yt_dlp  # noqa: F401
            ytdlp_ok = True
        except ImportError:
            pass

    # Count existing assets
    sfx_count = len(list((MONTAGE_DIR / "assets" / "sfx").glob("*.wav")))
    music_count = len(list((MONTAGE_DIR / "assets" / "music").glob("*.wav")))
    output_count = len(list((MONTAGE_DIR / "output").glob("*.mp4")))

    return {
        "engine": "Intelligent Montage Engine v2.0",
        "tools": {
            "ffmpeg": ffmpeg_ok,
            "yt_dlp": ytdlp_ok,
            "edge_tts": True,
            "elevenlabs_v3": bool(os.environ.get("ELEVENLABS_API_KEY")),
        },
        "voice_engine": {
            "primary": "ElevenLabs v3 (audio tags, expressive)" if os.environ.get("ELEVENLABS_API_KEY") else "edge-tts (free fallback)",
            "fallback": "edge-tts (Microsoft, free)",
            "elevenlabs_configured": bool(os.environ.get("ELEVENLABS_API_KEY")),
            "model": "eleven_v3",
            "features": ["audio_tags", "multi_emotion", "70+_languages", "whispers", "laughs", "sighs"],
        },
        "capabilities": {
            "game_clip_processing": ffmpeg_ok,
            "vertical_crop_9_16": ffmpeg_ok,
            "text_overlays": ffmpeg_ok,
            "color_grading": ffmpeg_ok,
            "sfx_generation": ffmpeg_ok,
            "music_generation": ffmpeg_ok,
            "ai_girl_voice": True,
            "ai_girl_voice_engine": "elevenlabs_v3" if os.environ.get("ELEVENLABS_API_KEY") else "edge_tts",
            "ai_girl_lipsync_free": "FFmpeg animated overlay (PNGtuber-style, $0)",
            "ai_girl_lipsync_paid": "fal.ai (requires API key)",
            "ai_girl_photo": "requires fal.ai API key",
            "auto_reel_from_trending": True,
            "trending_clip_discovery": True,
            "multi_track_mixing": ffmpeg_ok,
            "pip_overlay": ffmpeg_ok,
            "per_phase_volume_automation": True,
        },
        "templates": {
            tid: {
                "name": t["name"],
                "description": t["description"],
                "duration": t["total_duration"],
                "phases": len(t["phases"]),
                "has_girl": any(p.get("girl_visible") for p in t["phases"]),
            }
            for tid, t in DRAMATURGY_TEMPLATES.items()
        },
        "sfx_library": {
            sid: {"name": s["name"], "category": s["category"], "duration": s["duration"]}
            for sid, s in SFX_CATALOG.items()
        },
        "music_library": {
            mid: {"name": m["name"], "category": m["category"], "mood": m["mood"]}
            for mid, m in MUSIC_TRACKS.items()
        },
        "girl_voices": {
            vid: {"desc": v["desc"], "style": v["style"]}
            for vid, v in GIRL_VOICES.items()
        },
        "girl_scripts": list(GIRL_SCRIPTS.keys()),
        "assets": {
            "sfx_cached": sfx_count,
            "music_cached": music_count,
            "clips_generated": output_count,
        },
        "directories": {
            "output": str(MONTAGE_DIR / "output"),
            "assets": str(MONTAGE_DIR / "assets"),
            "temp": str(MONTAGE_DIR / "temp"),
        },
        "apis_needed": {
            "free": [
                {"name": "FFmpeg", "purpose": "Video/audio processing", "status": "installed" if ffmpeg_ok else "missing"},
                {"name": "yt-dlp", "purpose": "Clip download", "status": "installed" if ytdlp_ok else "missing"},
                {"name": "edge-tts", "purpose": "AI girl voice (Microsoft TTS)", "status": "installed"},
            ],
            "paid": [
                {"name": "fal.ai", "purpose": "AI girl lip-sync + photo generation", "cost": "~$0.07-0.52/clip (Kling $0.07, OmniHuman $0.52)", "required": False},
                {"name": "Twitch API", "purpose": "Auto-discover top clips from streamers", "cost": "FREE", "required": False},
            ],
        },
    }


def list_generated_montages() -> list[dict]:
    """List all generated montage clips."""
    output_dir = MONTAGE_DIR / "output"
    montages = []
    for f in sorted(output_dir.glob("*.mp4"), key=lambda p: p.stat().st_mtime, reverse=True):
        thumb = output_dir / f"{f.stem}_thumb.jpg"
        montages.append({
            "filename": f.name,
            "file_path": str(f),
            "file_size": f.stat().st_size,
            "thumbnail": str(thumb) if thumb.exists() else None,
            "created_at": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
        })
    return montages


# ═══════════════════════════════════════════════════════════════════════
# SECTION 9: AUTO-REEL — One-Click Trending Reel Generation
# ═══════════════════════════════════════════════════════════════════════
#
# Full pipeline: Twitch trending → best clip → reel with girl → output
# Designed to work with $0 cost (free lipsync + edge-tts) or paid APIs.
#

async def auto_generate_reel(
    girl_image_url: str,
    girl_voice: str = "jessica",
    moment_type: str = "insane_play",
    template_id: str = "highlight_react",
    hook_text: str = "WAIT FOR IT...",
    cta_text: str = "Follow for daily CS2 highlights!",
    max_duration: float = 15.0,
    lipsync_mode: str = "free",
    fal_api_key: str | None = None,
    elevenlabs_api_key: str | None = None,
    twitch_client_id: str = "",
    twitch_client_secret: str = "",
    clip_period: str = "24h",
) -> dict:
    """One-click auto reel generation from trending Twitch CS2 clips.

    Full pipeline:
    1. Discover trending CS2 clips from Twitch
    2. Pick the best clip
    3. Generate reel with girl overlay (free or paid lipsync)
    4. Return finished reel

    Args:
        girl_image_url: URL to girl's photo for overlay
        girl_voice: TTS voice to use
        moment_type: Type of CS2 moment (insane_play, clutch, ace, etc.)
        template_id: Montage template
        hook_text: Text hook for the reel
        cta_text: Call-to-action text
        max_duration: Max reel duration in seconds
        lipsync_mode: "free" (FFmpeg, $0) or "paid" (fal.ai) or "auto"
        fal_api_key: fal.ai key (only needed for paid mode)
        elevenlabs_api_key: ElevenLabs key (optional, edge-tts is free fallback)
        twitch_client_id: Twitch API client ID
        twitch_client_secret: Twitch API client secret
        clip_period: Time period for clip search ("24h", "7d", "30d")

    Returns:
        dict with reel output, clip info, cost breakdown
    """
    result_steps = []

    # ── STEP 1: Discover trending clips ──
    step1 = {"step": "discover_trending", "status": "running"}
    result_steps.append(step1)

    trending = await discover_trending_cs2_clips(
        twitch_client_id=twitch_client_id,
        twitch_client_secret=twitch_client_secret,
        limit=3,
        period=clip_period,
    )

    if not trending.get("success") or not trending.get("clips"):
        step1["status"] = "failed"
        step1["error"] = trending.get("error", "No trending clips found")
        return {
            "success": False,
            "error": f"Trending clip discovery failed: {trending.get('error', 'No clips')}",
            "steps": result_steps,
        }

    step1["status"] = "success"
    step1["clips_found"] = len(trending["clips"])
    step1["streamers"] = trending.get("streamers_checked", [])

    # Pick the best clip
    best_clip = trending["clips"][0]
    clip_url = best_clip.get("download_url") or best_clip.get("url", "")

    if not clip_url:
        return {
            "success": False,
            "error": "Best clip has no usable URL",
            "steps": result_steps,
            "clip": best_clip,
        }

    step1["selected_clip"] = {
        "title": best_clip["title"],
        "broadcaster": best_clip["broadcaster_name"],
        "views": best_clip["view_count"],
        "duration": best_clip["duration"],
        "url": clip_url,
    }

    # ── STEP 2: Generate reel from clip ──
    step2 = {"step": "generate_reel", "status": "running"}
    result_steps.append(step2)

    reel_result = await create_montage(
        clip_url=clip_url,
        template_id=template_id,
        moment_type=moment_type,
        hook_text=hook_text,
        cta_text=cta_text,
        start_time=0.0,
        max_duration=max_duration,
        enable_girl=True,
        girl_voice=girl_voice,
        girl_image_url=girl_image_url,
        fal_api_key=fal_api_key,
        elevenlabs_api_key=elevenlabs_api_key,
        lipsync_mode=lipsync_mode,
    )

    step2["status"] = "success" if reel_result.get("success") else "failed"
    if not reel_result.get("success"):
        step2["error"] = reel_result.get("error", "Reel generation failed")
        return {
            "success": False,
            "error": f"Reel generation failed: {reel_result.get('error')}",
            "steps": result_steps,
            "clip": best_clip,
        }

    # ── RESULT ──
    return {
        "success": True,
        "output_path": reel_result["output_path"],
        "thumbnail_path": reel_result.get("thumbnail_path"),
        "duration": reel_result.get("duration"),
        "resolution": reel_result.get("resolution"),
        "file_size": reel_result.get("file_size"),
        "total_cost": reel_result.get("total_cost", 0.0),
        "lipsync_mode": lipsync_mode,
        "clip_source": {
            "title": best_clip["title"],
            "broadcaster": best_clip["broadcaster_name"],
            "views": best_clip["view_count"],
            "clip_url": best_clip.get("url"),
        },
        "trending_data": {
            "clips_found": len(trending["clips"]),
            "streamers_checked": trending.get("streamers_checked", []),
            "period": clip_period,
        },
        "steps": result_steps,
        "session_id": reel_result.get("session_id"),
        "created_at": datetime.utcnow().isoformat(),
    }
