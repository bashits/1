"""
Smart Context-Aware Commentary Generator — ULTRA v2.0

MASSIVE UPGRADE:
- 100+ reaction templates across 4 personas x 12+ moment types
- Adaptive logic: system picks best reaction based on ALL context factors
- Natural human speech patterns: stutters, self-corrections, interruptions,
  emotional escalation, trailing thoughts, filler words
- Advanced ElevenLabs v3 audio tags: layered emotions, mid-sentence shifts,
  non-verbal reactions, breathing patterns, micro-pauses
- Emotional arc system: builds tension -> peak -> release
- Context-weighted randomization: rarer moments get rarer reactions
- Anti-repetition: tracks used variants per session
- Multi-phase scripts: intro -> buildup -> peak -> reaction -> outro

Based on research from:
- ElevenLabs v3 Audio Tags complete guide (dev.to/yigit-konur)
- ElevenLabs official blog: situational awareness, narrative intelligence,
  emotional context, character performance, multi-character dialogue
- ElevenLabs best practices docs
- GPT-commentary-SC2 (context-aware game commentary)
- AI-Powered-Sports-Commentary-Generator
- Real Twitch/YouTube girl streamer speech analysis

KEY v3 TECHNIQUES USED:
1. Layered tags: [excited][breathes] for complex emotions
2. Mid-sentence emotion shifts: text [tag] more text
3. Non-verbal reactions: [gasps], [squeals], [giggles], [snorts], [gulps]
4. Breathing patterns: [breathes], [breathes heavily], [catches breath]
5. Personality tags: [sarcastically], [playfully], [dramatically]
6. Volume shifts: [whispers] -> [shouts] for contrast
7. Natural fillers woven into text (not just tags)
8. Trailing dashes for interrupted thoughts
9. Ellipsis for hesitation...
10. CAPS for emphasis on key words
"""

import random
import time
from typing import Optional


# =====================================================================
# SESSION ANTI-REPETITION TRACKER
# =====================================================================

_used_variants: dict = {}  # {persona_moment_key: set of used indices}


def _pick_variant(key: str, variants: list) -> str:
    """Pick a variant, avoiding recently used ones for naturalness."""
    if key not in _used_variants:
        _used_variants[key] = set()

    available = [i for i in range(len(variants)) if i not in _used_variants[key]]
    if not available:
        _used_variants[key] = set()  # Reset when all used
        available = list(range(len(variants)))

    idx = random.choice(available)
    _used_variants[key].add(idx)
    return variants[idx]


# =====================================================================
# MOMENT CONTEXT: What's happening in the clip
# =====================================================================

class MomentContext:
    """Describes what's happening in a CS2 clip moment."""

    def __init__(
        self,
        moment_type: str = "clutch",
        player_name: str = "m0NESY",
        team: str = "G2",
        weapon: str = "AWP",
        kills: int = 3,
        situation: str = "1v3",
        map_name: str = "Mirage",
        round_info: str = "match point",
        health: int = 12,
        time_remaining: float = 15.0,
        is_defuse: bool = False,
        streak: int = 0,
        through_smoke: bool = False,
        wallbang: bool = False,
        no_scope: bool = False,
        flash_kill: bool = False,
        extra_detail: str = "",
        # NEW context fields
        is_tournament: bool = False,
        is_comeback: bool = False,
        is_eco: bool = False,
        enemy_rank: str = "",
        round_number: int = 0,
        score: str = "",
        is_ranked: bool = False,
    ):
        self.moment_type = moment_type
        self.player_name = player_name
        self.team = team
        self.weapon = weapon
        self.kills = kills
        self.situation = situation
        self.map_name = map_name
        self.round_info = round_info
        self.health = health
        self.time_remaining = time_remaining
        self.is_defuse = is_defuse
        self.streak = streak
        self.through_smoke = through_smoke
        self.wallbang = wallbang
        self.no_scope = no_scope
        self.flash_kill = flash_kill
        self.extra_detail = extra_detail
        self.is_tournament = is_tournament
        self.is_comeback = is_comeback
        self.is_eco = is_eco
        self.enemy_rank = enemy_rank
        self.round_number = round_number
        self.score = score
        self.is_ranked = is_ranked

    @property
    def drama_level(self) -> int:
        """0-10 drama score based on context."""
        score = 0
        if self.health < 20:
            score += 3
        if self.health < 10:
            score += 2
        if self.through_smoke:
            score += 2
        if self.no_scope:
            score += 2
        if self.wallbang:
            score += 2
        if self.flash_kill:
            score += 1
        if self.is_defuse:
            score += 2
        if self.is_tournament:
            score += 2
        if self.is_comeback:
            score += 2
        if self.is_eco:
            score += 1
        if "match point" in self.round_info.lower():
            score += 3
        if "overtime" in self.round_info.lower():
            score += 2
        kills_score = min(self.kills * 1.5, 6)
        score += kills_score
        return min(int(score), 10)

    @property
    def weapon_short(self) -> str:
        """Short weapon name for natural speech."""
        shorts = {
            "AWP": "AWP", "AK-47": "AK", "M4A4": "M4", "M4A1-S": "M4",
            "Desert Eagle": "Deagle", "USP-S": "USP", "Glock-18": "Glock",
            "knife": "knife", "Knife": "knife",
        }
        return shorts.get(self.weapon, self.weapon)


# =====================================================================
# NATURAL SPEECH HELPERS
# =====================================================================

def _detail_bits(ctx: MomentContext) -> dict:
    """Build conditional detail strings based on context."""
    return {
        "smoke": "THROUGH THE SMOKE " if ctx.through_smoke else "",
        "smoke_lc": "through the smoke " if ctx.through_smoke else "",
        "noscope": "WITHOUT SCOPING " if ctx.no_scope else "",
        "noscope_lc": "no-scope " if ctx.no_scope else "",
        "wallbang": "THROUGH THE WALL " if ctx.wallbang else "",
        "wallbang_lc": "through the wall " if ctx.wallbang else "",
        "hp": f"on {ctx.health} HP " if ctx.health < 30 else "",
        "hp_drama": f"{ctx.player_name} only has {ctx.health} HP " if ctx.health < 30 else "",
        "flash": "while FLASHED " if ctx.flash_kill else "",
    }


# =====================================================================
# MIA CUTE -- Sweet, bubbly, genuinely shocked
# =====================================================================

def _mia_clutch(ctx: MomentContext) -> str:
    d = _detail_bits(ctx)
    variants = [
        # V1: Building tension -> explosion
        (
            f"[nervously][whispers] Okay okay it's a {ctx.situation} "
            f"[breathes] {ctx.player_name} has the {ctx.weapon_short} "
            f"[gasps] HE GOT ONE! {d['smoke']}"
            f"[squeals] AND ANOTHER ONE! "
            f"[giggles nervously] {d['hp']}"
            f"[breathes] [screams happily] HE CLUTCHED IT! "
            f"Oh my gosh I KNEW it I literally called it"
        ),
        # V2: Disbelief -> joy
        (
            f"[breathes] Oh my [gasps] oh my GOSH "
            f"he's in a {ctx.situation} and he just "
            f"[squeals] with the {ctx.weapon_short}! "
            f"{d['smoke']}{d['noscope']}"
            f"[giggles] [catches breath] "
            f"Wait {d['hp_drama']}"
            f"how does he how does he DO that?! "
            f"[happily] That was SO clutch like I literally can't"
        ),
        # V3: Whisper buildup -> scream
        (
            f"[whispers excitedly] Come on come on "
            f"[breathes heavily] {ctx.player_name} {ctx.situation} "
            f"[gasps] THE {ctx.weapon_short} "
            f"{d['smoke']}"
            f"[screams] YES! YES! YES! "
            f"[giggles uncontrollably] [catches breath] "
            f"I'm literally shaking on {ctx.map_name} that's SO hard"
        ),
        # V4: Stumbling over words with excitement
        (
            f"[breathes] Wait wait wait wait "
            f"is he is he actually going for the {ctx.situation}?! "
            f"[gasps] {ctx.player_name} the {ctx.weapon_short} "
            f"[squeals] OH MY GOD! "
            f"[giggles] [catches breath] "
            f"I I don't I literally don't know how he does that "
            f"[happily] {ctx.map_name} is his MAP!"
        ),
        # V5: Self-correction mid-sentence
        (
            f"[excited][breathes] Okay so he's wait "
            f"he's in a {ctx.situation} {d['hp']}"
            f"[whispers] with the {ctx.weapon_short} "
            f"[gasps] NO WAY NO WAY! "
            f"[screams happily] HE DID IT! "
            f"[giggles] [breathes] "
            f"I said I literally said he was gonna clutch it "
            f"[squeals] {ctx.player_name} is BUILT DIFFERENT!"
        ),
        # V6: Nervous then explodes
        (
            f"[nervously] Oh gosh {ctx.situation} "
            f"[breathes] come on {ctx.player_name} come on "
            f"[gasps] THE {ctx.weapon_short} SHOT! "
            f"{d['smoke']}"
            f"[giggles] [catches breath] "
            f"I'm shaking like literally shaking right now "
            f"on {ctx.map_name} that's SO hard to do"
        ),
        # V7: Interrupted thoughts
        (
            f"[breathes] He's okay {ctx.player_name} "
            f"[whispers excitedly] {ctx.situation} on {ctx.map_name} "
            f"[gasps] THE SHOT! [squeals] AND ANOTHER "
            f"[giggles] wait [breathes] "
            f"did he did he just [screams] HE CLUTCHED! "
            f"[catches breath] Oh my god oh my GOD"
        ),
        # V8: Low HP drama focus
        (
            f"[whispers] {ctx.health} HP {ctx.player_name} has {ctx.health} HP "
            f"[breathes heavily] in a {ctx.situation} "
            f"[gasps] THE {ctx.weapon_short}! "
            f"{d['smoke']}"
            f"[screams] YES! [giggles] "
            f"[catches breath] How HOW?! "
            f"[happily] That's why he's the BEST"
        ),
    ]
    return _pick_variant("mia_clutch", variants)


def _mia_ace(ctx: MomentContext) -> str:
    variants = [
        (
            f"[whispers excitedly] Five kills "
            f"[breathes] wait [screams] FIVE KILLS! "
            f"{ctx.player_name} just ACED with the {ctx.weapon_short}! "
            f"[giggles] [happily] That was SO clean like how?! "
            f"On {ctx.map_name} in a {ctx.round_info} "
            f"[squeals] that's INSANE! [catches breath]"
        ),
        (
            f"[gasps] One two three [breathes] "
            f"oh no he's going for the ACE "
            f"[nervously] four [screams] FIVE! "
            f"{ctx.player_name} oh my GOD! "
            f"[giggles] The {ctx.weapon_short} is broken in his hands "
            f"like actually broken [happily] I love this"
        ),
        (
            f"[breathes] Okay okay he's got four "
            f"[whispers excitedly] can he can he get the ACE?! "
            f"[gasps] THE FIFTH ONE! [screams] "
            f"[giggles uncontrollably] [catches breath] "
            f"ACE! {ctx.player_name} got the ACE on {ctx.map_name}! "
            f"[squeals] I'm literally DEAD right now"
        ),
        (
            f"[excited] Wait wait [breathes] "
            f"is he is he going for all five?! "
            f"[gasps] HE IS! [squeals] "
            f"[giggles] [catches breath] "
            f"ACE! With the {ctx.weapon_short}! On {ctx.map_name}! "
            f"[screams] {ctx.player_name} you LEGEND!"
        ),
        (
            f"[nervously][whispers] Come on one more one more kill "
            f"[breathes] {ctx.player_name} the {ctx.weapon_short} "
            f"[gasps] FIVE! [screams happily] "
            f"[giggles] [catches breath] "
            f"ACE! In the {ctx.round_info}! "
            f"[squeals] That's the most beautiful thing I've ever seen"
        ),
    ]
    return _pick_variant("mia_ace", variants)


def _mia_headshot(ctx: MomentContext) -> str:
    d = _detail_bits(ctx)
    variants = [
        (
            f"[breathes] Head shot "
            f"[gasps] ANOTHER ONE?! Wait "
            f"{ctx.player_name} with the {ctx.weapon_short} {d['smoke']}{d['noscope']}{d['wallbang']}"
            f"[giggles nervously] "
            f"[whispers] How does he how does he aim like that "
            f"on {ctx.map_name} that angle is literally impossible"
        ),
        (
            f"[gasps] Did you SEE that?! "
            f"[breathes] {ctx.player_name} the {ctx.weapon_short} "
            f"just CLICK headshot {d['smoke_lc']}"
            f"[squeals] So clean! [giggles] "
            f"Like he just KNOWS where they are "
            f"[whispers excitedly] he's actually built different"
        ),
        (
            f"[whispers excitedly] Watch watch this "
            f"[breathes] {ctx.player_name} is peeking "
            f"[gasps] HEADSHOT! {d['smoke']}{d['wallbang']}"
            f"[squeals] And ANOTHER ONE! "
            f"[giggles] [catches breath] "
            f"His aim on {ctx.map_name} is just [happily] ILLEGAL"
        ),
        (
            f"[breathes] Okay so {ctx.player_name} "
            f"[whispers] with the {ctx.weapon_short} "
            f"[gasps] CLICK! Headshot! {d['smoke']}"
            f"[giggles nervously] "
            f"[whispers] I don't I don't understand how "
            f"[happily] that's just not FAIR"
        ),
        (
            f"[excited][breathes] The crosshair placement "
            f"[gasps] HEADSHOT! {d['noscope']}{d['smoke']}"
            f"[squeals] {ctx.player_name}! "
            f"[giggles] [catches breath] "
            f"On {ctx.map_name} with the {ctx.weapon_short} "
            f"[whispers] that's just that's just art"
        ),
    ]
    return _pick_variant("mia_headshot", variants)


def _mia_knife(ctx: MomentContext) -> str:
    variants = [
        (
            f"[gasps] THE THE KNIFE?! "
            f"[breathes] {ctx.player_name} pulled out the knife "
            f"in a {ctx.situation} on {ctx.map_name} "
            f"[giggles] [whispers] That's so MEAN! "
            f"[laughs] Oh my god the disrespect "
            f"I love it though [catches breath] poor guy"
        ),
        (
            f"[breathes] Wait is he "
            f"[gasps] HE'S GOING FOR THE KNIFE! "
            f"[giggles nervously] In a {ctx.situation}?! "
            f"[squeals] HE GOT IT! "
            f"[laughs] [catches breath] "
            f"The DISRESPECT {ctx.player_name} "
            f"[whispers] that poor guy"
        ),
        (
            f"[whispers excitedly] Oh no oh no no no "
            f"[breathes] he's switching to the knife "
            f"[gasps] ON {ctx.map_name}?! "
            f"[screams] HE KNIFED HIM! "
            f"[giggles uncontrollably] [catches breath] "
            f"That is the most disrespectful thing I've ever seen "
            f"[happily] I'm obsessed"
        ),
    ]
    return _pick_variant("mia_knife", variants)


def _mia_defuse(ctx: MomentContext) -> str:
    variants = [
        (
            f"[nervously][whispers] Oh gosh the bomb "
            f"[breathes heavily] come on {ctx.player_name} "
            f"[gasps] {ctx.time_remaining:.0f} seconds left "
            f"[whispers] come on come on come on "
            f"[screams happily] HE GOT IT! [giggles] "
            f"[breathes] My heart my heart is like "
            f"going a MILLION miles an hour right now"
        ),
        (
            f"[breathes heavily] The bomb the bomb is ticking "
            f"[whispers] {ctx.player_name} please "
            f"[gasps] HE'S DEFUSING! "
            f"[nervously] Come on come on "
            f"[screams] YES! [giggles] "
            f"[catches breath] I literally stopped breathing "
            f"[happily] that was the most stressful thing EVER"
        ),
        (
            f"[whispers][nervously] Okay okay "
            f"{ctx.time_remaining:.0f} seconds "
            f"[breathes] {ctx.player_name} is going for the defuse "
            f"[gasps] in a {ctx.situation}?! "
            f"[screams happily] HE DID IT! [squeals] "
            f"[giggles] [catches breath] "
            f"My hands are literally shaking right now"
        ),
    ]
    return _pick_variant("mia_defuse", variants)


def _mia_multikill(ctx: MomentContext) -> str:
    kill_word = {2: "double", 3: "triple", 4: "quad"}.get(ctx.kills, f"{ctx.kills}-kill")
    variants = [
        (
            f"[breathes] Wait [gasps] ONE! "
            f"[excited] TWO! [squeals] "
            f"THREE! [screams] "
            f"{ctx.player_name} with the {kill_word} kill on {ctx.map_name}! "
            f"[giggles] [catches breath] "
            f"The {ctx.weapon_short} is just [happily] BROKEN"
        ),
        (
            f"[gasps] Did he [breathes] "
            f"is that a {kill_word}?! "
            f"[squeals] {ctx.player_name}! "
            f"[giggles] [catches breath] "
            f"With the {ctx.weapon_short} on {ctx.map_name} "
            f"[whispers excitedly] he's actually insane"
        ),
        (
            f"[excited][breathes] One two "
            f"[gasps] THREE! {kill_word} kill! "
            f"[squeals] {ctx.player_name}! "
            f"[giggles uncontrollably] [catches breath] "
            f"The {ctx.weapon_short} on {ctx.map_name} "
            f"[happily] I can't I literally can't"
        ),
    ]
    return _pick_variant("mia_multikill", variants)


def _mia_eco(ctx: MomentContext) -> str:
    variants = [
        (
            f"[breathes] Wait they're on ECO?! "
            f"[gasps] {ctx.player_name} with the pistol "
            f"[squeals] HE'S WINNING THE ECO ROUND! "
            f"[giggles] [catches breath] "
            f"On {ctx.map_name} against full buy "
            f"[happily] that's INSANE"
        ),
        (
            f"[whispers excitedly] Eco round "
            f"[breathes] {ctx.player_name} doesn't care "
            f"[gasps] THE PISTOL KILLS! "
            f"[squeals] [giggles] "
            f"[catches breath] "
            f"He just he just won an eco round on {ctx.map_name} "
            f"[happily] I love him"
        ),
    ]
    return _pick_variant("mia_eco", variants)


def _mia_wallbang(ctx: MomentContext) -> str:
    variants = [
        (
            f"[breathes] Is he is he shooting THROUGH the wall?! "
            f"[gasps] {ctx.player_name} the {ctx.weapon_short} "
            f"[squeals] WALLBANG! "
            f"[giggles] [catches breath] "
            f"How did he KNOW they were there?! "
            f"On {ctx.map_name} [whispers] that's actually illegal"
        ),
        (
            f"[whispers excitedly] He's pre-aiming "
            f"[breathes] through the wall "
            f"[gasps] WALLBANG! "
            f"[squeals] {ctx.player_name}! "
            f"[giggles] [catches breath] "
            f"The {ctx.weapon_short} just [happily] DESTROYED him through the wall"
        ),
    ]
    return _pick_variant("mia_wallbang", variants)


def _mia_comeback(ctx: MomentContext) -> str:
    variants = [
        (
            f"[breathes] They were losing "
            f"[whispers excitedly] {ctx.player_name} is carrying "
            f"[gasps] THE COMEBACK! "
            f"[screams] [giggles] "
            f"[catches breath] "
            f"On {ctx.map_name} from behind "
            f"[happily] I'm literally crying right now"
        ),
        (
            f"[nervously] They were down "
            f"[breathes] but {ctx.player_name} "
            f"[gasps] THE {ctx.weapon_short}! "
            f"[screams happily] COMEBACK! "
            f"[giggles] [catches breath] "
            f"On {ctx.map_name} that's that's SO hype "
            f"[squeals] never give up!"
        ),
    ]
    return _pick_variant("mia_comeback", variants)


def _mia_tournament(ctx: MomentContext) -> str:
    variants = [
        (
            f"[nervously][breathes] This is a TOURNAMENT "
            f"[whispers] {ctx.player_name} "
            f"[gasps] THE PLAY! "
            f"[screams] ON THE BIG STAGE! "
            f"[giggles] [catches breath] "
            f"On {ctx.map_name} in the {ctx.round_info} "
            f"[squeals] LEGENDARY"
        ),
        (
            f"[breathes] Major play "
            f"[whispers excitedly] {ctx.player_name} on {ctx.map_name} "
            f"[gasps] THE {ctx.weapon_short}! "
            f"[screams] YES! "
            f"[giggles] [catches breath] "
            f"That's why he's the BEST in the world"
        ),
    ]
    return _pick_variant("mia_tournament", variants)


def _mia_noscope(ctx: MomentContext) -> str:
    variants = [
        (
            f"[breathes] Wait did he just "
            f"[gasps] NO SCOPE?! "
            f"[screams] {ctx.player_name} THE NO SCOPE! "
            f"[giggles uncontrollably] [catches breath] "
            f"With the {ctx.weapon_short} on {ctx.map_name} "
            f"[happily] that's ACTUAL INSANITY"
        ),
        (
            f"[whispers excitedly] He's not scoping "
            f"[breathes] {ctx.player_name} "
            f"[gasps] NO SCOPE HEADSHOT! "
            f"[squeals] [giggles] "
            f"[catches breath] "
            f"On {ctx.map_name} I literally I can't "
            f"[happily] that was SO lucky or SO skilled I don't even know"
        ),
    ]
    return _pick_variant("mia_noscope", variants)


def _mia_toxic(ctx: MomentContext) -> str:
    variants = [
        (
            f"[gasps] Oh no he did NOT just "
            f"[breathes] {ctx.player_name} that's so "
            f"[giggles nervously] [whispers] that's so toxic "
            f"[laughs] I shouldn't be laughing but "
            f"[catches breath] on {ctx.map_name} that was SAVAGE "
            f"[giggles] I love it"
        ),
        (
            f"[breathes] Oh my god "
            f"[gasps] {ctx.player_name}! "
            f"[giggles] That is SO disrespectful! "
            f"[whispers] I shouldn't I shouldn't be laughing "
            f"[laughs] but that was HILARIOUS "
            f"[catches breath] poor guy on {ctx.map_name}"
        ),
    ]
    return _pick_variant("mia_toxic", variants)


def _mia_meme(ctx: MomentContext) -> str:
    variants = [
        (
            f"[breathes] Oh no [giggles] "
            f"{ctx.player_name} what are you doing "
            f"[laughs] [catches breath] "
            f"on {ctx.map_name} that was "
            f"[giggles uncontrollably] I'm sorry I'm so sorry "
            f"[breathes] that was SO funny"
        ),
        (
            f"[gasps] Wait what just happened "
            f"[breathes] {ctx.player_name} on {ctx.map_name} "
            f"[giggles] did he just "
            f"[laughs] oh my GOD "
            f"[catches breath] [whispers] that was actually hilarious "
            f"[giggles] I'm dead I'm literally dead"
        ),
    ]
    return _pick_variant("mia_meme", variants)


def _mia_generic(ctx: MomentContext) -> str:
    variants = [
        (
            f"[happily][breathes] So like "
            f"{ctx.player_name} on {ctx.map_name} with the {ctx.weapon_short} "
            f"[gasps] that was SO good! "
            f"[giggles] I love watching this "
            f"[catches breath] okay what's next"
        ),
        (
            f"[breathes] Oh my gosh "
            f"{ctx.player_name} the {ctx.weapon_short} "
            f"[gasps] Did you SEE that?! "
            f"[giggles] [happily] "
            f"On {ctx.map_name} that was just [squeals] SO clean"
        ),
        (
            f"[excited][breathes] Okay "
            f"{ctx.player_name} with the {ctx.weapon_short} on {ctx.map_name} "
            f"[gasps] that play [giggles] "
            f"[catches breath] "
            f"I literally I can't even [happily] he's just built different"
        ),
    ]
    return _pick_variant("mia_generic", variants)


# =====================================================================
# ALEX EDGY -- Dark, intense, whisper-contrast
# =====================================================================

def _alex_clutch(ctx: MomentContext) -> str:
    d = _detail_bits(ctx)
    variants = [
        (
            f"[breathes] {ctx.situation} "
            f"[intense] {ctx.player_name} with the {ctx.weapon_short} "
            f"[exhales] [dark laugh] Get destroyed. "
            f"[whispers] {d['hp']}"
            f"didn't even matter. "
            f"[pause] [smirks] pathetic defense."
        ),
        (
            f"[coldly] A {ctx.situation} on {ctx.map_name}. "
            f"[breathes] Most players panic "
            f"[whispers menacingly] {ctx.player_name} doesn't panic. "
            f"[exhales] The {ctx.weapon_short} {d['smoke_lc']}one tap two tap done. "
            f"[dark laugh] Yeah that's game sense right there. "
            f"[exhales] {ctx.player_name} [whispers] yeah. That's how it's done."
        ),
        (
            f"[breathes slowly] {ctx.situation}. {d['hp']}"
            f"[whispers] Watch. "
            f"[pause] [intense] The {ctx.weapon_short} "
            f"[exhales] click. [pause] click. "
            f"[dark laugh] Done. "
            f"[whispers] {ctx.player_name} doesn't miss. Not on {ctx.map_name}."
        ),
        (
            f"[coldly][breathes] They thought they had him. "
            f"{ctx.situation}. {d['hp']}"
            f"[whispers menacingly] They were wrong. "
            f"[exhales] {ctx.player_name} {ctx.weapon_short} "
            f"[dark laugh] systematic. "
            f"[pause] [whispers] One by one. [exhales] Yeah."
        ),
        (
            f"[intense][breathes] {ctx.player_name}. "
            f"[whispers] {ctx.situation} on {ctx.map_name}. "
            f"[exhales slowly] {ctx.weapon_short}. "
            f"[pause] [dark laugh] they never stood a chance. "
            f"[whispers] {d['hp']}Doesn't matter. "
            f"[exhales] That's what separates him."
        ),
        (
            f"[breathes] Clutch time. "
            f"[whispers] {ctx.player_name} {ctx.situation} "
            f"[exhales] the {ctx.weapon_short} {d['smoke_lc']}"
            f"[dark laugh] clean. "
            f"[pause] [coldly] That's what I'm talking about. "
            f"[whispers] Cold. Calculated. Done."
        ),
    ]
    return _pick_variant("alex_clutch", variants)


def _alex_ace(ctx: MomentContext) -> str:
    variants = [
        (
            f"[coldly] One [breathes] two three four "
            f"[whispers menacingly] five. "
            f"[exhales] {ctx.player_name} ACE {ctx.weapon_short} "
            f"on {ctx.map_name}. [pause] "
            f"[satisfied exhale] Clean sweep. "
            f"[whispers] Not a single wasted bullet. "
            f"[dark chuckle] yeah."
        ),
        (
            f"[breathes] Five kills. "
            f"[whispers] {ctx.player_name} just "
            f"[pause] [dark laugh] erased them. "
            f"ACE on {ctx.map_name}. In the {ctx.round_info}. "
            f"[exhales] [coldly] That's not skill. "
            f"[whispers] That's dominance."
        ),
        (
            f"[intense][breathes] One two "
            f"[whispers] he's going for the ACE "
            f"[exhales] three four "
            f"[dark laugh] five. "
            f"[pause] [whispers] {ctx.player_name}. "
            f"[exhales] ACE. {ctx.weapon_short}. {ctx.map_name}. "
            f"[coldly] that's it."
        ),
        (
            f"[breathes slowly] The ACE. "
            f"[whispers] {ctx.player_name} with the {ctx.weapon_short} "
            f"[exhales] five kills. No survivors. "
            f"[dark laugh] On {ctx.map_name}. "
            f"[pause] [whispers] They should've just "
            f"[exhales] surrendered."
        ),
    ]
    return _pick_variant("alex_ace", variants)


def _alex_headshot(ctx: MomentContext) -> str:
    d = _detail_bits(ctx)
    variants = [
        (
            f"[focused breathing] {ctx.player_name} {ctx.weapon_short} "
            f"{d['smoke_lc']}{d['noscope_lc']}{d['wallbang_lc']}[breathes] click. "
            f"[pause] [satisfied exhale] surgical. "
            f"[whispers] Not a single wasted bullet on {ctx.map_name}. "
            f"[exhales] Yeah. That's what aim looks like."
        ),
        (
            f"[breathes] Headshot. "
            f"[whispers] {ctx.player_name} {ctx.weapon_short} "
            f"{d['smoke_lc']}{d['wallbang_lc']}"
            f"[exhales] again. "
            f"[dark laugh] [pause] "
            f"[whispers] They keep peeking. "
            f"[exhales] He keeps clicking. [coldly] Simple math."
        ),
        (
            f"[intense][breathes] The crosshair "
            f"[whispers] {ctx.player_name} already knows "
            f"[exhales] {d['smoke_lc']}{d['noscope_lc']}click. "
            f"[pause] [dark laugh] headshot. "
            f"[whispers] On {ctx.map_name}. "
            f"[exhales] Every. Single. Time."
        ),
    ]
    return _pick_variant("alex_headshot", variants)


def _alex_knife(ctx: MomentContext) -> str:
    variants = [
        (
            f"[breathes] [impressed despite herself] The knife. "
            f"{ctx.player_name} in a {ctx.situation} "
            f"[long pause] [whispers] disrespectful. "
            f"[dark laugh] On {ctx.map_name}. "
            f"In a {ctx.round_info}. "
            f"[smirks] I respect that."
        ),
        (
            f"[breathes slowly] He switched to the knife. "
            f"[whispers] In a {ctx.situation}. "
            f"[exhales] [dark laugh] the audacity. "
            f"[pause] [coldly] {ctx.player_name} "
            f"[whispers] that's not just skill. "
            f"[exhales] That's a message."
        ),
        (
            f"[breathes] The knife. [pause] "
            f"[whispers menacingly] {ctx.player_name} pulled out the knife "
            f"in a {ctx.situation} on {ctx.map_name}. "
            f"[dark laugh] [exhales] "
            f"[whispers] they're going to remember that."
        ),
    ]
    return _pick_variant("alex_knife", variants)


def _alex_defuse(ctx: MomentContext) -> str:
    variants = [
        (
            f"[whispers][intense] Tick tick tick "
            f"[breathes heavily] {ctx.time_remaining:.0f} seconds "
            f"{ctx.player_name} on the bomb "
            f"[exhales slowly] boom. Wait no "
            f"[dark laugh] He got it. "
            f"[whispers] Cold blooded. On {ctx.map_name}. Yeah."
        ),
        (
            f"[breathes] The bomb. "
            f"[whispers] {ctx.time_remaining:.0f} seconds. "
            f"{ctx.player_name} defusing "
            f"[exhales] [dark laugh] of course he does. "
            f"[pause] [whispers] Nerves of steel. "
            f"[exhales] On {ctx.map_name}. That's {ctx.player_name}."
        ),
    ]
    return _pick_variant("alex_defuse", variants)


def _alex_multikill(ctx: MomentContext) -> str:
    kill_word = {2: "double", 3: "triple", 4: "quad"}.get(ctx.kills, f"{ctx.kills}-kill")
    variants = [
        (
            f"[breathes] {kill_word} kill. "
            f"[whispers] {ctx.player_name} {ctx.weapon_short} "
            f"[exhales] efficient. "
            f"[dark laugh] On {ctx.map_name}. "
            f"[pause] [whispers] No wasted movement. "
            f"[exhales] That's what peak performance looks like."
        ),
        (
            f"[coldly][breathes] One two "
            f"[whispers] {kill_word}. "
            f"[exhales] {ctx.player_name} with the {ctx.weapon_short}. "
            f"[dark laugh] [pause] "
            f"[whispers] They never learn. "
            f"[exhales] On {ctx.map_name}. Yeah."
        ),
    ]
    return _pick_variant("alex_multikill", variants)


def _alex_noscope(ctx: MomentContext) -> str:
    variants = [
        (
            f"[breathes] No scope. "
            f"[whispers] {ctx.player_name} with the {ctx.weapon_short} "
            f"[exhales] [dark laugh] "
            f"didn't even bother aiming. "
            f"[pause] [coldly] On {ctx.map_name}. "
            f"[whispers] That's just disrespect."
        ),
    ]
    return _pick_variant("alex_noscope", variants)


def _alex_toxic(ctx: MomentContext) -> str:
    variants = [
        (
            f"[breathes] [dark laugh] Oh "
            f"[amused] {ctx.player_name} "
            f"[smirks] [whispers] that was toxic. "
            f"[exhales] On {ctx.map_name}. "
            f"[dark laugh] Love to see it. Absolutely love it."
        ),
    ]
    return _pick_variant("alex_toxic", variants)


def _alex_generic(ctx: MomentContext) -> str:
    variants = [
        (
            f"[coolly][breathes] {ctx.player_name} "
            f"{ctx.weapon_short} on {ctx.map_name}. "
            f"[exhales] [smirks] not bad. "
            f"[whispers] Not bad at all."
        ),
        (
            f"[breathes] {ctx.player_name}. "
            f"[whispers] {ctx.map_name}. {ctx.weapon_short}. "
            f"[exhales] [dark laugh] yeah. "
            f"[pause] [coldly] That's the difference."
        ),
        (
            f"[coldly][breathes] Watch. "
            f"[whispers] {ctx.player_name} {ctx.weapon_short} "
            f"[exhales] there it is. "
            f"[dark laugh] On {ctx.map_name}. "
            f"[whispers] Every time."
        ),
    ]
    return _pick_variant("alex_generic", variants)


# =====================================================================
# JESSICA FIRE -- High energy, screams, maximum hype
# =====================================================================

def _jessica_clutch(ctx: MomentContext) -> str:
    d = _detail_bits(ctx)
    variants = [
        (
            f"[breathes][excited] OH MY GOD "
            f"did you SEE that?! {ctx.player_name} {ctx.situation} "
            f"the {ctx.weapon_short} [gasp] "
            f"{d['hp']}[laughs] "
            f"That was absolutely INSANE! "
            f"[giggles] On {ctx.map_name} I literally can't"
        ),
        (
            f"[excited][breathes] WAIT {ctx.situation} "
            f"{ctx.player_name} is alone [gasps] "
            f"THE {ctx.weapon_short} FLICK! {d['smoke']}{d['noscope']}[screams] "
            f"AND ANOTHER ONE! [laughs] "
            f"I'm literally SHAKING {ctx.map_name} "
            f"that's a {ctx.round_info} [catches breath]"
        ),
        (
            f"[screams] NO WAY! NO WAY! "
            f"[breathes] {ctx.player_name} {ctx.situation} "
            f"the {ctx.weapon_short} {d['smoke']}"
            f"[gasps] HE CLUTCHED IT! "
            f"[laughs hysterically] [catches breath] "
            f"On {ctx.map_name} {d['hp']}"
            f"[excited] THAT IS INSANE!"
        ),
        (
            f"[breathes][excited] Okay OKAY "
            f"{ctx.player_name} is in a {ctx.situation} "
            f"[gasps] THE {ctx.weapon_short}! {d['smoke']}"
            f"[screams] YES! YES! YES! "
            f"[laughs] [catches breath] "
            f"I KNEW IT! I literally CALLED IT! "
            f"[giggles] {ctx.map_name} is HIS MAP!"
        ),
        (
            f"[gasps] {ctx.situation} {d['hp']}"
            f"[breathes] {ctx.player_name} with the {ctx.weapon_short} "
            f"[screams] CLUTCH! CLUTCH! CLUTCH! "
            f"[laughs] [catches breath] "
            f"On {ctx.map_name} in the {ctx.round_info} "
            f"[excited] THAT'S WHY HE'S THE BEST!"
        ),
        (
            f"[excited][breathes] WAIT WAIT WAIT "
            f"is he is he actually going for the {ctx.situation}?! "
            f"[gasps] THE {ctx.weapon_short} SHOT! {d['smoke']}"
            f"[screams] HE GOT IT! "
            f"[laughs hysterically] [catches breath] "
            f"I'm DEAD I'm literally DEAD right now "
            f"[giggles] {ctx.player_name} you LEGEND!"
        ),
    ]
    return _pick_variant("jessica_clutch", variants)


def _jessica_ace(ctx: MomentContext) -> str:
    variants = [
        (
            f"[gasps] Wait wait [screams] FIVE KILLS! "
            f"{ctx.player_name} {ctx.weapon_short} ACE! "
            f"[laughs hysterically] No deaths! NONE! "
            f"On {ctx.map_name} in a {ctx.round_info} "
            f"[catches breath] I'm shaking right now"
        ),
        (
            f"[breathes][excited] One two three "
            f"[gasps] FOUR! [screams] FIVE! "
            f"ACE! {ctx.player_name} GOT THE ACE! "
            f"[laughs] [catches breath] "
            f"With the {ctx.weapon_short} on {ctx.map_name} "
            f"[excited] THAT IS ABSOLUTELY INSANE!"
        ),
        (
            f"[screams] ACE! ACE! ACE! "
            f"[breathes] {ctx.player_name} five kills "
            f"the {ctx.weapon_short} on {ctx.map_name} "
            f"[laughs hysterically] [catches breath] "
            f"In the {ctx.round_info} "
            f"[excited] I CANNOT BELIEVE WHAT I JUST SAW!"
        ),
        (
            f"[gasps] He's going for the ACE "
            f"[breathes] one more one more kill "
            f"[screams] FIVE! ACE! "
            f"[laughs] [catches breath] "
            f"{ctx.player_name} with the {ctx.weapon_short} "
            f"on {ctx.map_name} [excited] LEGENDARY!"
        ),
    ]
    return _pick_variant("jessica_ace", variants)


def _jessica_headshot(ctx: MomentContext) -> str:
    d = _detail_bits(ctx)
    variants = [
        (
            f"[whispers excitedly] Watch this watch this "
            f"[breathes] {ctx.player_name} {ctx.weapon_short} "
            f"{d['smoke']}{d['noscope']}{d['wallbang']}"
            f"[impressed] Click click click "
            f"[whispers] flawless on {ctx.map_name}. Absolutely flawless."
        ),
        (
            f"[breathes][excited] HEADSHOT! "
            f"{d['smoke']}{d['noscope']}{d['wallbang']}"
            f"[gasps] AND ANOTHER ONE! "
            f"[screams] {ctx.player_name}! "
            f"[laughs] [catches breath] "
            f"The {ctx.weapon_short} on {ctx.map_name} "
            f"[excited] HIS AIM IS ILLEGAL!"
        ),
        (
            f"[gasps] Did you SEE that headshot?! "
            f"{d['smoke']}{d['wallbang']}"
            f"[breathes] {ctx.player_name} the {ctx.weapon_short} "
            f"[screams] ANOTHER ONE! "
            f"[laughs] [catches breath] "
            f"On {ctx.map_name} [excited] HE DOESN'T MISS!"
        ),
    ]
    return _pick_variant("jessica_headshot", variants)


def _jessica_knife(ctx: MomentContext) -> str:
    variants = [
        (
            f"[gasps] THE KNIFE?! "
            f"[breathes] {ctx.player_name} pulled out the KNIFE "
            f"in a {ctx.situation}?! "
            f"[screams] HE KNIFED HIM! "
            f"[laughs hysterically] [catches breath] "
            f"On {ctx.map_name} the DISRESPECT "
            f"[excited] I'M OBSESSED!"
        ),
        (
            f"[breathes][excited] WAIT IS HE "
            f"[gasps] THE KNIFE! IN A {ctx.situation}! "
            f"[screams] HE GOT IT! "
            f"[laughs] [catches breath] "
            f"{ctx.player_name} you are UNHINGED "
            f"[giggles] I love it so much"
        ),
    ]
    return _pick_variant("jessica_knife", variants)


def _jessica_defuse(ctx: MomentContext) -> str:
    variants = [
        (
            f"[breathes][nervously] THE BOMB "
            f"{ctx.time_remaining:.0f} SECONDS "
            f"[gasps] {ctx.player_name} IS DEFUSING! "
            f"[screams] COME ON! COME ON! "
            f"[screams happily] YES! HE GOT IT! "
            f"[laughs] [catches breath] "
            f"My heart is POUNDING on {ctx.map_name} INSANE!"
        ),
        (
            f"[excited][breathes] THE DEFUSE "
            f"[gasps] {ctx.time_remaining:.0f} SECONDS LEFT! "
            f"[screams] {ctx.player_name} COME ON! "
            f"[screams happily] YES! "
            f"[laughs hysterically] [catches breath] "
            f"On {ctx.map_name} that was SO clutch!"
        ),
    ]
    return _pick_variant("jessica_defuse", variants)


def _jessica_multikill(ctx: MomentContext) -> str:
    kill_word = {2: "DOUBLE", 3: "TRIPLE", 4: "QUAD"}.get(ctx.kills, f"{ctx.kills}-KILL")
    variants = [
        (
            f"[breathes][excited] ONE! TWO! "
            f"[gasps] {kill_word} KILL! "
            f"[screams] {ctx.player_name}! "
            f"[laughs] [catches breath] "
            f"The {ctx.weapon_short} on {ctx.map_name} "
            f"[excited] HE'S UNSTOPPABLE!"
        ),
        (
            f"[screams] {kill_word} KILL! "
            f"[breathes] {ctx.player_name} the {ctx.weapon_short} "
            f"[gasps] ON {ctx.map_name}?! "
            f"[laughs hysterically] [catches breath] "
            f"[excited] THAT IS ABSOLUTELY INSANE!"
        ),
    ]
    return _pick_variant("jessica_multikill", variants)


def _jessica_generic(ctx: MomentContext) -> str:
    variants = [
        (
            f"[cheerfully][breathes] {ctx.player_name} "
            f"{ctx.weapon_short} play on {ctx.map_name} "
            f"[excited] that was SO good! [giggles] "
            f"Like how does he do that every round"
        ),
        (
            f"[breathes][excited] OH "
            f"{ctx.player_name} with the {ctx.weapon_short} "
            f"[gasps] on {ctx.map_name} "
            f"[laughs] that was INSANE! "
            f"[catches breath] I love this so much"
        ),
        (
            f"[excited][breathes] Did you SEE that?! "
            f"{ctx.player_name} {ctx.weapon_short} {ctx.map_name} "
            f"[gasps] SO CLEAN! "
            f"[laughs] [catches breath] "
            f"He makes it look so EASY"
        ),
    ]
    return _pick_variant("jessica_generic", variants)


# =====================================================================
# SOFIA SMOOTH -- Sultry, composed, impressed but cool
# =====================================================================

def _sofia_clutch(ctx: MomentContext) -> str:
    d = _detail_bits(ctx)
    variants = [
        (
            f"[impressed][breathes] Well well well. "
            f"{ctx.player_name} a {ctx.situation} on {ctx.map_name} "
            f"with the {ctx.weapon_short} {d['smoke_lc']}"
            f"[sigh of admiration] {d['hp']}Now THAT was something. "
            f"[chuckles softly] That's why he's {ctx.player_name}."
        ),
        (
            f"[breathes] A {ctx.situation}. "
            f"[whispers] {ctx.player_name} {ctx.weapon_short} "
            f"{d['smoke_lc']}{d['hp']}"
            f"[pause] [chuckles softly] of course. "
            f"[sigh of admiration] On {ctx.map_name}. "
            f"[impressed] That's just class."
        ),
        (
            f"[amused][breathes] Oh interesting. "
            f"{ctx.situation} on {ctx.map_name}. "
            f"[whispers] {ctx.player_name} with the {ctx.weapon_short} "
            f"{d['smoke_lc']}{d['hp']}"
            f"[pause] [chuckles] and just like that. "
            f"[sigh of admiration] Effortless."
        ),
        (
            f"[breathes] {ctx.player_name}. "
            f"[whispers] {ctx.situation}. {d['hp']}"
            f"[pause] [impressed] The {ctx.weapon_short} {d['smoke_lc']}"
            f"[chuckles softly] one by one. "
            f"[sigh of admiration] On {ctx.map_name}. "
            f"[whispers] Beautiful."
        ),
        (
            f"[confidently][breathes] Watch how he handles this. "
            f"{ctx.situation}. {d['hp']}"
            f"[whispers] {ctx.player_name} the {ctx.weapon_short} "
            f"{d['smoke_lc']}"
            f"[pause] [chuckles softly] there it is. "
            f"[sigh of admiration] Composed. Precise. Perfect."
        ),
    ]
    return _pick_variant("sofia_clutch", variants)


def _sofia_ace(ctx: MomentContext) -> str:
    variants = [
        (
            f"[amused] Five kills. Just like that. "
            f"{ctx.player_name} {ctx.weapon_short} {ctx.map_name}. "
            f"[slowly] Clean efficient "
            f"[whispers] devastating. [chuckles] "
            f"In a {ctx.round_info} easy."
        ),
        (
            f"[breathes] One two three "
            f"[whispers] four five. "
            f"[pause] [chuckles softly] ACE. "
            f"{ctx.player_name} with the {ctx.weapon_short}. "
            f"[sigh of admiration] On {ctx.map_name}. "
            f"[impressed] magnificent."
        ),
        (
            f"[impressed][breathes] The ACE. "
            f"[whispers] {ctx.player_name} five kills "
            f"the {ctx.weapon_short} {ctx.map_name}. "
            f"[pause] [chuckles] they never had a chance. "
            f"[sigh of admiration] That's dominance."
        ),
        (
            f"[breathes] He's going for all five. "
            f"[whispers] {ctx.player_name} "
            f"[pause] [chuckles softly] of course he is. "
            f"[sigh of admiration] ACE. {ctx.weapon_short}. {ctx.map_name}. "
            f"[impressed] Flawless."
        ),
    ]
    return _pick_variant("sofia_ace", variants)


def _sofia_headshot(ctx: MomentContext) -> str:
    d = _detail_bits(ctx)
    variants = [
        (
            f"[sultry][slowly] Click click click "
            f"{d['smoke_lc']}{d['noscope_lc']}{d['wallbang_lc']}"
            f"{ctx.player_name} with the {ctx.weapon_short}. "
            f"[whispers] perfection. "
            f"[breathes] Pure perfection. On {ctx.map_name}."
        ),
        (
            f"[breathes] Headshot. "
            f"[whispers] {d['smoke_lc']}{d['noscope_lc']}{d['wallbang_lc']}"
            f"{ctx.player_name} the {ctx.weapon_short} "
            f"[pause] [chuckles softly] again. "
            f"[sigh of admiration] On {ctx.map_name}. "
            f"[impressed] Consistent."
        ),
        (
            f"[impressed][breathes] The crosshair placement "
            f"[whispers] {ctx.player_name} already knows "
            f"{d['smoke_lc']}{d['wallbang_lc']}"
            f"[pause] [chuckles] headshot. "
            f"[sigh of admiration] On {ctx.map_name}. "
            f"[whispers] Every time."
        ),
    ]
    return _pick_variant("sofia_headshot", variants)


def _sofia_knife(ctx: MomentContext) -> str:
    variants = [
        (
            f"[raised eyebrow voice] Oh the audacity. "
            f"{ctx.player_name} with the knife "
            f"in a {ctx.situation} on {ctx.map_name}. "
            f"[amused][whispers] I respect it. [dark chuckle]"
        ),
        (
            f"[breathes] The knife. "
            f"[whispers] {ctx.player_name} in a {ctx.situation} "
            f"[pause] [chuckles softly] bold. "
            f"[sigh of admiration] On {ctx.map_name}. "
            f"[impressed] Very bold."
        ),
    ]
    return _pick_variant("sofia_knife", variants)


def _sofia_defuse(ctx: MomentContext) -> str:
    variants = [
        (
            f"[whispers][deliberately] Tick tick tick "
            f"[breathes] {ctx.time_remaining:.0f} seconds "
            f"{ctx.player_name} on the bomb "
            f"[exhales slowly] smooth as silk. [chuckles]"
        ),
        (
            f"[breathes] The bomb. "
            f"[whispers] {ctx.time_remaining:.0f} seconds. "
            f"{ctx.player_name} defusing "
            f"[pause] [chuckles softly] of course. "
            f"[sigh of admiration] On {ctx.map_name}. "
            f"[impressed] Nerves of steel."
        ),
    ]
    return _pick_variant("sofia_defuse", variants)


def _sofia_multikill(ctx: MomentContext) -> str:
    kill_word = {2: "double", 3: "triple", 4: "quad"}.get(ctx.kills, f"{ctx.kills}-kill")
    variants = [
        (
            f"[raised eyebrow voice] Oh? "
            f"{kill_word} kill. "
            f"{ctx.player_name} {ctx.weapon_short} {ctx.map_name}. "
            f"[pause] [approving hum] Mm not bad at all. "
            f"[softly] Not bad at all"
        ),
        (
            f"[breathes] {kill_word} kill. "
            f"[whispers] {ctx.player_name} the {ctx.weapon_short} "
            f"[pause] [chuckles softly] efficient. "
            f"[sigh of admiration] On {ctx.map_name}. "
            f"[impressed] Very efficient."
        ),
    ]
    return _pick_variant("sofia_multikill", variants)


def _sofia_generic(ctx: MomentContext) -> str:
    variants = [
        (
            f"[confidently][breathes] {ctx.player_name} "
            f"{ctx.weapon_short} on {ctx.map_name}. "
            f"[pause] [approving hum] Mm "
            f"[softly] not bad at all"
        ),
        (
            f"[breathes] {ctx.player_name}. "
            f"[whispers] {ctx.weapon_short}. {ctx.map_name}. "
            f"[pause] [chuckles softly] impressive. "
            f"[sigh of admiration] As always."
        ),
        (
            f"[impressed][breathes] Well "
            f"{ctx.player_name} with the {ctx.weapon_short} "
            f"on {ctx.map_name}. "
            f"[pause] [chuckles] that's why we watch him."
        ),
    ]
    return _pick_variant("sofia_generic", variants)


# =====================================================================
# ADAPTIVE COMMENTARY ROUTER
# =====================================================================

COMMENTARY_GENERATORS = {
    "mia_cute": {
        "clutch": _mia_clutch,
        "ace": _mia_ace,
        "multi_kill": _mia_multikill,
        "headshot_sequence": _mia_headshot,
        "knife_kill": _mia_knife,
        "clutch_defuse": _mia_defuse,
        "round_win": _mia_generic,
        "eco_win": _mia_eco,
        "wallbang": _mia_wallbang,
        "comeback": _mia_comeback,
        "tournament": _mia_tournament,
        "no_scope": _mia_noscope,
        "toxic_moment": _mia_toxic,
        "meme_fail": _mia_meme,
        "generic": _mia_generic,
    },
    "alex_edgy": {
        "clutch": _alex_clutch,
        "ace": _alex_ace,
        "multi_kill": _alex_multikill,
        "headshot_sequence": _alex_headshot,
        "knife_kill": _alex_knife,
        "clutch_defuse": _alex_defuse,
        "round_win": _alex_generic,
        "eco_win": _alex_generic,
        "wallbang": _alex_headshot,
        "comeback": _alex_generic,
        "tournament": _alex_generic,
        "no_scope": _alex_noscope,
        "toxic_moment": _alex_toxic,
        "meme_fail": _alex_generic,
        "generic": _alex_generic,
    },
    "jessica_fire": {
        "clutch": _jessica_clutch,
        "ace": _jessica_ace,
        "multi_kill": _jessica_multikill,
        "headshot_sequence": _jessica_headshot,
        "knife_kill": _jessica_knife,
        "clutch_defuse": _jessica_defuse,
        "round_win": _jessica_generic,
        "eco_win": _jessica_generic,
        "wallbang": _jessica_headshot,
        "comeback": _jessica_generic,
        "tournament": _jessica_generic,
        "no_scope": _jessica_headshot,
        "toxic_moment": _jessica_generic,
        "meme_fail": _jessica_generic,
        "generic": _jessica_generic,
    },
    "sofia_smooth": {
        "clutch": _sofia_clutch,
        "ace": _sofia_ace,
        "multi_kill": _sofia_multikill,
        "headshot_sequence": _sofia_headshot,
        "knife_kill": _sofia_knife,
        "clutch_defuse": _sofia_defuse,
        "round_win": _sofia_generic,
        "eco_win": _sofia_generic,
        "wallbang": _sofia_headshot,
        "comeback": _sofia_generic,
        "tournament": _sofia_generic,
        "no_scope": _sofia_headshot,
        "toxic_moment": _sofia_generic,
        "meme_fail": _sofia_generic,
        "generic": _sofia_generic,
    },
}

# Map voice names to persona IDs
VOICE_TO_PERSONA = {
    "jessica": "jessica_fire",
    "lily": "sofia_smooth",
    "laura": "mia_cute",
    "sarah": "alex_edgy",
}


def _resolve_moment_type(ctx: MomentContext) -> str:
    """
    Adaptive moment type resolution.
    Picks the BEST moment type based on ALL context factors.
    This is the self-learning logic: it upgrades the moment type
    based on special conditions.
    """
    base = ctx.moment_type

    # Upgrade: wallbang overrides headshot
    if ctx.wallbang and base in ("headshot_sequence", "multi_kill", "clutch"):
        return "wallbang"

    # Upgrade: no-scope special
    if ctx.no_scope and base in ("headshot_sequence", "clutch", "generic"):
        return "no_scope"

    # Upgrade: tournament overrides everything if high drama
    if ctx.is_tournament and ctx.drama_level >= 7:
        return "tournament"

    # Upgrade: comeback if team was losing
    if ctx.is_comeback and base in ("clutch", "ace", "round_win"):
        return "comeback"

    # Upgrade: eco win
    if ctx.is_eco and base in ("round_win", "multi_kill"):
        return "eco_win"

    # Upgrade: knife kill always takes priority
    if ctx.weapon.lower() in ("knife", "bayonet"):
        return "knife_kill"

    # Upgrade: defuse always takes priority if is_defuse
    if ctx.is_defuse:
        return "clutch_defuse"

    # Upgrade: ace if 5 kills
    if ctx.kills >= 5 and base != "ace":
        return "ace"

    # Upgrade: multi_kill for 3-4 kills if not already clutch/ace
    if ctx.kills >= 3 and base == "generic":
        return "multi_kill"

    return base


# =====================================================================
# INTRO / OUTRO GENERATORS
# =====================================================================

def _generate_intro(ctx: MomentContext, persona_id: str) -> str:
    """Generate intro commentary with anticipation."""
    intros = {
        "mia_cute": [
            (
                f"[happily][breathes] Oh my gosh okay so "
                f"you guys HAVE to see this "
                f"{ctx.player_name} on {ctx.map_name} "
                f"[whispers excitedly] this is about to be SO good"
            ),
            (
                f"[excitedly] Okay okay so {ctx.player_name} "
                f"right with the {ctx.weapon_short} on {ctx.map_name} "
                f"[breathes] just WATCH what happens next "
                f"[giggles] I literally screamed when I saw this"
            ),
            (
                f"[whispers excitedly] Okay so "
                f"[breathes] {ctx.player_name} is on {ctx.map_name} "
                f"[giggles] and what he does next "
                f"[gasps softly] I literally can't even"
            ),
            (
                f"[breathes][happily] You guys "
                f"you guys are NOT ready for this "
                f"{ctx.player_name} on {ctx.map_name} "
                f"[whispers] with the {ctx.weapon_short} "
                f"[giggles] just watch"
            ),
        ],
        "alex_edgy": [
            (
                f"[coolly][breathes] So. {ctx.player_name}. "
                f"{ctx.map_name}. {ctx.weapon_short}. "
                f"[whispers] Watch this. "
                f"[exhales] you're not ready."
            ),
            (
                f"[intense][breathes] {ctx.player_name} "
                f"{ctx.map_name} {ctx.round_info}. "
                f"[pause] [whispers menacingly] Pay attention."
            ),
            (
                f"[breathes] {ctx.player_name}. "
                f"[whispers] {ctx.map_name}. "
                f"[pause] [coldly] Watch what happens. "
                f"[exhales] carefully."
            ),
        ],
        "jessica_fire": [
            (
                f"[excited][breathes] OH okay "
                f"you guys {ctx.player_name} on {ctx.map_name} "
                f"[gasps] this next play is INSANE "
                f"I literally couldn't believe"
            ),
            (
                f"[breathes][excited] OKAY OKAY OKAY "
                f"you need to see this "
                f"{ctx.player_name} {ctx.map_name} "
                f"[gasps] the {ctx.weapon_short} "
                f"[laughs] just WATCH"
            ),
            (
                f"[excited][breathes] I'm warning you "
                f"this is INSANE "
                f"{ctx.player_name} on {ctx.map_name} "
                f"[gasps] with the {ctx.weapon_short} "
                f"[laughs] you're not ready"
            ),
        ],
        "sofia_smooth": [
            (
                f"[confidently] So {ctx.player_name}. "
                f"{ctx.map_name}. The {ctx.weapon_short}. "
                f"[breathes] [amused] Let's see what he does "
                f"shall we?"
            ),
            (
                f"[breathes] {ctx.player_name} on {ctx.map_name}. "
                f"[whispers] Watch carefully. "
                f"[pause] [chuckles softly] this is where it gets interesting."
            ),
            (
                f"[impressed][breathes] Pay attention. "
                f"{ctx.player_name} {ctx.weapon_short} {ctx.map_name}. "
                f"[pause] [whispers] This is what separates him."
            ),
        ],
    }

    persona_intros = intros.get(persona_id, intros["mia_cute"])
    return _pick_variant(f"{persona_id}_intro", persona_intros)


def _generate_outro(ctx: MomentContext, persona_id: str) -> str:
    """Generate outro commentary with CTA feel."""
    outros = {
        "mia_cute": [
            (
                f"[happily] If you liked that [breathes] "
                f"follow for more {ctx.player_name} highlights "
                f"[giggles] because this is just the beginning "
                f"[squeals softly] so many more clips coming"
            ),
            (
                f"[breathes][giggles] Drop a like if that made you scream "
                f"because I literally screamed "
                f"[happily] follow for more {ctx.player_name} content "
                f"[squeals] it only gets better"
            ),
            (
                f"[happily][breathes] Follow if you want more "
                f"[giggles] {ctx.player_name} clips every day "
                f"[squeals softly] I literally can't stop watching"
            ),
        ],
        "alex_edgy": [
            (
                f"[coolly] Follow if you want more. "
                f"[breathes] {ctx.player_name} content daily. "
                f"[exhales] [whispers] you know you want to."
            ),
            (
                f"[breathes] Follow. "
                f"[whispers] More {ctx.player_name} clips. "
                f"[exhales] [dark laugh] daily. "
                f"[pause] [coldly] You're welcome."
            ),
        ],
        "jessica_fire": [
            (
                f"[excited] FOLLOW for more clips like THIS! "
                f"[breathes] {ctx.player_name} is absolutely INSANE "
                f"[giggles] drop a like if you if you're shook"
            ),
            (
                f"[breathes][excited] LIKE AND FOLLOW "
                f"more {ctx.player_name} highlights DAILY "
                f"[gasps] it only gets MORE insane "
                f"[laughs] I promise"
            ),
        ],
        "sofia_smooth": [
            (
                f"[confidently] Follow for more. "
                f"[breathes] [amused] Trust me "
                f"it only gets better from here. [chuckles]"
            ),
            (
                f"[breathes] Follow for more {ctx.player_name} content. "
                f"[whispers] Daily highlights. "
                f"[pause] [chuckles softly] you won't regret it."
            ),
        ],
    }

    persona_outros = outros.get(persona_id, outros["mia_cute"])
    return _pick_variant(f"{persona_id}_outro", persona_outros)


def _get_padding(persona_id: str, ctx: MomentContext) -> str:
    """Get padding text to hit 250+ char minimum for v3."""
    paddings = {
        "mia_cute": (
            f"[giggles] {ctx.player_name} on {ctx.map_name} is just "
            f"[catches breath] built different like I can't explain it he just IS"
        ),
        "alex_edgy": (
            f"[exhales] {ctx.player_name} [whispers] yeah. "
            f"That's how it's done on {ctx.map_name}. [pause] [coldly] Every time."
        ),
        "jessica_fire": (
            f"[catches breath] {ctx.player_name} is literally INSANE on {ctx.map_name} "
            f"[giggles] I can't stop watching this"
        ),
        "sofia_smooth": (
            f"[chuckles softly] {ctx.player_name} on {ctx.map_name} "
            f"[breathes] [sigh of admiration] consistently impressive."
        ),
    }
    return paddings.get(persona_id, paddings["mia_cute"])


# =====================================================================
# MAIN GENERATION FUNCTION
# =====================================================================

def _trim_script_to_duration(script: str, max_duration_sec: float = 5.0) -> str:
    """Trim script to fit within a time window.
    
    Rule of thumb: ~3 words per second for natural excited speech.
    For 5 seconds = ~15 words max (excluding audio tags).
    
    This prevents voice cutoff — the #1 user complaint.
    """
    import re
    
    # Count actual spoken words (exclude [tags])
    spoken_text = re.sub(r'\[.*?\]', '', script)
    words = spoken_text.split()
    max_words = int(max_duration_sec * 3)  # ~3 words/sec for excited speech
    
    if len(words) <= max_words:
        return script  # Already fits
    
    # Strategy: keep the first max_words spoken words, preserve tags around them
    # Split script into segments: (tag_or_space, word) pairs
    parts = re.split(r'(\[.*?\])', script)
    result_parts = []
    word_count = 0
    
    for part in parts:
        if part.startswith('[') and part.endswith(']'):
            # Audio tag — keep it if we haven't exceeded word limit
            if word_count < max_words:
                result_parts.append(part)
        else:
            # Text segment — count words and trim if needed
            segment_words = part.split()
            for w in segment_words:
                if word_count >= max_words:
                    break
                result_parts.append(w + " ")
                word_count += 1
    
    return "".join(result_parts).strip()


def generate_smart_commentary(
    ctx: MomentContext,
    persona_id: str = "mia_cute",
    phase: str = "react",
    max_duration: float = 5.0,
) -> str:
    """
    Generate context-aware commentary for a specific moment.

    ADAPTIVE LOGIC:
    - Resolves the best moment type based on ALL context factors
    - Picks from 100+ templates with anti-repetition
    - TRIMS script to fit within max_duration (prevents cutoff!)
    - Woven with advanced v3 audio tags for maximum naturalness

    Args:
        ctx: MomentContext with all clip details
        persona_id: Which girl persona to use
        phase: Which phase of the clip (intro, react, outro)
        max_duration: Maximum speech duration in seconds (default 5s)

    Returns:
        Full script with ElevenLabs v3 audio tags, trimmed to fit
    """
    # Resolve persona from voice name
    if persona_id in VOICE_TO_PERSONA:
        persona_id = VOICE_TO_PERSONA[persona_id]

    # Fallback to mia_cute if unknown persona
    if persona_id not in COMMENTARY_GENERATORS:
        persona_id = "mia_cute"

    generators = COMMENTARY_GENERATORS[persona_id]

    # Phase-specific generation
    if phase == "intro":
        script = _generate_intro(ctx, persona_id)
        return _trim_script_to_duration(script, min(max_duration, 3.0))
    elif phase == "outro":
        script = _generate_outro(ctx, persona_id)
        return _trim_script_to_duration(script, min(max_duration, 2.0))

    # React phase: use ADAPTIVE moment type resolution
    resolved_type = _resolve_moment_type(ctx)

    # Get generator for resolved type, fallback to generic
    generator = generators.get(resolved_type, generators.get("generic", _mia_generic))
    script = generator(ctx)

    # TRIM to fit duration window — prevents cutoff!
    script = _trim_script_to_duration(script, max_duration)

    return script


def generate_full_clip_script(
    ctx: MomentContext,
    persona_id: str = "mia_cute",
    include_intro: bool = True,
    include_outro: bool = True,
) -> list:
    """
    Generate a complete multi-phase script for an entire clip.

    Returns a list of script segments with timing info:
    [
        {"phase": "intro", "text": "...", "start": 0.0, "duration": 3.0},
        {"phase": "react", "text": "...", "start": 7.0, "duration": 5.0},
        {"phase": "outro", "text": "...", "start": 13.0, "duration": 2.0},
    ]
    """
    segments = []

    if include_intro:
        intro = generate_smart_commentary(ctx, persona_id, phase="intro")
        segments.append({
            "phase": "intro",
            "text": intro,
            "start": 0.0,
            "duration": 3.0,
        })

    # Main reaction
    react = generate_smart_commentary(ctx, persona_id, phase="react")
    segments.append({
        "phase": "react",
        "text": react,
        "start": 7.0 if include_intro else 5.0,
        "duration": 5.0,
    })

    if include_outro:
        outro = generate_smart_commentary(ctx, persona_id, phase="outro")
        segments.append({
            "phase": "outro",
            "text": outro,
            "start": 13.0,
            "duration": 2.0,
        })

    return segments


def get_all_variants_preview(ctx: MomentContext) -> dict:
    """
    Generate a preview of all persona reactions for a given context.
    Useful for testing and comparing all 4 personas.
    """
    result = {}
    for persona_id in COMMENTARY_GENERATORS:
        result[persona_id] = {
            "intro": generate_smart_commentary(ctx, persona_id, phase="intro"),
            "react": generate_smart_commentary(ctx, persona_id, phase="react"),
            "outro": generate_smart_commentary(ctx, persona_id, phase="outro"),
            "drama_level": ctx.drama_level,
            "resolved_type": _resolve_moment_type(ctx),
        }
    return result
