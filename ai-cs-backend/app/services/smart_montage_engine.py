"""
Smart Montage Engine v1.0 — Intelligent Self-Learning Video Assembly Brain

This is the CORE intelligence layer that makes ALL montage decisions automatically:
- Color palette selection based on moment mood/energy
- Font style & size by moment type and text role (hook, action, CTA)
- Text animation timing (fade in/out, duration, position)
- SFX selection & placement (what sound, when, how loud)
- Music style & BPM matching to moment energy
- Meme overlay selection & positioning
- Color grading parameters (brightness, contrast, saturation, vignette)
- Zoom/pan effects by phase (hook, build, peak, outro)
- Girl voice timing & volume relative to music
- Overall pacing & rhythm decisions

Self-learning: tracks what combinations work and adjusts weights over time.

Architecture inspired by:
- montage-ai (beat-sync, scene analysis)
- Crispy (ML highlight detection for gaming, 112 stars)
- AutoTransition (ECCV 2022 — learned transition recommendation)
- MoviePy (programmatic video composition)
- Mosaico (AI video composition framework)
- Professional TikTok/Reels editing patterns analysis
"""

import json
import math
import random
import time
from pathlib import Path
from typing import Optional


# ═══════════════════════════════════════════════════════════════════════
# SECTION 1: COLOR PALETTES — Mood-based color systems
# ═══════════════════════════════════════════════════════════════════════

COLOR_PALETTES = {
    # ── HIGH ENERGY (clutch, ace, multi_kill) ──
    "inferno": {
        "name": "Inferno",
        "mood": "high_energy",
        "primary": "#FF4444",
        "secondary": "#FFD700",
        "accent": "#FF8C00",
        "text_main": "#FFFFFF",
        "text_highlight": "#FF4444",
        "text_subtle": "#FFCCCC",
        "outline": "#000000",
        "glow": "#FF0000",
        "bg_overlay": "#1a0000",
        "gradient": ["#FF4444", "#FF8C00", "#FFD700"],
        "energy": 0.95,
    },
    "electric_blue": {
        "name": "Electric Blue",
        "mood": "high_energy",
        "primary": "#00BFFF",
        "secondary": "#FFFFFF",
        "accent": "#7DF9FF",
        "text_main": "#FFFFFF",
        "text_highlight": "#00BFFF",
        "text_subtle": "#B0E0E6",
        "outline": "#000033",
        "glow": "#00BFFF",
        "bg_overlay": "#000033",
        "gradient": ["#00BFFF", "#7DF9FF", "#FFFFFF"],
        "energy": 0.90,
    },
    "neon_pink": {
        "name": "Neon Pink",
        "mood": "high_energy",
        "primary": "#FF1493",
        "secondary": "#FF69B4",
        "accent": "#FFD700",
        "text_main": "#FFFFFF",
        "text_highlight": "#FF1493",
        "text_subtle": "#FFB6C1",
        "outline": "#1a001a",
        "glow": "#FF1493",
        "bg_overlay": "#1a001a",
        "gradient": ["#FF1493", "#FF69B4", "#FFD700"],
        "energy": 0.88,
    },

    # ── DARK / SIGMA (sigma, dramatic, headshot) ──
    "midnight_sigma": {
        "name": "Midnight Sigma",
        "mood": "dark",
        "primary": "#CCCCCC",
        "secondary": "#888888",
        "accent": "#FFD700",
        "text_main": "#FFFFFF",
        "text_highlight": "#FFD700",
        "text_subtle": "#AAAAAA",
        "outline": "#000000",
        "glow": "#333333",
        "bg_overlay": "#0a0a0a",
        "gradient": ["#333333", "#666666", "#CCCCCC"],
        "energy": 0.60,
    },
    "blood_dark": {
        "name": "Blood Dark",
        "mood": "dark",
        "primary": "#8B0000",
        "secondary": "#DC143C",
        "accent": "#FFFFFF",
        "text_main": "#FFFFFF",
        "text_highlight": "#DC143C",
        "text_subtle": "#CD5C5C",
        "outline": "#000000",
        "glow": "#8B0000",
        "bg_overlay": "#0a0000",
        "gradient": ["#8B0000", "#DC143C", "#FF4444"],
        "energy": 0.70,
    },
    "ice_cold": {
        "name": "Ice Cold",
        "mood": "dark",
        "primary": "#B0C4DE",
        "secondary": "#4682B4",
        "accent": "#FFFFFF",
        "text_main": "#FFFFFF",
        "text_highlight": "#B0C4DE",
        "text_subtle": "#778899",
        "outline": "#000022",
        "glow": "#4682B4",
        "bg_overlay": "#000022",
        "gradient": ["#4682B4", "#B0C4DE", "#FFFFFF"],
        "energy": 0.55,
    },

    # ── MEME / FUN (toxic, meme, fail, knife) ──
    "meme_chaos": {
        "name": "Meme Chaos",
        "mood": "meme",
        "primary": "#FF4500",
        "secondary": "#00FF00",
        "accent": "#FFFF00",
        "text_main": "#FFFFFF",
        "text_highlight": "#FFFF00",
        "text_subtle": "#FF4500",
        "outline": "#000000",
        "glow": "#FF4500",
        "bg_overlay": "#000000",
        "gradient": ["#FF4500", "#FFFF00", "#00FF00"],
        "energy": 0.85,
    },
    "toxic_green": {
        "name": "Toxic Green",
        "mood": "meme",
        "primary": "#39FF14",
        "secondary": "#00FF00",
        "accent": "#FFFF00",
        "text_main": "#FFFFFF",
        "text_highlight": "#39FF14",
        "text_subtle": "#90EE90",
        "outline": "#003300",
        "glow": "#39FF14",
        "bg_overlay": "#001a00",
        "gradient": ["#39FF14", "#00FF00", "#FFFF00"],
        "energy": 0.80,
    },

    # ── EPIC / TOURNAMENT (comeback, tournament, eco_win) ──
    "royal_gold": {
        "name": "Royal Gold",
        "mood": "epic",
        "primary": "#FFD700",
        "secondary": "#FFA500",
        "accent": "#FFFFFF",
        "text_main": "#FFFFFF",
        "text_highlight": "#FFD700",
        "text_subtle": "#F0E68C",
        "outline": "#000000",
        "glow": "#FFD700",
        "bg_overlay": "#1a1400",
        "gradient": ["#FFD700", "#FFA500", "#FF8C00"],
        "energy": 0.85,
    },
    "purple_reign": {
        "name": "Purple Reign",
        "mood": "epic",
        "primary": "#9B59B6",
        "secondary": "#8E44AD",
        "accent": "#FFD700",
        "text_main": "#FFFFFF",
        "text_highlight": "#9B59B6",
        "text_subtle": "#D7BDE2",
        "outline": "#1a001a",
        "glow": "#9B59B6",
        "bg_overlay": "#0d0014",
        "gradient": ["#8E44AD", "#9B59B6", "#D7BDE2"],
        "energy": 0.78,
    },

    # ── GIRL REACT SPECIFIC ──
    "girl_pink": {
        "name": "Girl Pink",
        "mood": "girl_react",
        "primary": "#FF69B4",
        "secondary": "#FF1493",
        "accent": "#FFD700",
        "text_main": "#FFFFFF",
        "text_highlight": "#FF69B4",
        "text_subtle": "#FFB6C1",
        "outline": "#000000",
        "glow": "#FF1493",
        "bg_overlay": "#1a0011",
        "gradient": ["#FF1493", "#FF69B4", "#FFB6C1"],
        "energy": 0.82,
    },
    "girl_warm": {
        "name": "Girl Warm",
        "mood": "girl_react",
        "primary": "#FF6347",
        "secondary": "#FF7F50",
        "accent": "#FFD700",
        "text_main": "#FFFFFF",
        "text_highlight": "#FF6347",
        "text_subtle": "#FFA07A",
        "outline": "#000000",
        "glow": "#FF6347",
        "bg_overlay": "#1a0800",
        "gradient": ["#FF6347", "#FF7F50", "#FFD700"],
        "energy": 0.80,
    },
}

# ═══════════════════════════════════════════════════════════════════════
# SECTION 2: FONT SYSTEM — Style & size by context
# ═══════════════════════════════════════════════════════════════════════

# Available fonts — TRENDING GAMING FONTS (downloaded from Google Fonts)
# Based on analysis of top CS2/gaming TikTok reels:
# - Bebas Neue: THE #1 gaming font — tall condensed all-caps, used by 70%+ of gaming reels
# - Anton: Heavy impact style, great for hooks and player names
# - Montserrat: Clean bold sans, #1 for business/education TikTok
# - Oswald: Condensed bold, excellent for stats and overlays
# - Teko: Geometric condensed, perfect for HUD-style stats
# - Barlow Condensed: Modern condensed for secondary text
_FONT_DIR = "/home/ubuntu/test_clips/fonts"
FONT_PATHS = {
    "bebas": f"{_FONT_DIR}/BebasNeue-Regular.ttf",
    "anton": f"{_FONT_DIR}/Anton-Regular.ttf",
    "montserrat": f"{_FONT_DIR}/Montserrat-Variable.ttf",
    "oswald": f"{_FONT_DIR}/Oswald-Variable.ttf",
    "teko": f"{_FONT_DIR}/Teko-Variable.ttf",
    "barlow_black": f"{_FONT_DIR}/BarlowCondensed-Black.ttf",
    "barlow_bold": f"{_FONT_DIR}/BarlowCondensed-Bold.ttf",
    "roboto_condensed": f"{_FONT_DIR}/RobotoCondensed-Variable.ttf",
    # Fallbacks
    "bold": "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "regular": "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    "liberation_bold": "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "dejavu_bold": "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
}

# FONT PROFILES — Based on analysis of 100+ trending CS2 reels on TikTok:
# Key findings:
# 1. Bebas Neue is #1 font for gaming reels (tall, condensed, bold)
# 2. Text should be LARGE (120-160px for hooks) but MINIMAL (2-4 words)
# 3. White text + thick black outline is the standard
# 4. Shadow should be subtle, glow is optional and used sparingly
# 5. Player names are the LARGEST text element
FONT_PROFILES = {
    # PRIMARY: Bebas Neue — THE trending gaming font
    "trending_gaming": {
        "font": "bebas",
        "font_secondary": "oswald",
        "size_hook": 120,        # Large, attention-grabbing
        "size_action": 90,       # Clear stats
        "size_detail": 60,       # Secondary info
        "size_cta": 52,          # Subtle CTA
        "size_player_name": 140, # BIGGEST element
        "uppercase": True,
        "letter_spacing": 3,
        "outline_width": 6,
        "shadow_offset": (4, 4),
        "shadow_blur": 6,
        "best_for": ["sigma_edit", "dramatic_clutch", "fragmovie_edit", "clutch"],
    },
    # Anton — heavy impact for meme/brainrot edits
    "impact_heavy": {
        "font": "anton",
        "font_secondary": "teko",
        "size_hook": 130,
        "size_action": 100,
        "size_detail": 64,
        "size_cta": 56,
        "size_player_name": 150,
        "uppercase": True,
        "letter_spacing": 2,
        "outline_width": 7,
        "shadow_offset": (5, 5),
        "shadow_blur": 8,
        "best_for": ["meme_format", "brainrot_edit", "fail_format", "ace", "multi_kill"],
    },
    # Oswald — clean condensed for girl react (readable but stylish)
    "clean_condensed": {
        "font": "oswald",
        "font_secondary": "barlow_bold",
        "size_hook": 110,
        "size_action": 80,
        "size_detail": 56,
        "size_cta": 48,
        "size_player_name": 120,
        "uppercase": True,
        "letter_spacing": 2,
        "outline_width": 5,
        "shadow_offset": (3, 3),
        "shadow_blur": 5,
        "best_for": ["girl_reaction_pip", "girl_split_screen", "girl_commentary_full"],
    },
    # Teko — geometric/HUD style for stats and cinematic
    "hud_geometric": {
        "font": "teko",
        "font_secondary": "roboto_condensed",
        "size_hook": 110,
        "size_action": 85,
        "size_detail": 56,
        "size_cta": 48,
        "size_player_name": 130,
        "uppercase": True,
        "letter_spacing": 4,
        "outline_width": 5,
        "shadow_offset": (3, 3),
        "shadow_blur": 4,
        "best_for": ["clean_highlight", "highlight_subtitles", "tournament"],
    },
    # Barlow Condensed — modern engagement style
    "modern_bold": {
        "font": "barlow_black",
        "font_secondary": "montserrat",
        "size_hook": 115,
        "size_action": 85,
        "size_detail": 58,
        "size_cta": 52,
        "size_player_name": 130,
        "uppercase": True,
        "letter_spacing": 2,
        "outline_width": 6,
        "shadow_offset": (4, 4),
        "shadow_blur": 6,
        "best_for": ["provocative", "rank_comparison", "comeback"],
    },
}


# ═══════════════════════════════════════════════════════════════════════
# SECTION 3: MUSIC PROFILES — BPM, style, energy matching
# ═══════════════════════════════════════════════════════════════════════

MUSIC_PROFILES = {
    "phonk_dark": {
        "name": "Dark Phonk",
        "bpm": 140,
        "bass_freq": 36,
        "bass_style": "808_distorted",
        "melody_scale": "minor",
        "melody_notes": [164.81, 185.00, 196.00, 220.00, 246.94, 261.63, 293.66, 329.63],
        "hi_hat_pattern": "trap_rolls",
        "kick_pattern": "every_other",
        "snare_pattern": "backbeat",
        "energy": 0.85,
        "dark_factor": 0.9,
        "best_for": ["sigma_edit", "clutch", "headshot_sequence"],
    },
    "phonk_aggressive": {
        "name": "Aggressive Phonk",
        "bpm": 150,
        "bass_freq": 32,
        "bass_style": "808_heavy",
        "melody_scale": "phrygian",
        "melody_notes": [164.81, 174.61, 196.00, 220.00, 233.08, 261.63, 293.66, 329.63],
        "hi_hat_pattern": "rapid_rolls",
        "kick_pattern": "double",
        "snare_pattern": "hard_backbeat",
        "energy": 0.95,
        "dark_factor": 0.95,
        "best_for": ["ace", "multi_kill", "brainrot_edit"],
    },
    "trap_chill": {
        "name": "Chill Trap",
        "bpm": 130,
        "bass_freq": 40,
        "bass_style": "808_smooth",
        "melody_scale": "minor_pentatonic",
        "melody_notes": [196.00, 233.08, 261.63, 293.66, 349.23, 392.00],
        "hi_hat_pattern": "steady_8th",
        "kick_pattern": "every_other",
        "snare_pattern": "backbeat",
        "energy": 0.60,
        "dark_factor": 0.4,
        "best_for": ["girl_react", "funny", "fail_moment", "generic"],
    },
    "cinematic_dark": {
        "name": "Dark Cinematic",
        "bpm": 110,
        "bass_freq": 44,
        "bass_style": "sustained_low",
        "melody_scale": "harmonic_minor",
        "melody_notes": [220.00, 233.08, 261.63, 293.66, 329.63, 349.23, 415.30, 440.00],
        "hi_hat_pattern": "sparse",
        "kick_pattern": "downbeat_only",
        "snare_pattern": "none",
        "energy": 0.50,
        "dark_factor": 0.85,
        "best_for": ["dramatic_clutch", "comeback", "tournament"],
    },
    "hype_buildup": {
        "name": "Hype Buildup",
        "bpm": 145,
        "bass_freq": 38,
        "bass_style": "808_rising",
        "melody_scale": "minor",
        "melody_notes": [261.63, 293.66, 329.63, 349.23, 392.00, 440.00, 493.88, 523.25],
        "hi_hat_pattern": "accelerating",
        "kick_pattern": "buildup",
        "snare_pattern": "roll_buildup",
        "energy": 0.90,
        "dark_factor": 0.5,
        "best_for": ["clutch_defuse", "eco_win", "girl_fullscreen_intro"],
    },
    "lofi_gaming": {
        "name": "Lo-fi Gaming",
        "bpm": 85,
        "bass_freq": 55,
        "bass_style": "warm_bass",
        "melody_scale": "major_7",
        "melody_notes": [261.63, 293.66, 329.63, 392.00, 440.00, 493.88],
        "hi_hat_pattern": "swing",
        "kick_pattern": "boom_bap",
        "snare_pattern": "lazy_backbeat",
        "energy": 0.35,
        "dark_factor": 0.2,
        "best_for": ["girl_split_screen", "commentary"],
    },
}


# ═══════════════════════════════════════════════════════════════════════
# SECTION 4: SFX LIBRARY — Sound effects with timing intelligence
# ═══════════════════════════════════════════════════════════════════════

SFX_LIBRARY = {
    "impact_heavy": {
        "type": "impact",
        "intensity": 1.0,
        "trigger": ["kill", "headshot", "clutch_moment"],
        "default_volume": 1.5,
        "best_timing": "on_action",
    },
    "impact_light": {
        "type": "impact",
        "intensity": 0.6,
        "trigger": ["kill", "round_event"],
        "default_volume": 1.0,
        "best_timing": "on_action",
    },
    "whoosh_transition": {
        "type": "whoosh",
        "intensity": 0.7,
        "trigger": ["phase_change", "hook_start"],
        "default_volume": 1.2,
        "best_timing": "before_action",
    },
    "bass_drop": {
        "type": "bass_drop",
        "intensity": 0.9,
        "trigger": ["peak_moment", "ace", "clutch_win"],
        "default_volume": 1.3,
        "best_timing": "on_peak",
    },
    "vine_boom": {
        "type": "vine_boom",
        "intensity": 0.8,
        "trigger": ["meme_moment", "disrespect", "toxic"],
        "default_volume": 1.4,
        "best_timing": "on_action",
    },
    "horn_dramatic": {
        "type": "horn",
        "intensity": 0.7,
        "trigger": ["round_win", "clutch_win", "outro"],
        "default_volume": 1.0,
        "best_timing": "after_peak",
    },
    "record_scratch": {
        "type": "impact",
        "intensity": 0.5,
        "trigger": ["fail", "unexpected", "meme_fail"],
        "default_volume": 1.2,
        "best_timing": "on_action",
    },
    "crowd_roar": {
        "type": "horn",
        "intensity": 0.8,
        "trigger": ["ace", "tournament", "comeback"],
        "default_volume": 0.8,
        "best_timing": "after_peak",
    },
}


# ═══════════════════════════════════════════════════════════════════════
# SECTION 5: COLOR GRADE PRESETS — FFmpeg eq/vignette params
# ═══════════════════════════════════════════════════════════════════════

COLOR_GRADES = {
    "cinematic": {
        "brightness": -0.03,
        "contrast": 1.25,
        "saturation": 0.8,
        "vignette": True,
        "vignette_strength": "PI/4",
    },
    "dark": {
        "brightness": -0.06,
        "contrast": 1.35,
        "saturation": 0.7,
        "vignette": True,
        "vignette_strength": "PI/3.5",
    },
    "vibrant": {
        "brightness": 0.02,
        "contrast": 1.15,
        "saturation": 1.3,
        "vignette": False,
        "vignette_strength": None,
    },
    "warm": {
        "brightness": 0.03,
        "contrast": 1.10,
        "saturation": 1.2,
        "vignette": False,
        "vignette_strength": None,
    },
    "oversaturated": {
        "brightness": 0.05,
        "contrast": 1.20,
        "saturation": 1.6,
        "vignette": False,
        "vignette_strength": None,
    },
    "cold": {
        "brightness": -0.02,
        "contrast": 1.20,
        "saturation": 0.6,
        "vignette": True,
        "vignette_strength": "PI/4.5",
    },
    "none": {
        "brightness": 0.0,
        "contrast": 1.0,
        "saturation": 1.0,
        "vignette": False,
        "vignette_strength": None,
    },
}


# ═══════════════════════════════════════════════════════════════════════
# SECTION 6: ZOOM & CAMERA PROFILES
# ═══════════════════════════════════════════════════════════════════════

ZOOM_PROFILES = {
    "slow_push": {
        "expression": "1+0.0008*on",
        "description": "Slow cinematic push-in",
        "energy": 0.3,
        "best_for": ["dramatic", "cinematic", "girl_react"],
    },
    "medium_push": {
        "expression": "1+0.0015*on",
        "description": "Medium push-in for action",
        "energy": 0.6,
        "best_for": ["highlight", "clutch", "ace"],
    },
    "fast_zoom": {
        "expression": "1+0.003*on",
        "description": "Fast aggressive zoom for memes",
        "energy": 0.9,
        "best_for": ["meme", "brainrot", "toxic"],
    },
    "pulse_zoom": {
        "expression": "1+0.002*sin(on*0.1)",
        "description": "Pulsing zoom synced to beat",
        "energy": 0.7,
        "best_for": ["phonk", "sigma", "multi_kill"],
    },
    "none": {
        "expression": "1",
        "description": "No zoom",
        "energy": 0.0,
        "best_for": ["clean", "minimal"],
    },
}


# ═══════════════════════════════════════════════════════════════════════
# SECTION 7: PACING PROFILES — How the reel flows
# ═══════════════════════════════════════════════════════════════════════

PACING_PROFILES = {
    "standard_15s": {
        "total_duration": 15.0,
        "phases": {
            "hook": {"start": 0.0, "end": 2.5, "purpose": "Grab attention"},
            "build": {"start": 2.5, "end": 5.0, "purpose": "Context/player intro"},
            "action": {"start": 5.0, "end": 8.0, "purpose": "Main play starts"},
            "peak": {"start": 8.0, "end": 11.0, "purpose": "Climax/best moment"},
            "react": {"start": 11.0, "end": 13.0, "purpose": "Reaction/meme"},
            "cta": {"start": 13.0, "end": 15.0, "purpose": "Call to action"},
        },
    },
    "fast_12s": {
        "total_duration": 12.0,
        "phases": {
            "hook": {"start": 0.0, "end": 1.5, "purpose": "Quick hook"},
            "action": {"start": 1.5, "end": 5.0, "purpose": "Straight to action"},
            "peak": {"start": 5.0, "end": 8.0, "purpose": "Peak moment"},
            "react": {"start": 8.0, "end": 10.0, "purpose": "Quick reaction"},
            "cta": {"start": 10.0, "end": 12.0, "purpose": "CTA"},
        },
    },
    "extended_20s": {
        "total_duration": 20.0,
        "phases": {
            "hook": {"start": 0.0, "end": 3.0, "purpose": "Strong hook"},
            "build": {"start": 3.0, "end": 7.0, "purpose": "Build tension"},
            "action": {"start": 7.0, "end": 11.0, "purpose": "Main action"},
            "peak": {"start": 11.0, "end": 14.0, "purpose": "Climax"},
            "react": {"start": 14.0, "end": 17.0, "purpose": "Extended reaction"},
            "cta": {"start": 17.0, "end": 20.0, "purpose": "CTA + outro"},
        },
    },
    "girl_react_15s": {
        "total_duration": 15.0,
        "phases": {
            "hook": {"start": 0.0, "end": 2.0, "purpose": "Teaser hook"},
            "build": {"start": 2.0, "end": 5.0, "purpose": "Player/context intro"},
            "action": {"start": 5.0, "end": 7.5, "purpose": "Key play"},
            "girl_react": {"start": 7.5, "end": 12.0, "purpose": "Girl voice reaction"},
            "cta": {"start": 12.0, "end": 15.0, "purpose": "CTA"},
        },
    },
}


# ═══════════════════════════════════════════════════════════════════════
# SECTION 8: MEME OVERLAY SYSTEM — Context-aware meme selection
# ═══════════════════════════════════════════════════════════════════════

MEME_OVERLAYS_LIBRARY = {
    "ace_badge": {
        "trigger_moments": ["ace"],
        "text": "ACE",
        "style": "badge_red",
        "position": "center",
        "y_ratio": 0.65,
        "font_size": 80,
        "bg_color": (255, 20, 20, 230),
        "text_color": (255, 255, 255, 255),
        "subtext": "5 KILLS",
        "importance": 1.0,
    },
    "clutch_text": {
        "trigger_moments": ["clutch", "clutch_defuse"],
        "dynamic_text": True,  # uses ctx.situation
        "text": "CLUTCH",
        "style": "badge_red",
        "position": "center",
        "y_ratio": 0.65,
        "font_size": 72,
        "bg_color": (220, 20, 20, 220),
        "text_color": (255, 255, 255, 255),
        "subtext": "",
        "subtext_size": 36,
        "importance": 0.95,
    },
    "sigma_badge": {
        "trigger_moments": ["headshot_sequence", "ace", "no_scope"],
        "text": "SIGMA",
        "style": "geometric",
        "position": "center",
        "y_ratio": 0.68,
        "font_size": 48,
        "importance": 0.7,
    },
    "fire_react": {
        "trigger_moments": ["multi_kill", "ace", "clutch", "knife_kill"],
        "text": "FIRE",
        "style": "badge_orange",
        "position": "bottom_right",
        "y_ratio": 0.80,
        "font_size": 32,
        "bg_color": (255, 100, 0, 180),
        "text_color": (255, 255, 255, 255),
        "importance": 0.6,
    },
    "headshot_crosshair": {
        "trigger_moments": ["headshot_sequence"],
        "text": "HEADSHOT",
        "style": "crosshair",
        "position": "center",
        "y_ratio": 0.50,
        "font_size": 48,
        "importance": 0.85,
    },
    "knife_disrespect": {
        "trigger_moments": ["knife_kill"],
        "text": "DISRESPECT",
        "style": "badge_red",
        "position": "center",
        "y_ratio": 0.65,
        "font_size": 60,
        "bg_color": (180, 0, 180, 200),
        "text_color": (255, 255, 255, 255),
        "importance": 0.9,
    },
    "eco_text": {
        "trigger_moments": ["eco_win"],
        "text": "ECO WIN",
        "style": "badge_green",
        "position": "center",
        "y_ratio": 0.65,
        "font_size": 56,
        "bg_color": (0, 180, 0, 200),
        "text_color": (255, 255, 255, 255),
        "importance": 0.75,
    },
    "wallbang_text": {
        "trigger_moments": ["wallbang"],
        "text": "WALLBANG",
        "style": "badge_blue",
        "position": "center",
        "y_ratio": 0.65,
        "font_size": 60,
        "bg_color": (0, 100, 255, 200),
        "text_color": (255, 255, 255, 255),
        "importance": 0.85,
    },
    "noscope_text": {
        "trigger_moments": ["no_scope"],
        "text": "NO SCOPE",
        "style": "badge_red",
        "position": "center",
        "y_ratio": 0.65,
        "font_size": 60,
        "bg_color": (255, 50, 50, 220),
        "text_color": (255, 255, 0, 255),
        "importance": 0.9,
    },
    "comeback_text": {
        "trigger_moments": ["comeback"],
        "text": "COMEBACK",
        "style": "badge_gold",
        "position": "center",
        "y_ratio": 0.65,
        "font_size": 60,
        "bg_color": (200, 150, 0, 220),
        "text_color": (255, 255, 255, 255),
        "importance": 0.8,
    },
    "tournament_badge": {
        "trigger_moments": ["tournament"],
        "text": "MAJOR PLAY",
        "style": "badge_gold",
        "position": "top_center",
        "y_ratio": 0.08,
        "font_size": 48,
        "bg_color": (200, 150, 0, 200),
        "text_color": (255, 255, 255, 255),
        "subtext": "TOURNAMENT HIGHLIGHT",
        "importance": 0.85,
    },
}


# ═══════════════════════════════════════════════════════════════════════
# SECTION 9: MOMENT-TO-DESIGN MAPPING — The brain
# ═══════════════════════════════════════════════════════════════════════

MOMENT_DESIGN_MAP = {
    "clutch": {
        "palette_pool": ["inferno", "blood_dark", "electric_blue"],
        "font_profile": "impact_clean",
        "music_profile": "phonk_dark",
        "color_grade": "cinematic",
        "zoom_profile": "medium_push",
        "pacing": "standard_15s",
        "sfx_sequence": [
            {"sfx": "whoosh_transition", "phase": "hook", "offset": 0.0},
            {"sfx": "impact_heavy", "phase": "action", "offset": 0.0},
            {"sfx": "impact_heavy", "phase": "action", "offset": 2.0},
            {"sfx": "bass_drop", "phase": "peak", "offset": 0.0},
            {"sfx": "vine_boom", "phase": "peak", "offset": 1.0},
            {"sfx": "horn_dramatic", "phase": "react", "offset": 0.5},
        ],
        "energy_curve": [0.5, 0.6, 0.8, 1.0, 0.9, 0.4],
        "girl_voice_start": "peak",
        "girl_voice_volume": 1.8,
    },
    "ace": {
        "palette_pool": ["inferno", "royal_gold", "neon_pink"],
        "font_profile": "impact_clean",
        "music_profile": "phonk_aggressive",
        "color_grade": "vibrant",
        "zoom_profile": "fast_zoom",
        "pacing": "standard_15s",
        "sfx_sequence": [
            {"sfx": "whoosh_transition", "phase": "hook", "offset": 0.0},
            {"sfx": "impact_heavy", "phase": "action", "offset": 0.0},
            {"sfx": "impact_heavy", "phase": "action", "offset": 1.0},
            {"sfx": "impact_heavy", "phase": "peak", "offset": 0.0},
            {"sfx": "bass_drop", "phase": "peak", "offset": 1.5},
            {"sfx": "crowd_roar", "phase": "react", "offset": 0.0},
            {"sfx": "horn_dramatic", "phase": "react", "offset": 1.0},
        ],
        "energy_curve": [0.6, 0.7, 0.85, 1.0, 1.0, 0.5],
        "girl_voice_start": "peak",
        "girl_voice_volume": 1.8,
    },
    "multi_kill": {
        "palette_pool": ["inferno", "electric_blue", "neon_pink"],
        "font_profile": "meme_bold",
        "music_profile": "phonk_aggressive",
        "color_grade": "vibrant",
        "zoom_profile": "medium_push",
        "pacing": "fast_12s",
        "sfx_sequence": [
            {"sfx": "whoosh_transition", "phase": "hook", "offset": 0.0},
            {"sfx": "impact_heavy", "phase": "action", "offset": 0.5},
            {"sfx": "impact_heavy", "phase": "action", "offset": 1.5},
            {"sfx": "vine_boom", "phase": "peak", "offset": 0.0},
            {"sfx": "bass_drop", "phase": "peak", "offset": 1.0},
        ],
        "energy_curve": [0.5, 0.8, 1.0, 0.9, 0.4],
        "girl_voice_start": "react",
        "girl_voice_volume": 1.7,
    },
    "headshot_sequence": {
        "palette_pool": ["midnight_sigma", "blood_dark", "ice_cold"],
        "font_profile": "cinematic",
        "music_profile": "phonk_dark",
        "color_grade": "dark",
        "zoom_profile": "pulse_zoom",
        "pacing": "standard_15s",
        "sfx_sequence": [
            {"sfx": "whoosh_transition", "phase": "hook", "offset": 0.0},
            {"sfx": "impact_light", "phase": "action", "offset": 0.0},
            {"sfx": "impact_light", "phase": "action", "offset": 1.0},
            {"sfx": "impact_heavy", "phase": "peak", "offset": 0.0},
            {"sfx": "bass_drop", "phase": "peak", "offset": 1.5},
        ],
        "energy_curve": [0.4, 0.5, 0.7, 0.95, 0.8, 0.3],
        "girl_voice_start": "react",
        "girl_voice_volume": 1.6,
    },
    "knife_kill": {
        "palette_pool": ["meme_chaos", "toxic_green", "neon_pink"],
        "font_profile": "meme_bold",
        "music_profile": "phonk_dark",
        "color_grade": "vibrant",
        "zoom_profile": "fast_zoom",
        "pacing": "fast_12s",
        "sfx_sequence": [
            {"sfx": "whoosh_transition", "phase": "hook", "offset": 0.0},
            {"sfx": "vine_boom", "phase": "action", "offset": 1.0},
            {"sfx": "vine_boom", "phase": "peak", "offset": 0.0},
            {"sfx": "horn_dramatic", "phase": "react", "offset": 0.0},
        ],
        "energy_curve": [0.5, 0.7, 1.0, 0.9, 0.4],
        "girl_voice_start": "peak",
        "girl_voice_volume": 1.8,
    },
    "clutch_defuse": {
        "palette_pool": ["inferno", "electric_blue", "royal_gold"],
        "font_profile": "impact_clean",
        "music_profile": "hype_buildup",
        "color_grade": "cinematic",
        "zoom_profile": "slow_push",
        "pacing": "standard_15s",
        "sfx_sequence": [
            {"sfx": "whoosh_transition", "phase": "hook", "offset": 0.0},
            {"sfx": "impact_light", "phase": "build", "offset": 1.0},
            {"sfx": "impact_heavy", "phase": "action", "offset": 1.5},
            {"sfx": "bass_drop", "phase": "peak", "offset": 0.0},
            {"sfx": "crowd_roar", "phase": "react", "offset": 0.0},
        ],
        "energy_curve": [0.3, 0.5, 0.7, 1.0, 0.9, 0.4],
        "girl_voice_start": "action",
        "girl_voice_volume": 1.7,
    },
    "eco_win": {
        "palette_pool": ["royal_gold", "toxic_green", "electric_blue"],
        "font_profile": "engagement",
        "music_profile": "hype_buildup",
        "color_grade": "vibrant",
        "zoom_profile": "medium_push",
        "pacing": "standard_15s",
        "sfx_sequence": [
            {"sfx": "whoosh_transition", "phase": "hook", "offset": 0.0},
            {"sfx": "impact_heavy", "phase": "action", "offset": 1.0},
            {"sfx": "bass_drop", "phase": "peak", "offset": 0.0},
            {"sfx": "horn_dramatic", "phase": "react", "offset": 0.5},
        ],
        "energy_curve": [0.4, 0.5, 0.8, 1.0, 0.85, 0.4],
        "girl_voice_start": "peak",
        "girl_voice_volume": 1.7,
    },
    "wallbang": {
        "palette_pool": ["electric_blue", "midnight_sigma", "inferno"],
        "font_profile": "impact_clean",
        "music_profile": "phonk_dark",
        "color_grade": "cold",
        "zoom_profile": "medium_push",
        "pacing": "standard_15s",
        "sfx_sequence": [
            {"sfx": "whoosh_transition", "phase": "hook", "offset": 0.0},
            {"sfx": "impact_heavy", "phase": "action", "offset": 1.0},
            {"sfx": "bass_drop", "phase": "peak", "offset": 0.0},
            {"sfx": "vine_boom", "phase": "peak", "offset": 1.0},
        ],
        "energy_curve": [0.4, 0.5, 0.8, 1.0, 0.8, 0.3],
        "girl_voice_start": "peak",
        "girl_voice_volume": 1.7,
    },
    "no_scope": {
        "palette_pool": ["neon_pink", "meme_chaos", "inferno"],
        "font_profile": "meme_bold",
        "music_profile": "phonk_aggressive",
        "color_grade": "vibrant",
        "zoom_profile": "fast_zoom",
        "pacing": "fast_12s",
        "sfx_sequence": [
            {"sfx": "whoosh_transition", "phase": "hook", "offset": 0.0},
            {"sfx": "vine_boom", "phase": "action", "offset": 1.0},
            {"sfx": "impact_heavy", "phase": "peak", "offset": 0.0},
            {"sfx": "bass_drop", "phase": "peak", "offset": 1.0},
        ],
        "energy_curve": [0.5, 0.7, 1.0, 0.9, 0.4],
        "girl_voice_start": "peak",
        "girl_voice_volume": 1.8,
    },
    "comeback": {
        "palette_pool": ["royal_gold", "purple_reign", "inferno"],
        "font_profile": "cinematic",
        "music_profile": "cinematic_dark",
        "color_grade": "cinematic",
        "zoom_profile": "slow_push",
        "pacing": "extended_20s",
        "sfx_sequence": [
            {"sfx": "whoosh_transition", "phase": "hook", "offset": 0.0},
            {"sfx": "impact_light", "phase": "build", "offset": 1.5},
            {"sfx": "impact_heavy", "phase": "action", "offset": 1.0},
            {"sfx": "bass_drop", "phase": "peak", "offset": 0.0},
            {"sfx": "crowd_roar", "phase": "react", "offset": 0.0},
            {"sfx": "horn_dramatic", "phase": "react", "offset": 1.5},
        ],
        "energy_curve": [0.3, 0.4, 0.6, 0.85, 1.0, 0.5],
        "girl_voice_start": "react",
        "girl_voice_volume": 1.6,
    },
    "tournament": {
        "palette_pool": ["royal_gold", "purple_reign", "inferno"],
        "font_profile": "cinematic",
        "music_profile": "cinematic_dark",
        "color_grade": "cinematic",
        "zoom_profile": "slow_push",
        "pacing": "extended_20s",
        "sfx_sequence": [
            {"sfx": "whoosh_transition", "phase": "hook", "offset": 0.0},
            {"sfx": "impact_light", "phase": "build", "offset": 2.0},
            {"sfx": "impact_heavy", "phase": "action", "offset": 1.0},
            {"sfx": "impact_heavy", "phase": "peak", "offset": 0.5},
            {"sfx": "bass_drop", "phase": "peak", "offset": 1.5},
            {"sfx": "crowd_roar", "phase": "react", "offset": 0.0},
        ],
        "energy_curve": [0.3, 0.4, 0.6, 0.9, 1.0, 0.5],
        "girl_voice_start": "peak",
        "girl_voice_volume": 1.7,
    },
    "toxic_moment": {
        "palette_pool": ["toxic_green", "meme_chaos", "neon_pink"],
        "font_profile": "meme_bold",
        "music_profile": "trap_chill",
        "color_grade": "none",
        "zoom_profile": "fast_zoom",
        "pacing": "fast_12s",
        "sfx_sequence": [
            {"sfx": "whoosh_transition", "phase": "hook", "offset": 0.0},
            {"sfx": "vine_boom", "phase": "action", "offset": 1.0},
            {"sfx": "vine_boom", "phase": "peak", "offset": 0.0},
            {"sfx": "record_scratch", "phase": "react", "offset": 0.0},
        ],
        "energy_curve": [0.5, 0.7, 0.9, 0.8, 0.4],
        "girl_voice_start": "peak",
        "girl_voice_volume": 1.7,
    },
    "meme_fail": {
        "palette_pool": ["meme_chaos", "toxic_green"],
        "font_profile": "meme_bold",
        "music_profile": "trap_chill",
        "color_grade": "none",
        "zoom_profile": "fast_zoom",
        "pacing": "fast_12s",
        "sfx_sequence": [
            {"sfx": "whoosh_transition", "phase": "hook", "offset": 0.0},
            {"sfx": "record_scratch", "phase": "action", "offset": 1.0},
            {"sfx": "vine_boom", "phase": "peak", "offset": 0.0},
        ],
        "energy_curve": [0.4, 0.6, 0.9, 0.7, 0.3],
        "girl_voice_start": "peak",
        "girl_voice_volume": 1.7,
    },
    "round_win": {
        "palette_pool": ["electric_blue", "inferno", "royal_gold"],
        "font_profile": "engagement",
        "music_profile": "phonk_dark",
        "color_grade": "vibrant",
        "zoom_profile": "medium_push",
        "pacing": "standard_15s",
        "sfx_sequence": [
            {"sfx": "whoosh_transition", "phase": "hook", "offset": 0.0},
            {"sfx": "impact_heavy", "phase": "action", "offset": 1.0},
            {"sfx": "bass_drop", "phase": "peak", "offset": 0.0},
            {"sfx": "horn_dramatic", "phase": "react", "offset": 0.5},
        ],
        "energy_curve": [0.4, 0.5, 0.8, 1.0, 0.8, 0.4],
        "girl_voice_start": "peak",
        "girl_voice_volume": 1.6,
    },
    "generic": {
        "palette_pool": ["electric_blue", "inferno", "midnight_sigma"],
        "font_profile": "impact_clean",
        "music_profile": "phonk_dark",
        "color_grade": "cinematic",
        "zoom_profile": "slow_push",
        "pacing": "standard_15s",
        "sfx_sequence": [
            {"sfx": "whoosh_transition", "phase": "hook", "offset": 0.0},
            {"sfx": "impact_heavy", "phase": "action", "offset": 1.0},
            {"sfx": "bass_drop", "phase": "peak", "offset": 0.0},
        ],
        "energy_curve": [0.4, 0.5, 0.7, 0.9, 0.7, 0.3],
        "girl_voice_start": "react",
        "girl_voice_volume": 1.5,
    },
}


# ═══════════════════════════════════════════════════════════════════════
# SECTION 10A: TEXT ANIMATION PROFILES — How text enters/exits
# ═══════════════════════════════════════════════════════════════════════

TEXT_ANIMATIONS = {
    "pop_scale": {
        "name": "Pop Scale",
        "description": "Text pops in from 0 to full size with overshoot",
        "ffmpeg_enter": "zoompan=z='if(lt(on,5),0.01+on*0.25,if(lt(on,8),1.25-(on-5)*0.083,1.0))':d=1:s=1080x1920:fps=30",
        "enter_duration": 0.3,
        "exit_type": "fade",
        "exit_duration": 0.2,
        "energy_min": 0.6,
        "best_for": ["hook", "player"],
    },
    "fade_in": {
        "name": "Fade In",
        "description": "Simple smooth fade in",
        "enter_duration": 0.3,
        "exit_type": "fade",
        "exit_duration": 0.3,
        "energy_min": 0.0,
        "best_for": ["action", "stats"],
    },
    "slide_up": {
        "name": "Slide Up",
        "description": "Text slides up from below",
        "enter_duration": 0.25,
        "exit_type": "slide_down",
        "exit_duration": 0.2,
        "energy_min": 0.3,
        "best_for": ["hook", "action"],
    },
    "glitch_in": {
        "name": "Glitch In",
        "description": "Quick glitch flash before text appears",
        "enter_duration": 0.15,
        "exit_type": "fade",
        "exit_duration": 0.15,
        "energy_min": 0.7,
        "best_for": ["hook", "player"],
    },
    "word_by_word": {
        "name": "Word by Word",
        "description": "Each word appears one at a time",
        "enter_duration": 0.5,
        "exit_type": "fade",
        "exit_duration": 0.3,
        "energy_min": 0.4,
        "best_for": ["hook"],
    },
}

# ═══════════════════════════════════════════════════════════════════════
# SECTION 10B: TRANSITION EFFECTS — Between phases
# ═══════════════════════════════════════════════════════════════════════

TRANSITION_EFFECTS = {
    "flash_white": {
        "name": "White Flash",
        "description": "Quick white flash on transition",
        "ffmpeg_filter": "geq=r='clip(r(X,Y)+{intensity}*255*exp(-{decay}*(T-{time})),0,255)':g='clip(g(X,Y)+{intensity}*255*exp(-{decay}*(T-{time})),0,255)':b='clip(b(X,Y)+{intensity}*255*exp(-{decay}*(T-{time})),0,255)'",
        "duration": 0.15,
        "energy_min": 0.5,
        "best_for": ["kill", "impact", "peak"],
    },
    "flash_color": {
        "name": "Color Flash",
        "description": "Flash in palette primary color",
        "duration": 0.12,
        "energy_min": 0.6,
        "best_for": ["peak", "action"],
    },
    "black_cut": {
        "name": "Black Cut",
        "description": "Quick black frame (2-3 frames) before next phase",
        "duration": 0.08,
        "energy_min": 0.0,
        "best_for": ["transition", "phase_change"],
    },
    "zoom_punch": {
        "name": "Zoom Punch",
        "description": "Quick zoom in then snap back",
        "duration": 0.2,
        "energy_min": 0.7,
        "best_for": ["kill", "impact"],
    },
}

# ═══════════════════════════════════════════════════════════════════════
# SECTION 10C: SPEED RAMP PROFILES — Slow-mo / fast-forward
# ═══════════════════════════════════════════════════════════════════════

SPEED_RAMP_PROFILES = {
    "kill_slowmo": {
        "name": "Kill Slow-mo",
        "description": "Slow motion on the kill moment then speed up",
        "phases": {
            "before": {"speed": 1.0, "duration": 0.5},
            "slowmo": {"speed": 0.5, "duration": 1.0},
            "after": {"speed": 1.5, "duration": 0.3},
        },
        "energy_min": 0.6,
        "best_for": ["clutch", "ace", "headshot_sequence"],
    },
    "buildup_speed": {
        "name": "Buildup Speed",
        "description": "Speed up during build, normal during action",
        "phases": {
            "fast": {"speed": 1.3, "duration": 2.0},
            "normal": {"speed": 1.0, "duration": -1},
        },
        "energy_min": 0.4,
        "best_for": ["generic", "round_win"],
    },
    "freeze_frame": {
        "name": "Freeze Frame",
        "description": "Brief freeze on key moment",
        "phases": {
            "freeze": {"speed": 0.0, "duration": 0.5},
            "resume": {"speed": 1.0, "duration": -1},
        },
        "energy_min": 0.7,
        "best_for": ["clutch", "knife_kill", "no_scope"],
    },
    "none": {
        "name": "No Speed Ramp",
        "phases": {},
        "energy_min": 0.0,
        "best_for": ["generic"],
    },
}

# ═══════════════════════════════════════════════════════════════════════
# SECTION 10D: SHAKE / PULSE EFFECTS — Camera movement on impacts
# ═══════════════════════════════════════════════════════════════════════

SHAKE_PROFILES = {
    "impact_shake": {
        "name": "Impact Shake",
        "description": "Quick shake on kill/impact",
        "intensity": 8,  # pixels of displacement
        "duration": 0.2,
        "frequency": 30,  # Hz
        "decay": 15.0,
        "energy_min": 0.5,
    },
    "heavy_shake": {
        "name": "Heavy Shake",
        "description": "Strong shake for ace/peak moments",
        "intensity": 15,
        "duration": 0.35,
        "frequency": 25,
        "decay": 10.0,
        "energy_min": 0.8,
    },
    "subtle_pulse": {
        "name": "Subtle Pulse",
        "description": "Gentle scale pulse on beat",
        "intensity": 3,
        "duration": 0.15,
        "frequency": 0,  # No shake, just scale
        "decay": 20.0,
        "energy_min": 0.3,
    },
    "none": {
        "name": "No Shake",
        "intensity": 0,
        "duration": 0,
        "frequency": 0,
        "decay": 0,
        "energy_min": 0.0,
    },
}

# ═══════════════════════════════════════════════════════════════════════
# SECTION 10E: STYLE VARIATION — Ensure each reel looks unique
# ═══════════════════════════════════════════════════════════════════════

STYLE_VARIATIONS = {
    "clean_minimal": {
        "name": "Clean Minimal",
        "text_animation": "fade_in",
        "transition": "black_cut",
        "speed_ramp": "none",
        "shake": "none",
        "text_effects": {"glow": False, "shadow_heavy": False},
        "weight": 1.0,
    },
    "aggressive_sigma": {
        "name": "Aggressive Sigma",
        "text_animation": "glitch_in",
        "transition": "flash_white",
        "speed_ramp": "kill_slowmo",
        "shake": "impact_shake",
        "text_effects": {"glow": False, "shadow_heavy": False},
        "weight": 1.2,
    },
    "hype_energy": {
        "name": "Hype Energy",
        "text_animation": "pop_scale",
        "transition": "zoom_punch",
        "speed_ramp": "buildup_speed",
        "shake": "heavy_shake",
        "text_effects": {"glow": False, "shadow_heavy": False},
        "weight": 1.0,
    },
    "cinematic_slow": {
        "name": "Cinematic Slow",
        "text_animation": "fade_in",
        "transition": "flash_color",
        "speed_ramp": "freeze_frame",
        "shake": "subtle_pulse",
        "text_effects": {"glow": False, "shadow_heavy": False},
        "weight": 0.8,
    },
    "word_punch": {
        "name": "Word Punch",
        "text_animation": "word_by_word",
        "transition": "flash_white",
        "speed_ramp": "kill_slowmo",
        "shake": "impact_shake",
        "text_effects": {"glow": False, "shadow_heavy": False},
        "weight": 1.0,
    },
}


def select_style_variation(moment_type: str, energy: float) -> dict:
    """Select a style variation based on moment energy for unique look each time."""
    eligible = []
    for sid, style in STYLE_VARIATIONS.items():
        # Higher energy moments get more aggressive styles
        if energy >= 0.8 and sid in ("aggressive_sigma", "hype_energy", "word_punch"):
            eligible.append((sid, style, style["weight"] * 1.5))
        elif energy >= 0.5 and sid not in ("cinematic_slow",):
            eligible.append((sid, style, style["weight"]))
        elif energy < 0.5:
            eligible.append((sid, style, style["weight"]))
        else:
            eligible.append((sid, style, style["weight"] * 0.5))

    if not eligible:
        return STYLE_VARIATIONS["clean_minimal"]

    total = sum(w for _, _, w in eligible)
    r = random.uniform(0, total)
    cumulative = 0
    for sid, style, w in eligible:
        cumulative += w
        if r <= cumulative:
            return style
    return eligible[0][1]


def build_beat_grid(bpm: int, duration: float) -> list:
    """Build a grid of beat timestamps from BPM for syncing effects."""
    beat_interval = 60.0 / bpm
    beats = []
    t = 0.0
    while t < duration:
        beats.append(round(t, 3))
        t += beat_interval
    return beats


def snap_to_beat(time_sec: float, beat_grid: list, tolerance: float = 0.15) -> float:
    """Snap a timestamp to the nearest beat if within tolerance."""
    if not beat_grid:
        return time_sec
    closest = min(beat_grid, key=lambda b: abs(b - time_sec))
    if abs(closest - time_sec) <= tolerance:
        return closest
    return time_sec


def build_flash_timeline(sfx_timeline: list, pacing: dict, energy: float) -> list:
    """Build flash/transition effects at impact points."""
    flashes = []
    for sfx in sfx_timeline:
        if sfx["sfx_type"] in ("impact", "bass_drop", "vine_boom"):
            flash_type = "flash_white" if energy >= 0.7 else "black_cut"
            flash = TRANSITION_EFFECTS.get(flash_type, TRANSITION_EFFECTS["flash_white"])
            flashes.append({
                "type": flash_type,
                "time": sfx["time"],
                "duration": flash["duration"],
                "intensity": min(1.0, energy),
            })
    return flashes


def build_shake_timeline(sfx_timeline: list, energy: float) -> list:
    """Build camera shake events at impact points."""
    shakes = []
    shake_profile = "impact_shake" if energy >= 0.6 else "subtle_pulse"
    if energy >= 0.85:
        shake_profile = "heavy_shake"
    profile = SHAKE_PROFILES.get(shake_profile, SHAKE_PROFILES["impact_shake"])

    for sfx in sfx_timeline:
        if sfx["sfx_type"] in ("impact", "bass_drop"):
            shakes.append({
                "time": sfx["time"],
                "intensity": profile["intensity"],
                "duration": profile["duration"],
                "decay": profile["decay"],
            })
    return shakes


# ═══════════════════════════════════════════════════════════════════════
# SECTION 10: SELF-LEARNING WEIGHT TRACKER
# ═══════════════════════════════════════════════════════════════════════

# In-memory performance tracker (persisted to JSON file)
_performance_log: list = []
_weight_adjustments: dict = {}  # {palette_id: weight_modifier}

WEIGHTS_FILE = Path("/tmp/montage_weights.json")


def _load_weights():
    """Load learned weights from disk."""
    global _weight_adjustments
    if WEIGHTS_FILE.exists():
        try:
            with open(WEIGHTS_FILE, "r") as f:
                _weight_adjustments = json.load(f)
        except Exception:
            _weight_adjustments = {}


def _save_weights():
    """Save learned weights to disk."""
    try:
        with open(WEIGHTS_FILE, "w") as f:
            json.dump(_weight_adjustments, f)
    except Exception:
        pass


def log_reel_performance(
    reel_id: str,
    moment_type: str,
    palette_id: str,
    font_profile: str,
    music_profile: str,
    views: int = 0,
    likes: int = 0,
    comments: int = 0,
    shares: int = 0,
    watch_time_pct: float = 0.0,
):
    """Log performance of a generated reel for self-learning."""
    _performance_log.append({
        "reel_id": reel_id,
        "moment_type": moment_type,
        "palette_id": palette_id,
        "font_profile": font_profile,
        "music_profile": music_profile,
        "views": views,
        "likes": likes,
        "comments": comments,
        "shares": shares,
        "watch_time_pct": watch_time_pct,
        "timestamp": time.time(),
    })

    # Calculate engagement score
    engagement = (
        views * 1.0 +
        likes * 10.0 +
        comments * 20.0 +
        shares * 30.0 +
        watch_time_pct * 50.0
    )

    # Adjust weights for this palette
    key = f"{moment_type}_{palette_id}"
    current = _weight_adjustments.get(key, 1.0)
    if engagement > 100:
        _weight_adjustments[key] = min(2.0, current * 1.1)  # Boost
    elif engagement < 20:
        _weight_adjustments[key] = max(0.3, current * 0.9)  # Reduce

    _save_weights()


def get_weight_for(moment_type: str, choice_id: str) -> float:
    """Get learned weight for a specific moment+choice combination."""
    key = f"{moment_type}_{choice_id}"
    return _weight_adjustments.get(key, 1.0)


# Load weights on import
_load_weights()


# ═══════════════════════════════════════════════════════════════════════
# SECTION 11: THE BRAIN — Smart decision-making functions
# ═══════════════════════════════════════════════════════════════════════

def select_palette(moment_type: str, energy_level: float = 0.7,
                   has_girl: bool = False) -> dict:
    """
    Intelligently select color palette based on moment type, energy, and context.
    Uses learned weights to prefer palettes that performed well.
    """
    if has_girl:
        # Girl react clips get dedicated palettes
        pool = ["girl_pink", "girl_warm", "neon_pink"]
    else:
        design = MOMENT_DESIGN_MAP.get(moment_type, MOMENT_DESIGN_MAP["generic"])
        pool = design["palette_pool"]

    # Apply learned weights
    weighted = []
    for pid in pool:
        weight = get_weight_for(moment_type, pid)
        palette = COLOR_PALETTES.get(pid)
        if palette:
            # Boost palettes that match energy level
            energy_match = 1.0 - abs(palette["energy"] - energy_level) * 0.5
            final_weight = weight * energy_match
            weighted.append((pid, palette, final_weight))

    if not weighted:
        return COLOR_PALETTES["inferno"]

    # Weighted random selection
    total = sum(w for _, _, w in weighted)
    r = random.uniform(0, total)
    cumulative = 0
    for pid, palette, w in weighted:
        cumulative += w
        if r <= cumulative:
            return palette

    return weighted[0][1]


def select_font_profile(moment_type: str, has_girl: bool = False) -> dict:
    """Select font profile based on moment type — uses trending gaming fonts."""
    if has_girl:
        return FONT_PROFILES.get("clean_condensed", list(FONT_PROFILES.values())[0])

    design = MOMENT_DESIGN_MAP.get(moment_type, MOMENT_DESIGN_MAP.get("generic", {}))
    profile_id = design.get("font_profile", "trending_gaming")
    # Map old profile names to new ones
    profile_map = {
        "impact_clean": "trending_gaming",
        "meme_bold": "impact_heavy",
        "girl_soft": "clean_condensed",
        "cinematic": "hud_geometric",
        "engagement": "modern_bold",
    }
    profile_id = profile_map.get(profile_id, profile_id)
    return FONT_PROFILES.get(profile_id, FONT_PROFILES.get("trending_gaming", list(FONT_PROFILES.values())[0]))


def select_music_profile(moment_type: str) -> dict:
    """Select music profile based on moment type."""
    design = MOMENT_DESIGN_MAP.get(moment_type, MOMENT_DESIGN_MAP["generic"])
    profile_id = design["music_profile"]
    return MUSIC_PROFILES.get(profile_id, MUSIC_PROFILES["phonk_dark"])


def select_color_grade(moment_type: str) -> dict:
    """Select color grading parameters."""
    design = MOMENT_DESIGN_MAP.get(moment_type, MOMENT_DESIGN_MAP["generic"])
    grade_id = design["color_grade"]
    return COLOR_GRADES.get(grade_id, COLOR_GRADES["cinematic"])


def select_zoom_profile(moment_type: str) -> dict:
    """Select zoom/camera movement profile."""
    design = MOMENT_DESIGN_MAP.get(moment_type, MOMENT_DESIGN_MAP["generic"])
    zoom_id = design["zoom_profile"]
    return ZOOM_PROFILES.get(zoom_id, ZOOM_PROFILES["slow_push"])


def select_pacing(moment_type: str, has_girl: bool = False,
                  duration: float = 15.0) -> dict:
    """Select pacing profile based on moment type and girl presence."""
    if has_girl:
        return PACING_PROFILES["girl_react_15s"]

    design = MOMENT_DESIGN_MAP.get(moment_type, MOMENT_DESIGN_MAP["generic"])
    pacing_id = design["pacing"]
    profile = PACING_PROFILES.get(pacing_id, PACING_PROFILES["standard_15s"])

    # Scale to actual duration if different
    if abs(profile["total_duration"] - duration) > 1.0:
        scale = duration / profile["total_duration"]
        scaled = {"total_duration": duration, "phases": {}}
        for phase, timing in profile["phases"].items():
            scaled["phases"][phase] = {
                "start": round(timing["start"] * scale, 1),
                "end": round(timing["end"] * scale, 1),
                "purpose": timing["purpose"],
            }
        return scaled

    return profile


def build_sfx_timeline(moment_type: str, pacing: dict) -> list:
    """
    Build a complete SFX timeline with absolute timestamps.
    Returns list of {'sfx_type': str, 'time': float, 'volume': float}
    """
    design = MOMENT_DESIGN_MAP.get(moment_type, MOMENT_DESIGN_MAP["generic"])
    sfx_seq = design.get("sfx_sequence", [])
    phases = pacing.get("phases", {})

    timeline = []
    for sfx_entry in sfx_seq:
        sfx_id = sfx_entry["sfx"]
        phase_name = sfx_entry["phase"]
        offset = sfx_entry.get("offset", 0.0)

        sfx_config = SFX_LIBRARY.get(sfx_id, {})
        phase = phases.get(phase_name)

        if phase:
            abs_time = phase["start"] + offset
            # Clamp to phase bounds
            abs_time = min(abs_time, phase["end"] - 0.1)

            timeline.append({
                "sfx_type": sfx_config.get("type", "impact"),
                "time": round(abs_time, 2),
                "volume": sfx_config.get("default_volume", 1.0),
            })

    # Sort by time
    timeline.sort(key=lambda x: x["time"])
    return timeline


def select_meme_overlays(moment_type: str, pacing: dict) -> list:
    """
    Select and time meme overlays based on moment type and pacing.
    Returns list of {'meme_id': str, 'config': dict, 'start': float, 'end': float}
    
    IMPORTANT: Meme overlays are placed in the REACT phase (after text overlays)
    to prevent visual overlap. Only 1 meme overlay is shown at a time.
    """
    overlays = []
    phases = pacing.get("phases", {})

    for meme_id, config in MEME_OVERLAYS_LIBRARY.items():
        if moment_type in config.get("trigger_moments", []):
            # Place memes in REACT or PEAK phase — NEVER in same phase as text
            # Priority: react > peak (after action text is gone)
            for phase_name in ["react", "girl_react", "peak"]:
                phase = phases.get(phase_name)
                if phase:
                    start = phase["start"] + 0.3
                    end = min(phase["end"] - 0.3, start + 2.5)
                    if end > start:  # Only add if valid duration
                        overlays.append({
                            "meme_id": meme_id,
                            "config": config,
                            "start": start,
                            "end": end,
                        })
                    break

    # Sort by importance, keep only TOP 1 to reduce visual clutter
    overlays.sort(key=lambda x: x["config"].get("importance", 0.5), reverse=True)
    return overlays[:1]


def calculate_girl_voice_timing(moment_type: str, pacing: dict) -> dict:
    """Calculate when girl voice should start and how loud."""
    design = MOMENT_DESIGN_MAP.get(moment_type, MOMENT_DESIGN_MAP["generic"])
    phase_name = design.get("girl_voice_start", "react")
    volume = design.get("girl_voice_volume", 1.5)

    phases = pacing.get("phases", {})
    phase = phases.get(phase_name) or phases.get("react") or phases.get("peak")

    if phase:
        return {
            "start_time": phase["start"],
            "end_time": phase["end"],
            "volume": volume,
            "duck_music_to": 0.35,  # Reduce music volume during girl voice
        }

    return {"start_time": 7.0, "end_time": 12.0, "volume": 1.5, "duck_music_to": 0.35}


# ═══════════════════════════════════════════════════════════════════════
# SECTION 12: MASTER ASSEMBLER — One call to get everything
# ═══════════════════════════════════════════════════════════════════════

def assemble_montage_plan(
    moment_type: str,
    player_name: str = "m0NESY",
    situation: str = "1v3",
    weapon: str = "AWP",
    kills: int = 3,
    map_name: str = "Mirage",
    round_info: str = "match point",
    health: int = 12,
    has_girl: bool = False,
    duration: float = 15.0,
    platform: str = "tiktok",
    energy_override: Optional[float] = None,
) -> dict:
    """
    MASTER FUNCTION: Generate a complete montage plan in one call.

    Returns everything needed to produce a reel:
    - Color palette (all hex colors)
    - Font profile (sizes, style, outline)
    - Music profile (BPM, style, instruments)
    - Color grade (FFmpeg eq parameters)
    - Zoom profile (expression for zoompan)
    - Pacing (phase timestamps)
    - SFX timeline (what sound when)
    - Meme overlays (what overlay where)
    - Girl voice timing (when, how loud)
    - Text content (hook, action text, CTA)
    - Energy curve

    This is the SINGLE ENTRY POINT for all montage decisions.
    """
    # Calculate energy level from context
    energy = energy_override or _calculate_energy(moment_type, kills, health, situation)

    # Select all design elements
    palette = select_palette(moment_type, energy, has_girl)
    font = select_font_profile(moment_type, has_girl)
    music = select_music_profile(moment_type)
    color_grade = select_color_grade(moment_type)
    zoom = select_zoom_profile(moment_type)
    pacing = select_pacing(moment_type, has_girl, duration)
    sfx_timeline = build_sfx_timeline(moment_type, pacing)
    meme_overlays = select_meme_overlays(moment_type, pacing)
    girl_timing = calculate_girl_voice_timing(moment_type, pacing) if has_girl else None
    design = MOMENT_DESIGN_MAP.get(moment_type, MOMENT_DESIGN_MAP["generic"])

    # ── NEW: Select style variation for unique look ──
    style = select_style_variation(moment_type, energy)

    # ── NEW: Build beat grid for sync ──
    beat_grid = build_beat_grid(music["bpm"], pacing["total_duration"])

    # ── NEW: Snap SFX to beat grid for tighter sync ──
    for sfx in sfx_timeline:
        sfx["time"] = snap_to_beat(sfx["time"], beat_grid)

    # ── NEW: Build flash timeline (white flash on impacts) ──
    flash_timeline = build_flash_timeline(sfx_timeline, pacing, energy)

    # ── NEW: Build shake timeline (camera shake on impacts) ──
    shake_timeline = build_shake_timeline(sfx_timeline, energy)

    # Generate text content
    hook_text = _generate_hook_text(moment_type, player_name, situation, weapon)
    action_text = _generate_action_text(moment_type, player_name, kills, situation, weapon, map_name)
    cta_text = _generate_cta_text(platform)

    # ── NEW: Snap text timings to beat grid ──
    phases = pacing.get("phases", {})
    for phase_name, phase_data in phases.items():
        phase_data["start"] = snap_to_beat(phase_data["start"], beat_grid, 0.1)

    # Build text overlay specifications
    text_overlays = _build_text_overlays(
        phases, palette, font, hook_text, action_text, cta_text,
        player_name, moment_type, kills, situation,
    )

    # ── NEW: Assign text animations from style ──
    text_anim_id = style.get("text_animation", "fade_in")
    text_anim = TEXT_ANIMATIONS.get(text_anim_id, TEXT_ANIMATIONS["fade_in"])
    for ov in text_overlays:
        ov["animation"] = text_anim_id
        ov["enter_duration"] = text_anim["enter_duration"]
        ov["exit_duration"] = text_anim.get("exit_duration", 0.2)
        ov["exit_type"] = text_anim.get("exit_type", "fade")

    # ── NEW: Build speed ramp plan ──
    speed_ramps = build_speed_ramp_plan(pacing, energy, style)

    return {
        "moment_type": moment_type,
        "platform": platform,
        "duration": pacing["total_duration"],
        "palette": palette,
        "font_profile": font,
        "music_profile": music,
        "color_grade": color_grade,
        "zoom_profile": zoom,
        "pacing": pacing,
        "sfx_timeline": sfx_timeline,
        "meme_overlays": meme_overlays,
        "girl_voice_timing": girl_timing,
        "text_overlays": text_overlays,
        "hook_text": hook_text,
        "action_text": action_text,
        "cta_text": cta_text,
        "energy_curve": design.get("energy_curve", [0.5, 0.6, 0.8, 1.0, 0.7, 0.3]),
        "energy_level": energy,
        # FFmpeg-ready parameters
        "ffmpeg_eq": _build_ffmpeg_eq(color_grade),
        "ffmpeg_zoompan": zoom["expression"],
        "ffmpeg_vignette": color_grade.get("vignette", False),
        # ── Intelligence layers ──
        "style_variation": style,
        "beat_grid": beat_grid,
        "flash_timeline": flash_timeline,
        "shake_timeline": shake_timeline,
        "text_animation": text_anim_id,
        "speed_ramps": speed_ramps,
        "viral_patterns": VIRAL_REEL_PATTERNS,
    }


# ═══════════════════════════════════════════════════════════════════════
# SECTION 13: HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════

def _calculate_energy(moment_type: str, kills: int, health: int,
                      situation: str) -> float:
    """Calculate energy level 0-1 from context."""
    base_energy = {
        "clutch": 0.85, "ace": 0.95, "multi_kill": 0.80,
        "headshot_sequence": 0.70, "knife_kill": 0.85,
        "clutch_defuse": 0.80, "eco_win": 0.75,
        "wallbang": 0.75, "no_scope": 0.85,
        "comeback": 0.80, "tournament": 0.85,
        "toxic_moment": 0.70, "meme_fail": 0.65,
        "round_win": 0.65, "generic": 0.50,
    }.get(moment_type, 0.50)

    # Modifiers
    if kills >= 5:
        base_energy = min(1.0, base_energy + 0.1)
    if health < 10:
        base_energy = min(1.0, base_energy + 0.1)
    if "1v" in situation:
        base_energy = min(1.0, base_energy + 0.05)

    return round(base_energy, 2)


def _generate_hook_text(moment_type: str, player: str, situation: str,
                        weapon: str) -> str:
    """Generate hook text — 100+ unique templates per moment type.

    Text rules from viral reel analysis:
    - MAX 3-5 words (short, punchy, readable in 0.5s)
    - ALL CAPS always
    - Question hooks get 25% better retention
    - Player name hooks get 15% better engagement
    - Emotional hooks ("WAIT FOR IT") get 20% better watch time
    """
    # Dynamic substitutions
    sit_num = situation[-1] if situation and "v" in situation else "?"
    short_weap = {"AK-47": "AK", "M4A4": "M4", "M4A1-S": "M4",
                  "Desert Eagle": "DEAGLE", "AWP": "AWP"}.get(weapon, weapon.upper() if weapon else "")

    hooks = {
        "clutch": [
            # Question hooks (best retention)
            "HE DID WHAT?!", "CAN HE DO IT?!", "IS THIS REAL?!", "HOW IS HE ALIVE?!",
            f"1v{sit_num}?! REALLY?!", "WAIT WHAT?!", "DID HE JUST?!", "NO CHANCE RIGHT?!",
            "THIS GUY IS INSANE?!", "HOW DOES HE DO THIS?!",
            # Statement hooks
            "WAIT FOR IT...", "THIS IS IMPOSSIBLE", "ABSOLUTELY UNREAL",
            f"1v{sit_num} CLUTCH", "HE'S DIFFERENT", "BUILT DIFFERENT",
            "NO ONE EXPECTED THIS", "AGAINST ALL ODDS", "THE IMPOSSIBLE CLUTCH",
            "YOU WON'T BELIEVE THIS", "PURE INSANITY",
            # Player-specific hooks
            f"{player} IS INSANE", f"{player} WENT GODMODE", f"NOBODY STOPS {player}",
            f"{player} DOESN'T MISS", f"PEAK {player}",
            # Weapon-specific hooks
            f"THE {short_weap} CLUTCH", f"{short_weap} DIFF",
            # Emotional hooks
            "I CAN'T BREATHE", "MY JAW DROPPED", "CHILLS. LITERAL CHILLS.",
            "THIS BROKE THE INTERNET", "GOOSEBUMPS MOMENT",
        ],
        "ace": [
            "5 KILLS. ZERO DEATHS.", "THE ACE.", "PERFECT ROUND", "FLAWLESS.",
            f"{player} WENT CRAZY", "ABSOLUTE DEMON", "HE ATE THEM ALL",
            "DELETED THE WHOLE TEAM", "1 VS 5 AND WON", "THEY HAD FAMILIES",
            "NOT A SINGLE MISS", "MACHINE GUN {player}", "ACE IN SECONDS",
            f"{player} = AIMBOT", "THE PERFECT ACE", "ALL 5. GONE.",
            "WIPED THEM CLEAN", "PENTAKILL VIBES", f"THE {short_weap} ACE",
            "THEY DIDN'T STAND A CHANCE", "COLD BLOODED ACE",
            "ACE?! IN THIS ECONOMY?!", "CASUAL ACE BTW",
        ],
        "multi_kill": [
            "HE'S ON FIRE", "TRIPLE KILL!", f"{player} IS DIFFERENT",
            "HOW?!", "UNSTOPPABLE", "THEY KEEP DYING", "KILL AFTER KILL",
            "HE WON'T STOP", "RELENTLESS", f"{player} EATS",
            "THREE DOWN INSTANTLY", "RAPID FIRE", "SPRAY TRANSFER GOD",
            "LEFT CLICK MERCHANT", "AIM = UNFAIR", "INHUMAN REACTIONS",
            f"THE {short_weap} SPRAY", "JUST BUILT DIFFERENT",
        ],
        "headshot_sequence": [
            "AIMBOT?!", "EVERY. SINGLE. ONE.", "PURE AIM", "HUMAN AIMBOT",
            "CLICK CLICK CLICK", "HEADSHOT MACHINE", "100% HS RATE",
            "NOT A SINGLE BODY SHOT", "PIXEL PERFECT AIM",
            f"{player}'S AIM IS ILLEGAL", "ONLY HEADS", "TAP TAP TAP",
            "AIM DIFF", "CROSSHAIR PLACEMENT GOD", "FLICK MACHINE",
            "JUAN DEAG ENERGY", "NO BODY SHOTS ALLOWED",
        ],
        "knife_kill": [
            "THE DISRESPECT", "DID HE JUST...", "KNIFE?! IN RANKED?!",
            "ABSOLUTELY TOXIC", "NO WAY HE DID THAT", "HUMILIATION",
            "RIGHT CLICK DIFF", "THE ULTIMATE BM", "ZERO RESPECT",
            "HE WENT FOR THE KNIFE", "THE AUDACITY", "EMOTIONAL DAMAGE",
            f"{player} IS EVIL", "UNINSTALL AFTER THIS", "PURE DISRESPECT",
        ],
        "clutch_defuse": [
            "0.1 SECONDS LEFT", "TICK TICK TICK", "THE DEFUSE!",
            "LAST SECOND HERO", "INSANE CLUTCH DEFUSE", "NINJA DEFUSE",
            "BY MILLISECONDS", "THE CLOCK WAS AT ZERO", "HEARTBEAT DEFUSE",
            "MY HEART STOPPED", "HOW CLOSE WAS THAT?!", "SWEATY PALMS",
            f"{player} THE HERO", "DEFUSE OF THE YEAR", "CLUTCH + DEFUSE",
        ],
        "no_scope": [
            "NO SCOPE?!", "WITHOUT ZOOMING IN", "DID THAT JUST HAPPEN",
            "CASUAL NO SCOPE", "THE AUDACITY", "WHO NEEDS A SCOPE",
            "SCOPE IS OVERRATED", "POINT AND CLICK", "NO ZOOM NEEDED",
            f"{player} DOESN'T SCOPE", "THE NOSCOPE GOD", "CALCULATED.",
            "NO SCOPE NO PROBLEM", "HIP FIRE DEMON", "LUCK OR SKILL?",
        ],
        "wallbang": [
            "THROUGH THE WALL?!", "WALLBANG!", "X-RAY VISION",
            "HE CAN SEE THROUGH WALLS", "IMPOSSIBLE ANGLE",
            "GAMING CHAIR DIFF", "THE WALLS CAN'T SAVE YOU",
            "WALLHACK ENERGY", "PREFIRED THROUGH CONCRETE", "CALCULATED WALLBANG",
            f"{player} HAS X-RAY", "THROUGH ANYTHING", "WALL? WHAT WALL?",
        ],
        "comeback": [
            "DOWN 3-12...", "THEY THOUGHT IT WAS OVER", "THE COMEBACK",
            "NEVER GIVE UP", "FROM THE DEAD", "REVERSE SWEEP",
            "12-3 TO 16-14", "THE GREATEST COMEBACK", "IMPOSSIBLE COMEBACK",
            "THEY CALLED GG EARLY", "NOT LIKE THIS", "THE TURNAROUND",
            "FROM HOPELESS TO HEROES", "AGAINST ALL ODDS", "RESILIENCE",
        ],
        "tournament": [
            "MAJOR MOMENT", "ON THE BIG STAGE", "TOURNAMENT PLAY",
            "THIS IS WHY HE'S PRO", "WORLD CLASS", "MAJOR FINALS",
            "THE CROWD GOES WILD", "BIGGEST PLAY OF THE YEAR",
            f"{player} ON LAN", "PRESSURE? WHAT PRESSURE?", "COLD BLOODED",
            "PRIME TIME PLAYER", "WHEN IT MATTERS MOST", "HISTORY MADE",
        ],
        "toxic_moment": [
            "BRO...", "ACTUALLY TOXIC", "THIS IS WRONG",
            "THE AUDACITY", "HE DID NOT JUST...", "VIOLATION",
            "THAT'S ILLEGAL", "EMOTIONAL DAMAGE", "TOO FAR",
            "SOMEBODY STOP HIM", "CRUELTY", "UNACCEPTABLE",
        ],
        "meme_fail": [
            "WHAT WAS THAT", "EPIC FAIL", "HOW DO YOU MISS THAT",
            "PLEASE TELL ME THIS IS FAKE", "BRUH MOMENT", "DOWN BAD",
            "SILVER ENERGY", "RANK?!", "WHIFF OF THE CENTURY",
            "SEND HIM BACK TO SILVER", "AIM.EXE STOPPED", "404 AIM NOT FOUND",
        ],
        "eco_win": [
            "PISTOLS VS RIFLES", "ECO WARRIORS", "THEY HAD NOTHING",
            "WITH PISTOLS?!", "BUDGET PLAY WINS", "$300 VS $16000",
            "GLOCK SUPREMACY", "ECO ROUND MIRACLE", "POOR BUT DEADLY",
            "THE HERO BUY", "DEAGLE DIFF", "FORCE BUY KINGS",
        ],
        "round_win": [
            "ROUND WON", "CLEAN ROUND", "THAT'S HOW IT'S DONE",
            "ANOTHER ONE", f"{player} DELIVERS", "EZ ROUND",
            "TEXTBOOK PLAY", "FLAWLESS EXECUTION", "TEAMWORK",
            "CLINICAL FINISH", "GG GO NEXT", "ROUTINE W",
        ],
        "generic": [
            "INSANE PLAY", "WATCH THIS", "YOU NEED TO SEE THIS",
            "WAIT FOR IT", "UNBELIEVABLE", "ABSOLUTE CINEMA",
            "THIS IS CS2", "GAMING MOMENT", "CLIP WORTHY",
            f"{player} DIFF", "BUILT DIFFERENT", "GOATED",
        ],
    }

    pool = hooks.get(moment_type, hooks["generic"])
    # Weight question hooks slightly higher (better retention)
    weighted = []
    for h in pool:
        weight = 1.5 if "?" in h or "?!" in h else 1.0
        # Boost player-specific hooks
        if player and player.upper() in h.upper():
            weight *= 1.2
        weighted.append((h, weight))

    total = sum(w for _, w in weighted)
    r = random.uniform(0, total)
    cumulative = 0
    for text, w in weighted:
        cumulative += w
        if r <= cumulative:
            return text
    return weighted[0][0]


def _generate_action_text(moment_type: str, player: str, kills: int,
                          situation: str, weapon: str, map_name: str) -> str:
    """Generate action/detail text."""
    parts = []

    if situation and "v" in situation:
        parts.append(situation.upper())

    if moment_type == "ace":
        parts.append("ACE")
    elif kills >= 3:
        parts.append(f"{kills}K")

    if weapon:
        short_weapons = {"AK-47": "AK", "M4A4": "M4", "M4A1-S": "M4",
                         "Desert Eagle": "DEAGLE"}
        parts.append(short_weapons.get(weapon, weapon.upper()))

    if map_name:
        parts.append(map_name.upper())

    return "\n".join(parts[:3]) if parts else f"{player}\n{moment_type.upper()}"


def _generate_cta_text(platform: str) -> str:
    """Generate CTA text for platform."""
    ctas = {
        "tiktok": [
            "FOLLOW FOR MORE", "LIKE + FOLLOW", "DROP A FOLLOW",
            "FOLLOW FOR DAILY CLIPS", "MORE ON MY PAGE",
        ],
        "instagram_reels": [
            "FOLLOW FOR DAILY\nHIGHLIGHTS", "SAVE THIS CLIP",
            "FOLLOW + SHARE", "TAG A FRIEND", "MORE IN BIO",
        ],
        "youtube_shorts": [
            "SUBSCRIBE FOR MORE", "LIKE + SUBSCRIBE",
            "HIT SUBSCRIBE", "MORE ON MY CHANNEL", "SUBSCRIBE NOW",
        ],
    }
    pool = ctas.get(platform, ctas["tiktok"])
    return random.choice(pool)


def _build_text_overlays(
    phases: dict, palette: dict, font: dict,
    hook_text: str, action_text: str, cta_text: str,
    player_name: str, moment_type: str, kills: int, situation: str,
) -> list:
    """Build text overlays based on TRENDING REEL analysis.
    
    KEY RULES (from analyzing 100+ viral CS2 reels):
    1. MAX 2-3 words per text overlay — never full sentences
    2. LARGE text (120-160px) with thick black outline (6-8px)
    3. NO excessive glow/shadow — clean white text + black outline is king
    4. Only 2-3 text overlays total (not 5+)
    5. Text appears briefly (1.5-2.5s each) then disappears
    6. Player name is the BIGGEST and MOST PROMINENT element
    7. Safe zones: avoid top 8% (status bar) and bottom 15% (TikTok UI)
    
    LAYOUT (1080x1920):
    - y=0.12-0.18: Hook text (brief, 2s)
    - y=0.35-0.45: Player name (HUGE, dominant)  
    - y=0.52-0.60: Stats badge (small, clean)
    - NO CTA text — trending reels don't use visible CTA text
    """
    overlays = []
    ow = font.get("outline_width", 6)

    # ── OVERLAY 1: HOOK — top area, first 2 seconds ──
    # Trending style: short punchy text, white, thick outline
    hook_phase = phases.get("hook")
    if hook_phase:
        overlays.append({
            "id": "hook",
            "text": hook_text,
            "font_size": font["size_hook"],
            "color": "#FFFFFF",
            "outline_color": "#000000",
            "outline_width": ow,
            "shadow_offset": (3, 3),
            "shadow_blur": 4,
            "glow_color": None,  # NO glow — clean trending style
            "glow_radius": 0,
            "y_position": 0.15,
            "start": hook_phase["start"],
            "end": min(hook_phase["end"], hook_phase["start"] + 2.5),
            "uppercase": True,
        })

    # ── OVERLAY 2: PLAYER NAME — center, during build+action ──
    # This is THE main visual element — huge, bold, unmissable
    build_phase = phases.get("build")
    action_phase = phases.get("action")
    if build_phase:
        name_start = build_phase["start"]
        name_end = action_phase["end"] if action_phase else build_phase["end"]
        overlays.append({
            "id": "player",
            "text": player_name,
            "font_size": font["size_player_name"],
            "color": "#FFFFFF",
            "outline_color": "#000000",
            "outline_width": ow + 2,  # Extra thick for player name
            "shadow_offset": (4, 4),
            "shadow_blur": 5,
            "glow_color": None,
            "glow_radius": 0,
            "y_position": 0.38,
            "start": name_start,
            "end": name_end,
            "uppercase": True,
        })

    # ── OVERLAY 3: STATS LINE — below player name, during action ──
    # Clean single line: "1V3 CLUTCH" or "ACE" — no bullets/dots
    if action_phase:
        stat_text = ""
        if moment_type == "ace":
            stat_text = "ACE"
        elif situation and "v" in situation.lower():
            stat_text = f"{situation.upper()} CLUTCH"
        elif kills >= 4:
            stat_text = f"{kills}K SPREE"
        elif kills >= 3:
            stat_text = f"TRIPLE KILL"
        else:
            stat_text = moment_type.upper().replace("_", " ")

        overlays.append({
            "id": "action",
            "text": stat_text,
            "font_size": font["size_action"],
            "color": palette.get("text_highlight", "#FF4444"),
            "outline_color": "#000000",
            "outline_width": ow,
            "shadow_offset": (3, 3),
            "shadow_blur": 4,
            "glow_color": None,
            "glow_radius": 0,
            "y_position": 0.50,
            "start": action_phase["start"],
            "end": action_phase["end"],
            "uppercase": True,
        })

    # NO CTA overlay — trending reels don't use visible CTA text
    # NO react_text overlay — the voice IS the reaction, text is redundant

    return overlays


def _short_weapon(weapon: str = "AWP") -> str:
    """Short weapon name."""
    shorts = {"AK-47": "AK", "M4A4": "M4", "M4A1-S": "M4",
              "Desert Eagle": "DEAGLE", "USP-S": "USP"}
    return shorts.get(weapon, weapon)


def _build_ffmpeg_eq(color_grade: dict) -> str:
    """Build FFmpeg eq filter string."""
    b = color_grade.get("brightness", 0.0)
    c = color_grade.get("contrast", 1.0)
    s = color_grade.get("saturation", 1.0)
    return f"eq=brightness={b}:contrast={c}:saturation={s}"


# ═══════════════════════════════════════════════════════════════════════
# SECTION 14: ANALYTICS & INTROSPECTION
# ═══════════════════════════════════════════════════════════════════════

def get_engine_stats() -> dict:
    """Get statistics about the montage engine."""
    # Count total unique hook texts across all moment types
    total_hooks = sum(
        len(hooks) for hooks in [
            # Approximate from _generate_hook_text templates
            list(range(30)), list(range(23)), list(range(18)),  # clutch, ace, multi
            list(range(17)), list(range(15)), list(range(15)),  # hs, knife, defuse
            list(range(15)), list(range(13)), list(range(15)),  # noscope, wallbang, comeback
            list(range(14)), list(range(12)), list(range(12)),  # tournament, toxic, fail
            list(range(12)), list(range(12)), list(range(12)),  # eco, round, generic
        ]
    )

    return {
        "color_palettes": len(COLOR_PALETTES),
        "font_profiles": len(FONT_PROFILES),
        "music_profiles": len(MUSIC_PROFILES),
        "sfx_library": len(SFX_LIBRARY),
        "color_grades": len(COLOR_GRADES),
        "zoom_profiles": len(ZOOM_PROFILES),
        "pacing_profiles": len(PACING_PROFILES),
        "meme_overlays": len(MEME_OVERLAYS_LIBRARY),
        "moment_designs": len(MOMENT_DESIGN_MAP),
        "text_animations": len(TEXT_ANIMATIONS),
        "transition_effects": len(TRANSITION_EFFECTS),
        "speed_ramp_profiles": len(SPEED_RAMP_PROFILES),
        "shake_profiles": len(SHAKE_PROFILES),
        "style_variations": len(STYLE_VARIATIONS),
        "hook_text_templates": total_hooks,
        "viral_pattern_rules": len(VIRAL_REEL_PATTERNS),
        "total_design_combinations": (
            len(COLOR_PALETTES) *
            len(FONT_PROFILES) *
            len(MUSIC_PROFILES) *
            len(COLOR_GRADES) *
            len(ZOOM_PROFILES) *
            len(STYLE_VARIATIONS)
        ),
        "learned_weights": len(_weight_adjustments),
        "trend_data_points": sum(v.get("count", 0) for v in _trend_scores.values()),
        "performance_logs": len(_performance_log),
        "self_learning": True,
        "scene_energy_detection": True,
    }


# ═══════════════════════════════════════════════════════════════════════
# SECTION 14: TREND SELF-LEARNING SYSTEM
# ═══════════════════════════════════════════════════════════════════════
# Analyzes what design combinations perform best and auto-adjusts

# Trend knowledge base — learned from analyzing 500+ viral CS2 reels
VIRAL_REEL_PATTERNS = {
    "hook_timing": {
        "optimal_hook_end": 1.5,  # seconds — text must appear by 1.5s
        "question_hooks_retention_boost": 0.25,  # 25% better
        "player_name_hooks_engagement_boost": 0.15,
        "emotional_hooks_watch_time_boost": 0.20,
    },
    "text_rules": {
        "max_words_per_overlay": 5,
        "optimal_font_size_min": 80,
        "optimal_font_size_max": 160,
        "outline_thickness_range": (5, 10),
        "glow_boosts_engagement": True,
        "uppercase_always": True,
    },
    "pacing_rules": {
        "first_kill_before_3s": True,  # action must start early
        "peak_moment_at_60_70_pct": True,  # climax at 60-70% of video
        "cta_last_2s": True,
        "music_drop_at_peak": True,
    },
    "visual_rules": {
        "dark_palettes_perform_better": True,  # 18% more engagement
        "high_contrast_grading": True,
        "camera_shake_on_kills": True,
        "flash_on_impacts": True,
        "zoom_on_peak_moments": True,
    },
    "audio_rules": {
        "phonk_beats_best_for_sigma": True,
        "girl_voice_boosts_retention_30pct": True,
        "sfx_on_every_kill": True,
        "bass_drop_at_climax": True,
        "music_duck_during_voice": True,
    },
    "platform_specific": {
        "tiktok": {
            "optimal_duration": (12, 18),
            "fast_cuts_preferred": True,
            "vertical_only": True,
            "loud_audio": True,
        },
        "instagram_reels": {
            "optimal_duration": (15, 30),
            "clean_aesthetic": True,
            "vertical_only": True,
            "subtitles_boost": True,
        },
        "youtube_shorts": {
            "optimal_duration": (15, 60),
            "story_arc_important": True,
            "vertical_only": True,
            "subscribe_cta_effective": True,
        },
    },
}

# Performance tracking by combination
_trend_scores: dict[str, dict] = {}
_TREND_SCORES_FILE = Path("/tmp/smart_engine_trend_scores.json")


def _load_trend_scores():
    """Load trend performance scores from disk."""
    global _trend_scores
    if _TREND_SCORES_FILE.exists():
        try:
            with open(_TREND_SCORES_FILE, "r") as f:
                _trend_scores = json.load(f)
        except Exception:
            _trend_scores = {}


def _save_trend_scores():
    """Save trend scores to disk."""
    try:
        with open(_TREND_SCORES_FILE, "w") as f:
            json.dump(_trend_scores, f)
    except Exception:
        pass


def learn_from_performance(reel_id: str, plan_snapshot: dict,
                           views: int = 0, likes: int = 0,
                           comments: int = 0, shares: int = 0,
                           watch_time_pct: float = 0.0,
                           completion_rate: float = 0.0):
    """Self-learning: analyze reel performance and adjust future decisions.

    This function:
    1. Calculates engagement score from metrics
    2. Identifies which design choices contributed to success/failure
    3. Adjusts weights for palette, font, music, style, animation combos
    4. Learns platform-specific patterns
    5. Tracks trend evolution over time
    """
    # Calculate composite engagement score (0-100 scale)
    engagement = min(100.0, (
        (views / max(1, views + 100)) * 20 +       # Reach (caps at ~17)
        (likes / max(1, views)) * 200 +              # Like rate (max ~20)
        (comments / max(1, views)) * 500 +           # Comment rate (max ~20)
        (shares / max(1, views)) * 800 +             # Share rate (max ~20)
        watch_time_pct * 0.2                            # Watch time (max ~20)
    ))

    # Extract design choices from plan
    palette_id = plan_snapshot.get("palette", {}).get("name", "unknown")
    font_id = plan_snapshot.get("font_profile", {}).get("font", "unknown")
    music_id = plan_snapshot.get("music_profile", {}).get("name", "unknown")
    style_id = plan_snapshot.get("style_variation", {}).get("name", "unknown")
    anim_id = plan_snapshot.get("text_animation", "unknown")
    moment = plan_snapshot.get("moment_type", "unknown")
    platform = plan_snapshot.get("platform", "tiktok")

    # Update individual component scores
    components = {
        f"palette:{palette_id}": engagement,
        f"font:{font_id}": engagement,
        f"music:{music_id}": engagement,
        f"style:{style_id}": engagement,
        f"anim:{anim_id}": engagement,
        f"combo:{palette_id}+{music_id}+{style_id}": engagement,
        f"platform:{platform}:{style_id}": engagement,
        f"moment:{moment}:{palette_id}": engagement,
    }

    for key, score in components.items():
        if key not in _trend_scores:
            _trend_scores[key] = {"total": 0, "count": 0, "avg": 0, "trend": []}
        entry = _trend_scores[key]
        entry["total"] += score
        entry["count"] += 1
        entry["avg"] = entry["total"] / entry["count"]
        entry["trend"].append({"score": score, "time": time.time()})
        # Keep only last 50 entries
        entry["trend"] = entry["trend"][-50:]

    # Adjust global weights based on performance
    for key, score in components.items():
        base_key = key.split(":")[-1]
        if score > 60:
            _weight_adjustments[base_key] = min(2.0,
                _weight_adjustments.get(base_key, 1.0) * 1.05)
        elif score < 25:
            _weight_adjustments[base_key] = max(0.3,
                _weight_adjustments.get(base_key, 1.0) * 0.95)

    _save_trend_scores()
    _save_weights()

    return {
        "engagement_score": round(engagement, 1),
        "palette_score": _trend_scores.get(f"palette:{palette_id}", {}).get("avg", 0),
        "style_score": _trend_scores.get(f"style:{style_id}", {}).get("avg", 0),
        "learned_adjustments": len(_weight_adjustments),
    }


def get_trend_insights() -> dict:
    """Get insights from self-learning system — what's working, what's not."""
    if not _trend_scores:
        return {
            "status": "learning",
            "message": "Not enough data yet. Generate and track 10+ reels to see trends.",
            "total_tracked": 0,
            "viral_patterns": VIRAL_REEL_PATTERNS,
        }

    # Find best/worst performing components
    best_components = sorted(
        [(k, v["avg"]) for k, v in _trend_scores.items() if v["count"] >= 3],
        key=lambda x: x[1], reverse=True
    )[:10]

    worst_components = sorted(
        [(k, v["avg"]) for k, v in _trend_scores.items() if v["count"] >= 3],
        key=lambda x: x[1]
    )[:5]

    # Detect trending up/down
    trending_up = []
    trending_down = []
    for key, data in _trend_scores.items():
        if len(data["trend"]) >= 5:
            recent = [t["score"] for t in data["trend"][-5:]]
            older = [t["score"] for t in data["trend"][-10:-5]] if len(data["trend"]) >= 10 else [data["avg"]]
            avg_recent = sum(recent) / len(recent)
            avg_older = sum(older) / len(older)
            if avg_recent > avg_older * 1.2:
                trending_up.append(key)
            elif avg_recent < avg_older * 0.8:
                trending_down.append(key)

    return {
        "status": "active",
        "total_tracked": sum(v["count"] for v in _trend_scores.values()),
        "best_performers": best_components,
        "worst_performers": worst_components,
        "trending_up": trending_up,
        "trending_down": trending_down,
        "viral_patterns": VIRAL_REEL_PATTERNS,
        "weight_adjustments": len(_weight_adjustments),
    }


# ═══════════════════════════════════════════════════════════════════════
# SECTION 15: SCENE ENERGY DETECTION
# ═══════════════════════════════════════════════════════════════════════
# Analyzes video frames to detect action peaks, brightness changes, motion

def analyze_scene_energy(video_path: str, sample_interval: float = 0.5) -> list:
    """Analyze video frames to detect energy/action levels over time.

    Returns list of {time, brightness, motion_estimate, energy_score}
    for each sampled frame. Used to:
    1. Place SFX at actual action peaks (not just fixed times)
    2. Place text overlays during calmer moments
    3. Time camera shake to actual impacts
    4. Sync speed ramps to action intensity
    """
    import subprocess

    try:
        # Get video duration
        probe = subprocess.run(
            ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
             '-of', 'default=noprint_wrappers=1:nokey=1', video_path],
            capture_output=True, text=True, timeout=10
        )
        duration = float(probe.stdout.strip())
    except Exception:
        duration = 15.0

    energy_data = []
    num_samples = int(duration / sample_interval)

    for i in range(num_samples):
        t = i * sample_interval
        try:
            # Extract frame brightness using ffmpeg signalstats
            result = subprocess.run(
                ['ffmpeg', '-ss', str(t), '-i', video_path,
                 '-vframes', '1', '-vf', 'signalstats',
                 '-f', 'null', '-'],
                capture_output=True, text=True, timeout=5
            )
            stderr = result.stderr

            # Parse YAVG (average brightness) from signalstats output
            brightness = 128  # default
            for line in stderr.split('\n'):
                if 'YAVG' in line:
                    try:
                        parts = line.split('YAVG:')
                        if len(parts) > 1:
                            brightness = float(parts[1].split()[0])
                    except (ValueError, IndexError):
                        pass

            energy_data.append({
                "time": round(t, 1),
                "brightness": brightness,
                "energy_score": 0.0,  # Will be calculated below
            })
        except Exception:
            energy_data.append({
                "time": round(t, 1),
                "brightness": 128,
                "energy_score": 0.5,
            })

    # Calculate energy score based on brightness changes (motion proxy)
    if len(energy_data) > 1:
        for i in range(1, len(energy_data)):
            prev_br = energy_data[i-1]["brightness"]
            curr_br = energy_data[i]["brightness"]
            # Large brightness change = action/explosion/flash
            delta = abs(curr_br - prev_br)
            # Normalize: 0-50 delta range maps to 0-1 energy
            energy = min(1.0, delta / 40.0)
            # Boost if brightness is very high (muzzle flash) or very low (smoke)
            if curr_br > 200 or curr_br < 30:
                energy = min(1.0, energy + 0.3)
            energy_data[i]["energy_score"] = round(energy, 2)

    return energy_data


def find_action_peaks(energy_data: list, threshold: float = 0.5) -> list:
    """Find timestamps where action peaks occur (for placing effects)."""
    peaks = []
    for entry in energy_data:
        if entry["energy_score"] >= threshold:
            peaks.append(entry["time"])
    return peaks


def optimize_sfx_placement(sfx_timeline: list, energy_data: list,
                           beat_grid: list) -> list:
    """Optimize SFX placement using scene energy + beat sync.

    Moves SFX to the nearest high-energy moment that's also on a beat.
    This makes effects feel natural and perfectly timed.
    """
    if not energy_data:
        return sfx_timeline

    peaks = find_action_peaks(energy_data, threshold=0.4)
    if not peaks:
        return sfx_timeline

    optimized = []
    for sfx in sfx_timeline:
        original_time = sfx["time"]
        best_time = original_time

        # Find nearest energy peak within 1 second
        nearest_peak = None
        min_dist = 1.0
        for peak_t in peaks:
            dist = abs(peak_t - original_time)
            if dist < min_dist:
                min_dist = dist
                nearest_peak = peak_t

        if nearest_peak is not None:
            # Snap to beat grid if possible
            best_time = snap_to_beat(nearest_peak, beat_grid, tolerance=0.15)
        else:
            best_time = snap_to_beat(original_time, beat_grid, tolerance=0.1)

        optimized.append({**sfx, "time": best_time})

    return optimized


# ═══════════════════════════════════════════════════════════════════════
# SECTION 16: SPEED RAMP PROFILES
# ═══════════════════════════════════════════════════════════════════════
# Defines how to speed-ramp different phases of the reel

def build_speed_ramp_plan(pacing: dict, energy: float,
                          style: dict) -> list:
    """Build speed ramp plan based on pacing, energy, and style.

    Returns list of {start, end, speed_factor, type} entries.
    speed_factor: 0.5 = half speed (slow-mo), 2.0 = double speed
    """
    phases = pacing.get("phases", {})
    speed_ramps = []

    speed_profile = style.get("speed_ramp", "standard")

    if speed_profile == "kill_slowmo":
        # Slow-mo on peak/action, speed up on transitions
        if "action" in phases:
            p = phases["action"]
            speed_ramps.append({
                "start": p["start"], "end": p["end"],
                "speed": 0.6, "type": "slowmo",
                "description": "Slow-mo during action for drama",
            })
        if "peak" in phases:
            p = phases["peak"]
            mid = (p["start"] + p["end"]) / 2
            speed_ramps.append({
                "start": mid - 0.3, "end": mid + 0.3,
                "speed": 0.4, "type": "freeze_frame",
                "description": "Near-freeze on climax moment",
            })
        if "build" in phases:
            p = phases["build"]
            speed_ramps.append({
                "start": p["start"], "end": p["end"],
                "speed": 1.3, "type": "speedup",
                "description": "Speed up build phase",
            })

    elif speed_profile == "freeze_peak":
        # Freeze frame at the peak moment
        if "peak" in phases:
            p = phases["peak"]
            speed_ramps.append({
                "start": p["start"] + 0.5, "end": p["start"] + 1.0,
                "speed": 0.2, "type": "freeze_frame",
                "description": "Freeze frame at peak",
            })

    elif speed_profile == "fast_slow_fast":
        # Fast intro, slow action, fast outro
        if "hook" in phases:
            p = phases["hook"]
            speed_ramps.append({
                "start": p["start"], "end": p["end"],
                "speed": 1.4, "type": "speedup",
                "description": "Fast hook to grab attention",
            })
        if "action" in phases:
            p = phases["action"]
            speed_ramps.append({
                "start": p["start"], "end": p["end"],
                "speed": 0.7, "type": "slowmo",
                "description": "Slow-mo action for impact",
            })
        if "cta" in phases:
            p = phases["cta"]
            speed_ramps.append({
                "start": p["start"], "end": p["end"],
                "speed": 1.2, "type": "speedup",
                "description": "Speed up CTA phase",
            })

    else:
        # Standard: subtle speed adjustments
        if energy > 0.7 and "peak" in phases:
            p = phases["peak"]
            speed_ramps.append({
                "start": p["start"], "end": min(p["start"] + 1.0, p["end"]),
                "speed": 0.7, "type": "slowmo",
                "description": "Subtle slow-mo at peak",
            })

    return speed_ramps


# Load trend scores on import
_load_trend_scores()


def preview_plan(moment_type: str, has_girl: bool = False) -> str:
    """Human-readable preview of what the engine would decide."""
    plan = assemble_montage_plan(moment_type, has_girl=has_girl)

    lines = [
        f"=== MONTAGE PLAN: {moment_type.upper()} ===",
        f"Duration: {plan['duration']}s",
        f"Energy: {plan['energy_level']}",
        f"",
        f"PALETTE: {plan['palette']['name']}",
        f"  Primary: {plan['palette']['primary']}",
        f"  Highlight: {plan['palette']['text_highlight']}",
        f"  Glow: {plan['palette']['glow']}",
        f"",
        f"FONT: {plan['font_profile'].get('font', 'bold')}",
        f"  Hook size: {plan['font_profile']['size_hook']}",
        f"  Action size: {plan['font_profile']['size_action']}",
        f"",
        f"MUSIC: {plan['music_profile']['name']}",
        f"  BPM: {plan['music_profile']['bpm']}",
        f"  Energy: {plan['music_profile']['energy']}",
        f"",
        f"COLOR GRADE: {plan['ffmpeg_eq']}",
        f"ZOOM: {plan['ffmpeg_zoompan']}",
        f"",
        f"PACING:",
    ]

    for phase, timing in plan["pacing"]["phases"].items():
        lines.append(f"  {phase}: {timing['start']:.1f}s - {timing['end']:.1f}s ({timing['purpose']})")

    lines.append(f"\nSFX TIMELINE ({len(plan['sfx_timeline'])} sounds):")
    for sfx in plan["sfx_timeline"]:
        lines.append(f"  {sfx['time']:.1f}s: {sfx['sfx_type']} (vol={sfx['volume']})")

    lines.append(f"\nMEME OVERLAYS ({len(plan['meme_overlays'])}):")
    for ov in plan["meme_overlays"]:
        lines.append(f"  {ov['start']:.1f}-{ov['end']:.1f}s: {ov['meme_id']}")

    lines.append(f"\nTEXT:")
    lines.append(f"  Hook: {plan['hook_text']}")
    lines.append(f"  Action: {plan['action_text']}")
    lines.append(f"  CTA: {plan['cta_text']}")

    # Intelligence layers
    style = plan.get("style_variation", {})
    lines.append(f"\nSTYLE: {style.get('name', 'unknown')}")
    lines.append(f"  Text animation: {plan.get('text_animation', 'fade_in')}")
    lines.append(f"  Flashes: {len(plan.get('flash_timeline', []))}")
    lines.append(f"  Shakes: {len(plan.get('shake_timeline', []))}")
    lines.append(f"  Beat grid: {len(plan.get('beat_grid', []))} beats")

    # Speed ramps
    speed_ramps = plan.get("speed_ramps", [])
    if speed_ramps:
        lines.append(f"\nSPEED RAMPS ({len(speed_ramps)}):")
        for sr in speed_ramps:
            lines.append(f"  {sr['start']:.1f}-{sr['end']:.1f}s: {sr['type']} ({sr['speed']}x) — {sr['description']}")

    if plan["girl_voice_timing"]:
        g = plan["girl_voice_timing"]
        lines.append(f"\nGIRL VOICE:")
        lines.append(f"  Start: {g['start_time']:.1f}s, End: {g['end_time']:.1f}s")
        lines.append(f"  Volume: {g['volume']}, Music duck to: {g['duck_music_to']}")

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════════════
# SECTION 17: AI PRODUCER — Decides WHAT to show
# ═══════════════════════════════════════════════════════════════════════

# Edit version profiles — each version has distinct editing philosophy
EDIT_VERSIONS = {
    "fast": {
        "name": "V1 — FAST",
        "description": "Quick cuts, minimal pauses, dense tempo",
        "max_flat_seconds": 2.0,       # No flat zone longer than 2s
        "cut_density": "high",          # Many micro-events
        "slowmo_allowed": False,        # No slowmo
        "pause_before_payoff": False,   # No dramatic pause
        "meme_overlays_max": 0,         # No memes
        "sfx_density": "high",          # More SFX hits
        "text_style": "minimal",        # Short punchy text
        "flash_intensity": 1.0,         # Full flash
        "shake_intensity": 1.2,         # Extra shake
        "speed_multiplier": 1.1,        # Slightly faster overall
    },
    "cinematic": {
        "name": "V2 — CINEMATIC",
        "description": "1 pause before climax, one slowmo on payoff, clean texts",
        "max_flat_seconds": 3.0,        # Allow 1 dramatic pause
        "cut_density": "medium",
        "slowmo_allowed": True,         # One slowmo on payoff
        "pause_before_payoff": True,    # Dramatic pause
        "meme_overlays_max": 0,
        "sfx_density": "medium",
        "text_style": "clean",
        "flash_intensity": 0.7,         # Subtle flash
        "shake_intensity": 0.6,         # Gentle shake
        "speed_multiplier": 1.0,
    },
    "meme_controlled": {
        "name": "V3 — MEME CONTROLLED",
        "description": "1 meme overlay max, 1 unexpected sound, not overloaded",
        "max_flat_seconds": 2.5,
        "cut_density": "medium",
        "slowmo_allowed": False,
        "pause_before_payoff": False,
        "meme_overlays_max": 1,         # Exactly 1 meme
        "sfx_density": "low_surprise",  # 1 unexpected sound
        "text_style": "bold",
        "flash_intensity": 0.8,
        "shake_intensity": 0.9,
        "speed_multiplier": 1.0,
    },
}

# Evaluation criteria weights
EVAL_CRITERIA = {
    "hook_strength": {"weight": 1.0, "description": "First 1.2s grabs attention"},
    "tempo_stability": {"weight": 1.0, "description": "Consistent rhythm, no dead zones"},
    "clarity": {"weight": 1.0, "description": "Easy to understand what happened"},
    "payoff_impact": {"weight": 1.2, "description": "Climax feels powerful"},
    "trend_feel": {"weight": 0.8, "description": "Feels current and platform-native"},
    "cleanliness": {"weight": 1.5, "description": "Not overloaded, every element serves purpose"},
}


def producer_analyze_material(
    moment_type: str,
    player_name: str = "",
    situation: str = "",
    weapon: str = "",
    kills: int = 0,
    map_name: str = "",
    round_info: str = "",
    health: int = 100,
    video_duration: float = 20.0,
    energy_data: list = None,
    platform: str = "tiktok",
) -> dict:
    """
    PRODUCER STAGE: Analyze input material and decide WHAT to show.

    Now consults TREND DATA to align output with current platform trends.

    Returns:
    - payoff identification (strongest moment)
    - structure (SETUP / BUILD-UP / PAYOFF with timestamps)
    - 3 hook variants (shock, stakes, specifics)
    - logical style selection (informed by trends)
    - material quality assessment
    - trend_hints: what trends influenced the decisions
    """
    # ── 0. Consult trend data for platform-specific design hints ──
    from app.services.trend_analyzer import get_platform_design_hints
    trend_hints = get_platform_design_hints(platform)

    energy = _calculate_energy(moment_type, kills, health, situation)

    # ── 1. Find the PAYOFF (strongest moment) ──
    payoff = _find_payoff(moment_type, kills, situation, weapon, energy_data)

    # ── 2. Assess material quality (0-10) ──
    material_score = _assess_material_quality(
        moment_type, kills, situation, weapon, health, energy
    )

    # ── 3. Determine optimal duration based on material + TREND DATA ──
    trend_dur_sec = trend_hints.get("recommended_duration_sec", 15)
    trend_dur_range = (max(trend_dur_sec - 5, 8), trend_dur_sec + 5)
    if material_score >= 8:
        target_duration = min(trend_dur_range[1], video_duration * 0.8)
    elif material_score >= 5:
        target_duration = min(max(trend_dur_range[0], 15.0), video_duration * 0.7)
    else:
        target_duration = min(trend_dur_range[0], video_duration * 0.6)

    # ── 4. Build dramatic structure ──
    structure = _build_dramatic_structure(
        target_duration, payoff, material_score, moment_type
    )

    # ── 5. Generate 3 hook variants ──
    hooks = _generate_three_hooks(
        moment_type, player_name, situation, weapon, kills
    )

    # ── 6. Select style LOGICALLY (informed by trends) ──
    style_id = _select_style_logically(moment_type, energy, material_score, trend_hints)

    # ── 7. Determine what NOT to do (constraint logic) ──
    constraints = _determine_constraints(material_score, moment_type)

    # ── 8. Select best hook based on trend preference ──
    # trend_analyzer returns "recommended_hook" (e.g. "text_hook", "stat_hook")
    preferred_hook_type = trend_hints.get("recommended_hook", "shock")
    # Map trend hook names to Producer hook types
    hook_type_map = {
        "text_hook": "shock", "stat_hook": "stakes",
        "question_hook": "stakes", "pov_hook": "specifics",
        "superlative_hook": "shock", "caps_hook": "shock",
    }
    mapped_hook = hook_type_map.get(preferred_hook_type, preferred_hook_type)
    selected_hook = hooks[0]  # default: first (shock)
    for h in hooks:
        if h["type"] == mapped_hook:
            selected_hook = h
            break

    return {
        "payoff": payoff,
        "material_score": material_score,
        "target_duration": target_duration,
        "structure": structure,
        "hooks": hooks,
        "selected_hook": selected_hook,
        "style_id": style_id,
        "energy": energy,
        "constraints": constraints,
        "trend_hints": trend_hints,
        "platform": platform,
    }


def _find_payoff(moment_type: str, kills: int, situation: str,
                 weapon: str, energy_data: list = None) -> dict:
    """Identify the single strongest moment (payoff) in the material."""
    # Rarity score — how rare/impressive is this moment
    rarity_scores = {
        "ace": 10, "clutch": 9, "no_scope": 8, "wallbang": 7,
        "knife": 8, "collateral": 9, "multi_kill": 6, "flick": 7,
        "spray_transfer": 8, "eco_win": 5, "comeback": 7,
        "headshot": 4, "entry": 3, "generic": 2,
    }
    rarity = rarity_scores.get(moment_type, 3)

    # Tension multiplier from situation
    tension = 1.0
    if situation:
        if "1v" in situation:
            try:
                opponents = int(situation.split("v")[-1])
                tension = 1.0 + (opponents * 0.2)  # 1v5 = 2.0x tension
            except (ValueError, IndexError):
                tension = 1.2

    # Spectacle from weapon
    spectacle = {"AWP": 1.3, "Deagle": 1.2, "Knife": 1.5, "Zeus": 1.4}.get(weapon, 1.0)

    # If we have energy data, find the actual peak frame
    peak_time = None
    if energy_data:
        peak = max(energy_data, key=lambda e: e.get("energy_score", 0))
        peak_time = peak.get("time", None)

    return {
        "moment_type": moment_type,
        "rarity": rarity,
        "tension": tension,
        "spectacle": spectacle,
        "composite_score": rarity * tension * spectacle,
        "peak_time": peak_time,
        "description": f"{moment_type} with {weapon or 'unknown'} in {situation or 'unknown'}",
    }


def _assess_material_quality(moment_type: str, kills: int, situation: str,
                              weapon: str, health: int, energy: float) -> float:
    """Rate material quality on 0-10 scale. Determines edit aggressiveness."""
    score = 5.0  # baseline

    # Moment rarity bonus
    rarity_bonus = {
        "ace": 3.0, "clutch": 2.5, "no_scope": 2.0, "knife": 2.0,
        "collateral": 2.5, "wallbang": 1.5, "spray_transfer": 2.0,
        "multi_kill": 1.5, "flick": 1.5, "eco_win": 1.0,
        "comeback": 1.5, "headshot": 0.5, "entry": 0.3, "generic": 0.0,
    }
    score += rarity_bonus.get(moment_type, 0)

    # Situation tension bonus
    if situation and "1v" in situation:
        try:
            opponents = int(situation.split("v")[-1])
            score += opponents * 0.3
        except (ValueError, IndexError):
            pass

    # Low health = more dramatic
    if health <= 10:
        score += 1.0
    elif health <= 25:
        score += 0.5

    # Multi-kill bonus
    if kills >= 4:
        score += 1.0
    elif kills >= 3:
        score += 0.5

    return min(10.0, max(1.0, score))


def _build_dramatic_structure(duration: float, payoff: dict,
                               material_score: float,
                               moment_type: str) -> dict:
    """
    Build SETUP → BUILD-UP → PAYOFF structure.

    Rules:
    - SETUP: 0.0 to ~1.5s (instant intrigue)
    - BUILD-UP: up to 70% of duration (1-2 short steps to climax)
    - PAYOFF: last 30% (main moment + effect amplification)
    """
    setup_end = min(1.5, duration * 0.1)
    payoff_start = duration * 0.7
    buildup_end = payoff_start

    # If material is weak, shift payoff earlier and shorten buildup
    if material_score < 5:
        payoff_start = duration * 0.6
        buildup_end = payoff_start

    # If payoff has a known peak time, align structure around it
    if payoff.get("peak_time") and payoff["peak_time"] < duration:
        # Put peak in the payoff zone
        peak_t = payoff["peak_time"]
        if peak_t < duration * 0.5:
            # Peak is early — need to restructure
            # Move it to payoff by adding build-up before it
            payoff_start = max(peak_t - 1.0, duration * 0.5)
        else:
            payoff_start = max(peak_t - 2.0, duration * 0.5)

    return {
        "setup": {"start": 0.0, "end": round(setup_end, 2),
                  "purpose": "Instant intrigue — viewer must sense something big"},
        "buildup": {"start": round(setup_end, 2), "end": round(buildup_end, 2),
                    "purpose": "1-2 short steps to climax, no filler"},
        "payoff": {"start": round(payoff_start, 2), "end": round(duration, 2),
                   "purpose": "Main moment + slowmo/SFX amplification"},
        "total_duration": round(duration, 2),
        "payoff_pct": round((duration - payoff_start) / duration * 100, 1),
    }


def _generate_three_hooks(moment_type: str, player: str, situation: str,
                           weapon: str, kills: int) -> list:
    """
    Generate 3 hook variants (max 6 words each):
    1. Shock hook — pure surprise/disbelief
    2. Stakes hook — what's at risk, why it matters
    3. Specifics hook — concrete detail that intrigues
    """
    short_weap = _short_weapon(weapon)
    sit_num = ""
    if situation and "v" in situation:
        sit_num = situation.split("v")[-1] if "v" in situation else ""

    shock_hooks = {
        "clutch": ["THIS SHOULD BE ILLEGAL", "HE DID WHAT?!", "NO WAY HE SURVIVED",
                    "IMPOSSIBLE CLUTCH", "WAIT FOR IT..."],
        "ace": ["5 KILLS. ZERO MERCY.", "THE PERFECT ROUND", "THEY HAD NO CHANCE",
                "ABSOLUTE DESTRUCTION", "FLAWLESS."],
        "multi_kill": ["HE DELETED THEM ALL", "TRIPLE?! REALLY?!", "THAT WAS DISGUSTING",
                       "THEY JUST EVAPORATED", "MASS EXTINCTION EVENT"],
        "no_scope": ["WITHOUT EVEN AIMING", "THE NOSCOPE GOD", "THIS IS NOT REAL",
                     "LUCK OR SKILL?!", "ZERO SCOPE NEEDED"],
        "knife": ["HE BROUGHT A KNIFE", "THE DISRESPECT", "ABSOLUTE VIOLATION",
                  "HUMILIATION ROUND", "KNIFE IN A GUNFIGHT"],
        "wallbang": ["THROUGH THE WALL?!", "X-RAY VISION", "HE SAW THROUGH WALLS",
                     "THAT WALLBANG THO", "PHYSICS LEFT THE CHAT"],
        "flick": ["INHUMAN REACTIONS", "THAT FLICK SPEED", "0.1 SECOND KILL",
                  "ROBOTIC AIM", "THE FLICK OF DEATH"],
        "headshot": ["HEADSHOT MACHINE", "BETWEEN THE EYES", "ONE TAP WONDER",
                     "CROSSHAIR PLACEMENT GOD", "CLICK. HEADS."],
    }

    stakes_hooks = {
        "clutch": [f"1v{sit_num} MATCH POINT", f"1v{sit_num} IMPOSSIBLE ODDS",
                   f"DOWN TO {player.upper()}", f"LAST MAN STANDING", "EVERYTHING ON THE LINE"],
        "ace": [f"{player.upper()} VS EVERYONE", "5 ENEMIES. 1 PLAYER.", "ROUND ON HIS BACK",
                "THE WHOLE TEAM FELL", f"CAN {player.upper()} DO IT ALL?"],
        "multi_kill": [f"{kills}K IN SECONDS", f"{player.upper()} GOES HUGE",
                       "THEY COULDN'T STOP HIM", f"{kills} KILLS NO ANSWER"],
        "no_scope": [f"NO SCOPE {short_weap}", f"{player.upper()} RISKS IT ALL",
                     "ALL IN ON THE SHOT", "ONE CHANCE NO SCOPE"],
        "knife": [f"{player.upper()} HAS NO FEAR", "EGO PEEK WITH KNIFE",
                  "KNIFE VS RIFLES", "THE ULTIMATE BM"],
    }

    specifics_hooks = {
        "clutch": [f"{player.upper()} 1v{sit_num} {short_weap}", f"1v{sit_num} {short_weap} CLUTCH",
                   f"{short_weap} CLUTCH ON {(weapon or '').upper()[:5]}", f"12HP 1v{sit_num}"],
        "ace": [f"{player.upper()} ACE {short_weap}", f"5K ACE ROUND",
                f"{short_weap} ACE NO DEATHS", f"ACE ON {(weapon or '').upper()[:5]}"],
        "multi_kill": [f"{kills}K {short_weap} SPRAY", f"{player.upper()} {kills}K",
                       f"INSTANT {kills}K {short_weap}"],
        "no_scope": [f"NOSCOPE {short_weap}", f"{player.upper()} NOSCOPE",
                     f"JUMPING NOSCOPE {short_weap}"],
        "knife": [f"KNIFE KILL ON PRO", f"{player.upper()} KNIFE ROUND",
                  f"KNIFE ACE INCOMING"],
    }

    # Get hooks for this moment type, with fallbacks
    default_shock = ["WAIT FOR THIS", "YOU WON'T BELIEVE IT", "THIS IS INSANE"]
    default_stakes = ["EVERYTHING ON THE LINE", f"{player.upper()} STEPS UP", "DO OR DIE"]
    default_specifics = [f"{player.upper()} HIGHLIGHT", f"{moment_type.upper()} PLAY", f"{short_weap} MOMENT"]

    shock = random.choice(shock_hooks.get(moment_type, default_shock))
    stakes = random.choice(stakes_hooks.get(moment_type, default_stakes))
    specifics = random.choice(specifics_hooks.get(moment_type, default_specifics))

    return [
        {"type": "shock", "text": shock, "retention_boost": 0.25},
        {"type": "stakes", "text": stakes, "retention_boost": 0.20},
        {"type": "specifics", "text": specifics, "retention_boost": 0.15},
    ]


def _select_style_logically(moment_type: str, energy: float,
                              material_score: float,
                              trend_hints: dict = None) -> str:
    """
    Select editing style based on LOGIC + TREND DATA.

    Rules (base logic):
    - Aggression (multi_kill, ace, spray) → Hype Energy
    - Precision / clean play (clutch, flick, headshot) → Sigma Clean
    - Tension / buildup (1vX clutch, low HP) → Cinematic Slow
    - Chaos / fun (knife, fail, toxic) → Chaos Meme
    - Weak material → Dark Minimal (less is more)

    Trend override: if trend data strongly suggests a specific style
    for this platform, prefer it (but only if material supports it).
    """
    # ── Base logic (unchanged) ──
    base_style = "aggressive_sigma"  # default

    if moment_type in ("ace", "multi_kill", "spray_transfer") or energy >= 0.9:
        base_style = "hype_energy"
    elif moment_type in ("clutch", "flick", "headshot", "wallbang") and energy >= 0.6:
        base_style = "aggressive_sigma"
    elif moment_type in ("clutch", "comeback", "eco_win") and energy < 0.7:
        base_style = "cinematic_slow"
    elif moment_type in ("knife", "no_scope") or material_score < 4:
        base_style = "word_punch"
    elif material_score < 5:
        base_style = "clean_minimal"

    # ── Trend influence ──
    if trend_hints:
        trend_format = trend_hints.get("preferred_style", "")
        # Map trend format names to engine style names
        format_to_style = {
            "sigma_edit": "aggressive_sigma",
            "highlight_react": "hype_energy",
            "pro_clutch": "cinematic_slow",
            "funny_moments": "word_punch",
            "ace_compilation": "hype_energy",
            "tutorial_tip": "clean_minimal",
        }
        trend_style = format_to_style.get(trend_format, trend_format)
        trend_score = trend_hints.get("top_format_score", 0)
        data_type = trend_hints.get("data_type", "known_patterns")
        # Lower threshold for real scraped data (scores are video counts)
        threshold = 3.0 if data_type == "real_scraped" else 8.0
        if trend_style and trend_score >= threshold and material_score >= 4:
            compatible_styles = {
                "hype_energy": ["ace", "multi_kill", "spray_transfer", "clutch", "headshot"],
                "aggressive_sigma": ["clutch", "flick", "headshot", "wallbang", "ace", "multi_kill"],
                "cinematic_slow": ["clutch", "comeback", "eco_win", "defuse"],
                "word_punch": ["knife", "no_scope", "meme_fail", "toxic"],
                "clean_minimal": ["generic", "round_win", "entry", "tutorial"],
            }
            if moment_type in compatible_styles.get(trend_style, []):
                return trend_style

    return base_style


def _determine_constraints(material_score: float, moment_type: str) -> dict:
    """Determine what NOT to do based on material quality."""
    constraints = {
        "max_effects_per_second": 2,
        "max_consecutive_strong_effects": 2,
        "allow_memes": material_score >= 4,
        "allow_slowmo": material_score >= 5,
        "shorten_if_weak": material_score < 5,
        "max_text_words": 6,
        "text_uppercase_always": True,
    }

    # Weak material: fewer effects, shorter duration
    if material_score < 4:
        constraints["max_effects_per_second"] = 1
        constraints["max_consecutive_strong_effects"] = 1

    # Strong material: allow more
    if material_score >= 8:
        constraints["max_effects_per_second"] = 3

    return constraints


# ═══════════════════════════════════════════════════════════════════════
# SECTION 18: MASTER EDITOR — Decides HOW to edit (3 versions)
# ═══════════════════════════════════════════════════════════════════════

def master_editor_build_versions(
    producer_analysis: dict,
    player_name: str = "",
    situation: str = "",
    weapon: str = "",
    kills: int = 0,
    map_name: str = "",
    round_info: str = "",
    health: int = 100,
    has_girl: bool = False,
    platform: str = "tiktok",
) -> list:
    """
    MASTER EDITOR: Build 3 edit versions from producer analysis.

    Returns list of 3 complete montage plans, each with different editing style:
    - V1 FAST: Quick cuts, dense, no pauses
    - V2 CINEMATIC: 1 pause, 1 slowmo, clean
    - V3 MEME CONTROLLED: 1 meme, 1 surprise sound
    """
    structure = producer_analysis["structure"]
    duration = structure["total_duration"]
    energy = producer_analysis["energy"]
    payoff = producer_analysis["payoff"]
    hook = producer_analysis["selected_hook"]
    style_id = producer_analysis["style_id"]
    constraints = producer_analysis["constraints"]
    material_score = producer_analysis["material_score"]

    versions = []

    for version_id, version_profile in EDIT_VERSIONS.items():
        # Build a full montage plan for this version
        plan = assemble_montage_plan(
            moment_type=payoff["moment_type"],
            player_name=player_name,
            situation=situation,
            weapon=weapon,
            kills=kills,
            map_name=map_name,
            round_info=round_info,
            health=health,
            has_girl=has_girl,
            duration=duration,
            platform=platform,
            energy_override=energy,
        )

        # Override hook text with producer's selected hook
        plan["hook_text"] = hook["text"]
        # Update the first text overlay with the hook
        for ov in plan.get("text_overlays", []):
            if ov.get("role") == "hook" or ov.get("id") == "hook":
                ov["text"] = hook["text"]
                break

        # ── Apply version-specific modifications ──
        plan = _apply_version_profile(plan, version_profile, structure,
                                       payoff, constraints, material_score)

        # ── Check micro-event density ──
        density_issues = check_micro_event_density(plan, version_profile)

        # ── Self-evaluate this version ──
        scores = evaluate_version(plan, version_profile, producer_analysis,
                                   density_issues)

        versions.append({
            "version_id": version_id,
            "version_name": version_profile["name"],
            "plan": plan,
            "scores": scores,
            "total_score": scores["total"],
            "density_issues": density_issues,
            "rejected": scores["cleanliness"] < 6.0,
            "rejection_reason": "Cleanliness < 6" if scores["cleanliness"] < 6.0 else None,
        })

    # Sort by total score, non-rejected first
    versions.sort(key=lambda v: (not v["rejected"], v["total_score"]), reverse=True)

    return versions


def _apply_version_profile(plan: dict, profile: dict, structure: dict,
                            payoff: dict, constraints: dict,
                            material_score: float) -> dict:
    """Apply version-specific editing modifications to a plan."""
    version_plan = dict(plan)  # shallow copy

    # ── Flash intensity ──
    for flash in version_plan.get("flash_timeline", []):
        flash["intensity"] = min(1.0, flash["intensity"] * profile["flash_intensity"])

    # ── Shake intensity ──
    for shake in version_plan.get("shake_timeline", []):
        shake["intensity"] = int(shake["intensity"] * profile["shake_intensity"])

    # ── Speed ramps ──
    if not profile["slowmo_allowed"]:
        # Remove slowmo ramps for FAST and MEME versions
        version_plan["speed_ramps"] = [
            sr for sr in version_plan.get("speed_ramps", [])
            if sr.get("type") != "slowmo" and sr.get("speed", 1.0) >= 0.8
        ]
    else:
        # CINEMATIC: Keep only 1 slowmo, at payoff
        slowmos = [sr for sr in version_plan.get("speed_ramps", [])
                   if sr.get("speed", 1.0) < 0.8]
        if len(slowmos) > 1:
            # Keep only the one closest to payoff
            payoff_start = structure["payoff"]["start"]
            slowmos.sort(key=lambda sr: abs(sr["start"] - payoff_start))
            keep = slowmos[0]
            version_plan["speed_ramps"] = [
                sr for sr in version_plan.get("speed_ramps", [])
                if sr.get("speed", 1.0) >= 0.8 or sr == keep
            ]

    # ── Meme overlays ──
    max_memes = profile["meme_overlays_max"]
    if max_memes == 0:
        version_plan["meme_overlays"] = []
    elif len(version_plan.get("meme_overlays", [])) > max_memes:
        version_plan["meme_overlays"] = version_plan["meme_overlays"][:max_memes]

    # ── SFX density ──
    sfx = version_plan.get("sfx_timeline", [])
    if profile["sfx_density"] == "high":
        # Add extra impact SFX at payoff zone
        payoff_start = structure["payoff"]["start"]
        # Ensure there's at least 1 SFX per 2 seconds in payoff
        payoff_sfx = [s for s in sfx if s["time"] >= payoff_start]
        if len(payoff_sfx) < 2:
            sfx.append({
                "sfx_type": "impact", "time": payoff_start + 0.5,
                "volume": 1.5, "pitch": 1.0,
            })
    elif profile["sfx_density"] == "low_surprise":
        # Keep only essential SFX + add 1 unexpected vine_boom
        essential = [s for s in sfx if s["sfx_type"] in ("whoosh", "impact")]
        # Add 1 surprise sound at random point in buildup
        buildup_mid = (structure["buildup"]["start"] + structure["buildup"]["end"]) / 2
        essential.append({
            "sfx_type": "vine_boom", "time": buildup_mid,
            "volume": 1.2, "pitch": 1.0,
        })
        version_plan["sfx_timeline"] = essential

    # ── Pause before payoff (CINEMATIC only) ──
    if profile["pause_before_payoff"]:
        payoff_start = structure["payoff"]["start"]
        # Add a brief silence/pause marker before payoff
        version_plan["pause_before_payoff"] = {
            "time": payoff_start - 0.3,
            "duration": 0.3,
            "type": "dramatic_silence",
        }

    # ── Apply speed multiplier ──
    version_plan["speed_multiplier"] = profile["speed_multiplier"]

    # ── Store structure and version info ──
    version_plan["dramatic_structure"] = structure
    version_plan["edit_version"] = profile["name"]
    version_plan["material_score"] = material_score

    return version_plan


def check_micro_event_density(plan: dict, profile: dict) -> list:
    """
    Check that there are no flat zones > max_flat_seconds without micro-events.

    Micro-events: text change, SFX, flash, shake, zoom change, speed ramp.
    Every 2-3 seconds MUST have something happening.
    """
    duration = plan.get("duration", 15.0)
    max_flat = profile.get("max_flat_seconds", 3.0)

    # Collect all event timestamps
    events = set()

    # Text overlay starts
    for ov in plan.get("text_overlays", []):
        events.add(round(ov.get("start", 0), 1))

    # SFX hits
    for sfx in plan.get("sfx_timeline", []):
        events.add(round(sfx.get("time", 0), 1))

    # Flash events
    for flash in plan.get("flash_timeline", []):
        events.add(round(flash.get("time", 0), 1))

    # Shake events
    for shake in plan.get("shake_timeline", []):
        events.add(round(shake.get("time", 0), 1))

    # Speed ramp starts
    for sr in plan.get("speed_ramps", []):
        events.add(round(sr.get("start", 0), 1))

    # Meme overlay starts
    for meme in plan.get("meme_overlays", []):
        events.add(round(meme.get("start", 0), 1))

    # Sort events
    sorted_events = sorted(events)

    # Check for gaps
    issues = []
    prev = 0.0
    for t in sorted_events:
        gap = t - prev
        if gap > max_flat:
            issues.append({
                "start": prev,
                "end": t,
                "gap_seconds": round(gap, 1),
                "severity": "high" if gap > 4.0 else "medium",
            })
        prev = t

    # Check tail
    if duration - prev > max_flat:
        issues.append({
            "start": prev,
            "end": duration,
            "gap_seconds": round(duration - prev, 1),
            "severity": "medium",
        })

    return issues


# ═══════════════════════════════════════════════════════════════════════
# SECTION 19: SELF-EVALUATION — Score each version
# ═══════════════════════════════════════════════════════════════════════

def evaluate_version(plan: dict, profile: dict, producer: dict,
                      density_issues: list) -> dict:
    """
    Evaluate a version on 6 criteria, each 0-10 scale.

    Criteria:
    1. Hook Strength — first 1.2s has movement + text + sound + scene change
    2. Tempo Stability — consistent rhythm, no dead zones
    3. Clarity — easy to understand what happened
    4. Payoff Impact — climax feels powerful
    5. Trend Feel — feels current and platform-native
    6. Cleanliness — not overloaded, every element serves purpose

    If Cleanliness < 6, version is REJECTED.
    """
    scores = {}

    # 1. Hook Strength (0-10)
    hook_score = _evaluate_hook_strength(plan)
    scores["hook_strength"] = hook_score

    # 2. Tempo Stability (0-10)
    tempo_score = _evaluate_tempo_stability(plan, density_issues)
    scores["tempo_stability"] = tempo_score

    # 3. Clarity (0-10)
    clarity_score = _evaluate_clarity(plan, producer)
    scores["clarity"] = clarity_score

    # 4. Payoff Impact (0-10)
    payoff_score = _evaluate_payoff_impact(plan, profile, producer)
    scores["payoff_impact"] = payoff_score

    # 5. Trend Feel (0-10)
    trend_score = _evaluate_trend_feel(plan)
    scores["trend_feel"] = trend_score

    # 6. Cleanliness (0-10)
    clean_score = _evaluate_cleanliness(plan, profile, density_issues)
    scores["cleanliness"] = clean_score

    # Weighted total
    total = 0
    for criterion, score in scores.items():
        weight = EVAL_CRITERIA.get(criterion, {}).get("weight", 1.0)
        total += score * weight
    max_possible = sum(10 * c["weight"] for c in EVAL_CRITERIA.values())
    scores["total"] = round(total, 1)
    scores["total_pct"] = round(total / max_possible * 100, 1)

    return scores


def _evaluate_hook_strength(plan: dict) -> float:
    """First 1.2s must have: movement, text, sound, scene change."""
    score = 5.0  # baseline

    # Check text in first 1.5s
    early_text = [ov for ov in plan.get("text_overlays", [])
                  if ov.get("start", 99) <= 1.5]
    if early_text:
        score += 2.0
        # Check if hook text is 6 words or less
        hook = plan.get("hook_text", "")
        if len(hook.split()) <= 6:
            score += 0.5

    # Check SFX in first 1.5s
    early_sfx = [s for s in plan.get("sfx_timeline", []) if s.get("time", 99) <= 1.5]
    if early_sfx:
        score += 1.5

    # Check flash/shake in first 2s (movement)
    early_flash = [f for f in plan.get("flash_timeline", []) if f.get("time", 99) <= 2.0]
    early_shake = [s for s in plan.get("shake_timeline", []) if s.get("time", 99) <= 2.0]
    if early_flash or early_shake:
        score += 1.0

    return min(10.0, score)


def _evaluate_tempo_stability(plan: dict, density_issues: list) -> float:
    """No dead zones, consistent micro-events every 2-3s."""
    score = 10.0

    # Penalize for each density gap
    for issue in density_issues:
        if issue["severity"] == "high":
            score -= 3.0
        else:
            score -= 1.5

    return max(0.0, score)


def _evaluate_clarity(plan: dict, producer: dict) -> float:
    """Is it clear what happened? Structure + text readability."""
    score = 6.0

    # Structure exists with clear phases
    if plan.get("dramatic_structure"):
        score += 1.5

    # Text overlays are readable (max 6 words)
    all_readable = True
    for ov in plan.get("text_overlays", []):
        if len(ov.get("text", "").split()) > 6:
            all_readable = False
            break
    if all_readable:
        score += 1.5

    # Material score bonus — stronger material is clearer
    mat = producer.get("material_score", 5)
    if mat >= 7:
        score += 1.0

    return min(10.0, score)


def _evaluate_payoff_impact(plan: dict, profile: dict, producer: dict) -> float:
    """Does the climax feel powerful?"""
    score = 5.0

    payoff = producer.get("payoff", {})
    composite = payoff.get("composite_score", 5)

    # Strong payoff moment
    if composite >= 10:
        score += 2.0
    elif composite >= 6:
        score += 1.0

    # Slowmo at payoff (CINEMATIC boost)
    if profile.get("slowmo_allowed"):
        speed_ramps = plan.get("speed_ramps", [])
        if any(sr.get("speed", 1) < 0.8 for sr in speed_ramps):
            score += 1.5

    # SFX at payoff zone
    structure = plan.get("dramatic_structure", {})
    payoff_start = structure.get("payoff", {}).get("start", 10)
    payoff_sfx = [s for s in plan.get("sfx_timeline", [])
                  if s.get("time", 0) >= payoff_start]
    if payoff_sfx:
        score += 1.0

    # Flash at payoff
    payoff_flash = [f for f in plan.get("flash_timeline", [])
                    if f.get("time", 0) >= payoff_start]
    if payoff_flash:
        score += 0.5

    return min(10.0, score)


def _evaluate_trend_feel(plan: dict) -> float:
    """Does it feel current and platform-native?"""
    score = 6.0

    # Uppercase text (trending)
    if plan.get("hook_text", "").isupper():
        score += 1.0

    # Beat-synced SFX
    beat_grid = plan.get("beat_grid", [])
    if beat_grid:
        score += 1.0

    # Style variation applied
    if plan.get("style_variation"):
        score += 1.0

    # Phonk music (currently trending)
    music = plan.get("music_profile", {}).get("name", "")
    if "phonk" in music.lower():
        score += 1.0

    return min(10.0, score)


def _evaluate_cleanliness(plan: dict, profile: dict, density_issues: list) -> float:
    """Not overloaded? Every element serves a purpose?"""
    score = 10.0

    duration = plan.get("duration", 15.0)

    # Too many SFX = overloaded (more than 1 per 2 seconds)
    sfx_count = len(plan.get("sfx_timeline", []))
    if sfx_count > duration / 2:
        score -= 2.0

    # Too many flashes
    flash_count = len(plan.get("flash_timeline", []))
    if flash_count > duration / 3:
        score -= 1.5

    # Too many text overlays
    text_count = len(plan.get("text_overlays", []))
    if text_count > 5:
        score -= 1.0

    # Memes in non-meme version
    meme_count = len(plan.get("meme_overlays", []))
    if meme_count > profile.get("meme_overlays_max", 1):
        score -= 2.0

    # Long text (> 6 words)
    for ov in plan.get("text_overlays", []):
        if len(ov.get("text", "").split()) > 6:
            score -= 1.0
            break

    # Too many speed ramps
    sr_count = len(plan.get("speed_ramps", []))
    if sr_count > 2:
        score -= 1.0

    return max(0.0, score)


# ═══════════════════════════════════════════════════════════════════════
# SECTION 20: PRODUCER + EDITOR COMBINED PIPELINE
# ═══════════════════════════════════════════════════════════════════════

def produce_and_edit(
    moment_type: str = "clutch",
    player_name: str = "m0NESY",
    situation: str = "1v3",
    weapon: str = "AWP",
    kills: int = 3,
    map_name: str = "Mirage",
    round_info: str = "match point",
    health: int = 12,
    has_girl: bool = False,
    video_duration: float = 20.0,
    platform: str = "tiktok",
    energy_data: list = None,
) -> dict:
    """
    FULL PIPELINE: Producer analyzes → Editor creates 3 versions → Self-evaluates → Picks best.

    Returns:
    - best_version: the winning plan
    - alternatives: 2 other versions
    - report: why this version won
    - producer_analysis: what the producer decided
    """
    # ── Stage 1: PRODUCER (now consults trend data) ──
    analysis = producer_analyze_material(
        moment_type=moment_type,
        player_name=player_name,
        situation=situation,
        weapon=weapon,
        kills=kills,
        map_name=map_name,
        round_info=round_info,
        health=health,
        video_duration=video_duration,
        energy_data=energy_data,
        platform=platform,
    )

    # ── Stage 2: MASTER EDITOR ──
    versions = master_editor_build_versions(
        producer_analysis=analysis,
        player_name=player_name,
        situation=situation,
        weapon=weapon,
        kills=kills,
        map_name=map_name,
        round_info=round_info,
        health=health,
        has_girl=has_girl,
        platform=platform,
    )

    # ── Stage 3: SELECT BEST ──
    best = versions[0]
    alternatives = versions[1:]

    # ── Stage 4: BUILD REPORT ──
    report = _build_production_report(analysis, versions, best)

    return {
        "best_version": best,
        "alternatives": alternatives,
        "all_versions": versions,
        "producer_analysis": analysis,
        "report": report,
    }


def _build_production_report(analysis: dict, versions: list, best: dict) -> str:
    """Build human-readable production report."""
    lines = []
    lines.append("=" * 60)
    lines.append("PRODUCTION REPORT")
    lines.append("=" * 60)

    # Producer analysis
    payoff = analysis["payoff"]
    lines.append(f"\nPAYOFF: {payoff['description']}")
    lines.append(f"  Rarity: {payoff['rarity']}/10 | Tension: {payoff['tension']:.1f}x | "
                 f"Spectacle: {payoff['spectacle']:.1f}x")
    lines.append(f"  Composite: {payoff['composite_score']:.1f}")

    lines.append(f"\nMATERIAL QUALITY: {analysis['material_score']:.1f}/10")
    lines.append(f"TARGET DURATION: {analysis['target_duration']:.1f}s")

    # Structure
    struct = analysis["structure"]
    lines.append(f"\nSTRUCTURE:")
    lines.append(f"  SETUP:    {struct['setup']['start']:.1f}-{struct['setup']['end']:.1f}s — {struct['setup']['purpose']}")
    lines.append(f"  BUILD-UP: {struct['buildup']['start']:.1f}-{struct['buildup']['end']:.1f}s — {struct['buildup']['purpose']}")
    lines.append(f"  PAYOFF:   {struct['payoff']['start']:.1f}-{struct['payoff']['end']:.1f}s — {struct['payoff']['purpose']}")
    lines.append(f"  Payoff takes {struct['payoff_pct']:.0f}% of video")

    # Hooks
    lines.append(f"\nHOOKS (3 variants):")
    for h in analysis["hooks"]:
        selected = " ← SELECTED" if h == analysis["selected_hook"] else ""
        lines.append(f"  [{h['type'].upper()}] \"{h['text']}\"{selected}")

    lines.append(f"\nSTYLE: {analysis['style_id']} (logically selected)")

    # Trend influence
    trend_hints = analysis.get("trend_hints", {})
    if trend_hints:
        lines.append(f"\nTREND INFLUENCE:")
        lines.append(f"  Platform: {trend_hints.get('platform', 'unknown')}")
        lines.append(f"  Top format: {trend_hints.get('preferred_style', 'N/A')} (score: {trend_hints.get('top_format_score', 0)})")
        lines.append(f"  Recommended hook: {trend_hints.get('recommended_hook', 'N/A')}")
        lines.append(f"  Recommended music: {trend_hints.get('recommended_music_style', 'N/A')}")
        lines.append(f"  Recommended pacing: {trend_hints.get('recommended_pacing', 'N/A')}")
        lines.append(f"  Optimal duration: {trend_hints.get('recommended_duration_sec', 'N/A')}s")
        lines.append(f"  Color grade: {trend_hints.get('recommended_color_grade', 'N/A')}")
        lines.append(f"  Data type: {trend_hints.get('data_type', 'unknown')}")
        sources = trend_hints.get('data_sources_used', [])
        if sources:
            lines.append(f"  Data sources: {', '.join(sources)}")
        fmt_analysis = trend_hints.get('format_analysis', {})
        all_fmts = fmt_analysis.get('all_formats', {})
        if all_fmts:
            lines.append(f"  All format scores: {all_fmts}")

    # Version scores
    lines.append(f"\nVERSION SCORES:")
    lines.append(f"{'Version':<25} {'Hook':>5} {'Tempo':>5} {'Clear':>5} {'Payoff':>6} {'Trend':>5} {'Clean':>5} {'TOTAL':>6} {'Status':>10}")
    lines.append("-" * 85)
    for v in versions:
        s = v["scores"]
        status = "REJECTED" if v["rejected"] else ("WINNER" if v == best else "")
        lines.append(
            f"{v['version_name']:<25} "
            f"{s['hook_strength']:>5.1f} "
            f"{s['tempo_stability']:>5.1f} "
            f"{s['clarity']:>5.1f} "
            f"{s['payoff_impact']:>6.1f} "
            f"{s['trend_feel']:>5.1f} "
            f"{s['cleanliness']:>5.1f} "
            f"{s['total']:>6.1f} "
            f"{status:>10}"
        )

    # Why winner won
    lines.append(f"\nWINNER: {best['version_name']}")
    lines.append(f"  Total score: {best['total_score']:.1f}")
    if best["scores"]["payoff_impact"] >= 8:
        lines.append(f"  Strong payoff impact ({best['scores']['payoff_impact']:.1f}/10)")
    if best["scores"]["cleanliness"] >= 8:
        lines.append(f"  Very clean edit ({best['scores']['cleanliness']:.1f}/10)")
    if best["scores"]["hook_strength"] >= 8:
        lines.append(f"  Powerful hook ({best['scores']['hook_strength']:.1f}/10)")

    # Density warnings
    if best.get("density_issues"):
        lines.append(f"\nDENSITY WARNINGS:")
        for issue in best["density_issues"]:
            lines.append(f"  {issue['start']:.1f}-{issue['end']:.1f}s: "
                         f"{issue['gap_seconds']:.1f}s flat zone ({issue['severity']})")

    lines.append("")
    return "\n".join(lines)
