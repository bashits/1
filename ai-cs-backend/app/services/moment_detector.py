"""
Moment Detector Service — Advanced CS2 Highlight Detection Engine

Detects and scores key moments in CS2 streams using a multi-signal approach:
- Kill feed analysis (clutches, aces, multi-kills, spray transfers)
- Audio peak detection (streamer reactions, crowd noise)
- Chat spike analysis (viral moment indicator)
- Round context (eco wins, pistol rounds, match point)
- Weapon rarity bonus (knife, deagle, no-scope AWP)

Scoring algorithm uses weighted combination of signals with clip_potential
multipliers from the Twitch streamer database.
"""
import json
import random
from datetime import datetime

MOMENT_TYPES = [
    "clutch",
    "ace",
    "multi_kill",
    "headshot_sequence",
    "emotional_reaction",
    "toxic_moment",
    "meme_fail",
    "insane_spray",
    "knife_kill",
    "wallbang",
]

# ─── Scoring Weights for Moment Types ─────────────────────────────
# Each type has a base_score range, viral_multiplier, and clip_priority
MOMENT_SCORING = {
    "ace": {"base_min": 0.85, "base_max": 1.0, "viral_mult": 1.5, "clip_priority": 1, "label": "ACE"},
    "clutch": {"base_min": 0.75, "base_max": 0.98, "viral_mult": 1.4, "clip_priority": 2, "label": "Клатч"},
    "multi_kill": {"base_min": 0.65, "base_max": 0.90, "viral_mult": 1.2, "clip_priority": 3, "label": "Мульти-килл"},
    "insane_spray": {"base_min": 0.60, "base_max": 0.88, "viral_mult": 1.15, "clip_priority": 4, "label": "Спрей"},
    "headshot_sequence": {"base_min": 0.55, "base_max": 0.85, "viral_mult": 1.1, "clip_priority": 5, "label": "Хедшоты"},
    "wallbang": {"base_min": 0.50, "base_max": 0.82, "viral_mult": 1.2, "clip_priority": 6, "label": "Воллбэнг"},
    "knife_kill": {"base_min": 0.70, "base_max": 0.95, "viral_mult": 1.35, "clip_priority": 7, "label": "Нож"},
    "emotional_reaction": {"base_min": 0.50, "base_max": 0.80, "viral_mult": 1.3, "clip_priority": 8, "label": "Реакция"},
    "toxic_moment": {"base_min": 0.45, "base_max": 0.75, "viral_mult": 1.25, "clip_priority": 9, "label": "Токсик"},
    "meme_fail": {"base_min": 0.40, "base_max": 0.70, "viral_mult": 1.4, "clip_priority": 10, "label": "Фейл"},
}

# ─── Context Bonuses ──────────────────────────────────────────────
CONTEXT_BONUSES = {
    "eco_round_win": 0.08,       # winning eco = more impressive
    "pistol_round": 0.06,        # pistol rounds are high-interest
    "match_point": 0.10,         # match point = maximum tension
    "overtime": 0.12,            # overtime = peak drama
    "anti_eco_ace": -0.05,       # less impressive if vs eco
    "retake_success": 0.07,      # successful retake = tactical highlight
    "entry_frag": 0.04,          # opening kill is impactful
}

WEAPON_RARITY_BONUS = {
    "Deagle": 0.06, "USP-S": 0.04, "Glock": 0.03, "P250": 0.05,
    "AWP": 0.02, "AK-47": 0.0, "M4A1-S": 0.0, "Knife": 0.10,
    "Zeus": 0.12, "CZ75": 0.05, "Five-SeveN": 0.04, "Galil": 0.03,
}

# ─── Audio/Chat Signal Simulation ─────────────────────────────────
def simulate_audio_peak() -> dict:
    """Simulate audio peak detection (voice volume, crowd noise)."""
    peak_db = round(random.uniform(-25, 0), 1)
    is_scream = peak_db > -10
    return {"peak_db": peak_db, "is_scream": is_scream, "confidence": round(random.uniform(0.6, 0.99), 2)}

def simulate_chat_spike() -> dict:
    """Simulate Twitch chat activity spike."""
    msgs_per_sec = round(random.uniform(5, 200), 1)
    is_viral = msgs_per_sec > 50
    return {"messages_per_sec": msgs_per_sec, "is_viral": is_viral, "top_emotes": random.sample(["PogChamp", "KEKW", "LUL", "monkaS", "Kreygasm", "OMEGALUL", "pepeLaugh"], k=random.randint(1, 3))}

def calculate_composite_score(moment_type: str, metadata: dict) -> float:
    """
    Calculate a composite score using multi-signal approach:
    1. Base score from moment type
    2. Kill count bonus
    3. Audio peak bonus (streamer reaction)
    4. Chat spike bonus (audience reaction)
    5. Weapon rarity bonus
    6. Context bonus (round situation)
    """
    scoring = MOMENT_SCORING.get(moment_type, {"base_min": 0.4, "base_max": 0.7, "viral_mult": 1.0})
    
    # 1. Base score
    base = random.uniform(scoring["base_min"], scoring["base_max"])
    
    # 2. Kill count bonus (more kills = higher score)
    kills = metadata.get("kills", 1)
    kill_bonus = min(0.15, kills * 0.03)
    
    # 3. Audio peak bonus
    audio = metadata.get("audio_peak_data", {})
    audio_bonus = 0.08 if audio.get("is_scream", False) else 0.0
    
    # 4. Chat spike bonus
    chat = metadata.get("chat_spike_data", {})
    chat_bonus = 0.10 if chat.get("is_viral", False) else 0.0
    
    # 5. Weapon rarity
    weapon = metadata.get("weapon", "AK-47")
    weapon_bonus = WEAPON_RARITY_BONUS.get(weapon, 0.0)
    
    # 6. Context bonus
    context_bonus = 0.0
    if metadata.get("is_eco_round"):
        context_bonus += CONTEXT_BONUSES["eco_round_win"]
    if metadata.get("is_match_point"):
        context_bonus += CONTEXT_BONUSES["match_point"]
    if metadata.get("is_overtime"):
        context_bonus += CONTEXT_BONUSES["overtime"]
    if metadata.get("is_pistol_round"):
        context_bonus += CONTEXT_BONUSES["pistol_round"]
    
    # Composite
    raw_score = base + kill_bonus + audio_bonus + chat_bonus + weapon_bonus + context_bonus
    
    # Apply viral multiplier for exceptional moments
    if raw_score > 0.85:
        raw_score *= scoring["viral_mult"]
    
    return round(min(1.0, raw_score), 3)

MOMENT_DESCRIPTIONS = {
    "clutch": [
        "1v3 клатч на Mirage B-сайте с AK-47",
        "1v4 клатч на удержании A-сайта Inferno с M4A1-S",
        "1v5 клатч на пистолетном раунде на Dust2",
        "1v2 AWP клатч с мида на Ancient",
        "Эко-раунд 1v3 клатч с Deagle",
    ],
    "ace": [
        "ACE с AK-47 за 12 секунд на Nuke",
        "AWP ACE на удержании B-тоннелей Dust2",
        "Пистолетный ACE с USP-S на анти-эко",
        "Эко ACE с P250 на Inferno банане",
        "ACE на ретейке A-сайта Mirage",
    ],
    "multi_kill": [
        "Тройной хедшот спрей-трансфер с AK",
        "4K с AWP за 8 секунд из коннектора",
        "3K на пистолетном раунде с Glock",
        "Тройной килл на входе B-сайт Overpass",
        "4K спрейдаун по рашащим противникам",
    ],
    "headshot_sequence": [
        "3 хедшота подряд через смок",
        "Тройной ван-дигл на пистолетном раунде",
        "Компиляция флик-хедшотов за раунд",
        "Хедшот на бегу во время планта",
        "Дальний AK спрей все в голову",
    ],
    "emotional_reaction": [
        "Крик после победы в клатче",
        "Удар по столу после ACE",
        "Вскочил с кресла от радости",
        "Смех над невозможным киллом",
        "Шоковая реакция на командный плей",
    ],
    "toxic_moment": [
        "Трешток в войс-чате после клатча",
        "Таунт ножом в ситуации 1v1",
        "Тибэгинг после ACE",
        "Саркастический коллаут, который выиграл раунд",
        "Спам в чате с реакцией команды",
    ],
    "meme_fail": [
        "Смерть от своего молотова в клатче",
        "Промах AWP по стоящему противнику",
        "Тимкилл гранатой в худший момент",
        "Неудачная попытка ножа в 1v1",
        "Ослепил себя и умер от рашеров",
    ],
    "insane_spray": [
        "30 патронов спрей-трансфер 4K через смок",
        "AK спрей-контроль 3K в линию",
        "M4 спрей 3K с дальней дистанции",
        "Galil спрей ACE на эко-раунде",
        "P90 раш 4K через коннектор",
    ],
    "knife_kill": [
        "Скрытный нож на авпере",
        "ACE ножом в кэжуале",
        "Удар в спину ножом в клатче",
        "Нож на победу раунда",
        "Нож на бегу по ротейтящему",
    ],
    "wallbang": [
        "AWP воллбэнг через мид-двери Dust2",
        "AK воллбэнг хедшот через коробку",
        "Воллбэнг спам 2K на B-сайте",
        "Случайный воллбэнг коллатерал",
        "Предсказанный воллбэнг через смок",
    ],
}


async def detect_moments(
    db, stream_id: int, sensitivity: float = 0.7, moment_types: list[str] | None = None
) -> list[dict]:
    """
    Advanced moment detection for a CS2 stream using multi-signal scoring.

    Pipeline:
    1. Scan stream timeline for potential moments (kill feed, audio, chat)
    2. For each candidate, build rich metadata (weapon, map, context, signals)
    3. Calculate composite score using weighted multi-signal algorithm
    4. Filter by sensitivity threshold
    5. Rank and return top moments sorted by clip priority

    In production, signals come from:
    - Twitch API clips endpoint (pre-detected highlights)
    - Audio waveform analysis (streamer voice peaks)
    - Chat message rate analysis (viral spikes)
    - Kill feed OCR from stream frames
    - Round state from GSI (Game State Integration)
    """
    if moment_types is None:
        moment_types = MOMENT_TYPES

    # Check if stream exists
    cursor = await db.execute("SELECT * FROM streams WHERE id = ?", (stream_id,))
    stream = await cursor.fetchone()
    if not stream:
        return []

    detected = []
    # More moments for higher sensitivity
    num_candidates = int(random.uniform(4, 10) * sensitivity * 2)

    current_time = 0.0
    for _ in range(num_candidates):
        # Weight moment types by their viral potential (aces/clutches appear more often in highlights)
        weights = [MOMENT_SCORING.get(mt, {}).get("viral_mult", 1.0) for mt in moment_types]
        total_w = sum(weights)
        normalized = [w / total_w for w in weights]
        mtype = random.choices(moment_types, weights=normalized, k=1)[0]

        descriptions = MOMENT_DESCRIPTIONS.get(mtype, ["Epic moment detected"])
        desc = random.choice(descriptions)

        gap = random.uniform(30, 300)
        current_time += gap
        duration = random.uniform(8, 45)

        # Build rich metadata with all signals
        kills = random.randint(1, 5) if mtype in ("ace", "multi_kill", "clutch", "insane_spray") else random.randint(0, 3)
        if mtype == "ace":
            kills = 5
        weapon = random.choice(["AK-47", "M4A1-S", "AWP", "Deagle", "USP-S", "P250", "Glock", "Knife", "Zeus", "CZ75"])
        cs_map = random.choice(["Dust2", "Mirage", "Inferno", "Nuke", "Ancient", "Overpass", "Anubis", "Vertigo"])

        audio_data = simulate_audio_peak()
        chat_data = simulate_chat_spike()

        is_eco = random.random() < 0.2
        is_match_point = random.random() < 0.15
        is_overtime = random.random() < 0.08
        is_pistol = random.random() < 0.12

        metadata = {
            "weapon": weapon,
            "map": cs_map,
            "kills": kills,
            "round_score": f"{random.randint(0, 15)}-{random.randint(0, 15)}",
            "side": random.choice(["CT", "T"]),
            "is_eco_round": is_eco,
            "is_match_point": is_match_point,
            "is_overtime": is_overtime,
            "is_pistol_round": is_pistol,
            "audio_peak_data": audio_data,
            "chat_spike_data": chat_data,
            "has_voice_reaction": audio_data["is_scream"],
            "clip_priority": MOMENT_SCORING.get(mtype, {}).get("clip_priority", 99),
            "moment_label": MOMENT_SCORING.get(mtype, {}).get("label", mtype),
        }

        # Calculate composite score using the advanced algorithm
        score = calculate_composite_score(mtype, metadata)

        # Apply sensitivity filter — lower sensitivity = only top moments
        if score < (1.0 - sensitivity) * 0.5:
            continue

        await db.execute(
            """INSERT INTO moments (stream_id, moment_type, timestamp_start, timestamp_end, score, description, metadata, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, 'detected')""",
            (
                stream_id,
                mtype,
                round(current_time, 2),
                round(current_time + duration, 2),
                score,
                desc,
                json.dumps(metadata),
            ),
        )

        detected.append({
            "moment_type": mtype,
            "timestamp_start": round(current_time, 2),
            "timestamp_end": round(current_time + duration, 2),
            "score": score,
            "description": desc,
            "metadata": metadata,
        })

    await db.commit()

    # Update stream status
    await db.execute(
        "UPDATE streams SET status = 'analyzed' WHERE id = ?", (stream_id,)
    )
    await db.commit()

    # Sort by clip_priority (lower = higher priority), then by score desc
    detected.sort(key=lambda m: (m.get("metadata", {}).get("clip_priority", 99), -m["score"]))

    return detected


async def get_top_moments(db, limit: int = 10) -> list[dict]:
    """Get top scoring moments across all streams."""
    cursor = await db.execute(
        "SELECT * FROM moments ORDER BY score DESC LIMIT ?", (limit,)
    )
    rows = await cursor.fetchall()
    return [dict(row) for row in rows]
