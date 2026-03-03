"""
Content Generator Service
Handles clip assembly pipeline configuration: overlays, subtitles, zooms, sound effects, thumbnails.

This module generates pipeline CONFIGURATION (JSON instructions) for the FFmpeg executor.
Actual video processing is performed by clip_montage.py and clip_executor.py using real FFmpeg.
"""
import json
import random


DRAMATURGY_STRUCTURE = {
    "clean_highlight": ["hook", "build", "kill_sequence", "outro"],
    "highlight_reaction": ["hook", "build", "kill_sequence", "reaction", "outro"],
    "highlight_subtitles": ["hook", "commentary", "kill_sequence", "reaction_text", "outro"],
    "highlight_ai_girl": ["ai_intro", "build", "kill_sequence", "ai_reaction", "outro"],
    "meme_format": ["meme_hook", "setup", "punchline", "meme_outro"],
    "dramatic_clutch": ["dramatic_hook", "situation_setup", "tension_build", "slow_mo_kill", "explosion", "reaction", "outro"],
    "provocative": ["provocative_hook", "context", "kill_sequence", "reveal", "cta"],
    "hard_fragmovie": ["beat_intro", "kill_1", "transition", "kill_2", "beat_drop", "multi_kill", "outro"],
    "fail_format": ["expectation_hook", "buildup", "fail_moment", "replay_slow", "comedy_sound", "outro"],
}

EFFECT_PRESETS = {
    "zoom_kill": {"type": "zoom", "intensity": 1.3, "duration": 0.3, "ease": "ease-out"},
    "zoom_headshot": {"type": "zoom", "intensity": 1.5, "duration": 0.2, "ease": "snap"},
    "slow_mo": {"type": "speed", "factor": 0.3, "duration": 2.0},
    "speed_ramp": {"type": "speed", "factor": 2.0, "duration": 0.5},
    "shake": {"type": "camera_shake", "intensity": 5, "duration": 0.3},
    "flash": {"type": "flash", "color": "white", "duration": 0.1},
    "color_grade_cinematic": {"type": "color", "contrast": 1.3, "saturation": 0.8, "temperature": -10},
    "color_grade_vibrant": {"type": "color", "contrast": 1.1, "saturation": 1.3, "temperature": 5},
}


async def generate_clip_pipeline(db, clip_id: int) -> dict:
    """
    Generate the full editing pipeline for a clip.
    Returns the pipeline configuration that would be used by FFmpeg.
    """
    cursor = await db.execute(
        """SELECT c.*, t.config as template_config, t.format_type as tmpl_format,
           m.moment_type, m.metadata as moment_metadata
           FROM clips c
           LEFT JOIN templates t ON c.template_id = t.id
           LEFT JOIN moments m ON c.moment_id = m.id
           WHERE c.id = ?""",
        (clip_id,),
    )
    clip = await cursor.fetchone()
    if not clip:
        return {"error": "Clip not found"}

    format_type = clip["format_type"]
    structure = DRAMATURGY_STRUCTURE.get(format_type, ["hook", "kill_sequence", "outro"])

    pipeline = {
        "clip_id": clip_id,
        "format_type": format_type,
        "duration": clip["duration"],
        "resolution": "1080x1920",  # Vertical for Reels/Shorts/TikTok
        "fps": 60,
        "structure": structure,
        "segments": [],
        "effects": [],
        "audio_tracks": [],
        "overlays": [],
    }

    # Build segments based on structure
    segment_duration = clip["duration"] / len(structure)
    current_time = 0.0

    for i, segment_type in enumerate(structure):
        segment = {
            "type": segment_type,
            "start": round(current_time, 2),
            "end": round(current_time + segment_duration, 2),
            "effects": [],
        }

        # Add effects based on segment type
        if "hook" in segment_type:
            segment["effects"].append(EFFECT_PRESETS["zoom_kill"])
            if clip["hook_text"]:
                pipeline["overlays"].append({
                    "type": "text",
                    "text": clip["hook_text"],
                    "start": current_time,
                    "end": current_time + 2.0,
                    "position": "center",
                    "style": "bold_large",
                    "animation": "scale_in",
                })

        if "kill" in segment_type:
            segment["effects"].append(EFFECT_PRESETS["zoom_headshot"])
            segment["effects"].append(EFFECT_PRESETS["shake"])
            segment["effects"].append(EFFECT_PRESETS["flash"])

        if "slow_mo" in segment_type:
            segment["effects"].append(EFFECT_PRESETS["slow_mo"])

        if "reaction" in segment_type and clip["has_face_cam"]:
            pipeline["overlays"].append({
                "type": "face_cam",
                "start": current_time,
                "end": current_time + segment_duration,
                "position": "top-right",
                "size": 0.2,
                "border": True,
            })

        if "outro" in segment_type and clip["cta_text"]:
            pipeline["overlays"].append({
                "type": "text",
                "text": clip["cta_text"],
                "start": current_time,
                "end": current_time + segment_duration,
                "position": "bottom",
                "style": "cta",
                "animation": "slide_up",
            })

        pipeline["segments"].append(segment)
        current_time += segment_duration

    # Add subtitles if enabled
    if clip["has_subtitles"]:
        pipeline["overlays"].append({
            "type": "subtitles",
            "style": "bold_dynamic",
            "font_size": 48,
            "color": "#FFFFFF",
            "stroke_color": "#000000",
            "stroke_width": 3,
            "position": "center-bottom",
            "animation": "word_by_word",
        })

    # Add AI girl overlay if enabled
    if clip["has_ai_girl"]:
        pipeline["overlays"].append({
            "type": "ai_girl",
            "position": "bottom-right",
            "size": 0.25,
            "animation": "talking",
            "voice_style": "energetic",
        })

    # Add audio tracks
    pipeline["audio_tracks"].append({
        "type": "game_audio",
        "volume": 0.7,
    })

    if format_type in ("dramatic_clutch", "hard_fragmovie"):
        pipeline["audio_tracks"].append({
            "type": "music",
            "style": "dramatic" if format_type == "dramatic_clutch" else "electronic",
            "volume": 0.4,
            "beat_sync": format_type == "hard_fragmovie",
        })

    if format_type == "meme_format":
        pipeline["audio_tracks"].append({
            "type": "sound_effects",
            "effects": ["vine_boom", "bruh", "metal_pipe"],
            "volume": 0.6,
        })

    # Add color grading for fragmovie
    if format_type == "hard_fragmovie":
        pipeline["effects"].append(EFFECT_PRESETS["color_grade_cinematic"])

    # Update clip status
    await db.execute(
        "UPDATE clips SET status = 'pipeline_ready' WHERE id = ?", (clip_id,)
    )
    await db.commit()

    return pipeline


async def get_dramaturgy_templates() -> dict:
    """Return all dramaturgy structure templates."""
    return DRAMATURGY_STRUCTURE
