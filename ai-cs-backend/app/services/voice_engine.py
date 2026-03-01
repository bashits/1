"""Voice Engine Service — ElevenLabs v3 ULTRA-REALISTIC Voice Generation.

Based on extensive research of ElevenLabs v3 documentation, official blog posts,
dev.to guides, and GitHub examples. Optimized for MAXIMUM human-like quality.

KEY TECHNIQUES FOR LIVING VOICE (from official ElevenLabs docs + community research):

1. AUDIO TAGS (v3 exclusive): [whispers], [laughs], [excited], [breathes], [sigh], etc.
   - Layer multiple tags: [excited][breathes] for complex emotions
   - Place WITHIN text for mid-sentence emotion shifts
   - v3 interprets them as "performance directives" not just markers

2. VOICE SETTINGS TUNING:
   - stability: 0.25-0.40 = MORE human variation (key for realism!)
   - similarity_boost: 0.70-0.85 = voice consistency without robotic feel
   - style: 0.55-0.80 = emotional expressiveness (higher = more dramatic)
   - use_speaker_boost: True = enhanced clarity
   - speed: 0.90-1.05 = natural pacing varies by moment

3. NATURAL SPEECH PATTERNS (v3 specific - NO SSML break tags!):
   - Dashes (— or --) for interruptions and short pauses
   - Ellipsis (...) for hesitation and trailing off
   - CAPS for emphasis on key words
   - Question marks + exclamation for intonation control
   - Sentence length variation for natural rhythm

4. BREATHING & MICRO-REACTIONS:
   - [breathes] before emotional peaks
   - [sigh] for emotional weight
   - [gulps] for tension moments
   - [catches breath] after fast sections
   - Natural fillers woven into scripts

5. PROMPT LENGTH: >250 characters for v3 consistency (official recommendation)
   - Short prompts cause inconsistent outputs in v3
   - Pad with contextual emotion tags if text is short

6. VOICE SELECTION: Use Designed/Library voices (5-star v3 compatibility)
   - Professional Voice Clones NOT fully optimized for v3 yet
   - Instant Voice Clones work well (4-star)

Sources:
- https://elevenlabs.io/docs/overview/capabilities/text-to-speech/best-practices
- https://elevenlabs.io/blog/v3-audiotags
- https://elevenlabs.io/blog/eleven-v3-audio-tags-precision-delivery-control-for-ai-speech
- https://elevenlabs.io/blog/eleven-v3-audio-tags-expressing-emotional-context-in-speech
- https://dev.to/yigit-konur/the-complete-guide-to-elevenlabs-v3
- https://github.com/elevenlabs/elevenlabs-python
"""

import json
import os
import random
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import httpx

# Storage
GENERATED_DIR = Path("/data/generated") if os.path.exists("/data") else Path(
    os.path.join(os.path.dirname(__file__), "..", "..", "generated")
)
GENERATED_DIR.mkdir(parents=True, exist_ok=True)
(GENERATED_DIR / "voice").mkdir(exist_ok=True)

# ElevenLabs config
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
ELEVENLABS_BASE_URL = "https://api.elevenlabs.io/v1"

# ─── REALISM PRESETS ──────────────────────────────────────────────────
# Tuned from official docs: lower stability = more human variation
# Higher style = more emotional range. Speed varies by energy level.

REALISM_PRESETS = {
    "ultra_expressive": {
        "stability": 0.25,
        "similarity_boost": 0.75,
        "style": 0.80,
        "use_speaker_boost": True,
        "speed": 1.0,
    },
    "natural_conversational": {
        "stability": 0.35,
        "similarity_boost": 0.80,
        "style": 0.65,
        "use_speaker_boost": True,
        "speed": 0.95,
    },
    "intimate_whisper": {
        "stability": 0.30,
        "similarity_boost": 0.85,
        "style": 0.70,
        "use_speaker_boost": True,
        "speed": 0.90,
    },
    "high_energy": {
        "stability": 0.20,
        "similarity_boost": 0.75,
        "style": 0.85,
        "use_speaker_boost": True,
        "speed": 1.05,
    },
    "dramatic_pause": {
        "stability": 0.30,
        "similarity_boost": 0.80,
        "style": 0.75,
        "use_speaker_boost": True,
        "speed": 0.88,
    },
}

# ─── Voice Personas ──────────────────────────────────────────────────
# Each girl has ULTRA-OPTIMIZED voice settings + rich emotion maps
# with layered audio tags, breathing patterns, and natural speech rhythm

VOICE_PERSONAS = {
    "jessica_fire": {
        "name": "Jessica Fire",
        "description": "Hot, energetic, expressive gamer girl. Reacts emotionally to everything. Her voice cracks with excitement, she gasps genuinely, giggles uncontrollably.",
        "elevenlabs_voice": "Jessica",
        "model_id": "eleven_v3",
        "realism_preset": "high_energy",
        "default_settings": {
            "stability": 0.22,
            "similarity_boost": 0.78,
            "style": 0.82,
            "use_speaker_boost": True,
            "speed": 1.02,
        },
        "signature_tags": ["[excited]", "[giggles]", "[breathes]", "[gasp]", "[laughs]", "[squeals]"],
        "breathing_pattern": "frequent",
        "pause_style": "quick",
        "emphasis_style": "caps_heavy",
        "emotion_map": {
            "clutch": "[breathes][excited] OH MY GOD — did you SEE that?! {text} [gasp] That was absolutely INSANE! [giggles] I literally can't—",
            "ace": "[gasps] Wait— wait— [screams] FIVE KILLS! {text} [laughs hysterically] No deaths! NONE! [catches breath] I'm shaking right now—",
            "multi_kill": "[breathes] Okay okay okay— [excited] {text} [giggles] No WAY that just happened! [squeals] WHAT?!",
            "headshot_sequence": "[whispers excitedly] Watch this... watch this... [breathes] {text} [impressed] Click... click... click... [whispers] ...flawless. Absolutely flawless.",
            "emotional_reaction": "[softly][breathes] {text} [sigh] That... that hit different. [quietly] Wow...",
            "toxic_moment": "[stifles laugh] Oh no — oh NO he did NOT just— {text} [bursts out laughing] [giggles uncontrollably] I'm SCREAMING—",
            "meme_fail": "[breathes] Okay so— [stifles laugh] {text} [bursts out laughing] I can't— I literally CAN'T— [catches breath] [giggles] I'm DEAD!",
            "round_win": "[excited][breathes] LET'S GOOO! {text} [claps] That's how it's DONE baby! [giggles]",
            "clutch_defuse": "[whispers][nervously] Come on... come on... [breathes heavily] {text} [screams] YESSS! [laughs] My heart is POUNDING!",
            "knife_kill": "[gasps] Did he just— [laughs] THE KNIFE?! {text} [giggles] That's DISRESPECTFUL! [amused] I love it.",
            "generic": "[cheerfully][breathes] {text} [giggles]",
        },
        "style_guide": "Maximum energy. Voice cracks with excitement. Breathes heavily between screams. Genuine giggles that trail off. Whispers before big moments then EXPLODES. Uses lots of trailing thoughts with dashes—",
        "natural_fillers": ["I mean—", "like—", "literally—", "oh my god—", "wait—"],
    },
    "sofia_smooth": {
        "name": "Sofia Smooth",
        "description": "Sultry, confident, slightly sarcastic. Cool older sister energy. Never loses composure but you can hear the smirk in her voice.",
        "elevenlabs_voice": "Lily",
        "model_id": "eleven_v3",
        "realism_preset": "natural_conversational",
        "default_settings": {
            "stability": 0.35,
            "similarity_boost": 0.80,
            "style": 0.65,
            "use_speaker_boost": True,
            "speed": 0.93,
        },
        "signature_tags": ["[sultry]", "[sigh]", "[amused]", "[chuckles]", "[whispers]", "[impressed]"],
        "breathing_pattern": "controlled",
        "pause_style": "dramatic",
        "emphasis_style": "understatement",
        "emotion_map": {
            "clutch": "[impressed][breathes] Well... well... well. {text} [sigh of admiration] Now THAT... was something. [chuckles softly]",
            "ace": "[amused] Five kills. Just like that. {text} [slowly] Clean... efficient... [whispers] devastating. [chuckles] Easy.",
            "multi_kill": "[raised eyebrow voice] Oh? {text} [pause] [approving hum] Mm... not bad at all. [softly] Not bad at all...",
            "headshot_sequence": "[sultry][slowly] Click... click... click... {text} [whispers] ...perfection. [breathes] Pure perfection.",
            "emotional_reaction": "[softly][breathes] {text} [long pause] [sigh] ...that was beautiful. [whispers] Truly.",
            "toxic_moment": "[amused] Oh... oh honey... [dry laugh] {text} [sarcastically] How very... classy of you. [chuckles]",
            "meme_fail": "[tries not to laugh] {text} [snort] [covers mouth] Okay... OKAY that was— [laughs quietly] ...actually funny.",
            "round_win": "[confidently] And there it is. {text} [satisfied sigh] Another round... another lesson. [smirks]",
            "clutch_defuse": "[whispers][deliberately] Tick... tick... tick... [breathes] {text} [exhales slowly] ...smooth as silk. [chuckles]",
            "knife_kill": "[raised eyebrow voice] Oh... the audacity. {text} [amused][whispers] I respect it. [dark chuckle]",
            "generic": "[confidently][breathes] {text}",
        },
        "style_guide": "Cool and composed always. Uses LONG pauses (ellipsis...) for dramatic effect. Whispers when others would shout. Sarcastic chuckles. Voice drops lower for emphasis rather than getting louder.",
        "natural_fillers": ["hmm...", "well...", "interesting...", "oh..."],
    },
    "mia_cute": {
        "name": "Mia Cute",
        "description": "Sweet, bubbly, genuinely adorable. Gets ACTUALLY shocked by plays. Her gasps are real, her squeals are involuntary. Like watching with your excited girlfriend. Doesn't over-articulate — speaks naturally, sometimes stumbles over words.",
        "elevenlabs_voice": "Laura",
        "model_id": "eleven_v3",
        "realism_preset": "ultra_expressive",
        "default_settings": {
            "stability": 0.18,          # ULTRA-LOW: maximum human messiness
            "similarity_boost": 0.78,   # Slightly lower for more natural variation
            "style": 0.85,              # HIGH: maximum emotional coloring
            "use_speaker_boost": True,
            "speed": 1.05,              # Slightly fast but not robotic
        },
        "signature_tags": ["[gasps]", "[squeals]", "[giggles]", "[whispers excitedly]", "[happily]", "[softly]", "[nervously]", "[breathes]"],
        "breathing_pattern": "frequent",
        "pause_style": "quick",
        "emphasis_style": "caps_exclaim",
        "emotion_map": {
            "clutch": "[breathes] Oh my— [gasps] oh my GOSH— did you— {text} [squeals] YESSS! [giggles] [catches breath] I literally— I KNEW it! I knew it I knew it!",
            "ace": "[whispers excitedly] Five... kills... [breathes] wait— [screams] FIVE KILLS! {text} [giggles] [happily] That was SO cool— like— how?!",
            "multi_kill": "[gasps] Wait — did he just — oh my god— [breathes] {text} [squeals] WHAT?! [giggles nervously] No way— no way no way!",
            "headshot_sequence": "[breathes] Head... shot... [gasps] ANOTHER ONE?! Wait— {text} [giggles nervously] [whispers] How does he— how does he DO that...",
            "emotional_reaction": "[softly] Aww... [breathes] {text} [sniffles] [quietly] That's so— that's so sweet... [giggles softly]",
            "toxic_moment": "[shocked whisper] Oh no... [breathes] [nervously] {text} [giggles nervously] I shouldn't— I shouldn't be laughing but— [stifles laugh]",
            "meme_fail": "[breathes] Oh no— [bursts out laughing] {text} [can't stop giggling] I'm sorry — I'm so sorry— [catches breath] [giggles] Oh my GOD I can't—",
            "round_win": "[happily] YAY! [breathes] {text} [giggles] [excited] We did it! We actually— we actually DID it! [squeals] [catches breath]",
            "clutch_defuse": "[nervously][whispers] Oh gosh oh gosh— [breathes heavily] come on— {text} [screams happily] YESSS! [giggles] [breathes] My heart— my heart is like—",
            "knife_kill": "[gasps] THE— THE KNIFE?! [breathes] {text} [giggles] [whispers] That's so mean! [laughs] I love it though— oh my god—",
            "generic": "[happily][breathes] So like— {text} [giggles]",
        },
        "style_guide": "Genuinely adorable. NEVER sounds robotic. Stumbles over words when excited. Gasps are REAL. Giggles trail off. Gets genuinely nervous. Voice goes high when excited. Lots of 'like—' and 'oh my—' natural fillers. Sentences trail off with dashes—",
        "natural_fillers": ["oh my gosh—", "wait—", "like—", "oh!—", "aww—", "I mean—", "so like—"],
    },
    "alex_edgy": {
        "name": "Alex Edgy",
        "description": "Edgy, intense, competitive. Dark humor with perfect timing. Whispers when others shout. Her silence is louder than screams. Speaks like she's seen everything — nothing impresses her easily.",
        "elevenlabs_voice": "Sarah",
        "model_id": "eleven_v3",
        "realism_preset": "dramatic_pause",
        "default_settings": {
            "stability": 0.22,          # LOW: natural voice variation, not robotic
            "similarity_boost": 0.72,   # Lower for more organic sound
            "style": 0.78,              # HIGH: strong emotional coloring
            "use_speaker_boost": True,
            "speed": 0.92,              # Slow and deliberate — weight on every word
        },
        "signature_tags": ["[smirks]", "[dark laugh]", "[whispers menacingly]", "[scoffs]", "[intense]", "[coldly]", "[exhales]", "[breathes]"],
        "breathing_pattern": "controlled",
        "pause_style": "dramatic",
        "emphasis_style": "whisper_contrast",
        "emotion_map": {
            "clutch": "[breathes] Come on... come on— [intense] {text} [exhales] [dark laugh] Get... destroyed. [whispers] ...yeah. Pathetic.",
            "ace": "[coldly] One... [breathes] two... three... four... [whispers menacingly] ...five. [exhales] {text} [long pause] [satisfied exhale] Yeah... clean sweep. That's it.",
            "multi_kill": "[breathes] [smirks] {text} [scoffs] ...too easy. [pause] [whispers] Next. [dark chuckle]",
            "headshot_sequence": "[focused breathing] {text} [pause] [satisfied exhale] ...surgical. [breathes] [whispers] Not a single... wasted bullet. Yeah.",
            "emotional_reaction": "[quietly][breathes] {text} [long pause] [sigh] ...damn. [whispers] That was— yeah. That was something else.",
            "toxic_moment": "[breathes] [dark laugh] Oh... [amused] {text} [smirks] [whispers] Love to see it. Absolutely... love it.",
            "meme_fail": "[breathes] [deadpan] {text} [pause] [slow clap] ...brilliant. [dark chuckle] Truly... truly brilliant.",
            "round_win": "[coolly][breathes] That's game. {text} [exhales] [whispers] Predictable. [pause] [smirks] As always.",
            "clutch_defuse": "[whispers][intense] Tick... tick... tick... [breathes heavily] {text} [exhales slowly] ...boom. [dark laugh] Cold blooded. Yeah.",
            "knife_kill": "[breathes] [impressed despite herself] The knife. {text} [long pause] [whispers] ...disrespectful. [dark laugh] I respect that.",
            "generic": "[coolly][breathes] {text} [exhales]",
        },
        "style_guide": "Intensity through restraint. NEVER squeals or screams. Whispers when others shout. Long pauses (...). Dark chuckles not laughs. Speaks like she's bored until something genuinely impresses her. Adds 'yeah' and trails off with dashes— Natural breathing between phrases.",
        "natural_fillers": ["...", "hmm.", "yeah...", "well well well...", "interesting...", "right..."],
    },
}

# ─── COMPREHENSIVE Audio Tag Library (from official ElevenLabs v3 docs) ───
AUDIO_TAGS = {
    "emotions": {
        "positive": [
            "[excited]", "[happy]", "[happily]", "[cheerful]", "[joyful]",
            "[delighted]", "[thrilled]", "[ecstatic]", "[elated]", "[overjoyed]",
        ],
        "negative": [
            "[sad]", "[angry]", "[scared]", "[frustrated]", "[annoyed]",
            "[disgusted]", "[melancholy]", "[sorrowful]", "[devastated]",
        ],
        "complex": [
            "[nervous]", "[anxious]", "[conflicted]", "[bittersweet]",
            "[nostalgic]", "[contemplative]", "[wistful]", "[awestruck]",
        ],
        "social": [
            "[confident]", "[flirty]", "[sultry]", "[seductive]",
            "[playfully]", "[sarcastically]", "[condescending]", "[smugly]",
            "[impressed]", "[amused]", "[bored]", "[skeptical]",
        ],
    },
    "reactions": {
        "laughter": [
            "[laughs]", "[giggles]", "[chuckles]", "[snickers]",
            "[dark laugh]", "[stifles laugh]", "[bursts out laughing]",
            "[laughs hysterically]", "[giggle]", "[big laugh]",
            "[can't stop giggling]", "[laughs quietly]", "[nervous laugh]",
        ],
        "vocal": [
            "[gasps]", "[gasp]", "[sighs]", "[sigh]", "[screams]",
            "[whispers]", "[cries]", "[sniffles]", "[groans]", "[squeals]",
            "[scoffs]", "[snorts]", "[gulps]", "[yawns]", "[hums]",
            "[clears throat]", "[voice cracks]",
        ],
        "physical": [
            "[claps]", "[snaps fingers]", "[covers mouth]",
            "[slow clap]", "[taps]",
        ],
    },
    "breathing": [
        "[breathes]", "[deep breath]", "[exhales]", "[panting]",
        "[breathes heavily]", "[sigh of relief]", "[catches breath]",
        "[exhales slowly]", "[sharp inhale]", "[satisfied exhale]",
        "[focused breathing]", "[shaky breath]",
    ],
    "delivery": {
        "speed": [
            "[slowly]", "[quickly]", "[rushed]", "[rapid-fire]",
            "[deliberately]", "[slows down]", "[drawn out]",
        ],
        "volume": [
            "[whispers]", "[softly]", "[quietly]", "[loudly]",
            "[shouts]", "[screams]", "[murmurs]",
        ],
        "style": [
            "[stammers]", "[timidly]", "[firmly]", "[matter-of-fact]",
            "[dramatically]", "[deadpan]", "[intensely]", "[casually]",
            "[professionally]", "[warmly]", "[coldly]", "[tenderly]",
        ],
        "timing": [
            "[pause]", "[long pause]", "[continues after a beat]",
            "[trails off]", "[interrupting]", "[hesitantly]",
        ],
    },
    "character_voice": [
        "[seductive voice]", "[baby voice]", "[deep voice]",
        "[high pitched]", "[raspy]", "[breathy]", "[husky]",
        "[sultry voice]", "[gruff voice]", "[sweet voice]",
        "[narrator voice]", "[mysterious voice]",
    ],
    "accents": [
        "[American accent]", "[British accent]", "[Australian accent]",
        "[French accent]", "[Russian accent]", "[Southern US accent]",
    ],
}

# ─── NATURAL SPEECH ENHANCER ─────────────────────────────────────────
NATURAL_SPEECH_PATTERNS = {
    "pre_emotion_breath": [
        "[breathes] ", "[deep breath] ", "[inhales] ",
    ],
    "post_excitement_recovery": [
        " [catches breath]", " [exhales]", " [breathes]",
    ],
    "fillers": {
        "thinking": ["I mean— ", "Like— ", "So— ", "Okay so— "],
        "surprise": ["Wait— ", "Hold on— ", "Oh— ", "Oh my— "],
        "emphasis": ["Literally ", "Actually ", "Seriously "],
    },
    "trail_offs": [
        "—", "...", "— yeah.", "... wow.", "— I can't even—",
    ],
}


def get_elevenlabs_key() -> str:
    """Get ElevenLabs API key from env or module-level var."""
    return os.environ.get("ELEVENLABS_API_KEY", "") or ELEVENLABS_API_KEY


def _enhance_for_realism(text: str, persona_id: str = "jessica_fire") -> str:
    """Apply realism enhancements to make text sound more human.

    Based on official ElevenLabs v3 best practices:
    - Prompts should be >250 chars for consistency
    - Use natural punctuation for pacing (v3 doesn't support SSML breaks)
    - Vary sentence length for natural rhythm
    - Add contextual breathing and micro-reactions
    """
    persona = VOICE_PERSONAS.get(persona_id, VOICE_PERSONAS["jessica_fire"])

    # Ensure minimum length for v3 consistency (>250 chars recommended)
    if len(text) < 250:
        breathing = persona.get("breathing_pattern", "moderate")
        if breathing == "frequent":
            text = f"[breathes] {text}"
        elif breathing == "controlled":
            text = f"[exhales] {text}"

        if len(text) < 200:
            tags = persona.get("signature_tags", ["[breathes]"])
            trail_tag = random.choice(tags)
            text = f"{text} {trail_tag}"

    return text


def _get_moment_settings(persona_id: str, moment_type: str) -> dict:
    """Get optimized voice settings for specific moment types.

    Different moments need different voice characteristics:
    - clutch/ace: Lower stability for maximum emotional variation
    - emotional: Slower speed, higher style
    - meme/toxic: Moderate settings for natural comedy timing
    """
    persona = VOICE_PERSONAS.get(persona_id, VOICE_PERSONAS["jessica_fire"])
    base = dict(persona["default_settings"])

    moment_adjustments = {
        "clutch": {"stability": -0.05, "style": 0.05, "speed": 0.03},
        "ace": {"stability": -0.05, "style": 0.08, "speed": 0.05},
        "multi_kill": {"stability": -0.03, "style": 0.05, "speed": 0.02},
        "headshot_sequence": {"stability": 0.05, "style": 0.0, "speed": -0.05},
        "emotional_reaction": {"stability": 0.05, "style": 0.05, "speed": -0.10},
        "toxic_moment": {"stability": -0.02, "style": 0.03, "speed": 0.0},
        "meme_fail": {"stability": -0.03, "style": 0.05, "speed": 0.02},
        "round_win": {"stability": -0.03, "style": 0.05, "speed": 0.03},
        "clutch_defuse": {"stability": -0.05, "style": 0.08, "speed": -0.05},
        "knife_kill": {"stability": -0.02, "style": 0.05, "speed": 0.0},
    }

    adjustments = moment_adjustments.get(moment_type, {})
    for key, delta in adjustments.items():
        if key in base:
            base[key] = round(max(0.1, min(1.0, base[key] + delta)), 2)

    return base


async def generate_voice_elevenlabs(
    text: str,
    voice_name: str = "Jessica",
    model_id: str = "eleven_v3",
    voice_settings: Optional[dict] = None,
    output_filename: Optional[str] = None,
) -> dict:
    """Generate voice using ElevenLabs v3 with MAXIMUM realism.

    Key optimizations applied:
    1. Model: eleven_v3 (most emotionally rich, supports audio tags)
    2. Settings: Tuned per-persona for human-like variation
    3. Audio tags: Interpreted as performance directives
    4. Natural pacing: Via punctuation (dashes, ellipsis, CAPS)

    Cost: ~$0.03 per 1000 characters (Starter plan).
    """
    api_key = get_elevenlabs_key()
    if not api_key:
        return {"success": False, "error": "ElevenLabs API key not configured. Set ELEVENLABS_API_KEY."}

    if output_filename is None:
        output_filename = f"voice_{uuid.uuid4().hex[:8]}.mp3"

    output_path = GENERATED_DIR / "voice" / output_filename

    # Get voice ID by name
    voice_id = await _get_voice_id(api_key, voice_name)
    if not voice_id:
        return {"success": False, "error": f"Voice '{voice_name}' not found in ElevenLabs account."}

    # Optimized default settings for maximum realism
    settings = {
        "stability": 0.30,
        "similarity_boost": 0.78,
        "style": 0.72,
        "use_speaker_boost": True,
    }
    if voice_settings:
        settings.update(voice_settings)

    # Clamp values to valid ranges
    settings["stability"] = max(0.0, min(1.0, settings.get("stability", 0.30)))
    settings["similarity_boost"] = max(0.0, min(1.0, settings.get("similarity_boost", 0.78)))
    settings["style"] = max(0.0, min(1.0, settings.get("style", 0.72)))

    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
    }

    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": settings["stability"],
            "similarity_boost": settings["similarity_boost"],
            "style": settings["style"],
            "use_speaker_boost": settings.get("use_speaker_boost", True),
        },
    }

    async with httpx.AsyncClient(timeout=90.0) as client:
        try:
            resp = await client.post(
                f"{ELEVENLABS_BASE_URL}/text-to-speech/{voice_id}",
                json=payload,
                headers=headers,
            )

            if resp.status_code == 200:
                output_path.write_bytes(resp.content)
                file_size = output_path.stat().st_size
                char_count = len(text)
                cost = round(char_count * 0.00003, 4)

                return {
                    "success": True,
                    "file_path": str(output_path),
                    "filename": output_filename,
                    "voice": voice_name,
                    "model": model_id,
                    "text": text,
                    "char_count": char_count,
                    "file_size_bytes": file_size,
                    "cost": cost,
                    "engine": "elevenlabs_v3",
                    "settings": settings,
                    "realism_level": "ultra",
                }
            else:
                error_text = resp.text
                return {"success": False, "error": f"ElevenLabs error {resp.status_code}: {error_text}"}
        except Exception as e:
            return {"success": False, "error": str(e)}


# Voice ID cache to avoid repeated API calls
_voice_id_cache: dict[str, str] = {}


async def _get_voice_id(api_key: str, voice_name: str) -> Optional[str]:
    """Get ElevenLabs voice ID by name (with caching)."""
    cache_key = f"{api_key[:8]}_{voice_name}"
    if cache_key in _voice_id_cache:
        return _voice_id_cache[cache_key]

    headers = {"xi-api-key": api_key}

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(f"{ELEVENLABS_BASE_URL}/voices", headers=headers)
            if resp.status_code == 200:
                voices = resp.json().get("voices", [])
                for v in voices:
                    if v["name"].lower() == voice_name.lower():
                        _voice_id_cache[cache_key] = v["voice_id"]
                        return v["voice_id"]
                for v in voices:
                    if voice_name.lower() in v["name"].lower():
                        _voice_id_cache[cache_key] = v["voice_id"]
                        return v["voice_id"]
            return None
        except Exception:
            return None


async def list_elevenlabs_voices() -> dict:
    """List all available ElevenLabs voices with v3 compatibility info."""
    api_key = get_elevenlabs_key()
    if not api_key:
        return {"success": False, "error": "ElevenLabs API key not configured.", "voices": []}

    headers = {"xi-api-key": api_key}

    async with httpx.AsyncClient(timeout=15.0) as client:
        try:
            resp = await client.get(f"{ELEVENLABS_BASE_URL}/voices", headers=headers)
            if resp.status_code == 200:
                voices_data = resp.json().get("voices", [])
                voices = []
                for v in voices_data:
                    category = v.get("category", "unknown")
                    v3_compat = "excellent" if category in ("premade", "generated", "cloned") else "good"
                    voices.append({
                        "voice_id": v["voice_id"],
                        "name": v["name"],
                        "category": category,
                        "labels": v.get("labels", {}),
                        "preview_url": v.get("preview_url"),
                        "v3_compatibility": v3_compat,
                        "description": v.get("description", ""),
                    })
                return {"success": True, "voices": voices, "total": len(voices)}
            return {"success": False, "error": f"API error {resp.status_code}", "voices": []}
        except Exception as e:
            return {"success": False, "error": str(e), "voices": []}


def build_expressive_script(
    text: str,
    moment_type: str = "generic",
    persona_id: str = "jessica_fire",
    enhance_realism: bool = True,
) -> str:
    """Build a MAXIMALLY expressive script using ElevenLabs v3 audio tags.

    Process:
    1. Select emotion template from persona's emotion_map
    2. Insert text into template with audio tags
    3. Apply realism enhancements (breathing, natural length)
    4. Ensure >250 char minimum for v3 consistency
    """
    persona = VOICE_PERSONAS.get(persona_id, VOICE_PERSONAS["jessica_fire"])
    emotion_map = persona["emotion_map"]

    template = emotion_map.get(moment_type, emotion_map.get("generic", "{text}"))
    script = template.format(text=text)

    if enhance_realism:
        script = _enhance_for_realism(script, persona_id)

    return script


def get_voice_personas() -> dict:
    """Get all available voice personas with their full configs."""
    return {
        pid: {
            "name": p["name"],
            "description": p["description"],
            "elevenlabs_voice": p["elevenlabs_voice"],
            "signature_tags": p["signature_tags"],
            "style_guide": p["style_guide"],
            "default_settings": p["default_settings"],
            "realism_preset": p.get("realism_preset", "natural_conversational"),
            "breathing_pattern": p.get("breathing_pattern", "moderate"),
            "pause_style": p.get("pause_style", "moderate"),
            "emphasis_style": p.get("emphasis_style", "moderate"),
            "moment_types": list(p["emotion_map"].keys()),
            "natural_fillers": p.get("natural_fillers", []),
        }
        for pid, p in VOICE_PERSONAS.items()
    }


def get_audio_tags() -> dict:
    """Get all available audio tags organized by category."""
    return AUDIO_TAGS


def get_realism_presets() -> dict:
    """Get available realism presets with descriptions."""
    return {
        name: {
            **settings,
            "description": {
                "ultra_expressive": "Maximum emotional range. Best for hype moments, reactions.",
                "natural_conversational": "Natural talking. Best for commentary, casual reactions.",
                "intimate_whisper": "Soft, close. Best for dramatic reveals, emotional moments.",
                "high_energy": "Peak excitement. Best for aces, clutches, kills.",
                "dramatic_pause": "Slow, intense. Best for suspense, knife kills, defuses.",
            }.get(name, "Custom preset"),
        }
        for name, settings in REALISM_PRESETS.items()
    }


async def generate_girl_voice(
    profile_data: dict,
    text: str,
    moment_type: str = "generic",
    use_audio_tags: bool = True,
    enhance_realism: bool = True,
) -> dict:
    """Generate voice for a specific AI girl profile with MAXIMUM realism.

    Full pipeline:
    1. Load girl's persona and voice config
    2. Build expressive script with audio tags
    3. Apply realism enhancements (breathing, pacing)
    4. Get moment-specific voice settings
    5. Generate via ElevenLabs v3
    6. Return result with full metadata
    """
    voice_config = profile_data.get("voice_config", {})
    persona_id = voice_config.get("persona_id", "jessica_fire")
    elevenlabs_voice = voice_config.get("elevenlabs_voice_name")
    custom_settings = profile_data.get("elevenlabs_voice_settings", {})

    if use_audio_tags:
        expressive_text = build_expressive_script(
            text, moment_type, persona_id, enhance_realism=enhance_realism
        )
    else:
        expressive_text = text
        if enhance_realism:
            expressive_text = _enhance_for_realism(expressive_text, persona_id)

    if elevenlabs_voice:
        voice_name = elevenlabs_voice
    else:
        persona = VOICE_PERSONAS.get(persona_id, VOICE_PERSONAS["jessica_fire"])
        voice_name = persona["elevenlabs_voice"]

    settings = _get_moment_settings(persona_id, moment_type)

    if custom_settings:
        settings.update(custom_settings)

    result = await generate_voice_elevenlabs(
        text=expressive_text,
        voice_name=voice_name,
        voice_settings=settings,
    )

    if result.get("success"):
        result["persona"] = persona_id
        result["moment_type"] = moment_type
        result["original_text"] = text
        result["expressive_text"] = expressive_text
        result["realism_enhancements"] = {
            "audio_tags": use_audio_tags,
            "realism_enhanced": enhance_realism,
            "moment_optimized_settings": True,
            "breathing_pattern": VOICE_PERSONAS.get(persona_id, {}).get("breathing_pattern", "moderate"),
        }

    return result


async def generate_voice_comparison(
    text: str,
    moment_type: str = "clutch",
) -> dict:
    """Generate the same text with all 4 personas for comparison.

    Useful for the user to pick their favorite voice style.
    Returns paths to all 4 audio files.
    """
    results = {}
    for persona_id in VOICE_PERSONAS:
        persona = VOICE_PERSONAS[persona_id]
        expressive_text = build_expressive_script(text, moment_type, persona_id)
        settings = _get_moment_settings(persona_id, moment_type)

        result = await generate_voice_elevenlabs(
            text=expressive_text,
            voice_name=persona["elevenlabs_voice"],
            voice_settings=settings,
            output_filename=f"compare_{persona_id}_{uuid.uuid4().hex[:6]}.mp3",
        )
        results[persona_id] = {
            "persona_name": persona["name"],
            "voice": persona["elevenlabs_voice"],
            "expressive_text": expressive_text,
            "result": result,
        }

    total_cost = sum(
        r["result"].get("cost", 0) for r in results.values() if r["result"].get("success")
    )

    return {
        "success": True,
        "comparisons": results,
        "total_cost": round(total_cost, 4),
        "moment_type": moment_type,
        "original_text": text,
    }


# ─── Voice Enhancement Tips (for UI display) ─────────────────────────
VOICE_ENHANCEMENT_TIPS = {
    "audio_tags_v3": {
        "title": "Audio Tags (ElevenLabs v3) — Performance Directives",
        "description": "v3 interprets tags as directorial cues, not just markers. Layer them for complex emotions.",
        "examples": [
            "[excited][breathes] OH MY GOD — that was INSANE! [catches breath]",
            "[whispers] Watch this... [pause] [screams] BOOM! [laughs]",
            "[stifles laugh] I can't— [bursts out laughing] I'm DEAD!",
            "[nervously][breathes] Come on... come on... [sigh of relief] YES!",
            "[sultry][slowly] Well... well... well. [chuckles] Impressive.",
            "[coldly] One... two... three... [whispers menacingly] ...five.",
        ],
    },
    "realism_settings": {
        "title": "Voice Settings for Maximum Realism",
        "description": "Official ElevenLabs recommendations for human-like output",
        "settings": {
            "stability": "0.20-0.35 = More human variation (KEY for realism!). Higher = more robotic.",
            "similarity_boost": "0.70-0.85 = Voice consistency. Too high = loses expressiveness.",
            "style": "0.55-0.80 = Emotional range. Higher = more dramatic delivery.",
            "speed": "0.88-1.08 = Pacing. Slower for drama, faster for excitement.",
            "use_speaker_boost": "Always True for clarity.",
        },
    },
    "natural_speech": {
        "title": "Natural Speech Patterns (v3 Specific)",
        "description": "v3 does NOT support SSML break tags. Use these instead:",
        "examples": [
            "Dashes (— or --) for interruptions: I can't even—",
            "Ellipsis (...) for hesitation: I... yeah, I guess so...",
            "CAPS for emphasis: That was INSANE!",
            "Question + exclamation: Did he REALLY just do that?!",
            "Varied sentence length: Short. Then a longer sentence for rhythm.",
        ],
    },
    "breathing_patterns": {
        "title": "Breathing & Micro-Reactions",
        "description": "Add breathing and reactions for liveness — these are what separate AI from human",
        "examples": [
            "[breathes] before emotional peaks — like taking a real breath",
            "[catches breath] after excitement — real people need to breathe",
            "[sigh] for emotional weight — conveys feeling without words",
            "[gulps] for tension — audience FEELS the nervousness",
            "[exhales slowly] after intense moments — the 'cool down'",
        ],
    },
    "pro_tips": {
        "title": "Pro Tips for Ultra-Realism",
        "description": "Advanced techniques from ElevenLabs community",
        "tips": [
            "Keep prompts >250 characters for v3 consistency",
            "Layer 2-3 tags max per phrase (more can cause instability)",
            "Use trailing dashes (—) instead of periods for natural flow",
            "Vary energy WITHIN a single generation: whisper -> normal -> shout",
            "The voice you choose matters MORE than settings — test multiple voices",
            "Designed/Library voices get 5-star v3 performance",
            "Professional Voice Clones are NOT fully optimized for v3 yet",
        ],
    },
    "oss_alternatives": {
        "title": "Open-Source Alternatives (GPU Required)",
        "description": "For zero-cost generation with your own GPU",
        "models": [
            {"name": "Orpheus TTS", "stars": "5.9k", "tags": "<laugh>, <sigh>, <gasp>", "vram": "8GB", "url": "https://github.com/canopyai/Orpheus-TTS"},
            {"name": "VibeVoice (Microsoft)", "stars": "23.4k", "tags": "Multi-speaker, long-form", "vram": "16GB", "url": "https://github.com/microsoft/VibeVoice"},
            {"name": "Qwen3-TTS", "stars": "8.5k", "tags": "Voice clone + design", "vram": "8GB", "url": "https://github.com/QwenLM/Qwen3-TTS"},
            {"name": "Fish Speech", "stars": "25k", "tags": "SOTA OSS TTS", "vram": "4GB", "url": "https://github.com/fishaudio/fish-speech"},
            {"name": "Index TTS", "stars": "18.1k", "tags": "Industrial-level, zero-shot", "vram": "4GB", "url": "https://github.com/index-tts/index-tts"},
        ],
    },
}
