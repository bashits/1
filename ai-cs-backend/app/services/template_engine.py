"""
Template Engine Service v2.0 — Intelligent Trending Content System

Manages clip format templates with:
1. Trending format configs (TikTok/Reels/Shorts optimized)
2. Dynamic text styles (karaoke, word-highlight, shake, glow, size pulse)
3. AI Girl insertion logic (PiP, fullscreen, split-screen, Instagram story)
4. Moment-to-template smart matching (auto-picks best format per moment type)
5. Self-learning analytics (tracks what works, adjusts weights)
6. Hook/CTA generation tuned for engagement on foreign markets (EN)
7. Meme overlay placement logic
8. Music-moment matching
"""
import json
import random
import time
from datetime import datetime


# ═══════════════════════════════════════════════════════════════════════
# SECTION 1: FORMAT CONFIGS — Every clip style the system can produce
# ═══════════════════════════════════════════════════════════════════════

FORMAT_CONFIGS = {
    # ── CORE FORMATS ──
    "clean_highlight": {
        "id": "clean_highlight",
        "name": "Clean Highlight",
        "description": "Pure gameplay, no overlays. Lets the play speak for itself.",
        "category": "minimal",
        "platforms": ["youtube_shorts", "tiktok", "instagram_reels"],
        "overlay": False,
        "subtitles": False,
        "ai_girl": False,
        "zoom_effects": False,
        "music": "none",
        "hook_style": "none",
        "color_grade": "cinematic",
        "target_duration": (15, 30),
        "trend_score": 0.6,
    },
    "highlight_reaction": {
        "id": "highlight_reaction",
        "name": "Highlight + Reaction",
        "description": "Gameplay with face-cam reaction overlay. Classic streamer clip format.",
        "category": "reaction",
        "platforms": ["tiktok", "youtube_shorts"],
        "overlay": True,
        "subtitles": False,
        "ai_girl": False,
        "face_cam": True,
        "face_cam_position": "top-right",
        "face_cam_size": 0.2,
        "zoom_effects": True,
        "music": "subtle",
        "hook_style": "reaction_preview",
        "color_grade": "vibrant",
        "target_duration": (20, 45),
        "trend_score": 0.75,
    },
    "highlight_subtitles": {
        "id": "highlight_subtitles",
        "name": "Dynamic Subtitles",
        "description": "Gameplay with bold animated subtitles. Word-by-word highlight style.",
        "category": "subtitles",
        "platforms": ["tiktok", "instagram_reels", "youtube_shorts"],
        "overlay": False,
        "subtitles": True,
        "subtitle_style": "karaoke_highlight",
        "subtitle_size": "large",
        "subtitle_color_scheme": "white_yellow_accent",
        "ai_girl": False,
        "zoom_effects": True,
        "music": "background",
        "hook_style": "text_question",
        "color_grade": "cinematic",
        "target_duration": (15, 35),
        "trend_score": 0.85,
    },

    # ── AI GIRL FORMATS ──
    "girl_reaction_pip": {
        "id": "girl_reaction_pip",
        "name": "Girl Reaction PiP",
        "description": "AI girl reacts in picture-in-picture while gameplay runs. Classic reaction format.",
        "category": "ai_girl",
        "platforms": ["tiktok", "instagram_reels", "youtube_shorts"],
        "overlay": True,
        "subtitles": True,
        "subtitle_style": "bold_dynamic",
        "ai_girl": True,
        "ai_girl_position": "pip_bottom_right",
        "ai_girl_size": 0.28,
        "ai_girl_voice": "energetic",
        "ai_girl_appears_at": "peak",
        "zoom_effects": True,
        "music": "background",
        "hook_style": "ai_intro",
        "color_grade": "vibrant",
        "target_duration": (20, 45),
        "trend_score": 0.9,
    },
    "girl_split_screen": {
        "id": "girl_split_screen",
        "name": "Girl Split Screen",
        "description": "50/50 split: gameplay top, AI girl bottom. Instagram story native format.",
        "category": "ai_girl",
        "platforms": ["instagram_reels", "instagram_stories", "tiktok"],
        "overlay": True,
        "subtitles": True,
        "subtitle_style": "minimal_white",
        "ai_girl": True,
        "ai_girl_position": "split_bottom",
        "ai_girl_size": 0.5,
        "ai_girl_voice": "conversational",
        "ai_girl_appears_at": "start",
        "zoom_effects": False,
        "music": "lofi_gaming",
        "hook_style": "girl_question",
        "color_grade": "warm",
        "target_duration": (15, 30),
        "trend_score": 0.88,
    },
    "girl_fullscreen_intro": {
        "id": "girl_fullscreen_intro",
        "name": "Girl Intro + Gameplay",
        "description": "AI girl introduces the clip fullscreen, then gameplay takes over. Maximum engagement.",
        "category": "ai_girl",
        "platforms": ["tiktok", "instagram_reels"],
        "overlay": True,
        "subtitles": True,
        "subtitle_style": "karaoke_highlight",
        "ai_girl": True,
        "ai_girl_position": "fullscreen_then_pip",
        "ai_girl_size": 1.0,
        "ai_girl_voice": "hype",
        "ai_girl_appears_at": "intro",
        "zoom_effects": True,
        "music": "hype_buildup",
        "hook_style": "girl_hype_intro",
        "color_grade": "vibrant",
        "target_duration": (20, 45),
        "trend_score": 0.92,
    },
    "girl_instagram_story": {
        "id": "girl_instagram_story",
        "name": "Instagram Story Style",
        "description": "Designed for Instagram stories. Girl appears with stickers, polls, text overlays.",
        "category": "ai_girl",
        "platforms": ["instagram_stories", "instagram_reels"],
        "overlay": True,
        "subtitles": True,
        "subtitle_style": "instagram_native",
        "ai_girl": True,
        "ai_girl_position": "bottom_third",
        "ai_girl_size": 0.35,
        "ai_girl_voice": "casual",
        "ai_girl_appears_at": "react",
        "instagram_elements": True,
        "poll_overlay": True,
        "sticker_overlay": True,
        "zoom_effects": False,
        "music": "trending_audio",
        "hook_style": "poll_question",
        "color_grade": "warm",
        "target_duration": (15, 15),
        "trend_score": 0.87,
    },

    # ── MEME / VIRAL FORMATS ──
    "meme_format": {
        "id": "meme_format",
        "name": "Meme Edit",
        "description": "Fast meme edits with vine boom, zoom, and meme sound stacking.",
        "category": "meme",
        "platforms": ["tiktok", "youtube_shorts"],
        "overlay": True,
        "subtitles": True,
        "subtitle_style": "meme_impact",
        "ai_girl": False,
        "meme_sounds": True,
        "meme_overlay_images": True,
        "zoom_effects": True,
        "zoom_intensity": "extreme",
        "screen_shake": True,
        "music": "meme_track",
        "hook_style": "meme_text",
        "color_grade": "none",
        "target_duration": (8, 20),
        "trend_score": 0.82,
    },
    "brainrot_edit": {
        "id": "brainrot_edit",
        "name": "Brainrot Edit",
        "description": "Maximum sensory overload: secondary gameplay bottom, main top, rapid text, SFX stack.",
        "category": "meme",
        "platforms": ["tiktok"],
        "overlay": True,
        "subtitles": True,
        "subtitle_style": "rapid_flash",
        "ai_girl": False,
        "split_screen_filler": True,
        "filler_type": "gameplay_secondary",
        "meme_sounds": True,
        "zoom_effects": True,
        "zoom_intensity": "extreme",
        "screen_shake": True,
        "music": "phonk_aggressive",
        "hook_style": "shock_text",
        "color_grade": "oversaturated",
        "target_duration": (10, 30),
        "trend_score": 0.78,
    },
    "sigma_edit": {
        "id": "sigma_edit",
        "name": "Sigma Edit",
        "description": "Dark cinematic edit with phonk music. Slow-mo + text.",
        "category": "meme",
        "platforms": ["tiktok", "youtube_shorts", "instagram_reels"],
        "overlay": True,
        "subtitles": True,
        "subtitle_style": "cinematic_caps",
        "ai_girl": False,
        "slow_motion": True,
        "slow_mo_factor": 0.5,
        "zoom_effects": True,
        "dark_vignette": True,
        "music": "phonk_dark",
        "hook_style": "sigma_text",
        "color_grade": "dark",
        "target_duration": (12, 25),
        "trend_score": 0.84,
    },

    # ── DRAMATIC / CINEMATIC FORMATS ──
    "dramatic_clutch": {
        "id": "dramatic_clutch",
        "name": "Dramatic Clutch",
        "description": "Cinematic clutch with slow-mo, tension music, countdown overlay.",
        "category": "dramatic",
        "platforms": ["youtube_shorts", "tiktok", "instagram_reels"],
        "overlay": True,
        "subtitles": True,
        "subtitle_style": "cinematic_caps",
        "ai_girl": False,
        "slow_motion": True,
        "slow_mo_factor": 0.5,
        "dramatic_music": True,
        "text_overlay": True,
        "zoom_effects": True,
        "music": "cinematic_dark",
        "hook_style": "countdown",
        "color_grade": "cinematic",
        "target_duration": (20, 45),
        "trend_score": 0.8,
    },
    "fragmovie_edit": {
        "id": "fragmovie_edit",
        "name": "Fragmovie Edit",
        "description": "Beat-synced kills, fast cuts, cinematic color grade. Classic frag movie style.",
        "category": "dramatic",
        "platforms": ["youtube_shorts", "tiktok"],
        "overlay": False,
        "subtitles": False,
        "ai_girl": False,
        "sync_music": True,
        "fast_cuts": True,
        "color_grade": "cinematic",
        "zoom_effects": True,
        "music": "synced_beats",
        "hook_style": "beat_drop",
        "target_duration": (20, 60),
        "trend_score": 0.72,
    },

    # ── ENGAGEMENT FORMATS ──
    "provocative": {
        "id": "provocative",
        "name": "Provocative Hook",
        "description": "Controversial question hook that forces comments.",
        "category": "engagement",
        "platforms": ["tiktok", "instagram_reels", "youtube_shorts"],
        "overlay": True,
        "subtitles": True,
        "subtitle_style": "bold_dynamic",
        "ai_girl": False,
        "provocative_hook": True,
        "bold_text": True,
        "zoom_effects": True,
        "music": "hype",
        "hook_style": "provocative_question",
        "color_grade": "vibrant",
        "target_duration": (12, 25),
        "trend_score": 0.86,
    },
    "fail_format": {
        "id": "fail_format",
        "name": "Fail / Funny",
        "description": "Comedy fail with replay, sad trombone, meme sounds.",
        "category": "comedy",
        "platforms": ["tiktok", "youtube_shorts", "instagram_reels"],
        "overlay": True,
        "subtitles": True,
        "subtitle_style": "meme_impact",
        "ai_girl": False,
        "fail_sounds": True,
        "replay": True,
        "replay_speed": 0.3,
        "zoom_effects": True,
        "music": "comedy",
        "hook_style": "expectation_subversion",
        "color_grade": "none",
        "target_duration": (8, 20),
        "trend_score": 0.79,
    },
    "rank_comparison": {
        "id": "rank_comparison",
        "name": "Rank Comparison",
        "description": "Split comparison format. Forces comments about rank.",
        "category": "engagement",
        "platforms": ["tiktok", "youtube_shorts"],
        "overlay": True,
        "subtitles": True,
        "subtitle_style": "comparison_split",
        "ai_girl": False,
        "split_comparison": True,
        "zoom_effects": True,
        "music": "hype",
        "hook_style": "rank_debate",
        "color_grade": "vibrant",
        "target_duration": (15, 30),
        "trend_score": 0.81,
    },
    "girl_commentary_full": {
        "id": "girl_commentary_full",
        "name": "Girl Full Commentary",
        "description": "AI girl narrates the entire clip — intro, play-by-play, reaction, outro.",
        "category": "ai_girl",
        "platforms": ["tiktok", "instagram_reels", "youtube_shorts"],
        "overlay": True,
        "subtitles": True,
        "subtitle_style": "karaoke_highlight",
        "ai_girl": True,
        "ai_girl_position": "dynamic",
        "ai_girl_size": 0.3,
        "ai_girl_voice": "commentary",
        "ai_girl_appears_at": "throughout",
        "zoom_effects": True,
        "music": "lofi_gaming",
        "hook_style": "girl_hype_intro",
        "color_grade": "warm",
        "target_duration": (20, 45),
        "trend_score": 0.91,
    },
}


# ═══════════════════════════════════════════════════════════════════════
# SECTION 2: DYNAMIC TEXT STYLES — How text looks on screen
# ═══════════════════════════════════════════════════════════════════════

TEXT_STYLES = {
    "karaoke_highlight": {
        "name": "Karaoke Highlight",
        "description": "Words highlight one-by-one as spoken. TikTok native feel.",
        "font_size": 58,
        "font_color": "white",
        "highlight_color": "#FFD700",
        "background": "none",
        "position": "center_bottom",
        "animation": "word_by_word",
        "border_width": 3,
        "border_color": "black",
        "shadow": True,
        "max_words_visible": 5,
        "trending": True,
    },
    "bold_dynamic": {
        "name": "Bold Dynamic",
        "description": "Large bold text with key words in color. Standard viral format.",
        "font_size": 62,
        "font_color": "white",
        "highlight_color": "#FF4444",
        "background": "rgba(0,0,0,0.5)",
        "position": "center",
        "animation": "scale_in",
        "border_width": 4,
        "border_color": "black",
        "shadow": True,
        "max_words_visible": 8,
        "trending": True,
    },
    "minimal_white": {
        "name": "Minimal White",
        "description": "Clean minimal white text. Instagram aesthetic.",
        "font_size": 44,
        "font_color": "white",
        "highlight_color": "white",
        "background": "none",
        "position": "center_bottom",
        "animation": "fade_in",
        "border_width": 2,
        "border_color": "rgba(0,0,0,0.5)",
        "shadow": True,
        "max_words_visible": 6,
        "trending": False,
    },
    "meme_impact": {
        "name": "Meme Impact",
        "description": "Impact font, all caps, white with black outline. Classic meme.",
        "font_size": 72,
        "font_color": "white",
        "highlight_color": "white",
        "background": "none",
        "position": "top_and_bottom",
        "animation": "slam_in",
        "border_width": 5,
        "border_color": "black",
        "shadow": False,
        "max_words_visible": 4,
        "trending": False,
    },
    "cinematic_caps": {
        "name": "Cinematic Caps",
        "description": "All-caps cinematic text with letter spacing. Dramatic feel.",
        "font_size": 52,
        "font_color": "white",
        "highlight_color": "#FFD700",
        "background": "none",
        "position": "center",
        "animation": "typewriter",
        "border_width": 3,
        "border_color": "black",
        "shadow": True,
        "letter_spacing": 4,
        "max_words_visible": 5,
        "trending": True,
    },
    "rapid_flash": {
        "name": "Rapid Flash",
        "description": "Words flash on screen one at a time. Maximum attention grab.",
        "font_size": 80,
        "font_color": "white",
        "highlight_color": "#FF0000",
        "background": "black",
        "position": "center",
        "animation": "flash_single_word",
        "border_width": 0,
        "border_color": "none",
        "shadow": False,
        "max_words_visible": 1,
        "trending": True,
    },
    "instagram_native": {
        "name": "Instagram Native",
        "description": "Looks like native Instagram story text. Rounded background pill.",
        "font_size": 38,
        "font_color": "white",
        "highlight_color": "white",
        "background": "rgba(0,0,0,0.6)",
        "background_shape": "rounded_pill",
        "position": "center_top",
        "animation": "slide_up",
        "border_width": 0,
        "border_color": "none",
        "shadow": False,
        "max_words_visible": 8,
        "trending": True,
    },
    "comparison_split": {
        "name": "Comparison Split",
        "description": "Left vs Right text comparison.",
        "font_size": 56,
        "font_color": "white",
        "highlight_color": "#00FF00",
        "secondary_color": "#FF0000",
        "background": "rgba(0,0,0,0.4)",
        "position": "split_labels",
        "animation": "slide_in_sides",
        "border_width": 3,
        "border_color": "black",
        "shadow": True,
        "max_words_visible": 4,
        "trending": True,
    },
}


# ═══════════════════════════════════════════════════════════════════════
# SECTION 3: HOOK TEMPLATES — First 1-3 seconds that grab attention
# ═══════════════════════════════════════════════════════════════════════

HOOK_TEMPLATES = {
    "none": [],
    "reaction_preview": [
        "WAIT FOR HIS REACTION...",
        "Watch his face when this happens",
        "He did NOT expect THIS",
        "POV: his reaction to this play",
    ],
    "text_question": [
        "Can he clutch this?!",
        "Could YOU hit this shot?",
        "Play of the year?!",
        "Is this the best play in CS2?",
        "How is this even possible?!",
    ],
    "ai_intro": [
        "OMG watch this play!",
        "You won't believe what happens next",
        "This is why he's the BEST",
        "I literally screamed watching this",
    ],
    "girl_question": [
        "Okay but HOW did he do this?!",
        "Can someone explain this to me?!",
        "I've watched this 50 times and I STILL can't believe it",
        "This might be the craziest thing I've ever seen",
    ],
    "girl_hype_intro": [
        "OKAY CHAT you NEED to see this",
        "I found the most INSANE clip today",
        "Stop scrolling right now. Watch this.",
        "If you play CS2 you're gonna LOSE IT",
    ],
    "poll_question": [
        "SKILL or LUCK? Vote below!",
        "Could you do this? Be honest",
        "Rate this play 1-10 in comments",
        "Is this the play of the week? Yes or no",
    ],
    "meme_text": [
        "bro actually did this",
        "average CS2 player",
        "he's DIFFERENT different",
        "my teammates vs the enemy team",
        "this has to be scripted",
    ],
    "countdown": [
        "1v5. 10 seconds. No kit.",
        "4HP. 1 bullet. All or nothing.",
        "Last alive. Bomb planted. 15 seconds.",
        "Down 14-15. Match point. This happens.",
    ],
    "provocative_question": [
        "This should be ILLEGAL in CS2",
        "Is this CHEATS or SKILL?",
        "NOBODY should play this well...",
        "This is why people are quitting CS2",
        "Valve needs to patch this immediately",
    ],
    "beat_drop": [
        "Wait for the drop...",
        "Turn up the volume",
        "Headphones on for this one",
    ],
    "expectation_subversion": [
        "POV: you think you're winning...",
        "Everything was going SO well...",
        "He almost got the ACE but...",
        "Average CS2 moment gone wrong",
    ],
    "shock_text": [
        "WHAT DID I JUST WATCH",
        "THIS CAN'T BE REAL",
        "I need to lay down after this one",
        "BRO...",
    ],
    "sigma_text": [
        "He built different.",
        "Not a single wasted bullet.",
        "They don't know...",
        "Cold. Calculated. Clinical.",
    ],
    "rank_debate": [
        "Silver or Global? You decide.",
        "What rank does this look like?",
        "Guess the rank challenge",
        "Chat said this is Silver",
    ],
}


# ═══════════════════════════════════════════════════════════════════════
# SECTION 4: CTA TEMPLATES — End-of-clip engagement drivers
# ═══════════════════════════════════════════════════════════════════════

CTA_TEMPLATES = {
    "follow": [
        "Follow for insane CS2 plays!",
        "Follow for daily clips",
        "More clips like this every day — follow!",
        "Follow and turn on notifications!",
    ],
    "engage": [
        "Drop a like if this was insane!",
        "Comment your rank below!",
        "Tag someone who plays like this",
        "Share this with your duo partner",
    ],
    "stream": [
        "He's LIVE right now — link in bio",
        "He's streaming right now, don't miss it!",
        "Catch more plays LIVE — link in bio",
    ],
    "subscribe": [
        "Subscribe for daily CS2 clips!",
        "Watch the full stream NOW",
        "More on the channel — subscribe!",
    ],
    "save": [
        "Save this for later",
        "Bookmark this clip",
        "Save and share this one",
    ],
}


# ═══════════════════════════════════════════════════════════════════════
# SECTION 5: MOMENT-TO-TEMPLATE MATCHING — Smart auto-selection
# ═══════════════════════════════════════════════════════════════════════

MOMENT_TEMPLATE_AFFINITY = {
    "clutch": {
        "best": ["dramatic_clutch", "girl_reaction_pip", "girl_fullscreen_intro"],
        "good": ["highlight_subtitles", "provocative", "sigma_edit"],
        "avoid": ["fail_format", "brainrot_edit"],
    },
    "ace": {
        "best": ["fragmovie_edit", "girl_reaction_pip", "dramatic_clutch"],
        "good": ["highlight_subtitles", "sigma_edit", "girl_commentary_full"],
        "avoid": ["fail_format"],
    },
    "multi_kill": {
        "best": ["meme_format", "girl_reaction_pip", "highlight_subtitles"],
        "good": ["sigma_edit", "brainrot_edit", "provocative"],
        "avoid": ["fail_format"],
    },
    "headshot_sequence": {
        "best": ["fragmovie_edit", "sigma_edit", "highlight_subtitles"],
        "good": ["girl_reaction_pip", "meme_format"],
        "avoid": ["fail_format"],
    },
    "funny": {
        "best": ["fail_format", "meme_format", "brainrot_edit"],
        "good": ["girl_reaction_pip", "girl_split_screen"],
        "avoid": ["dramatic_clutch", "fragmovie_edit"],
    },
    "fail_moment": {
        "best": ["fail_format", "meme_format"],
        "good": ["brainrot_edit", "girl_reaction_pip"],
        "avoid": ["dramatic_clutch", "sigma_edit", "fragmovie_edit"],
    },
    "toxic_play": {
        "best": ["meme_format", "provocative", "girl_reaction_pip"],
        "good": ["brainrot_edit", "highlight_subtitles"],
        "avoid": ["clean_highlight"],
    },
    "knife_kill": {
        "best": ["meme_format", "sigma_edit", "girl_reaction_pip"],
        "good": ["provocative", "highlight_subtitles"],
        "avoid": ["fail_format"],
    },
    "comeback": {
        "best": ["dramatic_clutch", "girl_commentary_full", "girl_fullscreen_intro"],
        "good": ["highlight_subtitles", "provocative"],
        "avoid": ["fail_format", "brainrot_edit"],
    },
    "insane_play": {
        "best": ["girl_reaction_pip", "highlight_subtitles", "provocative"],
        "good": ["sigma_edit", "meme_format", "girl_fullscreen_intro"],
        "avoid": ["fail_format"],
    },
    "default": {
        "best": ["highlight_subtitles", "girl_reaction_pip"],
        "good": ["meme_format", "provocative", "girl_split_screen"],
        "avoid": [],
    },
}


# ═══════════════════════════════════════════════════════════════════════
# SECTION 6: GIRL INSERTION LOGIC — How/where AI girl appears
# ═══════════════════════════════════════════════════════════════════════

GIRL_INSERTION_CONFIGS = {
    "pip_bottom_right": {
        "name": "PiP Bottom Right",
        "description": "Classic picture-in-picture in corner. Girl reacts while gameplay runs.",
        "layout": "overlay",
        "girl_x": "W-w-20",
        "girl_y": "H-h-20",
        "girl_scale": 0.28,
        "girl_shape": "circle",
        "border": True,
        "border_color": "#FF69B4",
        "border_width": 3,
        "appear_animation": "scale_bounce",
        "best_for": ["reaction", "commentary"],
    },
    "pip_top_right": {
        "name": "PiP Top Right",
        "description": "Top-right corner PiP. Good when subtitles are at bottom.",
        "layout": "overlay",
        "girl_x": "W-w-20",
        "girl_y": "20",
        "girl_scale": 0.25,
        "girl_shape": "circle",
        "border": True,
        "border_color": "#FF69B4",
        "border_width": 3,
        "appear_animation": "slide_in_right",
        "best_for": ["commentary"],
    },
    "split_bottom": {
        "name": "Split Screen Bottom",
        "description": "Gameplay on top, girl on bottom 50/50. Instagram native.",
        "layout": "split",
        "split_ratio": 0.5,
        "girl_area": "bottom",
        "appear_animation": "none",
        "best_for": ["instagram_stories", "commentary"],
    },
    "fullscreen_then_pip": {
        "name": "Fullscreen Intro then PiP",
        "description": "Girl starts fullscreen for intro, shrinks to PiP for gameplay, expands for reaction.",
        "layout": "dynamic",
        "phases": {
            "intro": {"size": 1.0, "position": "fullscreen"},
            "gameplay": {"size": 0.25, "position": "pip_top_right"},
            "reaction": {"size": 0.4, "position": "pip_bottom_right"},
            "outro": {"size": 1.0, "position": "fullscreen"},
        },
        "appear_animation": "smooth_transition",
        "best_for": ["full_commentary", "hype_intro"],
    },
    "bottom_third": {
        "name": "Bottom Third",
        "description": "Girl in bottom third with semi-transparent overlay. Like a news ticker.",
        "layout": "overlay",
        "girl_x": "0",
        "girl_y": "H*0.65",
        "girl_scale": 0.35,
        "girl_shape": "rectangle",
        "background": "rgba(0,0,0,0.4)",
        "appear_animation": "slide_up",
        "best_for": ["instagram_stories", "casual"],
    },
    "dynamic": {
        "name": "Dynamic Position",
        "description": "Girl moves position based on what is happening on screen. Smart avoidance.",
        "layout": "dynamic",
        "positions": ["pip_bottom_right", "pip_top_right", "pip_bottom_left"],
        "switch_on": "action_position",
        "appear_animation": "smooth_transition",
        "best_for": ["commentary", "full_stream"],
    },
}


# ═══════════════════════════════════════════════════════════════════════
# SECTION 7: MUSIC-MOMENT MATCHING
# ═══════════════════════════════════════════════════════════════════════

MUSIC_MOMENT_MAP = {
    "clutch": ["cinematic_dark", "ambient_tension", "epic_orchestral"],
    "ace": ["hard_phonk", "phonk_beat", "cinematic_dark"],
    "multi_kill": ["phonk_beat", "hard_phonk", "drill_beat"],
    "headshot_sequence": ["hard_phonk", "trap_chill", "phonk_beat"],
    "funny": ["trap_chill", "lofi_gaming", "synthwave_retro"],
    "fail_moment": ["trap_chill", "lofi_gaming", "synthwave_retro"],
    "toxic_play": ["drill_beat", "hard_phonk", "phonk_beat"],
    "knife_kill": ["phonk_beat", "drill_beat", "hard_phonk"],
    "comeback": ["epic_orchestral", "cinematic_dark", "synthwave_retro"],
    "insane_play": ["phonk_beat", "hard_phonk", "cinematic_dark"],
    "default": ["trap_chill", "phonk_beat", "lofi_gaming"],
}


# ═══════════════════════════════════════════════════════════════════════
# SECTION 8: MEME OVERLAY CONFIG
# ═══════════════════════════════════════════════════════════════════════

MEME_OVERLAYS = {
    "fire_text": {
        "trigger": ["ace", "multi_kill", "clutch", "insane_play"],
        "text": "FIRE",
        "position": "top_center",
        "size": 80,
        "font_color": "#FF4500",
        "animation": "scale_pulse",
        "duration": 2.0,
    },
    "question_marks": {
        "trigger": ["clutch", "insane_play"],
        "text": "???",
        "position": "random",
        "size": 72,
        "font_color": "#FF0000",
        "animation": "shake",
        "duration": 1.0,
    },
    "kill_counter": {
        "trigger": ["ace", "multi_kill"],
        "type": "counter",
        "position": "top_right",
        "size": 64,
        "font_color": "#FFD700",
        "animation": "count_up",
        "count_from": 0,
        "count_to": 5,
        "duration": 3.0,
    },
    "replay_badge": {
        "trigger": ["all"],
        "text": "REPLAY",
        "position": "top_left",
        "size": 36,
        "font_color": "white",
        "background": "rgba(255,0,0,0.8)",
        "animation": "fade_in",
        "duration": 2.0,
    },
    "rank_badge": {
        "trigger": ["all"],
        "type": "dynamic_badge",
        "position": "top_right",
        "size": 48,
        "animation": "slide_in",
        "duration": 3.0,
    },
}


# ═══════════════════════════════════════════════════════════════════════
# SECTION 9: FUNCTIONS — Template selection, generation, analytics
# ═══════════════════════════════════════════════════════════════════════

def select_best_templates(
    moment_type: str,
    platform: str = "tiktok",
    enable_girl: bool = False,
    max_results: int = 3,
) -> list[dict]:
    """Smart template selection based on moment type, platform, and girl preference.

    Returns ranked list of best-matching templates.
    Uses moment affinity scores + platform compatibility + trend scores.
    """
    affinity = MOMENT_TEMPLATE_AFFINITY.get(moment_type, MOMENT_TEMPLATE_AFFINITY["default"])
    avoid_set = set(affinity.get("avoid", []))

    scored = []
    for fmt_id, config in FORMAT_CONFIGS.items():
        if fmt_id in avoid_set:
            continue

        has_girl = config.get("ai_girl", False)
        if enable_girl and not has_girl:
            continue
        if not enable_girl and has_girl:
            continue

        platforms = config.get("platforms", [])
        if platform not in platforms:
            continue

        score = config.get("trend_score", 0.5)

        if fmt_id in affinity.get("best", []):
            score += 0.3
        elif fmt_id in affinity.get("good", []):
            score += 0.15

        scored.append({
            "template_id": fmt_id,
            "name": config.get("name", fmt_id),
            "description": config.get("description", ""),
            "category": config.get("category", ""),
            "score": round(score, 2),
            "config": config,
        })

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:max_results]


def get_hook_for_template(format_type: str, moment_type: str = "default") -> str:
    """Get the best hook text for a given template and moment type."""
    config = FORMAT_CONFIGS.get(format_type, {})
    hook_style = config.get("hook_style", "none")
    hooks = HOOK_TEMPLATES.get(hook_style, [])
    if hooks:
        return random.choice(hooks)
    return ""


def get_cta_for_platform(platform: str = "tiktok") -> str:
    """Get a CTA optimized for the target platform."""
    if platform in ("instagram_reels", "instagram_stories"):
        pool = CTA_TEMPLATES["follow"] + CTA_TEMPLATES["save"] + CTA_TEMPLATES["engage"]
    elif platform == "youtube_shorts":
        pool = CTA_TEMPLATES["subscribe"] + CTA_TEMPLATES["engage"]
    else:
        pool = CTA_TEMPLATES["follow"] + CTA_TEMPLATES["engage"]
    return random.choice(pool)


def get_text_style(style_id: str) -> dict:
    """Get text style configuration."""
    return TEXT_STYLES.get(style_id, TEXT_STYLES["bold_dynamic"])


def get_girl_insertion_config(position_id: str) -> dict:
    """Get girl insertion configuration."""
    return GIRL_INSERTION_CONFIGS.get(position_id, GIRL_INSERTION_CONFIGS["pip_bottom_right"])


def get_music_for_moment(moment_type: str) -> str:
    """Get the best music track for a moment type."""
    tracks = MUSIC_MOMENT_MAP.get(moment_type, MUSIC_MOMENT_MAP["default"])
    return tracks[0] if tracks else "trap_chill"


def get_meme_overlays_for_moment(moment_type: str) -> list[dict]:
    """Get applicable meme overlays for a moment type."""
    overlays = []
    for overlay_id, overlay in MEME_OVERLAYS.items():
        triggers = overlay.get("trigger", [])
        if moment_type in triggers or "all" in triggers:
            overlays.append({"id": overlay_id, **overlay})
    return overlays


def build_complete_template(
    moment_type: str,
    platform: str = "tiktok",
    enable_girl: bool = False,
    girl_persona: str = "mia_cute",
    custom_hook: str | None = None,
    custom_cta: str | None = None,
) -> dict:
    """Build a complete template configuration for montage creation.

    This is the main entry point: takes a moment type and returns
    everything needed to create a clip: template, text style, hook, CTA,
    music, girl config, meme overlays.
    """
    templates = select_best_templates(moment_type, platform, enable_girl)
    if not templates:
        templates = select_best_templates("default", platform, enable_girl)

    chosen = templates[0] if templates else {"template_id": "highlight_subtitles", "config": FORMAT_CONFIGS["highlight_subtitles"]}
    config = chosen["config"] if "config" in chosen else FORMAT_CONFIGS.get(chosen["template_id"], {})

    subtitle_style_id = config.get("subtitle_style", "bold_dynamic")
    text_style = get_text_style(subtitle_style_id)

    hook = custom_hook or get_hook_for_template(chosen.get("template_id", "highlight_subtitles"), moment_type)
    cta = custom_cta or get_cta_for_platform(platform)

    music_id = get_music_for_moment(moment_type)

    meme_overlays = get_meme_overlays_for_moment(moment_type) if config.get("meme_sounds") or config.get("meme_overlay_images") else []

    girl_config = None
    if enable_girl and config.get("ai_girl"):
        girl_position = config.get("ai_girl_position", "pip_bottom_right")
        girl_config = {
            "persona": girl_persona,
            "position": girl_position,
            "insertion": get_girl_insertion_config(girl_position.replace("-", "_")),
            "voice_style": config.get("ai_girl_voice", "energetic"),
            "appears_at": config.get("ai_girl_appears_at", "react"),
            "size": config.get("ai_girl_size", 0.28),
        }

    return {
        "template_id": chosen.get("template_id", "highlight_subtitles"),
        "template_name": chosen.get("name", ""),
        "score": chosen.get("score", 0.5),
        "moment_type": moment_type,
        "platform": platform,
        "format_config": config,
        "text_style": text_style,
        "hook_text": hook,
        "cta_text": cta,
        "music_track": music_id,
        "color_grade": config.get("color_grade", "cinematic"),
        "meme_overlays": meme_overlays,
        "girl_config": girl_config,
        "target_duration": config.get("target_duration", (15, 30)),
        "zoom_effects": config.get("zoom_effects", False),
        "slow_motion": config.get("slow_motion", False),
        "screen_shake": config.get("screen_shake", False),
    }


# ═══════════════════════════════════════════════════════════════════════
# SECTION 10: A/B TESTING
# ═══════════════════════════════════════════════════════════════════════

async def generate_ab_variants(db, moment_id: int, template_ids: list[int] | None = None) -> list[dict]:
    """
    Generate multiple clip variants of the same moment using different templates.
    This is the core A/B testing functionality.
    """
    cursor = await db.execute("SELECT * FROM moments WHERE id = ?", (moment_id,))
    moment = await cursor.fetchone()
    if not moment:
        return []

    if template_ids:
        placeholders = ",".join(["?" for _ in template_ids])
        cursor = await db.execute(
            f"SELECT * FROM templates WHERE id IN ({placeholders}) AND is_active = 1",
            template_ids,
        )
    else:
        cursor = await db.execute(
            "SELECT * FROM templates WHERE is_active = 1 ORDER BY weight DESC"
        )
    templates = await cursor.fetchall()

    if not templates:
        return []

    test_name = f"AB Test - Moment #{moment_id} - {moment['moment_type']}"
    cursor = await db.execute(
        "INSERT INTO ab_tests (name, moment_id, status) VALUES (?, ?, 'running')",
        (test_name, moment_id),
    )
    ab_test_id = cursor.lastrowid

    variants = []
    for tmpl in templates:
        format_type = tmpl["format_type"]
        config = FORMAT_CONFIGS.get(format_type, {})
        hooks = HOOK_TEMPLATES.get(config.get("hook_style", "none"), [])
        hook_text = random.choice(hooks) if hooks else None
        cta_pool = []
        for cta_list in CTA_TEMPLATES.values():
            cta_pool.extend(cta_list)
        cta_text = random.choice(cta_pool) if cta_pool else ""

        duration_range = config.get("target_duration", (15, 30))
        duration = round(random.uniform(*duration_range), 1)

        title = f"{moment['description'] or moment['moment_type']} [{tmpl['name']}]"

        has_ai_girl = 1 if config.get("ai_girl", False) else 0
        has_subtitles = 1 if config.get("subtitles", False) else 0
        has_face_cam = 1 if config.get("face_cam", False) else 0

        cursor = await db.execute(
            """INSERT INTO clips (moment_id, template_id, ab_test_id, title, description, format_type,
               duration, status, hook_text, cta_text, has_ai_girl, has_subtitles, has_face_cam)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'generated', ?, ?, ?, ?, ?)""",
            (
                moment_id,
                tmpl["id"],
                ab_test_id,
                title,
                f"Generated from moment #{moment_id} using template '{tmpl['name']}'",
                format_type,
                duration,
                hook_text,
                cta_text,
                has_ai_girl,
                has_subtitles,
                has_face_cam,
            ),
        )

        variants.append({
            "clip_id": cursor.lastrowid,
            "template_name": tmpl["name"],
            "format_type": format_type,
            "hook_text": hook_text,
            "duration": duration,
        })

    await db.commit()
    return {"ab_test_id": ab_test_id, "variants": variants}


# ═══════════════════════════════════════════════════════════════════════
# SECTION 11: ANALYTICS & SELF-LEARNING
# ═══════════════════════════════════════════════════════════════════════

async def update_template_weights(db) -> dict:
    """Self-learning: Analyze clip performance and adjust template weights.

    Looks at views, likes, comments, shares per template and adjusts
    the weight (selection probability) accordingly. Templates that
    perform well get higher weights, underperforming ones get lower.
    """
    try:
        cursor = await db.execute("""
            SELECT t.id, t.name, t.format_type, t.weight,
                   COUNT(c.id) as clip_count,
                   AVG(COALESCE(c.views, 0)) as avg_views,
                   AVG(COALESCE(c.likes, 0)) as avg_likes,
                   AVG(COALESCE(c.comments, 0)) as avg_comments,
                   AVG(COALESCE(c.shares, 0)) as avg_shares
            FROM templates t
            LEFT JOIN clips c ON c.template_id = t.id
            GROUP BY t.id
        """)
        results = await cursor.fetchall()

        if not results:
            return {"updated": 0, "message": "No templates found"}

        updates = []
        for row in results:
            clip_count = row["clip_count"] or 0
            if clip_count < 3:
                continue

            avg_views = row["avg_views"] or 0
            avg_likes = row["avg_likes"] or 0
            avg_comments = row["avg_comments"] or 0
            avg_shares = row["avg_shares"] or 0

            engagement = (
                avg_views * 1.0 +
                avg_likes * 10.0 +
                avg_comments * 20.0 +
                avg_shares * 30.0
            )

            old_weight = row["weight"] or 50
            new_weight = min(100, max(10, int(engagement * 0.001 * 0.7 + old_weight * 0.3)))

            updates.append({
                "id": row["id"],
                "name": row["name"],
                "old_weight": old_weight,
                "new_weight": new_weight,
                "engagement_score": round(engagement, 1),
                "clip_count": clip_count,
            })

        for u in updates:
            await db.execute(
                "UPDATE templates SET weight = ? WHERE id = ?",
                (u["new_weight"], u["id"]),
            )

        await db.commit()

        return {
            "updated": len(updates),
            "adjustments": updates,
            "timestamp": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        return {"updated": 0, "error": str(e)}


def adapt_weights_from_ab_result(
    winner_format: str,
    loser_formats: list[str],
    margin: float = 0.0,
) -> dict:
    """Synchronous weight adaptation after A/B test completion.

    Boosts the winner format's trend_score and lowers losers' scores
    in the in-memory FORMAT_CONFIGS. Changes persist until restart;
    the async update_template_weights() persists to DB.

    Args:
        winner_format: format_type of the winning clip
        loser_formats: format_types of losing clips
        margin: score difference (used to scale adjustment)

    Returns dict with old/new scores for each adjusted format.
    """
    adjustments: dict[str, dict] = {}
    boost = min(0.05, max(0.01, margin * 0.02))

    if winner_format in FORMAT_CONFIGS:
        old = FORMAT_CONFIGS[winner_format].get("trend_score", 0.5)
        new = min(1.0, old + boost)
        FORMAT_CONFIGS[winner_format]["trend_score"] = round(new, 3)
        adjustments[winner_format] = {"old": old, "new": round(new, 3), "role": "winner"}

    for fmt in loser_formats:
        if fmt in FORMAT_CONFIGS:
            old = FORMAT_CONFIGS[fmt].get("trend_score", 0.5)
            new = max(0.1, old - boost * 0.5)
            FORMAT_CONFIGS[fmt]["trend_score"] = round(new, 3)
            adjustments[fmt] = {"old": old, "new": round(new, 3), "role": "loser"}

    return adjustments


def get_format_configs() -> dict:
    """Return all available format configurations."""
    return FORMAT_CONFIGS


def get_all_text_styles() -> dict:
    """Return all text style configurations."""
    return TEXT_STYLES


def get_all_girl_insertions() -> dict:
    """Return all girl insertion configurations."""
    return GIRL_INSERTION_CONFIGS


def get_template_catalog() -> dict:
    """Return full template catalog with categories and metadata."""
    categories = {}
    for fmt_id, config in FORMAT_CONFIGS.items():
        cat = config.get("category", "other")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append({
            "id": fmt_id,
            "name": config.get("name", fmt_id),
            "description": config.get("description", ""),
            "platforms": config.get("platforms", []),
            "has_girl": config.get("ai_girl", False),
            "has_subtitles": config.get("subtitles", False),
            "trend_score": config.get("trend_score", 0.5),
            "target_duration": config.get("target_duration", (15, 30)),
        })

    return {
        "categories": categories,
        "total_templates": len(FORMAT_CONFIGS),
        "text_styles": len(TEXT_STYLES),
        "girl_positions": len(GIRL_INSERTION_CONFIGS),
        "hook_styles": len(HOOK_TEMPLATES),
        "cta_categories": len(CTA_TEMPLATES),
        "meme_overlays": len(MEME_OVERLAYS),
    }
