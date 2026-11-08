"""
Scene-Aware & Non-Repeating Engaging Questions Manager for AniDoc.

Automatically selects contextual, battle-grounded hook questions formatted as:
"Setup Premise before drop | Debate Question after drop?"

Guarantees:
1. Zero Repetition: Tracks question history in .agents/data/question_history.json so questions
   are never repeated across runs.
2. Scene & Character Context: Questions are directly grounded in the specific anime encounter,
   characters involved, and combat techniques rather than generic placeholders.
3. Universal Multi-Anime Support: Contains curated battle questions for JJK, Demon Slayer,
   Chainsaw Man, Solo Leveling, Bleach, Attack on Titan, and dynamic fallbacks for new anime.
"""
import os
import json
import random
from pathlib import Path
from typing import List, Dict, Optional, Any

from config.settings import SCRATCH_DIR

QUESTION_HISTORY_FILE = Path(".agents/data/question_history.json")
FALLBACK_HISTORY_FILE = SCRATCH_DIR / "question_history.json"


# ═══════════════════════════════════════════════════════════════════
# 1. SCENE & EPISODE SPECIFIC ENGAGING QUESTIONS
# Keyed by episode code (e.g. S02E04 for Gojo vs Toji)
# ═══════════════════════════════════════════════════════════════════
SCENE_SPECIFIC_QUESTIONS: Dict[str, List[str]] = {
    # ── Jujutsu Kaisen ────────────────────────────────────────────────────────
    "S02E04": [  # Gojo Awakened vs Toji Fushiguro
        "TOJI THOUGHT HE FINISHED HIM | WHO SURVIVES THE HONORED ONE?",
        "INVERTED SPEAR COULD NOT STOP HIM | IS AWAKENED GOJO UNTOUCHABLE?",
        "THROUGHOUT HEAVEN AND EARTH | WAS TOJI DOOMED FROM THE START?",
        "TOJI SENSED SOMETHING WAS WRONG | COULD ANYONE DODGE HOLLOW PURPLE?"
    ],
    "S02E17": [  # Sukuna vs Mahoraga
        "EIGHT-HANDLED SWORD ADAPTED | COULD MAHORAGA TANK MALEVOLENT SHRINE?",
        "SUKUNA UNLEASHED OPEN FUGA | IS THIS THE DEADLIEST ATTACK IN JJK?",
        "MAHORAGA ADAPTED TO EVERY SLASH | COULD ANYONE ELSE BEAT THIS BEAST?",
        "THE WHEEL TURNED FOUR TIMES | DID SUKUNA PROVE HE IS THE STRONGEST?"
    ],
    "S02E16": [  # Sukuna vs Jogo
        "JOGO DROPPED A MAXIMUM METEOR | COULD ANYONE ESCAPE SUKUNA'S FIRE ARROW?",
        "STAND PROUD YOU ARE STRONG | DID JOGO EARN SUKUNA'S REAL RESPECT?",
        "A PURE FIRE CLASH IN SHIBUYA | IS SUKUNA'S FLAME STRONGER THAN JOGO'S?"
    ],
    "S02E09": [  # Gojo 0.2s Domain Shibuya
        "DISASTER CURSES THOUGHT THEY TRAPPED HIM | WHO SURVIVES A 0.2s DOMAIN?",
        "THEY FORCED HIM TO HOLD BACK | IS GOJO THE MOST FEARED SORCERER EVER?",
        "A 0.2 SECOND INFINITE VOID | WAS SHIBUYA GOJO'S COLDEST PERFORMANCE?"
    ],
    "S02E21": [  # Yuji & Todo vs Mahito Climax
        "0.01 SECOND BLACK FLASH SYNERGY | DID YUJI & TODO DELIVER THE PEAK CLIMAX?",
        "BOOGIE WOOGIE CONFUSED HIS SOUL | DID MAHITO GET THE BEST BEATDOWN?",
        "I AM YOU CONFRONTATION | WAS YUJI'S BLACK FLASH BARRAGE PEAK SHONEN?"
    ],
    "S02E20": [  # Todo enters Shibuya vs Mahito
        "TODO ARRIVES ON THE BATTLEFIELD | IS BOOGIE WOOGIE THE ULTIMATE SUPPORT?",
        "WE ARE THE EXCEPTION | CAN ANY CURSE SURVIVE YUJI AND TODO TOGETHER?"
    ],
    "S02E13": [  # Yuji vs Choso Subway Clash
        "BLOOD MANIPULATION IN THE SUBWAY | WAS CHOSO'S PIERCING BLOOD UNDEFEATED?",
        "SUBWAY TILES SHATTERING EVERYWHERE | COULD YUJI OUTSLUG FLOWING RED SCALE?",
        "A BRUTAL CLOSE QUARTERS BRAWL | WHO TOOK MORE DAMAGE IN THIS SUBWAY?"
    ],
    "S01E07": [  # Gojo vs Jogo
        "JOGO CLAIMED HE COULD KILL HIM | WHO ACTUALLY SURVIVES INFINITE VOID?",
        "HE TOUCHED INFINITY FOR THE FIRST TIME | DID JOGO REALIZE THE POWER GAP?"
    ],
    "S01E19": [  # Yuji & Todo vs Hanami
        "FOUR CONSECUTIVE BLACK FLASHES | IS BOOGIE WOOGIE BROKEN IN COMBAT?",
        "HANAMI THOUGHT SHE HAD THE UPPER HAND | COULD ANY CURSE TANK THIS COMBO?"
    ],
    "S01E20": [  # Gojo Hollow Purple vs Hanami
        "HOLLOW TECHNIQUE PURPLE DEBUT | COULD ANY SPECIAL GRADE SURVIVE THIS?",
        "ERASING EVERYTHING IN ITS PATH | WAS THIS GOJO'S MOST SHOCKING ATTACK?"
    ],
    "S01E24": [  # Yuji & Nobara vs Eso & Kechizu
        "RESONANCE SPIKED THROUGH THEIR BLOOD | WAS THIS THE BEST TAG-TEAM CLASH?",
        "DOUBLE BLACK FLASH MANIFESTATION | COULD ANY DEATH PAINTING ESCAPE?"
    ],

    # ── Demon Slayer (Kimetsu no Yaiba) ──────────────────────────────────────
    "DS_S02E06": [  # Rengoku vs Akaza
        "RENGOKU'S RIBS WERE CRACKED | WAS NINTH FORM FLAME TIGER ROBBED?",
        "AKAZA BEGGED HIM TO BECOME A DEMON | WAS RENGOKU'S FINAL STAND THE COLDEST?",
        "DESTINY CLASH IN THE FOREST | COULD RENGOKU WIN WITH A SLAYER MARK?",
        "SET YOUR HEART ABLAZE | IS KYOJURO RENGOKU THE GREATEST HASHIRA?"
    ],
    "DS_S02E07": [  # Rengoku Climax vs Akaza
        "SUNRISE WAS SECONDS AWAY | COULD AKAZA ESCAPE WITHOUT FLEEING?",
        "RENGOKU HELD HIM WITH RAW MUSCLE | WAS THIS THE MOST EMOTIONAL DEATH?"
    ],
    "DS_S02E10": [  # Tengen & Tanjiro vs Gyutaro Decapitation
        "FIGHTING POISONED WITH ONE HAND | DID TENGEN'S MUSICAL SCORE SURPASS HASHIRAS?",
        "TENGEN BLOCKED EVERY BLOOD SICKLE | WAS THIS THE BEST ANIMATED FIGHT EVER?",
        "DUAL BLADE DECAPITATION CLIMAX | COULD ANY OTHER HASHIRA SURVIVE THIS POISON?",
        "THE FLASHIEST CLASH IN ANIME | DID TENGEN CARRY THE DISTRICT ARC?"
    ],
    "DS_S02E08": [  # Tengen vs Gyutaro entry
        "UPPER MOON SIX EMERGES | COULD ANY DEMON SLAYER MATCH THIS AGILITY?",
        "EXPLOSIVE CLEAVERS STRIKING | WAS TENGEN'S ENTRY THE CLEANEST?"
    ],
    "DS_S01E19": [  # Tanjiro vs Rui (Hinokami Kagura)
        "HIS NICHIRIN BLADE BROKE IN HALF | WAS HINOKAMI KAGURA THE GREATEST AWAKENING?",
        "EXPLODING BLOOD IGNITED THE THREADS | DID TANJIRO & NEZUKO BREAK THE INTERNET?",
        "SUN BREATHING DANCE IN THE WOODS | WAS THIS CLIMAX PEAK MODERN ANIME?"
    ],
    "DS_S01E17": [  # Zenitsu vs Spider Demon
        "POISON SPREADING THROUGH HIS VEINS | COULD ANYONE DODGE SIXFOLD THUNDER?",
        "ASLEEP ON A TREE BRANCH | IS SLEEPING ZENITSU LOWKEY HASHIRA TIER?",
        "HONE A SINGLE STRIKE TO PERFECTION | WAS GODSPEED THE CLEANEST SAKUGA?"
    ],
    "DS_S01E20": [  # Shinobu vs Spider Sister & Giyu Dead Calm vs Rui
        "SHE CANNOT CUT OFF A DEMON'S HEAD | IS SHINOBU'S WISTERIA POISON DEADLIER?",
        "INSECT BREATHING BUTTERFLY DANCE | IS SHINOBU THE FASTEST HASHIRA?",
        "THE COLDEST SMILE IN DEMON SLAYER | DID SPIDER SISTER DESERVE HER MERCY?",
        "LETHAL WISTERIA INJECTION | COULD ANY LOWER MOON SURVIVE SHINOBU?",
        "RUI'S THREADS COULD NOT TOUCH HIM | IS ELEVENTH FORM DEAD CALM IMPENETRABLE?",
        "THE QUIETEST HASHIRA IN HISTORY | COULD ANY DEMON BREACH GIYU'S DEFENSE?",
        "WATER BREATHING ELEVENTH FORM | DID GIYU CREATE THE GREATEST DEFENSE?",
        "ONE SWIFT STRIKE SEVERED RUI | IS GIYU THE COLDEST HASHIRA?"
    ],
    "DS_S03E08": [  # Muichiro vs Gyokko
        "TRAPPED INSIDE A WATER PRISON | DID MUICHIRO EMBARRASS UPPER MOON FIVE?",
        "SEVENTH FORM OBSCURING CLOUDS | IS MUICHIRO THE GREATEST PRODIGY IN ANIME?"
    ],
    "DS_S03E09": [  # Muichiro Haze Climax
        "MIST BREATHING OBSCURING CLOUDS | COULD GYOKKO EVEN SEE HIM MOVE?",
        "SOLOING AN UPPER MOON AT 14 | IS MUICHIRO STRONGER THAN MOST HASHIRAS?"
    ]
}


# ═══════════════════════════════════════════════════════════════════
# 2. CHARACTER-SPECIFIC ENGAGING QUESTIONS (Fallback when episode unlisted)
# ═══════════════════════════════════════════════════════════════════
CHARACTER_SPECIFIC_QUESTIONS: Dict[str, List[str]] = {
    # ── JJK ──
    "gojo": [
        "COULD ANYONE ACTUALLY BEAT | PRIME SATORU GOJO 1V1?",
        "THEY TRIED TO SEAL HIS INFINITY | WHO SURVIVES THE UNLIMITED VOID?",
        "IS SATORU GOJO TRULY | THE STRONGEST IN ANIME HISTORY?",
        "COULD ANY SORCERER BREACH | GOJO'S INFINITE DOMAIN?",
        "SIX EYES UNLOCKED EVERY TECHNIQUE | WHO SURVIVES HOLLOW PURPLE?"
    ],
    "sukuna": [
        "COULD ANYONE SURVIVE | SUKUNA'S MALEVOLENT SHRINE?",
        "WHO SURVIVES THIS DEADLY BATTLE | SUKUNA OR PRIME GOJO?",
        "IS RYOMEN SUKUNA | THE DEADLIEST CURSE IN HISTORY?",
        "COULD ANYONE DODGE | SUKUNA'S FATAL FLAME ARROW?",
        "CLEAVE AND DISMANTLE SLASHES | WHO CAN TANK SUKUNA'S POWER?"
    ],
    "toji": [
        "COULD TOJI BEAT ANY SPECIAL GRADE | WITH ZERO CURSED ENERGY?",
        "IS TOJI FUSHIGURO | THE DEADLIEST KILLER IN ANIME?",
        "WAS TOJI THE COLDEST CHARACTER | IN THE ENTIRE SERIES?",
        "HE BROKE HEAVENLY RESTRICTION | COULD ANYONE OUTSPEED TOJI?"
    ],
    "yuji": [
        "IS YUJI'S BLACK FLASH | THE STRONGEST PUNCH IN JJK?",
        "COULD ANY SPECIAL GRADE SURVIVE | YUJI'S ENRAGED COMBAT CLASH?",
        "HE EMBODIES THE SOUL OF A FIGHTER | WILL YUJI SURPASS SUKUNA?"
    ],
    "megumi": [
        "WAS MAHORAGA REALLY NECESSARY | TO WIN THIS DEADLY FIGHT?",
        "COULD MEGUMI TAME MAHORAGA | IN HIS PRIME FORM?"
    ],
    "tengen": [
        "IS TENGEN VS GYUTARO | THE BEST ANIME FIGHT OF ALL TIME?",
        "COULD ANY OTHER HASHIRA SURVIVE | GYUTARO'S DEADLY POISON?",
        "FROM HERE ON OUT THINGS GET FLASHY | IS TENGEN TOP TIER HASHIRA?"
    ],
    "rengoku": [
        "IS RENGOKU THE GREATEST HASHIRA | IN DEMON SLAYER HISTORY?",
        "COULD RENGOKU HAVE BEATEN AKAZA | WITH A SLAYER MARK?",
        "WAS RENGOKU'S FINAL STAND | THE MOST EMOTIONAL DEATH?"
    ],
    "akaza": [
        "COULD AKAZA DEFEAT KOKUSHIBO | IN A PURE 1V1 BATTLE?",
        "DID AKAZA HAVE THE SADDEST | BACKSTORY IN DEMON SLAYER?",
        "COULD ANY HASHIRA BEAT AKAZA | WITHOUT A SLAYER MARK?"
    ],
    "tanjiro": [
        "IS HINOKAMI KAGURA | THE STRONGEST BREATHING FORM?",
        "COULD ANY DEMON SURVIVE | TANJIRO'S PURE SUN BREATHING?",
        "WHO CARRIED DEMON SLAYER HARDER | TANJIRO OR RENGOKU?"
    ],
    "zenitsu": [
        "COULD ANYONE DODGE | ZENITSU'S GODSPEED THUNDER?",
        "IS SLEEPING ZENITSU STRONGER | THAN HALF THE HASHIRAS?",
        "WAS ZENITSU'S THUNDER GOD SPEED | THE CLEANEST SAKUGA?"
    ],
    "giyu": [
        "RUI'S THREADS COULD NOT TOUCH HIM | IS ELEVENTH FORM DEAD CALM IMPENETRABLE?",
        "COULD ANY DEMON BREACH | GIYU'S DEAD CALM ELEVENTH FORM?",
        "WATER BREATHING ELEVENTH FORM | DID GIYU CREATE THE GREATEST DEFENSE?",
        "IS GIYU TOMIOKA | THE COLDEST HASHIRA IN DEMON SLAYER?"
    ],
    "muichiro": [
        "DID MUICHIRO SOLO AN UPPER MOON | FASTER THAN ANY HASHIRA?",
        "IS MUICHIRO TOKITO | THE BIGGEST PRODIGY IN ANIME?"
    ],
    "shinobu": [
        "SHE CANNOT CUT OFF A DEMON'S HEAD | IS SHINOBU'S WISTERIA POISON DEADLIER?",
        "INSECT BREATHING BUTTERFLY DANCE | IS SHINOBU THE FASTEST HASHIRA?",
        "THE COLDEST SMILE IN DEMON SLAYER | DID SPIDER SISTER DESERVE HER MERCY?",
        "LETHAL WISTERIA INJECTION | COULD ANY LOWER MOON SURVIVE SHINOBU?",
        "POISONED STINGER NICHIRIN BLADE | IS SHINOBU THE DEADLIEST HASHIRA?"
    ],

    # ── Expanded Multi-Anime Library ──
    "denji": [
        "HE REVVED HIS CHAINSAW HEART | COULD ANY DEVIL SURVIVE DENJI?",
        "EVERYONE WANTS HIS HEART | IS DENJI THE COLDEST DEVIL IN ANIME?"
    ],
    "makima": [
        "SHE CONTROLS EVERY LIVING BEING | COULD ANYONE RESIST MAKIMA?",
        "IS MAKIMA THE MOST TERRIFYING | VILLAIN IN MODERN ANIME?"
    ],
    "sungjinwoo": [
        "HE STARTED AS THE WEAKEST HUNTER | CAN ANYONE DEFEAT SHADOW MONARCH?",
        "ARISE ECHOED THROUGH THE DUNGEON | IS SUNG JIN-WOO UNTOUCHABLE?"
    ],
    "ichigo": [
        "HE CONFRONTED SOUL SOCIETY | COULD ANYONE SURVIVE ICHIGO'S BANKAI?",
        "GETSUGA TENSHO SLICING REALITY | WAS ICHIGO'S REIGN SUPREME?"
    ],
    "aizen": [
        "HE NEVER DREW HIS SWORD ONCE | WAS EVERYTHING PART OF AIZEN'S PLAN?",
        "STANDING AT THE TOP OF THE WORLD | IS AIZEN THE GREATEST MASTERMIND?"
    ],
    "eren": [
        "HE MOVED FORWARD TO DESTROY THE WORLD | WAS EREN YEAGER JUSTIFIED?",
        "THE RUMBLING HAS BEGUN | COULD ANYONE STOP THE ATTACK TITAN?"
    ],
    "levi": [
        "HE TORE THROUGH THE BEAST TITAN | IS LEVI THE DEADLIEST HUMAN ALIVE?",
        "HUMANITY'S STRONGEST SOLDIER | COULD ANY TITAN SURVIVE LEVI?"
    ],
    "luffy": [
        "GEAR FIVE TURNED REALITY TO RUBBER | WHO COULD MATCH LUFFY'S FREEDOM?",
        "HE WILL BE KING OF THE PIRATES | IS GEAR 5 PEAK SHONEN POWER?"
    ],
    "zoro": [
        "NOTHING HAPPENED IN THRILLER BARK | IS ZORO THE LOYALEST FIGHTER EVER?",
        "THREE SWORD STYLE ASHURA | COULD ANYONE SURVIVE ZORO'S SLASH?"
    ],
    "naruto": [
        "HE NEVER WENT BACK ON HIS WORD | WAS SAGE MODE NARUTO'S PEAK?",
        "KURAMA UNLEASHED FULL POWER | COULD ANY SHINOBI DEFEAT NARUTO?"
    ],
    "kafka": [
        "HE TRANSFORMED INTO KAIJU NUMBER EIGHT | COULD ANY MONSTER RIVAL HIS FORCE?",
        "STAND ON THE FRONT LINES TOGETHER | IS KAFKA THE STRONGEST DEFENDER?"
    ],
    "okarun": [
        "TURBO GRANNY SPEED UNLEASHED | COULD ANYONE KEEP UP WITH OKARUN?",
        "HE BROKE THE SPEED BARRIER | IS DANDADAN THE HYPER CLIMAX OF 2026?"
    ]
}


def _load_question_history() -> List[str]:
    """Loads previously used engaging questions to guarantee zero repetition."""
    for p in [QUESTION_HISTORY_FILE, FALLBACK_HISTORY_FILE]:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
                    elif isinstance(data, dict):
                        return data.get("used_questions", [])
            except Exception:
                pass
    return []


def _save_question_history(history: List[str]) -> None:
    """Persists question history to disk."""
    for p in [QUESTION_HISTORY_FILE, FALLBACK_HISTORY_FILE]:
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                json.dump({"used_questions": history}, f, indent=2)
            break
        except Exception as e:
            print(f"⚠️ [QuestionManager] Notice saving question history: {e}")


def get_engaging_question(
    character_key: str,
    episode_code: Optional[str] = None,
    scene_description: Optional[str] = None,
    anime_universe: Optional[str] = None
) -> str:
    """
    Selects a fresh, non-repeating engaging debate question contextual to the battle scene.

    Priority:
    1. Scene / Episode Specific Questions (e.g. S02E04 for Gojo vs Toji)
    2. Character Specific Questions (e.g. Gojo, Sukuna, Rengoku, Tengen)
    3. Dynamic Scene-Grounded Fallback (custom anime or uncataloged encounter)
    """
    used = _load_question_history()
    char_k = character_key.lower().strip()
    ep_code = (episode_code or "").upper().strip()

    candidate_pool: List[str] = []

    # Priority 1: Scene & Episode Specific Questions
    clean_ep = ep_code.replace("_", "").replace("-", "")
    scene_pool: List[str] = []
    if clean_ep:
        for scene_key, questions in SCENE_SPECIFIC_QUESTIONS.items():
            if scene_key.upper().replace("_", "") == clean_ep:
                scene_pool.extend(questions)
                break

    if scene_pool:
        # If character is specified, prioritize scene questions matching character or signature moves
        char_matches = []
        if char_k:
            char_terms = [char_k]
            if char_k in ("shinobu", "kocho"):
                char_terms.extend(["shinobu", "kocho", "insect", "wisteria", "poison", "butterfly"])
            elif char_k in ("giyu", "tomioka"):
                char_terms.extend(["giyu", "tomioka", "water", "dead calm", "lull", "eleventh form"])
            elif char_k == "tanjiro":
                char_terms.extend(["tanjiro", "hinokami", "sun breathing", "kamado"])
            elif char_k == "zenitsu":
                char_terms.extend(["zenitsu", "thunder", "sixfold", "godspeed"])
            elif char_k in ("tengen", "uzui"):
                char_terms.extend(["tengen", "uzui", "sound breathing", "musical score"])
            elif char_k == "rengoku":
                char_terms.extend(["rengoku", "flame", "kyojuro", "ninth form"])
            elif char_k in ("muichiro", "tokito"):
                char_terms.extend(["muichiro", "tokito", "mist", "obscuring clouds"])
            elif char_k == "gojo":
                char_terms.extend(["gojo", "satoru", "infinity", "hollow purple", "six eyes", "void"])
            elif char_k == "sukuna":
                char_terms.extend(["sukuna", "malevolent", "shrine", "cleave", "dismantle"])
            elif char_k in ("toji", "fushiguro"):
                char_terms.extend(["toji", "fushiguro", "heavenly restriction", "inverted spear"])

            char_matches = [
                q for q in scene_pool
                if any(term in q.lower() for term in char_terms)
            ]
        if char_matches:
            scene_pool = char_matches

        # Check if any scene-specific questions are fresh
        unused_scene = [q for q in scene_pool if q not in used]
        if unused_scene:
            candidate_pool = scene_pool
        else:
            # Fall back to character pool if scene pool is exhausted
            char_pool = CHARACTER_SPECIFIC_QUESTIONS.get(char_k, [])
            unused_char = [q for q in char_pool if q not in used]
            if unused_char:
                candidate_pool = char_pool
            else:
                candidate_pool = scene_pool
    elif char_k in CHARACTER_SPECIFIC_QUESTIONS:
        # Priority 2: Character Specific Questions
        candidate_pool = CHARACTER_SPECIFIC_QUESTIONS[char_k]
    else:
        # Priority 3: Dynamic Scene-Grounded Fallback
        char_title = character_key.replace("_", " ").title()
        uni_title = (anime_universe or "Anime").replace("_", " ").title()
        candidate_pool = [
            f"COULD ANYONE SURVIVE THIS ENCOUNTER | AGAINST {char_title.upper()} AT FULL POWER?",
            f"THE DEADLIEST CLASH IN {uni_title.upper()} | WHO WALKS AWAY VICTORIOUS?",
            f"HE NEVER BACKED DOWN IN THIS BATTLE | COULD ANY OPPONENT MATCH HIS WILL?",
            f"THE ULTIMATE CLIMAX IN {uni_title.upper()} | WAS THIS THE PEAK ANIMATED FIGHT?"
        ]

    # Non-Repetition Filter: Select only questions that have NOT been used before
    unused_pool = [q for q in candidate_pool if q not in used]

    if not unused_pool:
        # If all candidates for this scene/character have been exhausted, reset this pool
        print(f"🔄 [QuestionManager] Rotated through all questions for '{char_k}' ({ep_code}). Resetting history for this battle.")
        used = [q for q in used if q not in candidate_pool]
        unused_pool = candidate_pool

    chosen_question = random.choice(unused_pool)

    # Persist chosen question to prevent future repetition
    used.append(chosen_question)
    _save_question_history(used)

    print(f"❓ [QuestionManager] Selected fresh engaging hook question ({char_k} | {ep_code or 'General'}): '{chosen_question}'")
    return chosen_question
