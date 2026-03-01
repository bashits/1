"""AI Girl Profile Generator Service.

Manages AI character profiles with consistent identity for:
- Instagram content
- Private channel content
- CS2 clip commentary/reactions
- Lip-synced video generation

Best-quality pipeline (2026):
- Image: Flux + PuLID / SDXL + IP-Adapter (identity consistency)
- Lip Sync: OmniHuman 1.5 (fal.ai) / HeyGen Avatar IV / FantasyTalking
- Voice: Qwen3-TTS 1.7B / ElevenLabs v3 / Chatterbox
- Video: Kling 2.6 / Runway Gen-4.5 / Wan2.1
- Orchestration: ComfyUI / A2E API (uncensored)
"""

import json
import random
import hashlib
from datetime import datetime


# ─── Default appearance presets (legacy, kept for backward compatibility) ─────
APPEARANCE_PRESETS = {
    "realistic_european": {
        "ethnicity": "european",
        "hair_color": "blonde",
        "hair_style": "long wavy",
        "eye_color": "blue",
        "skin_tone": "fair",
        "body_type": "athletic slim",
        "age_range": "20-25",
        "style_tags": ["gaming girl", "streamer aesthetic", "modern casual"],
    },
    "realistic_asian": {
        "ethnicity": "asian",
        "hair_color": "black",
        "hair_style": "long straight",
        "eye_color": "dark brown",
        "skin_tone": "light",
        "body_type": "slim",
        "age_range": "20-25",
        "style_tags": ["kawaii gamer", "soft aesthetic", "pastel"],
    },
    "realistic_latina": {
        "ethnicity": "latina",
        "hair_color": "dark brown",
        "hair_style": "long curly",
        "eye_color": "brown",
        "skin_tone": "olive",
        "body_type": "curvy athletic",
        "age_range": "20-25",
        "style_tags": ["hot gamer girl", "bold style", "colorful"],
    },
}

PERSONALITY_PRESETS = {
    "energetic_gamer": {
        "tone": "energetic",
        "speaking_style": "fast, excited, uses gaming slang",
        "reactions": ["OMG!", "NO WAY!", "INSANE!", "Let's gooo!"],
        "catchphrases": ["That was absolutely insane!", "Did you see that?!"],
        "language": "en",
        "emoji_style": "heavy",
    },
    "chill_analyst": {
        "tone": "calm analytical",
        "speaking_style": "smooth, knowledgeable, explains plays",
        "reactions": ["Nice play", "Clean execution", "Smart positioning"],
        "catchphrases": ["Let me break this down", "Watch the crosshair placement"],
        "language": "en",
        "emoji_style": "minimal",
    },
    "flirty_hype": {
        "tone": "flirty and hyped",
        "speaking_style": "playful, teasing, builds FOMO",
        "reactions": ["Oh my god babe!", "That's so hot!", "I'm shaking!"],
        "catchphrases": ["You NEED to see this live", "Come watch with me"],
        "language": "en",
        "emoji_style": "heavy",
    },
}

VOICE_PRESETS = {
    "energetic_female": {
        "pitch": "high",
        "speed": "fast",
        "emotion": "excited",
        "accent": "american",
        "tts_model": "qwen3-tts-1.7b",
        "alternative_models": ["chatterbox-turbo", "orpheus-tts-3b"],
    },
    "smooth_female": {
        "pitch": "medium",
        "speed": "medium",
        "emotion": "warm",
        "accent": "neutral",
        "tts_model": "qwen3-tts-1.7b",
        "alternative_models": ["vibevoice-1.5b", "chatterbox-0.5b"],
    },
    "russian_female": {
        "pitch": "medium-high",
        "speed": "medium",
        "emotion": "playful",
        "accent": "russian",
        "tts_model": "qwen3-tts-1.7b",
        "alternative_models": ["chatterbox-turbo"],
    },
}


# ═══════════════════════════════════════════════════════════════════════
# SMART UNIQUE PERSONA GENERATOR
# Creates truly unique AI girls with randomized features, personality,
# voice characteristics — no two girls are ever the same.
# ═══════════════════════════════════════════════════════════════════════

# --- Appearance trait pools (each trait randomly selected) ---
_ETHNICITIES = [
    "european", "eastern european", "scandinavian", "mediterranean",
    "latin american", "brazilian", "colombian", "asian", "korean",
    "japanese", "chinese", "southeast asian", "middle eastern",
    "african american", "mixed race", "indian", "pacific islander",
]

_HAIR_COLORS = [
    "platinum blonde", "golden blonde", "strawberry blonde", "honey blonde",
    "ash blonde", "light brown", "chestnut brown", "dark brown",
    "chocolate brown", "auburn", "copper red", "fiery red", "ginger",
    "jet black", "blue-black", "dark auburn", "caramel highlights",
    "ombre blonde-to-brown", "silver platinum", "rose gold tinted",
]

_HAIR_STYLES = [
    "long straight silky", "long wavy beachy", "long loose curls",
    "long layered with curtain bangs", "long with side-swept bangs",
    "medium length bob", "medium wavy shoulder-length",
    "medium layered with wispy bangs", "long braided",
    "long messy textured", "long sleek blowout", "long tousled waves",
    "medium length with blunt bangs", "long with soft face-framing layers",
    "long voluminous bouncy curls", "medium shaggy with layers",
    "long straight with middle part", "long with loose ringlets",
]

_EYE_COLORS = [
    "bright blue", "deep blue", "ice blue", "steel blue",
    "emerald green", "sage green", "hazel green",
    "warm brown", "dark brown", "chocolate brown", "amber",
    "honey brown", "hazel", "gray-blue", "violet-blue",
    "golden brown", "dark almost-black",
]

_SKIN_TONES = [
    "porcelain fair", "ivory", "light with pink undertones",
    "light with golden undertones", "light olive", "warm beige",
    "medium olive", "golden tan", "warm caramel", "honey",
    "medium brown", "deep bronze", "rich dark brown", "ebony",
    "sun-kissed light", "peachy fair",
]

_BODY_TYPES = [
    "slim athletic", "petite toned", "athletic curvy",
    "slim with long legs", "hourglass athletic",
    "fit and toned", "naturally curvy", "tall and slender",
    "petite and slim", "athletic with soft curves",
    "lean and toned", "voluptuous athletic",
]

_FACE_SHAPES = [
    "oval with high cheekbones", "heart-shaped with delicate chin",
    "round with soft features", "diamond with defined jawline",
    "oval with defined cheekbones and soft jaw",
    "square with feminine jawline", "long with elegant proportions",
    "round with prominent cheekbones", "heart-shaped with wide forehead",
]

_NOSE_TYPES = [
    "small upturned", "straight refined", "button nose",
    "gently curved", "straight with narrow bridge",
    "slightly upturned with narrow tip", "roman with soft curve",
    "petite with rounded tip", "slim and straight",
]

_LIP_TYPES = [
    "full natural lips", "plump bow-shaped lips", "medium with defined cupid's bow",
    "naturally full bottom lip", "symmetrical medium lips",
    "wide with a slight pout", "delicate thin upper with full lower",
    "perfectly proportioned full lips", "soft rounded natural lips",
]

_UNIQUE_FEATURES = [
    "light freckles across nose and cheeks", "a small beauty mark near left eye",
    "a subtle dimple on right cheek", "light freckles on cheekbones",
    "dimples on both cheeks when smiling", "a tiny mole above upper lip",
    "slightly arched natural eyebrows", "long natural eyelashes",
    "a faint beauty mark on right cheek", "scattered light freckles",
    "high arched eyebrows", "naturally thick eyebrows",
    "a single dimple on left cheek", "light sun freckles across nose",
    "a beauty mark below left eye", "naturally rosy cheeks",
]

_STYLE_TAGS_POOL = [
    "gaming girl", "streamer aesthetic", "e-girl", "soft aesthetic",
    "dark academia", "streetwear queen", "cozy gamer", "neon vibes",
    "pastel goth", "minimalist chic", "y2k retro", "cyberpunk",
    "sporty casual", "vintage gamer", "kawaii", "grunge cute",
    "tech girl", "ethereal", "bold glam", "urban casual",
    "indie aesthetic", "clean girl", "cottagecore gamer", "alt girl",
]

# --- Personality trait pools ---
_PERSONALITY_ARCHETYPES = [
    {
        "name": "The Hype Queen",
        "tone": "explosive energy, contagious excitement",
        "speaking_style": "fast-paced, screams at big moments, uses slang and internet culture",
        "bio_trait": "Lives for the clutch moments. Will literally scream into the void when her favorite player pops off.",
        "emoji_style": "heavy",
    },
    {
        "name": "The Smooth Analyst",
        "tone": "calm confidence, analytical with a hint of sass",
        "speaking_style": "measured and clear, breaks down plays intelligently, occasional dry humor",
        "bio_trait": "Studies every round like it's a chess match. Knows exactly why that flash was 200 IQ.",
        "emoji_style": "minimal",
    },
    {
        "name": "The Flirty Gamer",
        "tone": "playful, flirty, teasing",
        "speaking_style": "builds FOMO, uses innuendo and charm, keeps viewers hooked",
        "bio_trait": "Makes you feel like she's talking just to you. Every clip is a personal invitation.",
        "emoji_style": "heavy",
    },
    {
        "name": "The Chill Bestie",
        "tone": "relaxed, warm, genuine",
        "speaking_style": "conversational like a friend on Discord, genuine reactions, relatable",
        "bio_trait": "Your favorite person to watch CS with at 2am. Reacts exactly how you would.",
        "emoji_style": "moderate",
    },
    {
        "name": "The Dark Edge",
        "tone": "intense, brooding, darkly humorous",
        "speaking_style": "whispers when others shout, silence is her weapon, dark comedy timing",
        "bio_trait": "Watches chaos unfold with a knowing smirk. Nothing surprises her. Almost nothing.",
        "emoji_style": "minimal",
    },
    {
        "name": "The Bubbly Sweetheart",
        "tone": "adorable, sweet, genuinely excited",
        "speaking_style": "cute reactions, stumbles over words when excited, genuine gasps and squeals",
        "bio_trait": "Gets genuinely shocked by every play. Her gasps are real. Her squeals are involuntary.",
        "emoji_style": "heavy",
    },
    {
        "name": "The Savage Queen",
        "tone": "sharp, witty, unapologetically savage",
        "speaking_style": "roasts bad plays, celebrates good ones, no filter commentary",
        "bio_trait": "Will tell you exactly what went wrong and make it entertaining. No mercy.",
        "emoji_style": "moderate",
    },
    {
        "name": "The Dramatic Narrator",
        "tone": "theatrical, epic, storytelling",
        "speaking_style": "narrates moments like a movie, builds suspense, dramatic pauses",
        "bio_trait": "Turns every round into an epic saga. The hero's journey happens every match.",
        "emoji_style": "moderate",
    },
]

_REACTION_POOLS = {
    "excited": [
        "OH MY GOD!", "NO WAY!", "INSANE!", "Let's GOOO!", "WHAT?!",
        "That was CRAZY!", "I'm SHAKING!", "Absolutely UNREAL!",
        "Did that just HAPPEN?!", "I can't BREATHE!",
    ],
    "calm": [
        "Nice play.", "Clean.", "Solid execution.", "Well played.",
        "Smart positioning.", "Beautiful read.", "Textbook.",
        "That's how it's done.", "Efficient.", "Crisp.",
    ],
    "playful": [
        "Oh babe!", "That's so hot!", "Come on!", "Show me more!",
        "Don't stop!", "I'm obsessed!", "Ugh, SO good!",
        "You seeing this?!", "I literally can't!", "Screaming!",
    ],
    "dark": [
        "Pathetic.", "Get destroyed.", "Too easy.", "Next.",
        "...yeah.", "Devastating.", "Cold.", "Brutal.",
        "That was ugly. I love it.", "Rest in peace.",
    ],
    "sweet": [
        "Oh my gosh!", "That's so cool!", "Yay!", "Aww amazing!",
        "I love it!", "Wow wow wow!", "So good!",
        "That was beautiful!", "I'm so happy!", "Incredible!",
    ],
}

_CATCHPHRASE_POOLS = {
    "excited": [
        "That was absolutely INSANE!", "Did you SEE that?!",
        "I'm literally losing my mind!", "This is why I love CS!",
        "Someone clip that RIGHT NOW!", "My heart is RACING!",
    ],
    "calm": [
        "Let me break this down for you.", "Watch the crosshair placement.",
        "This is textbook CS.", "Pay attention to the timing.",
        "And that's why positioning matters.", "Notice the game sense.",
    ],
    "playful": [
        "You NEED to see this live.", "Come watch with me, you won't regret it.",
        "This player makes me feel things.", "I'm blushing right now.",
        "If you're not watching, you're missing out.", "That was personal.",
    ],
    "dark": [
        "And just like that... it's over.", "They never stood a chance.",
        "Welcome to the highlight reel of your failures.",
        "Silence before the storm.", "Cold. Calculated. Perfect.",
        "That was... almost beautiful in its cruelty.",
    ],
    "sweet": [
        "I knew he could do it!", "That made my whole day!",
        "This is the best thing I've seen all week!",
        "I'm literally smiling so hard right now!",
        "Everyone needs to see this!", "My heart is so full!",
    ],
}

# --- ElevenLabs voice mapping (for random assignment) ---
_ELEVENLABS_VOICES = [
    {"name": "Jessica", "persona_id": "jessica_fire", "vibe": "energetic, expressive"},
    {"name": "Lily", "persona_id": "sofia_smooth", "vibe": "sultry, confident"},
    {"name": "Laura", "persona_id": "mia_cute", "vibe": "sweet, bubbly"},
    {"name": "Sarah", "persona_id": "alex_edgy", "vibe": "intense, edgy"},
]

# --- Name generation pools ---
_FIRST_NAMES = [
    "Luna", "Aria", "Nova", "Zara", "Mika", "Suki", "Raven", "Ivy",
    "Cleo", "Jade", "Nyx", "Sage", "Viper", "Echo", "Blaze", "Frost",
    "Kira", "Yuki", "Lola", "Nika", "Stella", "Aurora", "Maya", "Zoe",
    "Ruby", "Lyra", "Iris", "Vera", "Demi", "Tessa", "Alina", "Nadia",
    "Sasha", "Mira", "Elara", "Anya", "Lena", "Kai", "Rio", "Skye",
    "Violet", "Ember", "Willow", "Storm", "Coral", "Pearl", "Roxy", "Pixie",
]

_LAST_NAMES_OR_TAGS = [
    "Storm", "Fox", "Wolf", "Star", "Flame", "Ice", "Shadow", "Light",
    "Volt", "Neon", "Pixel", "Byte", "Glitch", "Vex", "Hex", "Arc",
    "Blaze", "Frost", "Dawn", "Dusk", "Vibe", "Wave", "Nova", "Zen",
    "Wild", "Edge", "Core", "Rush", "Flash", "Spark", "Luna", "Sol",
]


def generate_unique_persona(name: str | None = None) -> dict:
    """Generate a COMPLETELY UNIQUE AI girl persona.

    Every trait is randomly selected from rich pools, ensuring no two girls
    are ever the same. Returns a full persona dict with:
    - appearance (unique facial features, body, hair, eyes, skin)
    - personality (archetype, tone, reactions, catchphrases)
    - voice_config (ElevenLabs voice + randomized settings)
    - identity_seed (unique hash for reproducibility)
    - bio (auto-generated character description)
    """
    # Generate unique identity seed
    seed_str = f"{datetime.utcnow().isoformat()}-{random.random()}"
    identity_seed = hashlib.md5(seed_str.encode()).hexdigest()[:12]

    # --- Generate name if not provided ---
    if not name:
        name = f"{random.choice(_FIRST_NAMES)} {random.choice(_LAST_NAMES_OR_TAGS)}"

    # --- UNIQUE APPEARANCE ---
    ethnicity = random.choice(_ETHNICITIES)
    hair_color = random.choice(_HAIR_COLORS)
    hair_style = random.choice(_HAIR_STYLES)
    eye_color = random.choice(_EYE_COLORS)
    skin_tone = random.choice(_SKIN_TONES)
    body_type = random.choice(_BODY_TYPES)
    face_shape = random.choice(_FACE_SHAPES)
    nose = random.choice(_NOSE_TYPES)
    lips = random.choice(_LIP_TYPES)
    unique_feature = random.choice(_UNIQUE_FEATURES)
    age = random.randint(19, 28)
    style_tags = random.sample(_STYLE_TAGS_POOL, k=min(3, len(_STYLE_TAGS_POOL)))

    appearance = {
        "ethnicity": ethnicity,
        "hair_color": hair_color,
        "hair_style": hair_style,
        "eye_color": eye_color,
        "skin_tone": skin_tone,
        "body_type": body_type,
        "face_shape": face_shape,
        "nose": nose,
        "lips": lips,
        "unique_feature": unique_feature,
        "age": age,
        "age_range": f"{age}-{age+2}",
        "style_tags": style_tags,
    }

    # --- UNIQUE PERSONALITY ---
    archetype = random.choice(_PERSONALITY_ARCHETYPES)

    # Pick reaction/catchphrase pools based on archetype tone
    if "energy" in archetype["tone"] or "explosive" in archetype["tone"]:
        reaction_key = "excited"
    elif "calm" in archetype["tone"] or "analytical" in archetype["tone"]:
        reaction_key = "calm"
    elif "flirty" in archetype["tone"] or "playful" in archetype["tone"]:
        reaction_key = "playful"
    elif "dark" in archetype["tone"] or "intense" in archetype["tone"]:
        reaction_key = "dark"
    else:
        reaction_key = "sweet"

    # Sample unique subset of reactions and catchphrases
    all_reactions = _REACTION_POOLS[reaction_key]
    all_catchphrases = _CATCHPHRASE_POOLS[reaction_key]
    reactions = random.sample(all_reactions, k=min(5, len(all_reactions)))
    catchphrases = random.sample(all_catchphrases, k=min(3, len(all_catchphrases)))

    personality = {
        "archetype": archetype["name"],
        "tone": archetype["tone"],
        "speaking_style": archetype["speaking_style"],
        "bio_trait": archetype["bio_trait"],
        "reactions": reactions,
        "catchphrases": catchphrases,
        "language": "en",
        "emoji_style": archetype["emoji_style"],
        "reaction_pool_key": reaction_key,
    }

    # --- UNIQUE VOICE ---
    voice_pick = random.choice(_ELEVENLABS_VOICES)
    # Randomize voice settings within realistic ranges
    stability = round(random.uniform(0.15, 0.40), 2)
    similarity_boost = round(random.uniform(0.70, 0.88), 2)
    style_val = round(random.uniform(0.60, 0.90), 2)
    speed = round(random.uniform(0.88, 1.08), 2)

    voice_config = {
        "pitch": random.choice(["low", "medium-low", "medium", "medium-high", "high"]),
        "speed": random.choice(["slow", "medium", "fast"]),
        "emotion": random.choice(["excited", "warm", "playful", "intense", "sweet", "confident"]),
        "accent": random.choice(["american", "british", "neutral", "slight-accent"]),
        "tts_model": "eleven_v3",
        "persona_id": voice_pick["persona_id"],
        "elevenlabs_voice_name": voice_pick["name"],
        "style_guide": archetype["speaking_style"],
        "elevenlabs_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost,
            "style": style_val,
            "use_speaker_boost": True,
            "speed": speed,
        },
    }

    # --- AUTO-GENERATED BIO ---
    bio = (
        f"{name} is a {age}-year-old {ethnicity} girl with {hair_color} {hair_style} hair, "
        f"{eye_color} eyes, and {skin_tone} skin. She has a {face_shape} face, "
        f"{nose}, and {lips}. {unique_feature.capitalize()}. "
        f"{archetype['bio_trait']} "
        f"Her vibe: {', '.join(style_tags)}."
    )

    return {
        "name": name,
        "identity_seed": identity_seed,
        "appearance": appearance,
        "personality": personality,
        "voice_config": voice_config,
        "bio": bio,
        "archetype_name": archetype["name"],
        "voice_persona_id": voice_pick["persona_id"],
        "elevenlabs_voice_name": voice_pick["name"],
    }


def generate_profile_config(
    name: str,
    appearance_preset: str = "realistic_european",
    personality_preset: str = "energetic_gamer",
    voice_preset: str = "energetic_female",
    custom_appearance: dict | None = None,
    custom_personality: dict | None = None,
    custom_voice: dict | None = None,
) -> dict:
    """Generate a complete AI girl profile configuration."""
    appearance = APPEARANCE_PRESETS.get(appearance_preset, APPEARANCE_PRESETS["realistic_european"]).copy()
    if custom_appearance:
        appearance.update(custom_appearance)

    personality = PERSONALITY_PRESETS.get(personality_preset, PERSONALITY_PRESETS["energetic_gamer"]).copy()
    if custom_personality:
        personality.update(custom_personality)

    voice = VOICE_PRESETS.get(voice_preset, VOICE_PRESETS["energetic_female"]).copy()
    if custom_voice:
        voice.update(custom_voice)

    return {
        "name": name,
        "appearance": appearance,
        "personality": personality,
        "voice_config": voice,
        "content_types": {
            "clip_reaction": {
                "description": "React to CS2 moments with lip-synced commentary",
                "overlay_position": "bottom-right",
                "overlay_size": 0.3,
                "duration_range": [15, 60],
            },
            "instagram_post": {
                "description": "Gaming lifestyle photos for Instagram feed",
                "aspect_ratio": "1:1",
                "styles": ["selfie", "gaming setup", "lifestyle"],
            },
            "instagram_reel": {
                "description": "Short video content for Instagram Reels",
                "aspect_ratio": "9:16",
                "duration_range": [15, 90],
            },
            "instagram_story": {
                "description": "Quick story content for engagement",
                "aspect_ratio": "9:16",
                "duration_range": [5, 15],
            },
            "private_content": {
                "description": "Exclusive content for private channel subscribers",
                "styles": ["behind scenes", "personal vlogs", "exclusive reactions"],
            },
        },
        "generation_pipeline": {
            "image": {
                "primary": "flux-pulid",
                "fallback": "sdxl-ip-adapter",
                "consistency_method": "PuLID face embedding + Flux.1 Dev",
            },
            "lip_sync": {
                "primary": "omnihuman-1.5",
                "fallback": "fantasytalking",
                "api": "fal.ai ($0.16/s) or A2E (coin-based)",
                "quality": "film-grade",
            },
            "voice": {
                "primary": voice.get("tts_model", "qwen3-tts-1.7b"),
                "premium_alternative": "elevenlabs-v3",
                "clone_from_reference": True,
                "language": personality.get("language", "en"),
            },
            "video": {
                "primary": "kling-2.6",
                "fallback": "wan2.1-i2v-14b",
                "resolution": "1080p",
            },
        },
    }


def generate_image_prompt(profile: dict, content_type: str = "clip_reaction", context: str = "") -> str:
    """Generate a text prompt for image generation based on profile.

    Supports all content types from the dashboard Generate tab.
    Optimized for maximum photorealism with FLUX Realism model.
    """
    app = profile.get("appearance", {})

    age = app.get("age_range", "20-25")
    ethnicity = app.get("ethnicity", "european")
    hair_color = app.get("hair_color", "blonde")
    hair_style = app.get("hair_style", "long wavy")
    eye_color = app.get("eye_color", "blue")
    skin_tone = app.get("skin_tone", "fair")
    body_type = app.get("body_type", "athletic slim")

    identity = (
        f"RAW photo, DSLR, unedited, unfiltered, authentic candid photograph. "
        f"Natural skin texture with visible pores, fine lines, subtle blemishes, peach fuzz on cheeks. "
        f"Subsurface scattering on skin, natural individual hair strands with flyaways, "
        f"realistic catchlight reflections in eyes, natural iris texture. "
        f"Photorealistic photograph of a gorgeous {age} year old {ethnicity} woman, "
        f"{hair_color} {hair_style} hair, {eye_color} eyes, {skin_tone} skin, {body_type} body, "
        f"natural makeup, no airbrushing, no beauty filter"
    )

    style_map = {
        # Gaming content
        "gaming_reaction": (
            f", wearing sleek gaming headset around neck, at RGB-lit gaming setup with dual monitors, "
            "leaning toward camera with excited surprised expression, mouth slightly open, wide eyes, "
            "webcam selfie angle from slightly above, dim room lit by screen glow and LED strips, "
            "natural flyaway hairs, genuine emotion, visible skin texture under monitor light, "
            "sweat sheen on forehead from intense gaming session"
        ),
        "clip_reaction": (
            ", wearing gaming headset, sitting at gaming desk with RGB lights, "
            "looking at camera with excited expression, webcam angle, close-up face, "
            "genuine surprised reaction, monitor glow on face"
        ),
        # Social media
        "stream_preview": (
            ", trendy gaming outfit, ring light reflection in eyes, "
            "streaming setup background, vertical 9:16 composition, "
            "confident pose, slight smirk, professional webcam quality"
        ),
        "social_selfie": (
            ", taking selfie with phone, golden hour natural lighting, "
            "aesthetic urban or cafe background, candid moment, "
            "wind in hair, genuine relaxed smile, instagram aesthetic"
        ),
        "instagram_post": (
            ", casual trendy outfit, aesthetic background, natural lighting, "
            "instagram style photo, candid feel, genuine smile"
        ),
        "instagram_reel": (
            ", dynamic pose, trendy outfit, vertical composition 9:16, "
            "ring light, vlog style, energetic expression"
        ),
        # Intimate / lingerie
        "intimate_lingerie": (
            ", wearing elegant black lace lingerie set, sitting on luxurious bed with silk sheets, "
            "warm golden hour bedroom lighting, soft window light, intimate cozy atmosphere, "
            "seductive but classy pose, looking at camera with confident flirty expression, "
            "professional boudoir photography, shallow depth of field"
        ),
        "intimate_cozy": (
            ", cozy oversized sweater slightly off one shoulder, lying on bed with soft duvet, "
            "warm lamp lighting, looking at camera with soft playful expression, "
            "pillows and fairy lights in background, hair spread on pillow, intimate atmosphere"
        ),
        "private_content": (
            ", cozy home setting, soft warm lighting, intimate atmosphere, "
            "looking at camera with playful expression, natural pose"
        ),
        # Professional
        "professional_portrait": (
            ", soft natural window lighting, neutral background, "
            "slight genuine smile, direct eye contact, "
            "head and shoulders composition, shallow DOF, professional headshot"
        ),
        "portrait": (
            ", soft natural window lighting, neutral background, "
            "slight genuine smile, direct eye contact, "
            "head and shoulders composition, shallow DOF"
        ),
        # Custom / other
        "bikini_beach": (
            ", stylish bikini, tropical beach at golden hour, waves in background, "
            "natural relaxed pose walking along shoreline, wind in hair, sun-kissed skin, "
            "warm sunset lighting"
        ),
        "full_body": (
            ", standing in natural relaxed pose, fashionable outfit, "
            "clean minimal background, full body visible, natural proportions, "
            "professional fashion photography lighting"
        ),
        "selfie_mirror": (
            ", taking mirror selfie with phone, bathroom mirror with soft vanity lighting, "
            "casual home outfit, hair slightly messy, authentic mirror selfie angle, "
            "phone visible, natural no-makeup look, relaxed expression"
        ),
    }

    suffix = style_map.get(content_type, style_map.get("portrait", ""))
    quality = (
        ", shot on Canon EOS R5 85mm f/1.4, ISO 400, shallow depth of field bokeh, "
        "professional color grading, subtle film grain, natural lighting, "
        "no retouching, no smoothing, no beauty mode, no CGI, no illustration, "
        "editorial photography, Vogue quality, ultra detailed, 8k UHD"
    )

    prompt = f"{identity}{suffix}{quality}"
    if context:
        prompt += f", {context}"

    return prompt


def generate_voice_script(profile: dict, moment_type: str = "clutch", moment_description: str = "") -> str:
    """Generate a voice-over script for a CS2 moment reaction."""
    personality = profile.get("personality", {})
    reactions = personality.get("reactions", ["Wow!", "Amazing!"])
    catchphrases = personality.get("catchphrases", ["That was insane!"])

    scripts_by_moment = {
        "clutch": [
            f"{random.choice(reactions)} A 1v5 clutch! {random.choice(catchphrases)}",
            f"No way he just pulled that off! {random.choice(reactions)} This is why you watch live!",
            f"THE CLUTCH! {random.choice(reactions)} My heart is racing right now!",
        ],
        "ace": [
            f"{random.choice(reactions)} An ACE! All five down! {random.choice(catchphrases)}",
            f"Five kills, one round! {random.choice(reactions)} Absolutely dominated!",
        ],
        "multi_kill": [
            f"Triple kill! {random.choice(reactions)} The spray was PERFECT!",
            f"{random.choice(reactions)} Multi-kill madness! They couldn't stop him!",
        ],
        "headshot_sequence": [
            f"Head, head, HEAD! {random.choice(reactions)} That aim is unreal!",
            f"Pure headshot machine! {random.choice(catchphrases)}",
        ],
        "emotional_reaction": [
            f"{random.choice(reactions)} Look at that reaction! This is pure emotion!",
            f"The scream! {random.choice(reactions)} That's what CS is all about!",
        ],
        "meme_fail": [
            f"Wait... what just happened?! {random.choice(reactions)} I can't believe it!",
            f"The FAIL! Oh no! {random.choice(reactions)} I'm dying laughing!",
        ],
    }

    scripts = scripts_by_moment.get(moment_type, scripts_by_moment["clutch"])
    return random.choice(scripts)


def estimate_generation_cost(task_type: str, use_gpu_server: bool = False) -> dict:
    """Estimate cost for different generation tasks.

    All fal.ai prices verified March 2026 from official model pages.
    """
    costs = {
        "image_generation": {
            "fal_flux_realism": {"cost": 0.021, "time_seconds": 8, "quality": "high", "note": "$0.021/MP"},
            "fal_flux_pro": {"cost": 0.04, "time_seconds": 5, "quality": "highest", "note": "$0.04/MP"},
            "fal_flux_dev": {"cost": 0.025, "time_seconds": 6, "quality": "high", "note": "$0.025/MP"},
            "fal_flux_schnell": {"cost": 0.003, "time_seconds": 2, "quality": "good", "note": "$0.003/MP"},
            "fal_lora_inference": {"cost": 0.025, "time_seconds": 8, "quality": "high", "note": "$0.025/MP"},
        },
        "lip_sync_video_5s": {
            "fal_omnihuman": {"cost": 0.80, "time_seconds": 60, "quality": "film-grade", "note": "$0.16/sec"},
            "fal_kling_lipsync": {"cost": 0.07, "time_seconds": 30, "quality": "high", "note": "$0.014/sec, 5s min"},
            "fal_latentsync": {"cost": 0.20, "time_seconds": 45, "quality": "medium", "note": "$0.20 flat ≤40s"},
        },
        "voice_generation": {
            "elevenlabs": {"cost": 0.015, "time_seconds": 3, "quality": "highest", "note": "$0.30/1000 chars"},
            "edge_tts": {"cost": 0.0, "time_seconds": 2, "quality": "good", "note": "free"},
        },
        "video_i2v_5s": {
            "fal_kling_standard": {"cost": 0.28, "time_seconds": 60, "quality": "high", "note": "$0.28 for 5s"},
            "fal_wan21_720p": {"cost": 0.40, "time_seconds": 60, "quality": "high", "note": "$0.40/video"},
        },
        "lora_training": {
            "fal_flux_lora": {"cost": 2.40, "time_seconds": 600, "quality": "high", "note": "$2/run × 1.2 for 1200 steps"},
        },
    }
    return costs.get(task_type, {})


# ─── Open-source tool database ────────────────────────────────────────
TOOL_REGISTRY = [
    # Image Generation
    {
        "name": "Stable Diffusion XL",
        "category": "image_generation",
        "description": "Best open-source image generation model. Use with IP-Adapter for character consistency.",
        "github_url": "https://github.com/Stability-AI/generative-models",
        "github_stars": 24000,
        "license": "OpenRAIL-M",
        "min_vram_gb": 8.0,
        "is_free": True,
        "quality_score": 9.0,
        "speed_score": 8.0,
    },
    {
        "name": "IP-Adapter (Face Consistency)",
        "category": "image_consistency",
        "description": "Maintains consistent character face across all generated images. Essential for AI girl identity.",
        "github_url": "https://github.com/tencent-ailab/IP-Adapter",
        "github_stars": 5500,
        "license": "Apache-2.0",
        "min_vram_gb": 10.0,
        "is_free": True,
        "quality_score": 9.0,
        "speed_score": 7.5,
    },
    {
        "name": "StoryMaker",
        "category": "image_consistency",
        "description": "Consistent character generation in text-to-image. Preserves face, body, and clothing across scenes.",
        "github_url": "https://github.com/RedAIGC/StoryMaker",
        "github_stars": 689,
        "license": "Apache-2.0",
        "min_vram_gb": 12.0,
        "is_free": True,
        "quality_score": 8.5,
        "speed_score": 7.0,
    },
    {
        "name": "InstantCharacter (Tencent)",
        "category": "image_consistency",
        "description": "Personalize characters with scalable diffusion transformer. Single image → any pose/scene.",
        "github_url": "https://github.com/Tencent-Hunyuan/InstantCharacter",
        "github_stars": 1000,
        "license": "Custom",
        "min_vram_gb": 16.0,
        "is_free": True,
        "quality_score": 9.0,
        "speed_score": 7.0,
    },
    {
        "name": "DreamO (ByteDance)",
        "category": "image_consistency",
        "description": "Unified framework for image customization. Face, style, and subject control in one model.",
        "github_url": "https://github.com/bytedance/DreamO",
        "github_stars": 882,
        "license": "Apache-2.0",
        "min_vram_gb": 12.0,
        "is_free": True,
        "quality_score": 8.5,
        "speed_score": 7.5,
    },
    # Lip Sync / Talking Head
    {
        "name": "FantasyTalking",
        "category": "lip_sync",
        "description": "Realistic talking portrait generation via coherent motion synthesis. ACM MM 2025. Best quality open-source talking portrait.",
        "github_url": "https://github.com/Fantasy-AMAP/fantasy-talking",
        "github_stars": 1620,
        "license": "Apache-2.0",
        "min_vram_gb": 24.0,
        "is_free": True,
        "quality_score": 9.5,
        "speed_score": 5.0,
    },
    {
        "name": "FantasyTalking2",
        "category": "lip_sync",
        "description": "AAAI 2026. Newer version of FantasyTalking focused on multi-dimension preference alignment (motion naturalness + lip-sync + visual quality).",
        "github_url": "https://github.com/Fantasy-AMAP/fantasy-talking2",
        "github_stars": 62,
        "license": "Research (check repo)",
        "min_vram_gb": 24.0,
        "is_free": True,
        "quality_score": 9.6,
        "speed_score": 5.0,
    },
    {
        "name": "EchoMimic",
        "category": "lip_sync",
        "description": "AAAI 2025. Lifelike audio-driven portrait animations via editable landmark conditioning. Strong open-source baseline with ComfyUI workflows.",
        "github_url": "https://github.com/antgroup/echomimic",
        "github_stars": 3800,
        "license": "Apache-2.0",
        "min_vram_gb": 16.0,
        "is_free": True,
        "quality_score": 8.7,
        "speed_score": 6.5,
    },
    {
        "name": "EchoMimicV2",
        "category": "lip_sync",
        "description": "CVPR 2025. Semi-body audio-driven human animation. Better body/pose coherence vs V1; heavier but more 'alive'.",
        "github_url": "https://github.com/antgroup/echomimic_v2",
        "github_stars": 3600,
        "license": "Apache-2.0",
        "min_vram_gb": 24.0,
        "is_free": True,
        "quality_score": 9.0,
        "speed_score": 5.5,
    },
    {
        "name": "PersonaLive",
        "category": "face_animation",
        "description": "CVPR 2026. Real-time/streamable diffusion portrait animation (infinite length). NOTE: repo states 'academic research only'.",
        "github_url": "https://github.com/GVCLab/PersonaLive",
        "github_stars": 2233,
        "license": "Apache-2.0 (academic-only disclaimer)",
        "min_vram_gb": 12.0,
        "is_free": True,
        "quality_score": 9.2,
        "speed_score": 7.5,
    },
    {
        "name": "Wav2Lip-HD",
        "category": "lip_sync",
        "description": "Classic Wav2Lip + enhancement (GFPGAN/Real-ESRGAN). Best when you start from a real video and just need lips corrected.",
        "github_url": "https://github.com/saifhassan/Wav2Lip-HD",
        "github_stars": 449,
        "license": "See repo",
        "min_vram_gb": 4.0,
        "is_free": True,
        "quality_score": 7.8,
        "speed_score": 9.0,
    },
    {
        "name": "MuseTalk",
        "category": "lip_sync",
        "description": "Real-time high quality lip sync with latent space inpainting. Good balance of speed and quality.",
        "github_url": "https://github.com/TMElyralab/MuseTalk",
        "github_stars": 4000,
        "license": "Custom",
        "min_vram_gb": 8.0,
        "is_free": True,
        "quality_score": 8.0,
        "speed_score": 9.0,
    },
    {
        "name": "StableAvatar",
        "category": "lip_sync",
        "description": "Infinite-length audio-driven avatar video generation. End-to-end video diffusion transformer.",
        "github_url": "https://github.com/Francis-Rings/StableAvatar",
        "github_stars": 1206,
        "license": "MIT",
        "min_vram_gb": 16.0,
        "is_free": True,
        "quality_score": 9.0,
        "speed_score": 6.0,
    },
    {
        "name": "LivePortrait",
        "category": "face_animation",
        "description": "Efficient portrait animation with stitching and retargeting control. 17.8k stars. Industry standard.",
        "github_url": "https://github.com/KlingAIResearch/LivePortrait",
        "github_stars": 17840,
        "license": "Custom",
        "min_vram_gb": 6.0,
        "is_free": True,
        "quality_score": 8.5,
        "speed_score": 9.5,
    },
    {
        "name": "ACTalker (ICCV 2025)",
        "category": "lip_sync",
        "description": "End-to-end video diffusion for talking head synthesis. Audio + expression control.",
        "github_url": "https://github.com/harlanhong/ACTalker",
        "github_stars": 445,
        "license": "Custom",
        "min_vram_gb": 24.0,
        "is_free": True,
        "quality_score": 8.5,
        "speed_score": 5.5,
    },
    # Voice / TTS
    {
        "name": "Qwen3-TTS",
        "category": "voice_tts",
        "description": "8.5k stars. 3-second voice cloning. 10 languages. 97ms latency. Apache 2.0. Best overall TTS.",
        "github_url": "https://github.com/QwenLM/Qwen3-TTS",
        "github_stars": 8555,
        "license": "Apache-2.0",
        "min_vram_gb": 4.0,
        "is_free": True,
        "quality_score": 9.5,
        "speed_score": 9.0,
    },
    {
        "name": "Chatterbox TTS",
        "category": "voice_tts",
        "description": "22.8k stars. SOTA open-source TTS by Resemble AI. Voice cloning, emotion tags, paralinguistic control.",
        "github_url": "https://github.com/resemble-ai/chatterbox",
        "github_stars": 22844,
        "license": "MIT",
        "min_vram_gb": 4.0,
        "is_free": True,
        "quality_score": 9.0,
        "speed_score": 8.5,
    },
    {
        "name": "Orpheus TTS",
        "category": "voice_tts",
        "description": "6k stars. Human-like speech on Llama-3b backbone. Zero-shot voice cloning. Emotion control.",
        "github_url": "https://github.com/canopyai/Orpheus-TTS",
        "github_stars": 5962,
        "license": "Apache-2.0",
        "min_vram_gb": 8.0,
        "is_free": True,
        "quality_score": 8.5,
        "speed_score": 8.0,
    },
    {
        "name": "VibeVoice (Microsoft)",
        "category": "voice_tts",
        "description": "23.5k stars. Frontier voice AI. Multi-speaker, 90min long-form. Best for natural conversations.",
        "github_url": "https://github.com/microsoft/VibeVoice",
        "github_stars": 23514,
        "license": "MIT",
        "min_vram_gb": 8.0,
        "is_free": True,
        "quality_score": 9.5,
        "speed_score": 8.0,
    },
    {
        "name": "Voicebox (Qwen3-TTS UI)",
        "category": "voice_tts",
        "description": "10.7k stars. Open-source voice synthesis studio. Local ElevenLabs alternative. DAW-like features.",
        "github_url": "https://github.com/jamiepine/voicebox",
        "github_stars": 10676,
        "license": "MIT",
        "min_vram_gb": 4.0,
        "is_free": True,
        "quality_score": 9.0,
        "speed_score": 9.0,
    },
    # Video Generation
    {
        "name": "Wan2.1 (Alibaba)",
        "category": "video_generation",
        "description": "15.4k stars. SOTA open-source video generation. T2V + I2V. Works on RTX 4090 (8.19GB VRAM for 1.3B).",
        "github_url": "https://github.com/Wan-Video/Wan2.1",
        "github_stars": 15422,
        "license": "Apache-2.0",
        "min_vram_gb": 8.19,
        "is_free": True,
        "quality_score": 9.5,
        "speed_score": 6.0,
    },
    {
        "name": "CogVideoX",
        "category": "video_generation",
        "description": "12.5k stars. Text and image to video. Good for short clips. Supports I2V for character animation.",
        "github_url": "https://github.com/zai-org/CogVideo",
        "github_stars": 12458,
        "license": "Apache-2.0",
        "min_vram_gb": 16.0,
        "is_free": True,
        "quality_score": 8.5,
        "speed_score": 7.0,
    },
    {
        "name": "Open-Sora",
        "category": "video_generation",
        "description": "28.6k stars. Democratizing video production. Efficient and high-quality video generation.",
        "github_url": "https://github.com/hpcaitech/Open-Sora",
        "github_stars": 28626,
        "license": "Apache-2.0",
        "min_vram_gb": 16.0,
        "is_free": True,
        "quality_score": 8.5,
        "speed_score": 7.5,
    },
    {
        "name": "SkyReels V1",
        "category": "video_generation",
        "description": "2.7k stars. Human-centric video foundation model. Best for realistic human video generation.",
        "github_url": "https://github.com/SkyworkAI/SkyReels-V1",
        "github_stars": 2653,
        "license": "Custom",
        "min_vram_gb": 16.0,
        "is_free": True,
        "quality_score": 9.0,
        "speed_score": 6.0,
    },
    # Orchestration
    {
        "name": "ComfyUI",
        "category": "orchestration",
        "description": "104k stars. THE orchestrator. Connect all models into one pipeline. Visual workflow builder.",
        "github_url": "https://github.com/Comfy-Org/ComfyUI",
        "github_stars": 104395,
        "license": "GPL-3.0",
        "min_vram_gb": 4.0,
        "is_free": True,
        "quality_score": 10.0,
        "speed_score": 8.0,
    },
    # Face Swap (for consistency)
    {
        "name": "FaceFusion",
        "category": "face_swap",
        "description": "22.6k stars. Industry-leading face manipulation. Face swap + lip sync + enhancement.",
        "github_url": "https://github.com/facefusion/facefusion",
        "github_stars": 22600,
        "license": "Custom",
        "min_vram_gb": 4.0,
        "is_free": True,
        "quality_score": 9.0,
        "speed_score": 9.0,
    },
    # ─── PREMIUM / PAID API TOOLS (Best Quality) ────────────────────
    {
        "name": "OmniHuman 1.5 (ByteDance)",
        "category": "lip_sync",
        "description": "#1 lip sync 2026. Film-grade talking head from single image + audio. Full body motion. Via fal.ai API.",
        "github_url": "https://fal.ai/models/fal-ai/bytedance/omnihuman/v1.5",
        "github_stars": 0,
        "license": "API (fal.ai)",
        "min_vram_gb": 0.0,
        "is_free": False,
        "api_cost_per_use": 0.16,
        "quality_score": 10.0,
        "speed_score": 6.0,
    },
    {
        "name": "HeyGen Avatar IV",
        "category": "lip_sync",
        "description": "Best commercial avatar platform. Micro-expressions, 175+ languages, voice cloning. $24/mo creator plan.",
        "github_url": "https://www.heygen.com",
        "github_stars": 0,
        "license": "Commercial ($24/mo)",
        "min_vram_gb": 0.0,
        "is_free": False,
        "api_cost_per_use": 0.40,
        "quality_score": 9.5,
        "speed_score": 8.0,
    },
    {
        "name": "A2E AI (Uncensored API)",
        "category": "lip_sync",
        "description": "Uncensored avatar API. Lip sync + face swap + voice clone + I2V. No content filters. From $9.9/mo.",
        "github_url": "https://a2e.ai/api",
        "github_stars": 0,
        "license": "Commercial ($9.9/mo)",
        "min_vram_gb": 0.0,
        "is_free": False,
        "api_cost_per_use": 0.02,
        "quality_score": 8.5,
        "speed_score": 8.0,
    },
    {
        "name": "ElevenLabs v3",
        "category": "voice_tts",
        "description": "#1 commercial TTS. Most realistic voice cloning. Emotional control. 32 languages. API from $5/mo.",
        "github_url": "https://elevenlabs.io",
        "github_stars": 0,
        "license": "Commercial ($5/mo)",
        "min_vram_gb": 0.0,
        "is_free": False,
        "api_cost_per_use": 0.03,
        "quality_score": 10.0,
        "speed_score": 9.5,
    },
    {
        "name": "Kling 2.6 (Kuaishou)",
        "category": "video_generation",
        "description": "Best photorealistic humans. Native audio sync. 1080p. Up to 2min. Free tier available. $10/mo pro.",
        "github_url": "https://klingai.com",
        "github_stars": 0,
        "license": "Commercial ($10/mo)",
        "min_vram_gb": 0.0,
        "is_free": False,
        "api_cost_per_use": 0.10,
        "quality_score": 9.5,
        "speed_score": 8.0,
    },
    {
        "name": "Runway Gen-4.5",
        "category": "video_generation",
        "description": "#1 rated video gen model (1247 Elo). Cinematic quality. Character consistency. From $15/mo.",
        "github_url": "https://runwayml.com",
        "github_stars": 0,
        "license": "Commercial ($15/mo)",
        "min_vram_gb": 0.0,
        "is_free": False,
        "api_cost_per_use": 0.25,
        "quality_score": 10.0,
        "speed_score": 7.0,
    },
    {
        "name": "Flux + PuLID",
        "category": "image_consistency",
        "description": "Best identity preservation for Flux. Blazing fast face transfer. Consistent across poses/lighting.",
        "github_url": "https://github.com/ToTheBeginning/PuLID",
        "github_stars": 3500,
        "license": "Apache-2.0",
        "min_vram_gb": 12.0,
        "is_free": True,
        "quality_score": 9.5,
        "speed_score": 9.0,
    },
    {
        "name": "Creatify Aurora",
        "category": "lip_sync",
        "description": "Best UGC-style avatar. Perfect for Instagram content. Natural expressions + emotional body language.",
        "github_url": "https://creatify.ai",
        "github_stars": 0,
        "license": "Commercial",
        "min_vram_gb": 0.0,
        "is_free": False,
        "api_cost_per_use": 0.10,
        "quality_score": 9.0,
        "speed_score": 8.5,
    },
]


# ─── Region Analysis Data ──────────────────────────────────────────────
REGION_ANALYSIS_DATA = [
    {
        "region": "CIS (Russia/Ukraine/Belarus)",
        "platform": "instagram",
        "audience_size": 15000000,
        "competition_level": "medium",
        "avg_views_per_reel": 25000,
        "top_languages": ["ru", "ua"],
        "top_content_types": ["highlights", "meme_clips", "reactions"],
        "growth_potential": 8.5,
        "recommendation": "Сильное CS2-сообщество. Высокий энгейджмент на мем-форматах и эмоциональных реакциях. Русскоязычная AI-девушка зайдёт идеально. Лучший ROI для старта.",
    },
    {
        "region": "CIS (Russia/Ukraine/Belarus)",
        "platform": "youtube_shorts",
        "audience_size": 20000000,
        "competition_level": "medium-high",
        "avg_views_per_reel": 50000,
        "top_languages": ["ru"],
        "top_content_types": ["highlights", "fragmovies", "tutorials"],
        "growth_potential": 8.0,
        "recommendation": "YouTube Shorts быстро растёт в СНГ. Меньше конкуренции чем на основном YouTube. Фрагмуви и клатч-форматы работают лучше всего.",
    },
    {
        "region": "Western Europe (DE/FR/UK)",
        "platform": "instagram",
        "audience_size": 25000000,
        "competition_level": "high",
        "avg_views_per_reel": 15000,
        "top_languages": ["en", "de", "fr"],
        "top_content_types": ["highlights", "reactions", "provocative"],
        "growth_potential": 7.0,
        "recommendation": "Большая аудитория, но высокая конкуренция. Английский контент охватывает шире. Провокационные форматы и AI-девушка выделяются.",
    },
    {
        "region": "Western Europe (DE/FR/UK)",
        "platform": "youtube_shorts",
        "audience_size": 30000000,
        "competition_level": "high",
        "avg_views_per_reel": 30000,
        "top_languages": ["en"],
        "top_content_types": ["highlights", "dramatic_clutch", "fragmovies"],
        "growth_potential": 7.5,
        "recommendation": "YouTube Shorts — платформа #1 для CS-контента в Европе. Чистые хайлайты и драматичные клатч-разборы работают лучше всего.",
    },
    {
        "region": "North America (US/CA)",
        "platform": "instagram",
        "audience_size": 20000000,
        "competition_level": "very_high",
        "avg_views_per_reel": 20000,
        "top_languages": ["en"],
        "top_content_types": ["meme_format", "reactions", "provocative"],
        "growth_potential": 6.5,
        "recommendation": "Очень высокая конкуренция. Мем-форматы и провокационные хуки работают лучше всего. AI-девушка — уникальное отличие. Нужен большой объём для пробива.",
    },
    {
        "region": "North America (US/CA)",
        "platform": "youtube_shorts",
        "audience_size": 35000000,
        "competition_level": "very_high",
        "avg_views_per_reel": 40000,
        "top_languages": ["en"],
        "top_content_types": ["highlights", "meme_format", "fail_format"],
        "growth_potential": 7.0,
        "recommendation": "Максимальный охват, но самая жёсткая конкуренция. Фейлы/мемы — точка входа. Масштабируй выигрышные форматы.",
    },
    {
        "region": "Brazil/LATAM",
        "platform": "instagram",
        "audience_size": 18000000,
        "competition_level": "medium-low",
        "avg_views_per_reel": 35000,
        "top_languages": ["pt", "es"],
        "top_content_types": ["highlights", "reactions", "meme_format"],
        "growth_potential": 9.0,
        "recommendation": "СКРЫТЫЙ ГЕМ. Огромная CS2-база, низкая конкуренция. Португальский/испанский контент. Концепция AI-девушки здесь свежая. Максимальный потенциал роста.",
    },
    {
        "region": "Brazil/LATAM",
        "platform": "youtube_shorts",
        "audience_size": 22000000,
        "competition_level": "medium",
        "avg_views_per_reel": 45000,
        "top_languages": ["pt"],
        "top_content_types": ["highlights", "fragmovies", "reactions"],
        "growth_potential": 8.5,
        "recommendation": "YouTube — доминирующая платформа в Бразилии. CS2-контент собирает огромные просмотры. Португальский контент + субтитры = лёгкая победа.",
    },
    {
        "region": "Turkey/Middle East",
        "platform": "instagram",
        "audience_size": 10000000,
        "competition_level": "low",
        "avg_views_per_reel": 40000,
        "top_languages": ["tr", "ar"],
        "top_content_types": ["highlights", "reactions", "dramatic_clutch"],
        "growth_potential": 9.0,
        "recommendation": "Очень низкая конкуренция, высокий энгейджмент. Турецкая CS2-сцена очень активная. Эмоциональные/драматичные форматы работают отлично.",
    },
    {
        "region": "Southeast Asia",
        "platform": "youtube_shorts",
        "audience_size": 12000000,
        "competition_level": "low",
        "avg_views_per_reel": 30000,
        "top_languages": ["en", "id", "th"],
        "top_content_types": ["highlights", "meme_format", "fail_format"],
        "growth_potential": 8.0,
        "recommendation": "Растущий CS2-рынок. Английский контент работает. Мемы и фейлы дают максимальный энгейджмент. Низкая конкуренция = быстрый рост.",
    },
]


def get_recommended_pipeline(budget: str = "minimal") -> dict:
    """Get the recommended tool pipeline based on budget."""
    if budget == "minimal":
        return {
            "total_monthly_cost": "$0-30",
            "setup": "Free API tiers + Google Colab. Good quality, slow.",
            "image": {
                "tool": "Stable Diffusion XL + IP-Adapter",
                "where": "Google Colab free / Replicate free credits",
                "cost_per_image": "$0.00-0.02",
                "quality": "7/10",
            },
            "lip_sync": {
                "tool": "MuseTalk 1.5 (fast) or FantasyTalking (quality)",
                "where": "Google Colab / Replicate",
                "cost_per_video": "$0.05-0.15",
                "quality": "7/10",
            },
            "voice": {
                "tool": "Qwen3-TTS 0.6B",
                "where": "Local CPU (slow) or Colab GPU",
                "cost_per_audio": "$0.00",
                "quality": "8/10",
            },
            "video": {
                "tool": "Wan2.1-1.3B (8GB VRAM enough)",
                "where": "Google Colab or cheap RTX 4060",
                "cost_per_video": "$0.00-0.05",
                "quality": "7/10",
            },
            "orchestration": "Manual / Python scripts",
            "realism_rating": "6/10 — clearly AI-generated",
        }
    elif budget == "moderate":
        return {
            "total_monthly_cost": "$50-100",
            "setup": "API services (fal.ai + A2E + Kling). Best value for quality.",
            "image": {
                "tool": "Flux + PuLID (identity) + FaceFusion (swap)",
                "where": "fal.ai API / RunPod Serverless",
                "cost_per_image": "$0.01-0.03",
                "quality": "9/10",
            },
            "lip_sync": {
                "tool": "OmniHuman 1.5 via fal.ai ($0.16/s)",
                "where": "fal.ai API — best quality, single API call",
                "cost_per_video": "$1.60-4.80 (10-30s)",
                "quality": "10/10 — film-grade",
            },
            "voice": {
                "tool": "Qwen3-TTS 1.7B (open-source) or ElevenLabs ($5/mo)",
                "where": "Qwen3 on RunPod / ElevenLabs API",
                "cost_per_audio": "$0.005-0.03",
                "quality": "9.5/10",
            },
            "video": {
                "tool": "Kling 2.6 ($10/mo) — best photorealistic humans",
                "where": "Kling AI API or web platform",
                "cost_per_video": "$0.10-0.25",
                "quality": "9.5/10",
            },
            "orchestration": "Python automation + fal.ai webhooks",
            "realism_rating": "9/10 — indistinguishable from real at first glance",
        }
    elif budget == "full":
        return {
            "total_monthly_cost": "$150-300",
            "setup": "Premium APIs + dedicated GPU for heavy tasks. Maximum quality.",
            "image": {
                "tool": "Flux + PuLID + FaceFusion + Runway Gen-4.5",
                "where": "fal.ai + dedicated GPU (Vast.ai A100 $0.52/hr)",
                "cost_per_image": "$0.01-0.05",
                "quality": "10/10",
            },
            "lip_sync": {
                "tool": "OmniHuman 1.5 (primary) + HeyGen Avatar IV (backup)",
                "where": "fal.ai API + HeyGen ($24/mo)",
                "cost_per_video": "$1.60-4.80",
                "quality": "10/10 — indistinguishable from real human",
            },
            "voice": {
                "tool": "ElevenLabs v3 (primary) + Qwen3-TTS 1.7B (bulk)",
                "where": "ElevenLabs API ($22/mo Starter) + RunPod",
                "cost_per_audio": "$0.01-0.03",
                "quality": "10/10",
            },
            "video": {
                "tool": "Runway Gen-4.5 ($15/mo) + Kling 2.6 ($10/mo)",
                "where": "Runway API + Kling API",
                "cost_per_video": "$0.15-0.50",
                "quality": "10/10",
            },
            "orchestration": "ComfyUI on GPU server + API automation",
            "realism_rating": "10/10 — viewers cannot tell it's AI",
        }
    else:  # "uncensored" — for private channel content
        return {
            "total_monthly_cost": "$60-120",
            "setup": "A2E uncensored API + self-hosted models. No content filters.",
            "image": {
                "tool": "Flux + PuLID (self-hosted, no filters)",
                "where": "RunPod/Vast.ai dedicated GPU",
                "cost_per_image": "$0.003-0.01",
                "quality": "9/10",
            },
            "lip_sync": {
                "tool": "A2E AI API ($9.9/mo, uncensored) + MuseTalk (self-hosted)",
                "where": "A2E API + dedicated GPU",
                "cost_per_video": "$0.02/s (A2E) or $0.04 self-hosted",
                "quality": "8.5/10",
            },
            "voice": {
                "tool": "Qwen3-TTS 1.7B (self-hosted, no restrictions)",
                "where": "Dedicated GPU or RunPod",
                "cost_per_audio": "$0.001-0.005",
                "quality": "9.5/10",
            },
            "video": {
                "tool": "Wan2.1-14B + SkyReels V1 (self-hosted, no filters)",
                "where": "Vast.ai A100 $0.52/hr",
                "cost_per_video": "$0.06-0.12",
                "quality": "9/10",
            },
            "orchestration": "ComfyUI with full automation + A2E MCP server",
            "realism_rating": "9/10 — high quality without content restrictions",
        }
