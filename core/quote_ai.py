"""
AI Quote, Dialogue & SEO Metadata Generator for Marvel & Jujutsu Kaisen Edits.
Powered by OpenCode DeepSeek v4 Flash with Nemotron, rich viral title catalogs, and non-repeating title rotation.
"""
import os
import re
import json
import random
import shutil
import subprocess
import requests
from pathlib import Path
from typing import Dict, Any, Optional, List

from config.settings import NVIDIA_API_KEY, OPENROUTER_API_KEY, CHANNEL_TAGS, SCRATCH_DIR
from core.clip_manager import CHARACTER_THEMES

TITLE_HISTORY_FILE = SCRATCH_DIR / "title_history.json"

CHARACTER_VIRAL_CONCEPTS: Dict[str, List[Dict[str, Any]]] = {
    "gojo": [
        {
            "quote": "Throughout heaven and earth, I alone am the honored one.",
            "title": "Gojo Awakened Mode Is Untouchable 🥶⚡ #gojo #jjk #4kedit #shorts",
            "tags": ["gojo", "satorugojo", "jjk", "jujutsukaisen", "animeedit", "4kedit", "shorts"]
        },
        {
            "quote": "Are you the strongest because you're Satoru Gojo, or are you Satoru Gojo because you're the strongest?",
            "title": "Gojo Proves Why He's The Strongest Sorcerer 💜 #gojo #jjk #shorts",
            "tags": ["gojo", "satorugojo", "jjk", "jujutsukaisen", "hollowpurple", "4kedit", "shorts"]
        },
        {
            "quote": "Don't worry, I'm the strongest.",
            "title": "Gojo's 0.2s Domain Expansion Was Pure Cinema 🥶 #gojo #jujutsukaisen #shorts",
            "tags": ["gojo", "domainexpansion", "jjk", "jujutsukaisen", "animeedit", "shorts"]
        },
        {
            "quote": "It's taken a bit of work, but I've finally reached this state.",
            "title": "The Exact Moment Toji Realized He Lost 💀 #gojo #toji #jjk #shorts",
            "tags": ["gojo", "toji", "jjk", "jujutsukaisen", "honoredone", "4kedit", "shorts"]
        },
        {
            "quote": "Phase, Paramita, Pillar of Light... Nine Ropes... Hollow Purple.",
            "title": "Gojo Satoru's Hollow Purple Obliteration 💜💥 #jjk #gojo #shorts",
            "tags": ["gojo", "hollowpurple", "jjk", "jujutsukaisen", "anime", "4kedit", "shorts"]
        },
        {
            "quote": "Dying to win and risking death to win are completely different, Megumi.",
            "title": "Throughout Heaven And Earth, Satoru Gojo Is Him 👑 #gojo #jjk #shorts",
            "tags": ["gojo", "satorugojo", "jjk", "animeedit", "4kedit", "shorts"]
        },
        {
            "quote": "Looks like you're having trouble.",
            "title": "Gojo's Speed In Shibuya Was Terrifying ⚡ #gojo #shibuya #jjk #shorts",
            "tags": ["gojo", "shibuyaincident", "jjk", "jujutsukaisen", "animeedit", "shorts"]
        },
        {
            "quote": "My Six Eyes tell me you're Suguru Geto, but my soul knows otherwise!",
            "title": "When Gojo Removes The Blindfold It's Game Over 👁️ #gojo #jjk #shorts",
            "tags": ["gojo", "sixeyes", "jjk", "jujutsukaisen", "animeedit", "shorts"]
        },
        {
            "quote": "You're weak, Jogo. It's almost embarrassing.",
            "title": "Gojo vs Disaster Curses Martial Arts Masterclass 🥋 #gojo #jjk #shorts",
            "tags": ["gojo", "jogo", "jjk", "jujutsukaisen", "4kedit", "shorts"]
        },
        {
            "quote": "Infinite Void. In here, you experience everything, yet you can do nothing.",
            "title": "Gojo Satoru Unlimited Void Pure Art 🌌 #gojo #jujutsukaisen #shorts",
            "tags": ["gojo", "unlimitedvoid", "jjk", "jujutsukaisen", "4kedit", "shorts"]
        },
    ],
    "sukuna": [
        {
            "quote": "Stand proud. You are strong. But this is my domain.",
            "title": "Sukuna's Malevolent Shrine Hits Different 🩸 #sukuna #jjk #jujutsukaisen #4kedit #shorts",
            "tags": ["sukuna", "ryomensukuna", "jjk", "jujutsukaisen", "malevolentshrine", "animeedit", "4kedit", "shorts"]
        },
        {
            "quote": "You dare look down on the King of Curses?",
            "title": "Sukuna vs Mahoraga Pure Destruction 💥 #sukuna #mahoraga #jjk #shorts",
            "tags": ["sukuna", "mahoraga", "jjk", "shibuya", "animeedit", "4kedit", "shorts"]
        },
        {
            "quote": "Open. Flame arrow, incinerate everything.",
            "title": "Sukuna's Fire Arrow Obliterates Shibuya 🔥 #sukuna #jjk #anime #shorts",
            "tags": ["sukuna", "firearrow", "jjk", "jujutsukaisen", "animeedit", "shorts"]
        },
        {
            "quote": "Know your place, fool. A brat who knows nothing of true jujutsu.",
            "title": "The King Of Curses Does Not Spare Anyone 💀 #sukuna #jjk #shorts",
            "tags": ["sukuna", "ryomensukuna", "jjk", "jujutsukaisen", "4kedit", "shorts"]
        },
        {
            "quote": "Let's see if you can entertain me for more than a second.",
            "title": "Sukuna Playing With Jogo Like A Toy 🥶 #sukuna #jogo #jjk #shorts",
            "tags": ["sukuna", "jogo", "jjk", "jujutsukaisen", "animeedit", "shorts"]
        },
    ],
    "toji": [
        {
            "quote": "Don't get cocky just because you were born with cursed energy.",
            "title": "Toji Fushiguro The Sorcerer Killer 🗡️ #toji #jjk #jujutsukaisen #animeedit #4kedit #shorts",
            "tags": ["toji", "tojifushiguro", "jjk", "jujutsukaisen", "animeedit", "4kedit", "shorts"]
        },
        {
            "quote": "I rejected the Zen'in clan and walked my own path.",
            "title": "Zero Cursed Energy, Pure Demonic Power 💀 #toji #jjk #shorts",
            "tags": ["toji", "tojifushiguro", "zenin", "jjk", "jujutsukaisen", "4kedit", "shorts"]
        },
        {
            "quote": "You're fast, kid. But not fast enough.",
            "title": "Toji Speed Blitzing Special Grade Sorcerers ⚡ #toji #jjk #shorts",
            "tags": ["toji", "dagon", "jjk", "jujutsukaisen", "animeedit", "shorts"]
        },
        {
            "quote": "Not Fushiguro... Zen'in. Good for you.",
            "title": "Toji vs Dagon Domain Infiltration 🌊🗡️ #toji #dagon #jjk #shorts",
            "tags": ["toji", "megumi", "jjk", "jujutsukaisen", "animeedit", "shorts"]
        },
    ],
    "yuji": [
        {
            "quote": "I don't care if it's impossible. I'm going to save everyone I can.",
            "title": "Yuji Itadori's Black Flash Impact 💥 #yuji #jjk #jujutsukaisen #blackflash #animeedit #4kedit #shorts",
            "tags": ["yuji", "yujiitadori", "jjk", "jujutsukaisen", "blackflash", "animeedit", "4kedit", "shorts"]
        },
        {
            "quote": "I'm a cog. And my role is to destroy curses like you.",
            "title": "Yuji & Todo Double Black Flash Combo 🔥 #yuji #todo #mahito #jjk #shorts",
            "tags": ["yuji", "todo", "mahito", "jjk", "jujutsukaisen", "blackflash", "shorts"]
        },
        {
            "quote": "I'm you, Mahito. Wherever you run, I'll hunt you down.",
            "title": "I'm You — Yuji Hunting Mahito Like A Wolf 🐺 #yuji #mahito #jjk #shorts",
            "tags": ["yuji", "mahito", "jjk", "jujutsukaisen", "animeedit", "shorts"]
        },
        {
            "quote": "Even if I die, I'll take you down with me!",
            "title": "Yuji vs Choso Bathroom Brawl Pure Cinema 🥋 #yuji #choso #jjk #shorts",
            "tags": ["yuji", "choso", "jjk", "jujutsukaisen", "4kedit", "shorts"]
        },
    ],
    "megumi": [
        {
            "quote": "With this treasure, I summon... Eight-Handled Sword Divergent Sila Divine General Mahoraga.",
            "title": "Megumi's Mahoraga Summoning Shibuya 🔥 #megumi #mahoraga #jjk #4kedit #shorts",
            "tags": ["megumi", "mahoraga", "jjk", "jujutsukaisen", "animeedit", "4kedit", "shorts"]
        },
        {
            "quote": "I don't care about being right. I just want to save good people.",
            "title": "With This Treasure I Summon... 💀 #megumi #mahoraga #jjk #shorts",
            "tags": ["megumi", "mahoraga", "jjk", "jujutsukaisen", "animeedit", "shorts"]
        },
        {
            "quote": "Chimera Shadow Garden! Expand your imagination!",
            "title": "Megumi Shadow Chimera Domain Expansion 🌑 #megumi #jjk #shorts",
            "tags": ["megumi", "domainexpansion", "jjk", "jujutsukaisen", "shorts"]
        },
    ],
    "mahito": [
        {
            "quote": "Humans are made of souls. The body is merely an imitation.",
            "title": "Mahito's True Soul Nature Is Pure Evil 💀 #mahito #jjk #animeedit #shorts",
            "tags": ["mahito", "jjk", "jujutsukaisen", "animeedit", "4kedit", "shorts"]
        },
        {
            "quote": "Domain Expansion: Self-Embodiment of Perfection.",
            "title": "Mahito 0.2s Domain Expansion Shibuya Cinema ✋ #mahito #domainexpansion #jjk #shorts",
            "tags": ["mahito", "domainexpansion", "jjk", "jujutsukaisen", "4kedit", "shorts"]
        },
        {
            "quote": "I am born from human hatred. You and I are the same, Yuji Itadori.",
            "title": "The True Essence Of Curses — Mahito Awakened 🩸 #mahito #jjk #shorts",
            "tags": ["mahito", "yuji", "jjk", "jujutsukaisen", "animeedit", "shorts"]
        },
        {
            "quote": "This is the true shape of my soul! Instant Spirit Body of Distorted Killing!",
            "title": "Mahito Final Form vs Yuji & Todo ⚔️ #mahito #yuji #todo #jjk #shorts",
            "tags": ["mahito", "jjk", "jujutsukaisen", "blackflash", "shorts"]
        }
    ],
    "todo": [
        {
            "quote": "We are the exception! Let's show this curse what brotherhood means.",
            "title": "Aoi Todo & Yuji 120% Potential Awakened 🔥 #todo #yuji #jjk #shorts",
            "tags": ["todo", "aoitodo", "yuji", "jjk", "jujutsukaisen", "blackflash", "shorts"]
        },
        {
            "quote": "My Boogie Woogie is already dead... but my soul will never lose.",
            "title": "Aoi Todo's 530,000 IQ Boogie Woogie Climax 👏 #todo #mahito #jjk #shorts",
            "tags": ["todo", "boogiewoogie", "jjk", "jujutsukaisen", "animeedit", "shorts"]
        }
    ],
    "nobara": [
        {
            "quote": "Resonance! Feel the nails piercing your cursed soul!",
            "title": "Nobara Kugisaki Hairpin & Resonance Climax 🔨 #nobara #jjk #shorts",
            "tags": ["nobara", "kugisaki", "jjk", "jujutsukaisen", "animeedit", "shorts"]
        },
        {
            "quote": "Tell everyone... that life wasn't so bad.",
            "title": "Nobara's Final Smile In Shibuya Broke Everyone 💔 #nobara #jjk #shorts",
            "tags": ["nobara", "shibuya", "jjk", "jujutsukaisen", "animeedit", "shorts"]
        }
    ],
    # ── Demon Slayer (Kimetsu no Yaiba) Universe ──
    "tanjiro": [
        {
            "quote": "Hinokami Kagura! Dance of the Fire God!",
            "title": "Tanjiro Awakens Sun Breathing Hinokami Kagura 🔥 #tanjiro #demonslayer #shorts",
            "tags": ["tanjiro", "demonslayer", "kimetsunoyaiba", "hinokamikagura", "animeedit", "4kedit", "shorts"]
        },
        {
            "quote": "No matter how many people you lose, you have no choice but to go on living!",
            "title": "Tanjiro vs Gyutaro Climax Was Pure Cinema 🥶⚔️ #tanjiro #gyutaro #demonslayer #shorts",
            "tags": ["tanjiro", "gyutaro", "demonslayer", "kimetsunoyaiba", "animeedit", "shorts"]
        },
        {
            "quote": "Don't stop! Keep running! Protect Nezuko at all costs!",
            "title": "Tanjiro's Demon Slayer Mark Awakening Gave Chills ⚡ #tanjiro #demonslayer #shorts",
            "tags": ["tanjiro", "slayermark", "demonslayer", "kimetsunoyaiba", "4kedit", "shorts"]
        },
        {
            "quote": "I swear I'll turn Nezuko back into a human, no matter what!",
            "title": "The Determination of Tanjiro Kamado 👑 #tanjiro #demonslayer #animeedit #shorts",
            "tags": ["tanjiro", "nezuko", "demonslayer", "kimetsunoyaiba", "shorts"]
        }
    ],
    "rengoku": [
        {
            "quote": "Set your heart ablaze! Go beyond your limits!",
            "title": "Rengoku's Legendary Words Will Never Die ❤️‍🔥 #rengoku #demonslayer #shorts",
            "tags": ["rengoku", "kyojurorengoku", "demonslayer", "kimetsunoyaiba", "mugentrain", "animeedit", "shorts"]
        },
        {
            "quote": "Ninth Form: Rengoku! I will fulfill my duty as a Hashira!",
            "title": "Rengoku vs Akaza Final Ninth Form Clash 🔥💥 #rengoku #akaza #demonslayer #shorts",
            "tags": ["rengoku", "akaza", "demonslayer", "mugentrain", "animeedit", "4kedit", "shorts"]
        },
        {
            "quote": "Growing old and dying is what gives meaning to human life.",
            "title": "Why Kyojuro Rengoku Refused To Become A Demon 👑 #rengoku #demonslayer #shorts",
            "tags": ["rengoku", "flamehashira", "demonslayer", "kimetsunoyaiba", "shorts"]
        }
    ],
    "zenitsu": [
        {
            "quote": "Thunder Breathing, First Form: Thunderclap and Flash — Sixfold!",
            "title": "When Zenitsu Falls Asleep It's Game Over ⚡💀 #zenitsu #demonslayer #shorts",
            "tags": ["zenitsu", "thunderclapandflash", "demonslayer", "kimetsunoyaiba", "animeedit", "4kedit", "shorts"]
        },
        {
            "quote": "Thunder Breathing, First Form: Thunderclap and Flash — God Speed!",
            "title": "Zenitsu's God Speed Broke The Sound Barrier ⚡💨 #zenitsu #demonslayer #shorts",
            "tags": ["zenitsu", "godspeed", "demonslayer", "kimetsunoyaiba", "animeedit", "shorts"]
        },
        {
            "quote": "If you can only do one thing, hone it to perfection!",
            "title": "Zenitsu Locked In Is A Whole Different Demon Slayer 🥶 #zenitsu #demonslayer #shorts",
            "tags": ["zenitsu", "zenitsuagatsuma", "demonslayer", "animeedit", "shorts"]
        }
    ],
    "akaza": [
        {
            "quote": "Technique Development: Destructive Death Compass Needle!",
            "title": "Akaza's Compass Needle Martial Arts In 4K ❄️🥋 #akaza #demonslayer #shorts",
            "tags": ["akaza", "compassneedle", "demonslayer", "kimetsunoyaiba", "animeedit", "4kedit", "shorts"]
        },
        {
            "quote": "Become a demon, Kyojuro! Let's battle for all eternity!",
            "title": "Upper Moon 3 Akaza vs Rengoku Full Power 🩸 #akaza #rengoku #demonslayer #shorts",
            "tags": ["akaza", "uppermoon3", "rengoku", "demonslayer", "shorts"]
        },
        {
            "quote": "I only want to fight the strong. The weak disgust me!",
            "title": "Why Akaza Is The Most Respected Upper Moon 💀 #akaza #demonslayer #shorts",
            "tags": ["akaza", "demonslayer", "kimetsunoyaiba", "animeedit", "shorts"]
        }
    ],
    "giyu": [
        {
            "quote": "Water Breathing, Eleventh Form: Dead Calm.",
            "title": "Giyu Tomioka's Eleventh Form Dead Calm Is Untouchable 🌊 #giyu #demonslayer #shorts",
            "tags": ["giyu", "giyutomioka", "deadcalm", "demonslayer", "kimetsunoyaiba", "4kedit", "shorts"]
        },
        {
            "quote": "Don't cry. Don't despair. Stand up and fight for your sister!",
            "title": "The Coldest Hashira Giyu Tomioka 🥶🌊 #giyu #demonslayer #animeedit #shorts",
            "tags": ["giyu", "waterhashira", "demonslayer", "kimetsunoyaiba", "shorts"]
        }
    ],
    "tengen": [
        {
            "quote": "From here on out, things are gonna get flashy!",
            "title": "Tengen Uzui Musical Score Technique Was Pure Cinema 💎 #tengen #demonslayer #shorts",
            "tags": ["tengen", "tengenuzui", "soundhashira", "demonslayer", "kimetsunoyaiba", "4kedit", "shorts"]
        },
        {
            "quote": "We're going for the win! Sound Breathing, Fifth Form: String Performance!",
            "title": "Tengen vs Gyutaro Best Fight In Anime History ⚔️🔥 #tengen #gyutaro #demonslayer #shorts",
            "tags": ["tengen", "gyutaro", "entertainmentdistrict", "demonslayer", "shorts"]
        }
    ],
    "inosuke": [
        {
            "quote": "Coming through! Coming through! Pig assault!",
            "title": "Lord Inosuke Unhinged Beast Breathing Energy 🐗⚔️ #inosuke #demonslayer #shorts",
            "tags": ["inosuke", "beastbreathing", "demonslayer", "kimetsunoyaiba", "animeedit", "4kedit", "shorts"]
        },
        {
            "quote": "Better watch out! Beast Breathing, Seventh Form: Spatial Awareness!",
            "title": "Inosuke's Spatial Awareness Saved Everyone 🐗⚡ #inosuke #demonslayer #shorts",
            "tags": ["inosuke", "beastbreathing", "demonslayer", "kimetsunoyaiba", "animeedit", "shorts"]
        },
        {
            "quote": "Don't you dare cry! What's done is done! We keep moving forward!",
            "title": "Inosuke Comforting Tanjiro Showed His Pure Heart 🐗❤️ #inosuke #demonslayer #shorts",
            "tags": ["inosuke", "tanjiro", "demonslayer", "kimetsunoyaiba", "animeedit", "shorts"]
        }
    ],
    "muzan": [
        {
            "quote": "Do I look pale to you? Does my face look sickly?",
            "title": "Muzan Kibutsuji Showed What True Fear Means 💀🌑 #muzan #demonslayer #shorts",
            "tags": ["muzan", "muzankibutsuji", "demonking", "demonslayer", "kimetsunoyaiba", "4kedit", "shorts"]
        },
        {
            "quote": "I am a living being who is infinitely close to perfection.",
            "title": "When Muzan Unleashed His Full Demon Power 🩸🌑 #muzan #demonslayer #shorts",
            "tags": ["muzan", "infinitycastle", "demonking", "demonslayer", "kimetsunoyaiba", "shorts"]
        },
        {
            "quote": "Lower Moons... you have disappointed me for the last time.",
            "title": "Muzan Eliminating The Lower Moons Was Terrifying 🩸 #muzan #demonslayer #shorts",
            "tags": ["muzan", "lowermoons", "demonslayer", "kimetsunoyaiba", "animeedit", "shorts"]
        }
    ],
    "nezuko": [
        {
            "quote": "Blood Demon Art: Exploding Blood!",
            "title": "Nezuko Awakened Full Demon Form Blood Art 🩸🔥 #nezuko #demonslayer #shorts",
            "tags": ["nezuko", "nezukokamado", "blooddemonart", "demonslayer", "kimetsunoyaiba", "shorts"]
        },
        {
            "quote": "I will protect humans! Humans are my family!",
            "title": "Nezuko Kicking Daki Through A Building 🩸💥 #nezuko #daki #demonslayer #shorts",
            "tags": ["nezuko", "entertainmentdistrict", "demonslayer", "kimetsunoyaiba", "4kedit", "shorts"]
        },
        {
            "quote": "Good morning, Inosuke! Good morning, Tanjiro!",
            "title": "The Moment Nezuko Conquered The Sun Gave Chills ☀️✨ #nezuko #demonslayer #shorts",
            "tags": ["nezuko", "swordsmithvillage", "demonslayer", "kimetsunoyaiba", "animeedit", "shorts"]
        }
    ],
    "muichiro": [
        {
            "quote": "Mist Breathing, Seventh Form: Obscuring Clouds.",
            "title": "Muichiro Tokito Disrespected Gyokko So Badly 🌫️💀 #muichiro #demonslayer #shorts",
            "tags": ["muichiro", "misthashira", "demonslayer", "kimetsunoyaiba", "swordsmithvillage", "shorts"]
        },
        {
            "quote": "Even if I lost my memories, my body remembers how to cut you down.",
            "title": "Muichiro Awakens The Demon Slayer Mark 🌫️⚡ #muichiro #demonslayer #4kedit #shorts",
            "tags": ["muichiro", "misthashira", "demonslayer", "kimetsunoyaiba", "slayermark", "shorts"]
        },
        {
            "quote": "The difference between you and me is that I fight for others, not myself.",
            "title": "14-Year-Old Muichiro Soloed An Upper Moon 👑🌫️ #muichiro #gyokko #demonslayer #shorts",
            "tags": ["muichiro", "uppermoon5", "demonslayer", "kimetsunoyaiba", "animeedit", "shorts"]
        }
    ],
    "gyutaro": [
        {
            "quote": "Blood Demon Art: Flying Blood Sickles!",
            "title": "Gyutaro's Blood Sickles Pure Terror 🩸⚔️ #gyutaro #demonslayer #shorts",
            "tags": ["gyutaro", "uppermoon6", "demonslayer", "kimetsunoyaiba", "entertainmentdistrict", "shorts"]
        },
        {
            "quote": "You've got a nice face, man... envy eats me alive!",
            "title": "Gyutaro vs Tengen Final Clash Was Pure Cinema ⚔️🔥 #gyutaro #tengen #demonslayer #shorts",
            "tags": ["gyutaro", "tengen", "entertainmentdistrict", "demonslayer", "kimetsunoyaiba", "4kedit", "shorts"]
        },
        {
            "quote": "I don't regret becoming a demon! I'll curse you forever!",
            "title": "Gyutaro & Daki's Tragic Backstory Broke Everyone 💔 #gyutaro #daki #demonslayer #shorts",
            "tags": ["gyutaro", "daki", "demonslayer", "kimetsunoyaiba", "animeedit", "shorts"]
        }
    ],
    "spiderman": [
        {
            "quote": "With great power comes great responsibility.",
            "title": "Peter Parker Reclaims His Power 🕷️💥 #spiderman #marvel #4kedit #shorts",
            "tags": ["spiderman", "peterparker", "marvel", "mcu", "4kedit", "shorts"]
        },
        {
            "quote": "I can't save everyone... but I have to try.",
            "title": "Spider-Man In No Way Home Final Battle 🕸️ #spiderman #nowayhome #marvel #shorts",
            "tags": ["spiderman", "nowayhome", "marvel", "avengers", "4kedit", "shorts"]
        },
        {
            "quote": "I wanted to kill him. But that's not who we are.",
            "title": "When Spider-Man Stopped Holding Back 🥶🕷️ #spiderman #marvel #shorts",
            "tags": ["spiderman", "greengoblin", "marvel", "nowayhome", "shorts"]
        },
        {
            "quote": "Hello Peter. You're not Peter Parker!",
            "title": "Spider-Man vs Doc Ock Bridge Fight 4K 💥 #spiderman #marvel #shorts",
            "tags": ["spiderman", "docock", "marvel", "nowayhome", "4kedit", "shorts"]
        },
    ],
    "thor": [
        {
            "quote": "Bring me Thanos! You will die for that!",
            "title": "Thor's Entrance In Wakanda Was Peak MCU ⚡ #thor #marvel #4kedit #shorts",
            "tags": ["thor", "wakanda", "infinitywar", "marvel", "stormbreaker", "4kedit", "shorts"]
        },
        {
            "quote": "I am not the God of Hammers. I am the God of Thunder.",
            "title": "Thor God Of Thunder Awakened In Ragnarok ⚡🔥 #thor #ragnarok #marvel #shorts",
            "tags": ["thor", "ragnarok", "marvel", "mcu", "4kedit", "shorts"]
        },
        {
            "quote": "He's a friend from work!",
            "title": "Thor vs Hulk Gladiator Arena Battle 4K ⚡🔨 #thor #hulk #marvel #shorts",
            "tags": ["thor", "hulk", "ragnarok", "marvel", "shorts"]
        },
    ],
    "ironman": [
        {
            "quote": "And I... am... Iron Man.",
            "title": "The Greatest Sacrifice In MCU History 🦾 #ironman #marvel #4kedit #shorts",
            "tags": ["ironman", "tonystark", "marvel", "endgame", "avengers", "4kedit", "shorts"]
        },
        {
            "quote": "I am Iron Man. The suit and I are one.",
            "title": "Tony Stark Proves He's Earth's Best Defender 🦾🔥 #ironman #marvel #shorts",
            "tags": ["ironman", "tonystark", "marvel", "mcu", "4kedit", "shorts"]
        },
    ],
    "thanos": [
        {
            "quote": "You could not live with your own failure. Where did that bring you? Back to me.",
            "title": "Thanos Was Unstoppable In Infinity War 💥 #thanos #marvel #4kedit #shorts",
            "tags": ["thanos", "marvel", "infinitywar", "endgame", "villain", "4kedit", "shorts"]
        },
    ],
    "wolverine": [
        {
            "quote": "I'm the best there is at what I do, but what I do isn't very nice.",
            "title": "Wolverine Unleashed In Deadpool & Wolverine 🩸 #wolverine #marvel #4kedit #shorts",
            "tags": ["wolverine", "logan", "deadpool", "marvel", "xmen", "4kedit", "shorts"]
        },
    ],
    "loki": [
        {
            "quote": "I know what kind of god I need to be. For all of us.",
            "title": "Loki God Of Stories Sacrifice Was Unmatched 👑 #loki #marvel #4kedit #shorts",
            "tags": ["loki", "godofstories", "marvel", "mcu", "tva", "4kedit", "shorts"]
        },
    ]
}


# Keyword lists for strict cross-universe quarantine
JJK_KEYWORDS = {
    "jjk", "jujutsukaisen", "jujutsu", "gojo", "satorugojo", "sukuna", "ryomensukuna",
    "toji", "tojifushiguro", "yuji", "yujiitadori", "itadori", "megumi", "fushiguro",
    "nobara", "kugisaki", "mahito", "todo", "aoitodo", "choso", "shibuya", "shibuyaincident",
    "domainexpansion", "blackflash", "hollowpurple", "unlimitedvoid", "malevolentshrine",
    "boogiewoogie", "mahoraga", "jogo", "dagon", "geto", "sugurugeto", "nanami", "honoredone", "sixeyes"
}

DEMONSLAYER_KEYWORDS = {
    "demonslayer", "kimetsunoyaiba", "kny", "tanjiro", "kamado", "nezuko", "zenitsu",
    "agatsuma", "inosuke", "rengoku", "kyojurorengoku", "akaza", "giyu", "tomioka",
    "tengen", "uzui", "muzan", "kibutsuji", "muichiro", "tokito", "gyutaro", "daki",
    "hinokamikagura", "sunbreathing", "waterbreathing", "thunderbreathing", "beastbreathing",
    "mistbreathing", "soundbreathing", "flamehashira", "waterhashira", "soundhashira",
    "misthashira", "mugentrain", "entertainmentdistrict", "swordsmithvillage", "hashira",
    "uppermoon", "uppermoon3", "uppermoon6", "uppermoon5", "blooddemonart", "slayermark"
}

MARVEL_KEYWORDS = {
    "marvel", "mcu", "spiderman", "peterparker", "nowayhome", "avengers", "ironman",
    "tonystark", "thor", "ragnarok", "infinitywar", "endgame", "thanos", "loki",
    "godofstories", "wolverine", "logan", "deadpool"
}


def is_concept_universe_clean(concept: Dict[str, Any], universe: str) -> bool:
    """Verifies that a title/quote/tags concept does not contain cross-universe terms."""
    title = (concept.get("title") or "").lower()
    quote = (concept.get("quote") or "").lower()
    tags = [t.lower() for t in concept.get("tags") or []]
    all_text = " ".join([title, quote] + tags)
    words = set(re.findall(r"\b[a-zA-Z0-9_]+\b", all_text))

    if universe == "demonslayer":
        forbidden = JJK_KEYWORDS | MARVEL_KEYWORDS
        if words & forbidden:
            return False
    elif universe == "jjk":
        forbidden = DEMONSLAYER_KEYWORDS | MARVEL_KEYWORDS
        if words & forbidden:
            return False
    elif universe == "marvel":
        forbidden = JJK_KEYWORDS | DEMONSLAYER_KEYWORDS
        if words & forbidden:
            return False

    return True


def sanitize_tags(tags: List[str], universe: str, character_key: str) -> List[str]:
    """Removes any cross-universe tags and guarantees canonical tags are present."""
    clean = []
    seen = set()

    raw_tokens = [t.lstrip("#").strip().lower() for t in tags if t]

    for tag in raw_tokens:
        if not tag:
            continue
        if universe == "demonslayer" and tag in (JJK_KEYWORDS | MARVEL_KEYWORDS):
            continue
        if universe == "jjk" and tag in (DEMONSLAYER_KEYWORDS | MARVEL_KEYWORDS):
            continue
        if universe == "marvel" and tag in (JJK_KEYWORDS | DEMONSLAYER_KEYWORDS):
            continue
        if tag not in seen:
            seen.add(tag)
            clean.append(tag)

    if universe == "demonslayer":
        mandatory = [character_key, "demonslayer", "kimetsunoyaiba", "animeedit", "4kedit", "phonk", "shorts"]
    elif universe == "jjk":
        mandatory = [character_key, "jjk", "jujutsukaisen", "animeedit", "4kedit", "phonk", "shorts"]
    elif universe == "marvel":
        mandatory = [character_key, "marvel", "mcu", "4kedit", "phonk", "shorts"]
    else:
        mandatory = [character_key, universe, "animeedit", "4kedit", "shorts"]

    for m in mandatory:
        if m not in seen:
            seen.add(m)
            clean.append(m)

    return clean[:12]


def format_anime_description(
    title: str,
    quote: str,
    character_name: str,
    universe: str,
    tags: List[str]
) -> str:
    """Builds a rich, 100% accurate YouTube description for the specific universe."""
    clean_tags = [t.lstrip("#").strip() for t in tags if t.strip()]
    tag_str = " ".join(f"#{t}" for t in clean_tags)

    if universe == "demonslayer":
        series_name = "Demon Slayer: Kimetsu no Yaiba (鬼滅の刃)"
        studio_info = "Koyoharu Gotouge, Shueisha, Aniplex, and ufotable"
        return (
            f"⚡ {title}\n\n"
            f"🗣️ Character: {character_name}\n"
            f"🗡️ Series: {series_name}\n"
            f"🔥 Iconic Quote: \"{quote}\"\n\n"
            f"Watch in 4K HDR with headphones for maximum immersion! 🎧✨\n"
            f"Like & Subscribe to @jazzcreates for daily 4K Demon Slayer and anime edits!\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 Series: Demon Slayer / Kimetsu no Yaiba\n"
            f"🎬 Type: Transformative 4K Phonk AMV / Fan Scene Edit\n"
            f"⚖️ Copyright Disclaimer: This video is a transformative fan edit created under Fair Use "
            f"(Section 107 of the Copyright Act 1976) for entertainment, commentary, and criticism. "
            f"All rights, audio, and visual assets belong to their respective creators ({studio_info}).\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{tag_str}"
        )
    elif universe == "jjk":
        series_name = "Jujutsu Kaisen (呪術廻戦)"
        studio_info = "Gege Akutami, Shueisha, and MAPPA"
        return (
            f"⚡ {title}\n\n"
            f"🗣️ Character: {character_name}\n"
            f"🥋 Series: {series_name}\n"
            f"🔥 Iconic Quote: \"{quote}\"\n\n"
            f"Watch in 4K HDR with headphones for maximum immersion! 🎧✨\n"
            f"Like & Subscribe to @jazzcreates for daily 4K Jujutsu Kaisen and anime edits!\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 Series: Jujutsu Kaisen (JJK)\n"
            f"🎬 Type: Transformative 4K Phonk AMV / Fan Scene Edit\n"
            f"⚖️ Copyright Disclaimer: This video is a transformative fan edit created under Fair Use "
            f"(Section 107 of the Copyright Act 1976) for entertainment, commentary, and criticism. "
            f"All rights, audio, and visual assets belong to their respective creators ({studio_info}).\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{tag_str}"
        )
    else:
        return (
            f"⚡ {title}\n\n"
            f"🗣️ Character: {character_name}\n"
            f"🎬 Universe: {universe.upper()}\n"
            f"🔥 Quote: \"{quote}\"\n\n"
            f"Watch in 4K HDR with headphones! 🎧✨\n"
            f"Like & Subscribe to @jazzcreates for daily 4K scene edits!\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"⚖️ Disclaimer: Transformative fan edit created for entertainment under Fair Use.\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"{tag_str}"
        )


def _load_title_history() -> List[str]:
    """Loads previously used titles from persistent history."""
    if TITLE_HISTORY_FILE.exists():
        try:
            with open(TITLE_HISTORY_FILE, "r") as f:
                return json.load(f).get("used_titles", [])
        except Exception:
            pass
    return []


def _save_title_history(used: List[str]):
    """Saves used titles to persistent history."""
    try:
        TITLE_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(TITLE_HISTORY_FILE, "w") as f:
            json.dump({"used_titles": used[-100:]}, f, indent=2)
    except Exception as e:
        print(f"⚠️ [QuoteAI] Failed to save title history: {e}")


def _extract_json_response(raw_text: str) -> Optional[Dict[str, Any]]:
    """Safely extracts JSON dictionary from LLM response text."""
    if not raw_text:
        return None
    clean = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL).strip()
    if "```json" in clean:
        clean = clean.split("```json")[1].split("```")[0].strip()
    elif "```" in clean:
        clean = clean.split("```")[1].split("```")[0].strip()
    try:
        return json.loads(clean)
    except Exception:
        match = re.search(r'\{[\s\S]*\}', clean)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                pass
    return None


def query_opencode_deepseek_v4_flash(character_name: str, universe: str) -> Optional[Dict[str, Any]]:
    """
    Priority 1: Queries OpenCode DeepSeek v4 Flash via OpenCode CLI.
    """
    opencode_bin = shutil.which("opencode") or str(Path.home() / ".opencode/bin/opencode")
    if not opencode_bin or not (Path(opencode_bin).exists() or shutil.which("opencode")):
        return None
        
    prompt = (
        f"You are a master viral YouTube Shorts creator making a 4K Phonk scene edit for {character_name} ({universe.upper()}). "
        f"CRITICAL REQUIREMENT: Character belongs strictly to {universe.upper()}. "
        f"Do NOT mention, tag, or reference any other anime franchise (e.g. no JJK for Demon Slayer, no Demon Slayer for JJK). "
        "Generate a JSON object with: "
        "1. 'quote': An iconic, punchy, badass 1-sentence quote or monologue line (under 12 words), "
        "2. 'title': Unique High-CTR YouTube Shorts title with emoji and hashtags (under 65 chars), "
        "3. 'tags': List of 8 viral trending hashtags without hash symbols. "
        "Output ONLY raw JSON with keys 'quote', 'title', 'tags'."
    )
    
    try:
        print(f"🧠 [QuoteAI] Querying OpenCode DeepSeek v4 Flash (opencode/deepseek-v4-flash-free)...")
        res = subprocess.run(
            [opencode_bin, "run", "-m", "opencode/deepseek-v4-flash-free", prompt],
            capture_output=True,
            text=True,
            timeout=15
        )
        if res.returncode == 0 and res.stdout:
            parsed = _extract_json_response(res.stdout)
            if parsed and "quote" in parsed and "title" in parsed:
                if is_concept_universe_clean(parsed, universe):
                    print(f"✅ [QuoteAI] DeepSeek v4 Flash successfully generated quote: \"{parsed['quote']}\"")
                    return parsed
                else:
                    print(f"⚠️ [QuoteAI] DeepSeek output failed universe isolation check for {universe}. Discarding.")
    except Exception as e:
        print(f"[QuoteAI] Notice querying OpenCode CLI: {e}")
        
    return None


def query_nvidia_nemotron(character_name: str, universe: str) -> Optional[Dict[str, Any]]:
    """
    Priority 2: Queries NVIDIA Nemotron 3 Ultra if API key is present.
    """
    if not NVIDIA_API_KEY:
        return None
        
    try:
        url = "https://integrate.api.nvidia.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {NVIDIA_API_KEY}",
            "Content-Type": "application/json"
        }
        prompt = (
            f"You are an elite YouTube Shorts editor creating viral 4K Phonk edits for {character_name} ({universe.upper()}). "
            f"CRITICAL: Character belongs strictly to {universe.upper()}. "
            f"Do NOT mention or tag other anime or franchises. "
            "Generate a JSON object with: "
            "1. 'quote': a legendary 1-sentence badass quote (under 12 words), "
            "2. 'title': unique viral YouTube Short title with hashtags (under 70 chars), "
            "3. 'tags': array of 8 viral hashtags."
        )
        payload = {
            "model": "nvidia/nemotron-3-super-550b-instruct",
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.85,
            "max_tokens": 200
        }
        res = requests.post(url, headers=headers, json=payload, timeout=8)
        if res.status_code == 200:
            data = res.json()
            raw_text = data["choices"][0]["message"]["content"]
            parsed = _extract_json_response(raw_text)
            if parsed and "quote" in parsed:
                if is_concept_universe_clean(parsed, universe):
                    return parsed
                else:
                    print(f"⚠️ [QuoteAI] Nemotron output failed universe isolation check for {universe}. Discarding.")
    except Exception as e:
        print(f"[QuoteAI] Notice querying NVIDIA NIM: {e}")
        
    return None


def generate_edit_metadata(character_key: str = None) -> Dict[str, Any]:
    """
    Generates quote, title, description, and tags with non-repeating title rotation.
    Strictly isolates anime universes to eliminate any cross-universe contamination.
    """
    if not character_key or character_key not in CHARACTER_THEMES:
        character_key = random.choice(list(CHARACTER_THEMES.keys()))
        
    theme = CHARACTER_THEMES[character_key]
    char_universe = theme.get("universe", "demonslayer")
    
    # 1. Try OpenCode DeepSeek v4 Flash (Priority 1)
    ai_meta = query_opencode_deepseek_v4_flash(theme["name"], char_universe)
    
    # 2. Try NVIDIA Nemotron (Priority 2)
    if not ai_meta:
        ai_meta = query_nvidia_nemotron(theme["name"], char_universe)
        
    used_titles = _load_title_history()
    
    chosen_concept = None
    if ai_meta and ai_meta.get("title") and ai_meta.get("title") not in used_titles:
        if is_concept_universe_clean(ai_meta, char_universe):
            chosen_concept = ai_meta
        else:
            print(f"⚠️ [QuoteAI] Discarded cross-universe AI metadata for '{character_key}' ({char_universe})")
            
    if not chosen_concept:
        # 3. Non-repeating rotation from curated rich viral concept catalog
        catalog = CHARACTER_VIRAL_CONCEPTS.get(character_key)
        if not catalog:
            catalog = [
                {
                    "quote": theme.get("quote", "I alone determine my destiny."),
                    "title": f"{theme['name']} Unleashed Pure Cinema 🔥 #{character_key} #{char_universe} #shorts",
                    "tags": [character_key, char_universe, "animeedit", "4kedit", "shorts"]
                }
            ]
        # Filter catalog ensuring clean universe
        clean_catalog = [c for c in catalog if is_concept_universe_clean(c, char_universe)]
        if not clean_catalog:
            clean_catalog = catalog
            
        unused_concepts = [c for c in clean_catalog if c["title"] not in used_titles]
        
        if not unused_concepts:
            print(f"🔄 [QuoteAI] All catalog titles rotated through for {character_key}. Resetting title history.")
            unused_concepts = clean_catalog
            used_titles = [t for t in used_titles if t not in [c["title"] for c in clean_catalog]]
            
        chosen_concept = random.choice(unused_concepts)
        
    quote = chosen_concept["quote"]
    title = chosen_concept["title"]
    raw_tags = chosen_concept.get("tags", [character_key, "animeedit", "4kedit", "shorts"])
    tags = sanitize_tags(raw_tags, char_universe, character_key)
    
    # Save to history
    used_titles.append(title)
    _save_title_history(used_titles)
    print(f"🎯 [QuoteAI] Selected fresh viral title ({char_universe.upper()}): '{title}'")
    
    # Build 100% accurate, rich, professional YouTube description
    description = format_anime_description(
        title=title,
        quote=quote,
        character_name=theme["name"],
        universe=char_universe,
        tags=tags
    )
    
    return {
        "character_key": character_key,
        "character_name": theme["name"],
        "universe": char_universe,
        "quote": quote,
        "title": title,
        "tags": tags,
        "description": description
    }

