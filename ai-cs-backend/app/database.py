import aiosqlite
import os
import json
from datetime import datetime

DB_PATH = os.environ.get("DB_PATH", "/data/app.db")

# Fallback for local dev
if not os.path.exists(os.path.dirname(DB_PATH)) and DB_PATH.startswith("/data"):
    DB_PATH = os.path.join(os.path.dirname(__file__), "..", "app.db")


async def get_db():
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")
    try:
        yield db
    finally:
        await db.close()


async def init_db():
    db = await aiosqlite.connect(DB_PATH)
    await db.execute("PRAGMA journal_mode=WAL")
    await db.execute("PRAGMA foreign_keys=ON")

    await db.executescript("""
    CREATE TABLE IF NOT EXISTS streams (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        platform TEXT NOT NULL DEFAULT 'twitch',
        url TEXT,
        streamer_name TEXT NOT NULL,
        started_at TEXT,
        ended_at TEXT,
        status TEXT NOT NULL DEFAULT 'pending',
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS moments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        stream_id INTEGER,
        moment_type TEXT NOT NULL,
        timestamp_start REAL NOT NULL DEFAULT 0,
        timestamp_end REAL NOT NULL DEFAULT 0,
        score REAL NOT NULL DEFAULT 0.0,
        description TEXT,
        metadata TEXT DEFAULT '{}',
        status TEXT NOT NULL DEFAULT 'detected',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (stream_id) REFERENCES streams(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS templates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        format_type TEXT NOT NULL,
        description TEXT,
        config TEXT NOT NULL DEFAULT '{}',
        is_active INTEGER NOT NULL DEFAULT 1,
        weight REAL NOT NULL DEFAULT 1.0,
        total_clips INTEGER NOT NULL DEFAULT 0,
        avg_retention REAL NOT NULL DEFAULT 0.0,
        avg_ctr REAL NOT NULL DEFAULT 0.0,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS clips (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        moment_id INTEGER,
        template_id INTEGER,
        ab_test_id INTEGER,
        title TEXT NOT NULL,
        description TEXT,
        format_type TEXT NOT NULL,
        duration REAL NOT NULL DEFAULT 0.0,
        status TEXT NOT NULL DEFAULT 'draft',
        hook_text TEXT,
        cta_text TEXT,
        has_ai_girl INTEGER NOT NULL DEFAULT 0,
        has_subtitles INTEGER NOT NULL DEFAULT 0,
        has_face_cam INTEGER NOT NULL DEFAULT 0,
        file_path TEXT,
        thumbnail_path TEXT,
        platform TEXT,
        published_at TEXT,
        views INTEGER NOT NULL DEFAULT 0,
        likes INTEGER NOT NULL DEFAULT 0,
        comments INTEGER NOT NULL DEFAULT 0,
        shares INTEGER NOT NULL DEFAULT 0,
        ctr REAL NOT NULL DEFAULT 0.0,
        retention_rate REAL NOT NULL DEFAULT 0.0,
        watch_through_rate REAL NOT NULL DEFAULT 0.0,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (moment_id) REFERENCES moments(id) ON DELETE SET NULL,
        FOREIGN KEY (template_id) REFERENCES templates(id) ON DELETE SET NULL,
        FOREIGN KEY (ab_test_id) REFERENCES ab_tests(id) ON DELETE SET NULL
    );

    CREATE TABLE IF NOT EXISTS ab_tests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        moment_id INTEGER,
        status TEXT NOT NULL DEFAULT 'running',
        winner_clip_id INTEGER,
        started_at TEXT NOT NULL DEFAULT (datetime('now')),
        ended_at TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (moment_id) REFERENCES moments(id) ON DELETE SET NULL
    );

    CREATE TABLE IF NOT EXISTS trends (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        platform TEXT NOT NULL,
        trend_type TEXT NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        score REAL NOT NULL DEFAULT 0.0,
        metadata TEXT NOT NULL DEFAULT '{}',
        source_url TEXT,
        detected_at TEXT NOT NULL DEFAULT (datetime('now')),
        expires_at TEXT,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS format_performance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        format_type TEXT NOT NULL,
        period TEXT NOT NULL,
        total_clips INTEGER NOT NULL DEFAULT 0,
        total_views INTEGER NOT NULL DEFAULT 0,
        avg_ctr REAL NOT NULL DEFAULT 0.0,
        avg_retention REAL NOT NULL DEFAULT 0.0,
        avg_watch_through REAL NOT NULL DEFAULT 0.0,
        avg_comments REAL NOT NULL DEFAULT 0.0,
        score REAL NOT NULL DEFAULT 0.0,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS ai_girl_config (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        is_enabled INTEGER NOT NULL DEFAULT 0,
        model_name TEXT NOT NULL DEFAULT 'default',
        voice_style TEXT NOT NULL DEFAULT 'energetic',
        appearance_style TEXT NOT NULL DEFAULT 'anime',
        overlay_position TEXT NOT NULL DEFAULT 'bottom-right',
        overlay_size REAL NOT NULL DEFAULT 0.25,
        use_only_when_better INTEGER NOT NULL DEFAULT 1,
        min_improvement_pct REAL NOT NULL DEFAULT 5.0,
        total_clips_with INTEGER NOT NULL DEFAULT 0,
        total_clips_without INTEGER NOT NULL DEFAULT 0,
        avg_retention_with REAL NOT NULL DEFAULT 0.0,
        avg_retention_without REAL NOT NULL DEFAULT 0.0,
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS strategy (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        current_phase INTEGER NOT NULL DEFAULT 1,
        phase_name TEXT NOT NULL DEFAULT 'max_testing',
        started_at TEXT NOT NULL DEFAULT (datetime('now')),
        config TEXT NOT NULL DEFAULT '{}',
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS ai_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        style TEXT NOT NULL DEFAULT 'realistic',
        description TEXT,
        appearance TEXT NOT NULL DEFAULT '{}',
        voice_config TEXT NOT NULL DEFAULT '{}',
        personality TEXT NOT NULL DEFAULT '{}',
        reference_images TEXT NOT NULL DEFAULT '[]',
        instagram_handle TEXT,
        tiktok_handle TEXT,
        telegram_channel TEXT,
        elevenlabs_voice_id TEXT,
        elevenlabs_voice_settings TEXT NOT NULL DEFAULT '{}',
        voice_audio_tags TEXT NOT NULL DEFAULT '[]',
        memory TEXT NOT NULL DEFAULT '{}',
        content_style TEXT NOT NULL DEFAULT '{}',
        social_config TEXT NOT NULL DEFAULT '{}',
        total_posts INTEGER NOT NULL DEFAULT 0,
        total_videos INTEGER NOT NULL DEFAULT 0,
        total_photos INTEGER NOT NULL DEFAULT 0,
        total_cost REAL NOT NULL DEFAULT 0.0,
        is_active INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS content_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        profile_id INTEGER NOT NULL,
        content_type TEXT NOT NULL,
        title TEXT,
        prompt TEXT,
        file_path TEXT,
        file_url TEXT,
        thumbnail_path TEXT,
        duration REAL,
        cost REAL NOT NULL DEFAULT 0.0,
        metadata TEXT NOT NULL DEFAULT '{}',
        status TEXT NOT NULL DEFAULT 'pending',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (profile_id) REFERENCES ai_profiles(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS social_posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        profile_id INTEGER NOT NULL,
        content_item_id INTEGER,
        platform TEXT NOT NULL,
        caption TEXT,
        hashtags TEXT NOT NULL DEFAULT '[]',
        scheduled_at TEXT,
        posted_at TEXT,
        post_url TEXT,
        status TEXT NOT NULL DEFAULT 'draft',
        engagement TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (profile_id) REFERENCES ai_profiles(id) ON DELETE CASCADE,
        FOREIGN KEY (content_item_id) REFERENCES content_items(id) ON DELETE SET NULL
    );

    CREATE TABLE IF NOT EXISTS voice_samples (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        profile_id INTEGER NOT NULL,
        text TEXT NOT NULL,
        audio_tags TEXT NOT NULL DEFAULT '[]',
        file_path TEXT,
        duration REAL,
        cost REAL NOT NULL DEFAULT 0.0,
        voice_settings TEXT NOT NULL DEFAULT '{}',
        rating INTEGER,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (profile_id) REFERENCES ai_profiles(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS generation_tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        profile_id INTEGER,
        task_type TEXT NOT NULL,
        prompt TEXT,
        config TEXT NOT NULL DEFAULT '{}',
        status TEXT NOT NULL DEFAULT 'pending',
        result TEXT DEFAULT '{}',
        error TEXT,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        completed_at TEXT,
        FOREIGN KEY (profile_id) REFERENCES ai_profiles(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS tool_registry (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL UNIQUE,
        category TEXT NOT NULL,
        description TEXT,
        github_url TEXT,
        github_stars INTEGER NOT NULL DEFAULT 0,
        license TEXT,
        min_vram_gb REAL NOT NULL DEFAULT 0,
        is_free INTEGER NOT NULL DEFAULT 1,
        api_cost_per_use REAL NOT NULL DEFAULT 0.0,
        quality_score REAL NOT NULL DEFAULT 0.0,
        speed_score REAL NOT NULL DEFAULT 0.0,
        config TEXT NOT NULL DEFAULT '{}',
        is_selected INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS accounts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        platform TEXT NOT NULL,
        handle TEXT NOT NULL,
        account_type TEXT NOT NULL DEFAULT 'streamer',
        region TEXT NOT NULL DEFAULT 'global',
        language TEXT NOT NULL DEFAULT 'en',
        target_audience TEXT NOT NULL DEFAULT '{}',
        streamer_names TEXT NOT NULL DEFAULT '[]',
        status TEXT NOT NULL DEFAULT 'active',
        total_posts INTEGER NOT NULL DEFAULT 0,
        total_followers INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TEXT NOT NULL DEFAULT (datetime('now'))
    );

    -- Profile photo gallery: stores ALL generated photos per girl (cloud URLs, no local files)
    CREATE TABLE IF NOT EXISTS profile_gallery (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        profile_id INTEGER NOT NULL,
        image_url TEXT NOT NULL,
        thumbnail_url TEXT,
        content_type TEXT NOT NULL DEFAULT 'portrait',
        prompt TEXT,
        model_key TEXT,
        is_reference INTEGER NOT NULL DEFAULT 0,
        is_approved INTEGER NOT NULL DEFAULT 0,
        is_favorite INTEGER NOT NULL DEFAULT 0,
        quality_rating INTEGER,
        metadata TEXT NOT NULL DEFAULT '{}',
        cost REAL NOT NULL DEFAULT 0.0,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (profile_id) REFERENCES ai_profiles(id) ON DELETE CASCADE
    );

    -- Prompt learning: tracks which prompts produce best results per profile
    CREATE TABLE IF NOT EXISTS prompt_learning (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        profile_id INTEGER NOT NULL,
        prompt_type TEXT NOT NULL DEFAULT 'photo',
        original_prompt TEXT NOT NULL,
        refined_prompt TEXT,
        model_key TEXT,
        content_type TEXT,
        success_score REAL NOT NULL DEFAULT 0.0,
        user_rating INTEGER,
        auto_features TEXT NOT NULL DEFAULT '{}',
        generation_count INTEGER NOT NULL DEFAULT 1,
        last_used_at TEXT NOT NULL DEFAULT (datetime('now')),
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (profile_id) REFERENCES ai_profiles(id) ON DELETE CASCADE
    );

    -- Voice identity: unique voice per girl with training data
    CREATE TABLE IF NOT EXISTS voice_identity (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        profile_id INTEGER NOT NULL UNIQUE,
        provider TEXT NOT NULL DEFAULT 'elevenlabs',
        voice_id TEXT,
        voice_name TEXT,
        voice_settings TEXT NOT NULL DEFAULT '{}',
        audio_tags TEXT NOT NULL DEFAULT '[]',
        sample_urls TEXT NOT NULL DEFAULT '[]',
        personality_traits TEXT NOT NULL DEFAULT '[]',
        speaking_style TEXT NOT NULL DEFAULT 'natural',
        language TEXT NOT NULL DEFAULT 'en',
        total_generations INTEGER NOT NULL DEFAULT 0,
        avg_quality_score REAL NOT NULL DEFAULT 0.0,
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        updated_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (profile_id) REFERENCES ai_profiles(id) ON DELETE CASCADE
    );

    -- LoRA models: trained face identity models per girl
    CREATE TABLE IF NOT EXISTS lora_models (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        profile_id INTEGER NOT NULL,
        trigger_word TEXT NOT NULL,
        lora_url TEXT,
        lora_weights_url TEXT,
        config_url TEXT,
        training_status TEXT NOT NULL DEFAULT 'pending',
        training_steps INTEGER NOT NULL DEFAULT 1000,
        training_images_count INTEGER NOT NULL DEFAULT 0,
        training_cost REAL NOT NULL DEFAULT 0.0,
        training_started_at TEXT,
        training_completed_at TEXT,
        fal_request_id TEXT,
        error TEXT,
        metadata TEXT NOT NULL DEFAULT '{}',
        created_at TEXT NOT NULL DEFAULT (datetime('now')),
        FOREIGN KEY (profile_id) REFERENCES ai_profiles(id) ON DELETE CASCADE
    );

    CREATE TABLE IF NOT EXISTS region_analysis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        region TEXT NOT NULL,
        platform TEXT NOT NULL,
        audience_size INTEGER NOT NULL DEFAULT 0,
        competition_level TEXT NOT NULL DEFAULT 'medium',
        avg_views_per_reel INTEGER NOT NULL DEFAULT 0,
        top_languages TEXT NOT NULL DEFAULT '[]',
        top_content_types TEXT NOT NULL DEFAULT '[]',
        growth_potential REAL NOT NULL DEFAULT 0.0,
        recommendation TEXT,
        analyzed_at TEXT NOT NULL DEFAULT (datetime('now')),
        UNIQUE(region, platform)
    );
    """)

    # Seed default templates if empty
    cursor = await db.execute("SELECT COUNT(*) as cnt FROM templates")
    row = await cursor.fetchone()
    if row[0] == 0:
        default_templates = [
            ("clean_highlight", "clean_highlight", "Чистый хайлайт без оверлеев", json.dumps({"overlay": False, "subtitles": False, "ai_girl": False})),
            ("highlight_reaction", "highlight_reaction", "Хайлайт с вебкой стримера", json.dumps({"overlay": True, "subtitles": False, "face_cam": True})),
            ("highlight_subtitles", "highlight_subtitles", "Хайлайт с динамичными субтитрами", json.dumps({"overlay": False, "subtitles": True, "ai_girl": False})),
            ("highlight_ai_girl", "highlight_ai_girl", "Хайлайт с AI-девушкой комментатором", json.dumps({"overlay": True, "subtitles": True, "ai_girl": True})),
            ("meme_format", "meme_format", "Мем-монтаж со звуковыми эффектами", json.dumps({"meme_sounds": True, "zoom_effects": True})),
            ("dramatic_clutch", "dramatic_clutch", "Драматичный клатч со слоу-мо", json.dumps({"slow_motion": True, "dramatic_music": True, "text_overlay": True})),
            ("provocative", "provocative", "Провокационный заголовок/хук", json.dumps({"provocative_hook": True, "bold_text": True})),
            ("hard_fragmovie", "hard_fragmovie", "Хардкорный фрагмуви монтаж", json.dumps({"sync_music": True, "fast_cuts": True, "color_grade": True})),
            ("fail_format", "fail_format", "Фейлы и смешные моменты", json.dumps({"fail_sounds": True, "replay": True})),
        ]
        await db.executemany(
            "INSERT INTO templates (name, format_type, description, config) VALUES (?, ?, ?, ?)",
            default_templates,
        )

    # Seed default AI girl config if empty
    cursor = await db.execute("SELECT COUNT(*) as cnt FROM ai_girl_config")
    row = await cursor.fetchone()
    if row[0] == 0:
        await db.execute("INSERT INTO ai_girl_config (is_enabled) VALUES (0)")

    # Seed default strategy if empty
    cursor = await db.execute("SELECT COUNT(*) as cnt FROM strategy")
    row = await cursor.fetchone()
    if row[0] == 0:
        await db.execute(
            "INSERT INTO strategy (current_phase, phase_name, config) VALUES (1, 'max_testing', ?)",
            (json.dumps({
                "phases": {
                    "1": {"name": "max_testing", "label": "Максимальное тестирование", "description": "Генерируем максимум вариантов, тестируем все форматы"},
                    "2": {"name": "focus_top", "label": "Фокус на топ-2-3 форматах", "description": "Удваиваем усилия на лучших форматах"},
                    "3": {"name": "scale", "label": "Масштабирование", "description": "Масштабируем лучшие форматы на все платформы"},
                    "4": {"name": "branding", "label": "Брендирование", "description": "Создаём узнаваемый бренд и стиль"},
                    "5": {"name": "ad_integration", "label": "Интеграция рекламы", "description": "Подключаем рекламу и спонсорство"}
                }
            }),)
        )

    # Seed/upgrade tool registry (idempotent)
    # Always attempt inserts so new tools get added to existing DBs.
    from app.services.ai_profile_generator import TOOL_REGISTRY
    for tool in TOOL_REGISTRY:
        try:
            await db.execute(
                """INSERT INTO tool_registry (
                       name, category, description, github_url, github_stars,
                       license, min_vram_gb, is_free, api_cost_per_use,
                       quality_score, speed_score, config, is_selected
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    tool["name"],
                    tool["category"],
                    tool.get("description"),
                    tool.get("github_url"),
                    tool.get("github_stars", 0),
                    tool.get("license"),
                    tool.get("min_vram_gb", 0.0),
                    1 if tool.get("is_free", True) else 0,
                    float(tool.get("api_cost_per_use", 0.0)),
                    float(tool.get("quality_score", 0.0)),
                    float(tool.get("speed_score", 0.0)),
                    json.dumps(tool.get("config", {})),
                    1 if tool["name"] in (
                        "Stable Diffusion XL",
                        "IP-Adapter (Face Consistency)",
                        "FantasyTalking",
                        "MuseTalk",
                        "LivePortrait",
                        "Qwen3-TTS",
                        "Wan2.1 (Alibaba)",
                        "ComfyUI",
                        "FaceFusion",
                    ) else 0,
                ),
            )
        except Exception:
            pass  # Skip duplicates

    # Migrate existing ai_profiles table to add new columns
    try:
        await db.execute("ALTER TABLE ai_profiles ADD COLUMN tiktok_handle TEXT")
    except Exception:
        pass
    try:
        await db.execute("ALTER TABLE ai_profiles ADD COLUMN telegram_channel TEXT")
    except Exception:
        pass
    try:
        await db.execute("ALTER TABLE ai_profiles ADD COLUMN elevenlabs_voice_id TEXT")
    except Exception:
        pass
    try:
        await db.execute("ALTER TABLE ai_profiles ADD COLUMN elevenlabs_voice_settings TEXT NOT NULL DEFAULT '{}'")
    except Exception:
        pass
    try:
        await db.execute("ALTER TABLE ai_profiles ADD COLUMN voice_audio_tags TEXT NOT NULL DEFAULT '[]'")
    except Exception:
        pass
    try:
        await db.execute("ALTER TABLE ai_profiles ADD COLUMN memory TEXT NOT NULL DEFAULT '{}'")
    except Exception:
        pass
    try:
        await db.execute("ALTER TABLE ai_profiles ADD COLUMN content_style TEXT NOT NULL DEFAULT '{}'")
    except Exception:
        pass
    try:
        await db.execute("ALTER TABLE ai_profiles ADD COLUMN social_config TEXT NOT NULL DEFAULT '{}'")
    except Exception:
        pass
    try:
        await db.execute("ALTER TABLE ai_profiles ADD COLUMN total_photos INTEGER NOT NULL DEFAULT 0")
    except Exception:
        pass
    try:
        await db.execute("ALTER TABLE ai_profiles ADD COLUMN total_cost REAL NOT NULL DEFAULT 0.0")
    except Exception:
        pass

    # LoRA fields on ai_profiles
    try:
        await db.execute("ALTER TABLE ai_profiles ADD COLUMN lora_model_url TEXT")
    except Exception:
        pass
    try:
        await db.execute("ALTER TABLE ai_profiles ADD COLUMN lora_trigger_word TEXT")
    except Exception:
        pass
    try:
        await db.execute("ALTER TABLE ai_profiles ADD COLUMN lora_training_status TEXT NOT NULL DEFAULT 'not_trained'")
    except Exception:
        pass
    try:
        await db.execute("ALTER TABLE ai_profiles ADD COLUMN lora_trained_at TEXT")
    except Exception:
        pass

    # Restore persisted ElevenLabs API key if available
    cursor = await db.execute("SELECT value FROM settings WHERE key='elevenlabs_api_key'")
    row = await cursor.fetchone()
    if row:
        os.environ["ELEVENLABS_API_KEY"] = row[0]

    # Restore persisted fal.ai API key if available
    cursor = await db.execute("SELECT value FROM settings WHERE key='fal_api_key'")
    row = await cursor.fetchone()
    if row:
        # content_generation reads FAL_KEY dynamically from the environment
        os.environ["FAL_KEY"] = row[0]

    # Restore persisted Twitch API credentials if available
    cursor = await db.execute("SELECT value FROM settings WHERE key='twitch_client_id'")
    row = await cursor.fetchone()
    if row:
        os.environ["TWITCH_CLIENT_ID"] = row[0]
        try:
            import app.services.clip_executor as ce
            ce.TWITCH_CLIENT_ID = row[0]
        except Exception:
            pass
    cursor = await db.execute("SELECT value FROM settings WHERE key='twitch_client_secret'")
    row = await cursor.fetchone()
    if row:
        os.environ["TWITCH_CLIENT_SECRET"] = row[0]
        try:
            import app.services.clip_executor as ce
            ce.TWITCH_CLIENT_SECRET = row[0]
        except Exception:
            pass
    cursor = await db.execute("SELECT value FROM settings WHERE key='twitch_access_token'")
    row = await cursor.fetchone()
    if row:
        os.environ["TWITCH_ACCESS_TOKEN"] = row[0]
        try:
            import app.services.clip_executor as ce
            ce.TWITCH_ACCESS_TOKEN = row[0]
        except Exception:
            pass

    # Seed region analysis if empty
    cursor = await db.execute("SELECT COUNT(*) as cnt FROM region_analysis")
    row = await cursor.fetchone()
    if row[0] == 0:
        from app.services.ai_profile_generator import REGION_ANALYSIS_DATA
        for region in REGION_ANALYSIS_DATA:
            await db.execute(
                """INSERT INTO region_analysis (region, platform, audience_size, competition_level,
                   avg_views_per_reel, top_languages, top_content_types, growth_potential, recommendation)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    region["region"], region["platform"], region["audience_size"],
                    region["competition_level"], region["avg_views_per_reel"],
                    json.dumps(region["top_languages"]), json.dumps(region["top_content_types"]),
                    region["growth_potential"], region["recommendation"],
                ),
            )

    await db.commit()
    await db.close()
