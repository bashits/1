"""Smart Prompt Interpreter — understands casual Russian text and builds pro-level EN prompts.

The user writes in their own words (Russian), like:
  "красное платье на пляже"
  "в спортзале в топике"
  "селфи в кафе с кофе"
  "дома на кровати в пижаме"

The system:
1. Detects clothing, location, pose, mood, lighting from the text
2. Maps Russian keywords to precise English photography terms
3. Builds a complete professional prompt with all realism boosters
4. Returns structured data: {prompt, content_type, detected}
"""

import re
from typing import Optional


# ═══════════════════════════════════════════════════════════════════════
# RUSSIAN → ENGLISH VOCABULARY MAPPINGS
# ═══════════════════════════════════════════════════════════════════════

# --- Clothing ---
CLOTHING_MAP = {
    # Dresses
    "платье": "dress", "платьe": "dress",
    "красное платье": "elegant red dress",
    "черное платье": "little black dress",
    "белое платье": "white summer dress",
    "вечернее платье": "glamorous evening gown",
    "короткое платье": "short cocktail dress",
    "длинное платье": "long flowing dress",
    "летнее платье": "light summer sundress",
    "мини платье": "mini dress",
    # Tops
    "топик": "crop top", "топ": "crop top", "кроп топ": "crop top",
    "майка": "tank top", "футболка": "casual t-shirt",
    "блузка": "elegant blouse", "рубашка": "button-up shirt",
    "худи": "oversized hoodie", "толстовка": "cozy sweatshirt",
    "свитер": "knit sweater", "водолазка": "turtleneck sweater",
    "корсет": "corset top",
    # Bottoms
    "джинсы": "jeans", "шорты": "denim shorts",
    "юбка": "skirt", "мини юбка": "mini skirt",
    "леггинсы": "leggings", "штаны": "pants",
    # Swimwear
    "бикини": "bikini", "купальник": "swimsuit",
    "раздельный купальник": "two-piece bikini",
    # Lingerie
    "белье": "lingerie", "нижнее белье": "lace lingerie set",
    "кружевное белье": "elegant lace lingerie",
    "пижама": "silk pajamas", "халат": "silk robe",
    # Sports
    "спортивная форма": "sports bra and leggings",
    "спортивный топ": "sports bra",
    "лосины": "yoga leggings",
    # Outerwear
    "куртка": "leather jacket", "пальто": "elegant coat",
    "шуба": "fur coat",
    # Accessories
    "шляпа": "sun hat", "очки": "sunglasses",
    "украшения": "elegant jewelry", "серьги": "earrings",
    "колье": "necklace", "часы": "luxury watch",
    # Gaming
    "наушники": "gaming headset", "геймерская одежда": "gaming hoodie",
}

# --- Locations ---
LOCATION_MAP = {
    # Beach / Pool
    "пляж": "tropical sandy beach, ocean waves, golden sunset light",
    "на пляже": "tropical sandy beach, ocean waves, golden sunset light",
    "море": "seaside, turquoise water, bright sunlight",
    "на море": "seaside cliff with ocean view, bright sunlight",
    "бассейн": "luxury infinity pool, tropical resort, turquoise water",
    "у бассейна": "luxury infinity pool, palm trees, bright sunlight",
    "океан": "ocean beach, dramatic waves, golden hour",
    # Urban
    "город": "modern city street, urban background, evening lights",
    "улица": "city street, urban background, natural daylight",
    "крыша": "luxury rooftop terrace, city skyline at sunset",
    "на крыше": "rooftop bar, city panorama, golden hour light",
    "мост": "iconic bridge, city lights, evening atmosphere",
    # Indoor
    "дом": "luxury modern apartment, soft natural window light",
    "дома": "cozy luxury apartment interior, warm natural lighting",
    "кровать": "luxury bedroom, white silk sheets, soft morning light from window",
    "на кровати": "luxury bedroom, plush bed with silk sheets, warm morning light",
    "ванна": "luxury marble bathroom, soft warm lighting, steam",
    "в ванной": "luxury marble bathroom, vanity mirror lights",
    "кухня": "modern bright kitchen, morning light, clean aesthetic",
    "диван": "luxury living room, velvet sofa, soft ambient lighting",
    # Food & Drink
    "кафе": "aesthetic modern cafe, large windows with natural light, coffee shop ambiance",
    "в кафе": "trendy cafe interior, warm tones, natural daylight through windows",
    "ресторан": "luxury restaurant, warm candlelight, elegant interior",
    "в ресторане": "upscale restaurant, intimate atmosphere, soft warm lighting",
    "бар": "stylish cocktail bar, moody lighting, neon accents",
    # Nature
    "парк": "beautiful park, golden hour sunlight, bokeh green foliage",
    "в парке": "lush green park, dappled sunlight through trees, natural environment",
    "лес": "enchanted forest, rays of light through canopy, misty atmosphere",
    "поле": "flower field, golden hour, warm breeze",
    "горы": "mountain landscape, dramatic scenery, epic vista",
    "сад": "blooming garden, colorful flowers, soft natural light",
    # Travel
    "отель": "luxury 5-star hotel room, panoramic view, elegant interior",
    "яхта": "luxury yacht deck, ocean view, bright sunlight, blue sky",
    "на яхте": "luxury yacht, turquoise sea, sunny day, wind in hair",
    "самолет": "private jet interior, luxury seats, champagne",
    "аэропорт": "modern airport terminal, stylish travel outfit",
    # Sports
    "спортзал": "modern gym, professional fitness equipment, dramatic lighting",
    "в спортзале": "upscale gym, weight training area, motivational atmosphere",
    "зал": "fitness studio, mirrors, professional gym lighting",
    "йога": "serene yoga studio, natural light, minimal aesthetic",
    # Studio
    "студия": "professional photography studio, clean white background, controlled lighting",
    "в студии": "high-end photography studio, professional lighting setup",
    # Gaming
    "за компом": "RGB-lit gaming setup, dual monitors, screen glow on face",
    "компьютер": "gaming desk setup, RGB lighting, multiple monitors",
    "стрим": "streaming setup, ring light, gaming room, RGB ambiance",
}

# --- Poses / Actions ---
POSE_MAP = {
    "сидит": "sitting in elegant pose",
    "стоит": "standing in confident pose",
    "лежит": "lying down in relaxed natural pose",
    "идет": "walking naturally, candid movement",
    "гуляет": "walking casually, candid street style",
    "бежит": "jogging, athletic movement",
    "танцует": "dancing, dynamic movement",
    "смотрит": "looking at camera with direct eye contact",
    "смеется": "laughing genuinely, natural joy",
    "улыбается": "soft natural smile, warm expression",
    "селфи": "taking selfie, phone in hand, selfie angle from slightly above",
    "зеркало": "mirror selfie, phone visible, bathroom mirror",
    "позирует": "posing confidently for camera",
    "обнимает": "hugging pose, warm intimate gesture",
    "держит": "holding",
    "пьет": "drinking",
    "ест": "eating",
    "читает": "reading, thoughtful expression",
    "работает": "working, focused expression",
    "играет": "playing games, focused on screen",
    "спит": "sleeping peacefully, eyes closed",
    "думает": "thoughtful expression, hand on chin",
    "флиртует": "flirty expression, playful look at camera",
    "грустит": "melancholic mood, contemplative",
    "злится": "fierce expression, intense look",
    "удивлена": "surprised expression, wide eyes",
    "кричит": "excited shouting, open mouth, energetic",
}

# --- Mood / Atmosphere ---
MOOD_MAP = {
    "романтик": "romantic atmosphere, soft warm tones, dreamy",
    "романтика": "romantic atmosphere, soft warm tones, dreamy bokeh",
    "сексуально": "sensual mood, dramatic lighting, intimate atmosphere",
    "секси": "sensual elegant pose, alluring atmosphere",
    "мило": "cute aesthetic, soft pastel tones, sweet vibe",
    "милая": "cute sweet expression, soft light",
    "дерзко": "bold confident attitude, sharp look",
    "дерзкая": "fierce confident expression, power pose",
    "нежно": "tender gentle mood, soft diffused light",
    "нежная": "gentle soft expression, delicate",
    "жестко": "edgy dark mood, dramatic shadows",
    "элегантно": "sophisticated elegant style, refined",
    "элегантная": "refined elegant look, graceful",
    "спортивно": "athletic energetic vibe, dynamic",
    "уютно": "cozy warm atmosphere, soft lighting",
    "уютная": "cozy comfortable setting, warm tones",
    "весело": "fun cheerful mood, bright colors, energy",
    "грустно": "melancholic mood, muted tones, thoughtful",
    "загадочно": "mysterious atmosphere, dramatic shadows, enigmatic",
    "ярко": "vibrant colorful setting, bold tones",
    "темно": "dark moody atmosphere, low key lighting",
    "светло": "bright airy setting, high key lighting",
}

# --- Props / Objects ---
PROPS_MAP = {
    "кофе": "holding coffee cup",
    "вино": "glass of red wine",
    "шампанское": "champagne glass",
    "коктейль": "cocktail drink",
    "телефон": "smartphone in hand",
    "цветы": "bouquet of flowers",
    "роза": "holding a red rose",
    "книга": "holding a book",
    "сумка": "designer handbag",
    "сигарета": "cigarette",
    "зонт": "umbrella",
    "мороженое": "ice cream cone",
    "подарок": "gift box",
    "камера": "camera in hand",
    "мяч": "sports ball",
    "наушники": "wearing headphones",
    "маска": "face mask",
    "шарф": "silk scarf",
}

# --- Time of Day / Lighting ---
LIGHTING_MAP = {
    "закат": "golden hour sunset light, warm orange tones",
    "рассвет": "early morning golden light, soft pink sky",
    "ночь": "nighttime, city lights, neon glow",
    "ночью": "nighttime urban setting, artificial lights, moody",
    "утро": "soft morning light, fresh bright atmosphere",
    "утром": "morning natural light, dewy fresh look",
    "день": "bright daylight, natural midday sun",
    "вечер": "warm evening light, golden hour atmosphere",
    "вечером": "evening atmosphere, warm ambient lighting",
    "неон": "neon lights, cyberpunk atmosphere, colorful glow",
    "свечи": "candlelight, warm intimate glow, romantic",
    "студийный свет": "professional studio lighting, controlled setup",
    "дождь": "rainy atmosphere, wet surfaces reflecting light, moody",
    "снег": "snowy winter setting, cold blue tones, frost",
}

# --- Colors (for clothes that just mention color) ---
COLOR_MAP = {
    "красный": "red", "красная": "red", "красное": "red", "красном": "red",
    "черный": "black", "черная": "black", "черное": "black", "черном": "black",
    "белый": "white", "белая": "white", "белое": "white", "белом": "white",
    "синий": "blue", "синяя": "blue", "синее": "blue", "синем": "blue",
    "розовый": "pink", "розовая": "pink", "розовое": "pink",
    "зеленый": "green", "зеленая": "green", "зеленое": "green",
    "золотой": "gold", "золотая": "gold", "золотое": "gold",
    "серебряный": "silver", "серебряная": "silver",
    "фиолетовый": "purple", "фиолетовая": "purple",
    "оранжевый": "orange", "оранжевая": "orange",
    "бежевый": "beige", "бежевая": "beige",
    "леопардовый": "leopard print", "леопардовая": "leopard print",
}

# --- Content type detection ---
CONTENT_TYPE_HINTS = {
    "селфи": "selfie",
    "зеркало": "selfie_mirror",
    "портрет": "portrait",
    "в полный рост": "full_body",
    "фулл боди": "full_body",
    "пляж": "bikini_beach",
    "бикини": "bikini_beach",
    "купальник": "bikini_beach",
    "бассейн": "pool_luxury",
    "белье": "intimate_lingerie",
    "нижнее белье": "intimate_lingerie",
    "кровать": "intimate_cozy",
    "пижама": "intimate_cozy",
    "спортзал": "fitness_gym",
    "зал": "fitness_gym",
    "кафе": "morning_coffee",
    "ресторан": "wine_evening",
    "вино": "wine_evening",
    "крыша": "instagram_lifestyle",
    "стрим": "gaming_reaction",
    "наушники": "gaming_reaction",
    "компьютер": "gaming_chill",
    "путешествие": "travel_exotic",
    "отпуск": "travel_exotic",
    "фитнес": "fitness_gym",
    "йога": "fitness_gym",
}


# ═══════════════════════════════════════════════════════════════════════
# CORE INTERPRETER
# ═══════════════════════════════════════════════════════════════════════

def interpret_prompt(
    user_text: str,
    appearance: Optional[dict] = None,
    trigger_word: Optional[str] = None,
) -> dict:
    """Interpret casual Russian text into a professional English generation prompt.

    Args:
        user_text: Casual Russian text like "красное платье на пляже"
        appearance: Profile appearance dict (ethnicity, hair, eyes, etc.)
        trigger_word: LoRA trigger word for face consistency

    Returns:
        {
            "prompt": "full English prompt with realism boosters",
            "content_type": "detected content type for scene selection",
            "detected": {
                "clothing": [...],
                "location": "...",
                "pose": "...",
                "mood": "...",
                "props": [...],
                "lighting": "...",
            },
            "original_text": "user's original Russian text",
        }
    """
    text = user_text.lower().strip()
    detected = {
        "clothing": [],
        "location": None,
        "pose": None,
        "mood": None,
        "props": [],
        "lighting": None,
        "colors": [],
    }

    # --- Detect all elements ---

    # Clothing (check multi-word first, then single-word)
    clothing_parts = []
    for ru, en in sorted(CLOTHING_MAP.items(), key=lambda x: -len(x[0])):
        if ru in text:
            clothing_parts.append(en)
            detected["clothing"].append(ru)
            text = text.replace(ru, " ", 1)
            break  # Take the best match only for main clothing

    # Detect additional clothing items
    remaining_text = text
    for ru, en in sorted(CLOTHING_MAP.items(), key=lambda x: -len(x[0])):
        if ru in remaining_text and en not in clothing_parts:
            clothing_parts.append(en)
            if ru not in detected["clothing"]:
                detected["clothing"].append(ru)
            remaining_text = remaining_text.replace(ru, " ", 1)

    # Location
    for ru, en in sorted(LOCATION_MAP.items(), key=lambda x: -len(x[0])):
        if ru in user_text.lower():
            detected["location"] = en
            break

    # Pose / Action
    for ru, en in sorted(POSE_MAP.items(), key=lambda x: -len(x[0])):
        if ru in user_text.lower():
            detected["pose"] = en
            break

    # Mood
    for ru, en in sorted(MOOD_MAP.items(), key=lambda x: -len(x[0])):
        if ru in user_text.lower():
            detected["mood"] = en
            break

    # Props
    for ru, en in sorted(PROPS_MAP.items(), key=lambda x: -len(x[0])):
        if ru in user_text.lower():
            detected["props"].append(en)

    # Lighting
    for ru, en in sorted(LIGHTING_MAP.items(), key=lambda x: -len(x[0])):
        if ru in user_text.lower():
            detected["lighting"] = en
            break

    # Colors
    for ru, en in sorted(COLOR_MAP.items(), key=lambda x: -len(x[0])):
        if ru in user_text.lower():
            if en not in detected["colors"]:
                detected["colors"].append(en)

    # --- Detect content type ---
    content_type = "portrait"  # default
    for ru, ct in sorted(CONTENT_TYPE_HINTS.items(), key=lambda x: -len(x[0])):
        if ru in user_text.lower():
            content_type = ct
            break

    # --- Build identity block ---
    app = appearance or {}
    age = app.get("age", app.get("age_range", "23"))
    ethnicity = app.get("ethnicity", "european")
    hair_color = app.get("hair_color", "dark blonde")
    hair_style = app.get("hair_style", "long wavy")
    eye_color = app.get("eye_color", "green")
    skin_tone = app.get("skin_tone", "fair")
    body_type = app.get("body_type", "slim fit")

    identity_parts = []
    if trigger_word:
        identity_parts.append(trigger_word)
    identity_parts.append(
        f"{age} year old {ethnicity} woman, "
        f"{hair_color} {hair_style} hair, {eye_color} eyes, {skin_tone} skin, {body_type} body"
    )

    # --- Build scene description ---
    scene_parts = []

    # Clothing
    if clothing_parts:
        # Apply detected colors to clothing
        if detected["colors"] and clothing_parts:
            colored_clothing = f"{detected['colors'][0]} {clothing_parts[0]}"
            scene_parts.append(f"wearing {colored_clothing}")
            for extra in clothing_parts[1:]:
                scene_parts.append(extra)
        else:
            scene_parts.append(f"wearing {clothing_parts[0]}")
            for extra in clothing_parts[1:]:
                scene_parts.append(extra)

    # Location
    if detected["location"]:
        scene_parts.append(detected["location"])

    # Pose
    if detected["pose"]:
        scene_parts.append(detected["pose"])

    # Props
    for prop in detected["props"][:3]:  # Max 3 props
        scene_parts.append(prop)

    # Mood
    if detected["mood"]:
        scene_parts.append(detected["mood"])

    # Lighting
    if detected["lighting"]:
        scene_parts.append(detected["lighting"])

    # --- Realism block (always appended) — maximum quality ---
    realism = (
        "RAW photo, shot on Sony A7IV 85mm f/1.4 GM, natural skin texture with visible pores "
        "and micro-imperfections, subsurface scattering on skin, individual hair strands visible, "
        "real catchlight reflections in eyes, shallow depth of field with natural bokeh, "
        "professional color grading with lifted blacks, subtle film grain, "
        "no airbrushing, no plastic skin, no beauty filter, "
        "photojournalistic quality, editorial magazine photography, "
        "ultra detailed 8K UHD, natural ambient occlusion, micro-contrast"
    )

    # --- Assemble final prompt ---
    prompt = ", ".join(identity_parts)
    if scene_parts:
        prompt += ", " + ", ".join(scene_parts)
    prompt += f", {realism}"

    return {
        "prompt": prompt,
        "content_type": content_type,
        "detected": detected,
        "original_text": user_text,
    }


def is_russian_text(text: str) -> bool:
    """Check if text contains Cyrillic characters (Russian input)."""
    return bool(re.search(r'[а-яА-ЯёЁ]', text))


def smart_prompt(
    user_text: str,
    appearance: Optional[dict] = None,
    trigger_word: Optional[str] = None,
) -> str:
    """Shortcut: interpret Russian text and return just the prompt string.

    If the text is already in English, return it as-is with realism boosters.
    """
    if is_russian_text(user_text):
        result = interpret_prompt(user_text, appearance, trigger_word)
        return result["prompt"]
    else:
        # English text — just add trigger word and realism
        parts = []
        if trigger_word:
            parts.append(trigger_word)
        parts.append(user_text)
        realism = (
            "RAW photo, shot on Sony A7IV 85mm f/1.4 GM, natural skin texture with visible pores "
            "and micro-imperfections, subsurface scattering on skin, individual hair strands visible, "
            "real catchlight reflections in eyes, shallow depth of field with natural bokeh, "
            "professional color grading with lifted blacks, subtle film grain, "
            "no airbrushing, no plastic skin, no beauty filter, "
            "photojournalistic quality, editorial magazine photography, "
            "ultra detailed 8K UHD, natural ambient occlusion, micro-contrast"
        )
        parts.append(realism)
        return ", ".join(parts)
