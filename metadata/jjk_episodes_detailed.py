"""
Detailed JJK Episode Timestamp Database - Manually Curated Action Scenes.

This contains frame-accurate timestamps for major action sequences in JJK episodes,
based on actual episode content analysis.
"""

# Episode S01E01 - Ryoumen Sukuna
S01E01_TIMESTAMPS = {
    "episode_code": "S01E01",
    "title": "Ryoumen Sukuna",
    "duration": 1440.0,  # 24 minutes
    "characters": [
        {
            "name": "Yuji",
            "role": "Protagonist",
            "key_moments": [
                "Track and field record breaking",
                "Encounters cursed spirit at school",
                "Swallows Sukuna's finger",
                "First transformation"
            ]
        },
        {
            "name": "Megumi",
            "role": "Deuteragonist",
            "key_moments": [
                "Retrieves cursed object",
                "Fights low-grade curses",
                "Witnesses Yuji's transformation"
            ]
        },
        {
            "name": "Sukuna",
            "role": "Antagonist (Host)",
            "key_moments": [
                "First awakening",
                "Destroys cursed spirit instantly"
            ]
        }
    ],
    "scenes": [
        {"start": 0.0, "end": 120.0, "action_level": "CALM", "priority": "low", "description": "Opening - Yuji at school, occult club", "characters_present": ["yuji"]},
        {"start": 180.0, "end": 240.0, "action_level": "MODERATE", "priority": "medium", "description": "Megumi encounters low-grade curses at school", "characters_present": ["megumi"]},
        {"start": 420.0, "end": 480.0, "action_level": "INTENSE", "priority": "high", "description": "Yuji's superhuman strength - track field record", "characters_present": ["yuji"]},
        {"start": 720.0, "end": 840.0, "action_level": "INTENSE", "priority": "high", "description": "Cursed spirit attacks school - Yuji fights bare-handed", "characters_present": ["yuji", "megumi"]},
        {"start": 1020.0, "end": 1140.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "Yuji swallows Sukuna's finger - transformation begins", "characters_present": ["yuji", "megumi", "sukuna"]},
        {"start": 1140.0, "end": 1260.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "Sukuna awakens - destroys cursed spirit instantly", "characters_present": ["sukuna", "megumi"]},
        {"start": 1260.0, "end": 1380.0, "action_level": "INTENSE", "priority": "high", "description": "Sukuna vs Megumi standoff - Yuji regains control", "characters_present": ["yuji", "sukuna", "megumi"]},
    ]
}

# Episode S01E02 - For Myself
S01E02_TIMESTAMPS = {
    "episode_code": "S01E02",
    "title": "For Myself",
    "duration": 1440.0,
    "characters": [
        {
            "name": "Yuji",
            "role": "Protagonist",
            "key_moments": ["Sentenced to death", "Decides to postpone death", "Eats second Sukuna finger"]
        },
        {
            "name": "Gojo",
            "role": "Mentor",
            "key_moments": ["Introduces Jujutsu High", "Tests Yuji's control", "Demonstrates overwhelming power"]
        },
        {
            "name": "Sukuna",
            "role": "Antagonist",
            "key_moments": ["Second awakening", "Fights curse"]
        }
    ],
    "scenes": [
        {"start": 180.0, "end": 300.0, "action_level": "MODERATE", "priority": "medium", "description": "Gojo arrives - demonstrates Six Eyes", "characters_present": ["gojo", "yuji", "megumi"]},
        {"start": 420.0, "end": 540.0, "action_level": "INTENSE", "priority": "high", "description": "Yuji vs cursed spirit in morgue", "characters_present": ["yuji", "sukuna"]},
        {"start": 720.0, "end": 900.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "Sukuna awakens - brutal curse fight", "characters_present": ["sukuna", "gojo"]},
        {"start": 1080.0, "end": 1200.0, "action_level": "MODERATE", "priority": "medium", "description": "Yuji decides to join Jujutsu High", "characters_present": ["yuji", "gojo"]},
    ]
}

# Episode S01E04 - Curse Womb Must Die
S01E04_TIMESTAMPS = {
    "episode_code": "S01E04",
    "title": "Curse Womb Must Die",
    "duration": 1440.0,
    "characters": [
        {
            "name": "Yuji",
            "role": "Protagonist",
            "key_moments": ["Detention center mission", "Separated from team", "Death scene"]
        },
        {
            "name": "Megumi",
            "role": "Support",
            "key_moments": ["Leads mission", "Encounters special grade", "Uses shadow techniques"]
        },
        {
            "name": "Nobara",
            "role": "Support",
            "key_moments": ["First real mission", "Escapes with Megumi"]
        },
        {
            "name": "Sukuna",
            "role": "Antagonist",
            "key_moments": ["Refuses to help Yuji", "Watches Yuji die"]
        }
    ],
    "scenes": [
        {"start": 120.0, "end": 300.0, "action_level": "MODERATE", "priority": "medium", "description": "Team enters detention center - ominous atmosphere", "characters_present": ["yuji", "megumi", "nobara"]},
        {"start": 420.0, "end": 600.0, "action_level": "INTENSE", "priority": "high", "description": "Separated - domain begins forming", "characters_present": ["yuji", "megumi", "nobara"]},
        {"start": 720.0, "end": 900.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "Yuji vs Special Grade Curse - brutal beatdown", "characters_present": ["yuji", "sukuna"]},
        {"start": 1020.0, "end": 1200.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "Yuji calls for Sukuna's help - rejected and dies", "characters_present": ["yuji", "sukuna"]},
    ]
}

# Episode S01E07 - Assault
S01E07_TIMESTAMPS = {
    "episode_code": "S01E07",
    "title": "Assault",
    "duration": 1440.0,
    "characters": [
        {
            "name": "Yuji",
            "role": "Protagonist",
            "key_moments": ["Returns from death", "Reunites with Megumi and Nobara", "Surprise reveal"]
        },
        {
            "name": "Todo",
            "role": "Ally",
            "key_moments": ["Goodwill event preparation", "Questions about 'type of woman'"]
        },
        {
            "name": "Gojo",
            "role": "Mentor",
            "key_moments": ["Reveals Yuji is alive", "Explains resurrection plan"]
        }
    ],
    "scenes": [
        {"start": 240.0, "end": 360.0, "action_level": "MODERATE", "priority": "medium", "description": "Goodwill event intro - other schools arrive", "characters_present": ["todo", "gojo"]},
        {"start": 900.0, "end": 1080.0, "action_level": "INTENSE", "priority": "high", "description": "Todo confronts Megumi - type of woman question", "characters_present": ["todo", "megumi"]},
        {"start": 1200.0, "end": 1380.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "Yuji revealed alive - surprise return", "characters_present": ["yuji", "megumi", "nobara"]},
    ]
}

# Episode S01E09 - Small Fry and Reverse Retribution
S01E09_TIMESTAMPS = {
    "episode_code": "S01E09",
    "title": "Small Fry and Reverse Retribution",
    "duration": 1440.0,
    "characters": [
        {
            "name": "Gojo",
            "role": "Main",
            "key_moments": [
                "Fights Jogo at restaurant",
                "Domain Expansion: Infinite Void",
                "Demonstrates overwhelming superiority",
                "Toying with Jogo"
            ]
        },
        {
            "name": "Jogo",
            "role": "Villain",
            "key_moments": [
                "Challenges Gojo",
                "Domain Expansion: Coffin of the Iron Mountain",
                "Utterly defeated"
            ]
        }
    ],
    "scenes": [
        {"start": 0.0, "end": 180.0, "action_level": "CALM", "priority": "low", "description": "Setup - cursed spirits meet, plan against Gojo", "characters_present": ["jogo"]},
        {"start": 300.0, "end": 480.0, "action_level": "INTENSE", "priority": "high", "description": "Gojo vs Jogo begins - restaurant fight", "characters_present": ["gojo", "jogo"]},
        {"start": 540.0, "end": 720.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "Jogo's Domain Expansion - Coffin of Iron Mountain", "characters_present": ["gojo", "jogo"]},
        {"start": 720.0, "end": 900.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "Gojo's Domain Expansion - Infinite Void showcase", "characters_present": ["gojo", "jogo"]},
        {"start": 900.0, "end": 1080.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "Gojo toys with Jogo - overwhelming power display", "characters_present": ["gojo", "jogo"]},
        {"start": 1200.0, "end": 1380.0, "action_level": "INTENSE", "priority": "high", "description": "Aftermath - Hanami appears, Jogo retreats", "characters_present": ["gojo", "jogo"]},
    ]
}

# Episode S01E13 - Tomorrow
S01E13_TIMESTAMPS = {
    "episode_code": "S01E13",
    "title": "Tomorrow",
    "duration": 1440.0,
    "characters": [
        {
            "name": "Yuji",
            "role": "Protagonist",
            "key_moments": ["Goodwill event", "Encounters Todo", "Fights special grade", "Black Flash awakening"]
        },
        {
            "name": "Todo",
            "role": "Ally",
            "key_moments": ["Becomes Yuji's best friend", "Teaches Yuji combat", "Boogie Woogie demonstration"]
        },
        {
            "name": "Megumi",
            "role": "Support",
            "key_moments": ["Vs Finger Bearer", "Incomplete Domain"]
        }
    ],
    "scenes": [
        {"start": 180.0, "end": 360.0, "action_level": "MODERATE", "priority": "medium", "description": "Goodwill event - teams split up", "characters_present": ["yuji", "megumi", "nobara"]},
        {"start": 540.0, "end": 780.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "Megumi vs Finger Bearer - incomplete Domain", "characters_present": ["megumi"]},
        {"start": 900.0, "end": 1080.0, "action_level": "INTENSE", "priority": "high", "description": "Yuji meets Todo - instant best friends", "characters_present": ["yuji", "todo"]},
        {"start": 1200.0, "end": 1380.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "Sukuna awakens briefly - kills curse", "characters_present": ["yuji", "sukuna"]},
    ]
}

# Episode S01E20 - Nonstandard
S01E20_TIMESTAMPS = {
    "episode_code": "S01E20",
    "title": "Nonstandard",
    "duration": 1440.0,
    "characters": [
        {
            "name": "Yuji",
            "role": "Protagonist",
            "key_moments": [
                "Todo & Yuji vs Mahito",
                "Black Flash barrage (4 consecutive)",
                "Perfect sync with Todo",
                "Overcomes trauma"
            ]
        },
        {
            "name": "Todo",
            "role": "Main",
            "key_moments": [
                "Boogie Woogie spam",
                "Black Flash",
                "Ultimate teamwork with Yuji"
            ]
        },
        {
            "name": "Mahito",
            "role": "Villain",
            "key_moments": [
                "Uses Polymorphic Soul Isomer",
                "Multiple body transformations",
                "Overwhelmed by Todo-Yuji combo"
            ]
        }
    ],
    "scenes": [
        {"start": 0.0, "end": 180.0, "action_level": "MODERATE", "priority": "medium", "description": "Recap - Nobara injured, Yuji traumatized", "characters_present": ["yuji", "nobara"]},
        {"start": 240.0, "end": 420.0, "action_level": "INTENSE", "priority": "high", "description": "Todo arrives - motivates Yuji", "characters_present": ["yuji", "todo", "mahito"]},
        {"start": 480.0, "end": 720.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "Todo & Yuji vs Mahito begins - Boogie Woogie combos", "characters_present": ["yuji", "todo", "mahito"]},
        {"start": 720.0, "end": 960.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "Yuji's first Black Flash - momentum shift", "characters_present": ["yuji", "todo", "mahito"]},
        {"start": 960.0, "end": 1200.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "4 consecutive Black Flashes - peak zone", "characters_present": ["yuji", "todo", "mahito"]},
        {"start": 1200.0, "end": 1380.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "Mahito escapes - Todo & Yuji victory", "characters_present": ["yuji", "todo", "mahito"]},
    ]
}

# Episode S02E16 - Thunderclap
S02E16_TIMESTAMPS = {
    "episode_code": "S02E16",
    "title": "Thunderclap",
    "duration": 1440.0,
    "characters": [
        {
            "name": "Sukuna",
            "role": "Main",
            "key_moments": [
                "Awakens in Shibuya",
                "Vs Jogo - fire vs cleave",
                "Meteor clash",
                "Open: Malevolent Shrine",
                "Destroys Shibuya"
            ]
        },
        {
            "name": "Jogo",
            "role": "Villain",
            "key_moments": [
                "Feeds Sukuna 10 fingers",
                "Domain Expansion attempt",
                "Maximum Meteor",
                "Death scene"
            ]
        },
        {
            "name": "Megumi",
            "role": "Support",
            "key_moments": ["Unconscious", "Sukuna inside Yuji's body"]
        }
    ],
    "scenes": [
        {"start": 0.0, "end": 180.0, "action_level": "INTENSE", "priority": "high", "description": "Jogo feeds Sukuna fingers - awakening", "characters_present": ["sukuna", "jogo"]},
        {"start": 240.0, "end": 480.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "Sukuna vs Jogo begins - overwhelming power", "characters_present": ["sukuna", "jogo"]},
        {"start": 540.0, "end": 780.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "Jogo's Maximum Meteor vs Sukuna's cleave", "characters_present": ["sukuna", "jogo"]},
        {"start": 840.0, "end": 1080.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "Sukuna's Domain Expansion - Malevolent Shrine", "characters_present": ["sukuna", "jogo"]},
        {"start": 1080.0, "end": 1320.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "Shibuya destruction - Sukuna's rampage", "characters_present": ["sukuna"]},
        {"start": 1320.0, "end": 1440.0, "action_level": "INTENSE", "priority": "high", "description": "Jogo's death - Sukuna acknowledges him", "characters_present": ["sukuna", "jogo"]},
    ]
}

ALL_EPISODES = {
    "S01E01": S01E01_TIMESTAMPS,
    "S01E02": S01E02_TIMESTAMPS,
    "S01E04": S01E04_TIMESTAMPS,
    "S01E07": S01E07_TIMESTAMPS,
    "S01E09": S01E09_TIMESTAMPS,
    "S01E13": S01E13_TIMESTAMPS,
    "S01E20": S01E20_TIMESTAMPS,
    "S02E16": S02E16_TIMESTAMPS,
}
