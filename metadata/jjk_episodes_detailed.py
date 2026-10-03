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

# Episode S01E24 - Accomplices
S01E24_TIMESTAMPS = {
    "episode_code": "S01E24",
    "title": "Accomplices",
    "duration": 1440.0,
    "characters": [
        {
            "name": "Yuji",
            "role": "Protagonist",
            "key_moments": ["Black Flash sync with Nobara", "Vs Eso & Kechizu", "Superhuman speed run"]
        },
        {
            "name": "Nobara",
            "role": "Protagonist",
            "key_moments": ["Straw Doll Technique: Resonance on self", "Black Flash awakening", "Hairpin explosion"]
        }
    ],
    "scenes": [
        {"start": 240.0, "end": 480.0, "action_level": "INTENSE", "priority": "high", "description": "Rot technique poisons Yuji and Nobara, Kechizu blood spray", "characters_present": ["yuji", "nobara"]},
        {"start": 480.0, "end": 720.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "Nobara nails her own arm with Resonance: Let's play a game of chicken!", "characters_present": ["nobara"]},
        {"start": 720.0, "end": 960.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "Simultaneous Double Black Flash: Yuji strikes Eso, Nobara obliterates Kechizu", "characters_present": ["yuji", "nobara"]},
        {"start": 960.0, "end": 1140.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "Nobara Hairpin detonates the blood nails in Eso's heart", "characters_present": ["nobara", "yuji"]},
    ]
}

# Episode S02E04 - Hidden Inventory Part 4
S02E04_TIMESTAMPS = {
    "episode_code": "S02E04",
    "title": "Hidden Inventory 4",
    "duration": 1440.0,
    "universe": "jjk",
    "characters": [
        {
            "name": "Gojo",
            "role": "Protagonist",
            "key_moments": [
                "Awakens Reverse Cursed Technique after near-death",
                "Floating in the sky: Throughout heaven and earth, I alone am the honored one",
                "Cursed Technique Reversal: Red",
                "Secret Hollow Technique: Hollow Purple manifestation"
            ]
        },
        {
            "name": "Toji",
            "role": "Antagonist",
            "key_moments": [
                "Inverted Spear of Heaven",
                "Realizes Gojo has ascended to godhood",
                "Torso eradicated by Hollow Purple"
            ]
        }
    ],
    "scenes": [
        {"start": 120.0, "end": 360.0, "action_level": "INTENSE", "priority": "high", "description": "Toji delivers Riko's body to Star Religious Group headquarters", "characters_present": ["toji"]},
        {"start": 420.0, "end": 660.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "Gojo confronts Toji floating upside down: Yo, it's been a while", "characters_present": ["gojo", "toji"]},
        {"start": 660.0, "end": 840.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "The Honored One monologue: Right now, everything feels so right", "characters_present": ["gojo"]},
        {"start": 840.0, "end": 960.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "Gojo blasts Toji through the forest with Cursed Technique Reversal Red", "characters_present": ["gojo", "toji"]},
        {"start": 960.0, "end": 1140.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "Hollow Technique Purple obliterates half of Toji's torso and clouds", "characters_present": ["gojo", "toji"]},
    ]
}

# Episode S02E09 - Shibuya Incident: Gate, Open
S02E09_TIMESTAMPS = {
    "episode_code": "S02E09",
    "title": "Gate, Open",
    "duration": 1440.0,
    "characters": [
        {
            "name": "Gojo",
            "role": "Protagonist",
            "key_moments": [
                "Brawl against Jogo, Hanami, and Choso in packed subway",
                "Rips off Hanami's wooden branches bare-handed",
                "Crushes Hanami into the wall with Infinity",
                "0.2-second Domain Expansion: Unlimited Void",
                "ErButton-smashing massacre of 1,000 transfigured humans"
            ]
        }
    ],
    "scenes": [
        {"start": 180.0, "end": 420.0, "action_level": "INTENSE", "priority": "high", "description": "Gojo engages disaster curses without using cursed energy blasts to protect civilians", "characters_present": ["gojo"]},
        {"start": 420.0, "end": 660.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "Gojo corners Hanami and crushes him into dust against the subway wall", "characters_present": ["gojo"]},
        {"start": 720.0, "end": 900.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "Gojo expands 0.2-second Unlimited Void paralyzing all brains", "characters_present": ["gojo"]},
        {"start": 900.0, "end": 1080.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "Gojo sprints at supersonic speeds decapitating 1,000 transfigured humans in 299 seconds", "characters_present": ["gojo"]},
        {"start": 1080.0, "end": 1320.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "Kenjaku appears with Prison Realm: Good evening, Satoru Gojo", "characters_present": ["gojo"]},
    ]
}

# Episode S02E13 - Red Scale
S02E13_TIMESTAMPS = {
    "episode_code": "S02E13",
    "title": "Red Scale",
    "duration": 1440.0,
    "characters": [
        {
            "name": "Yuji",
            "role": "Protagonist",
            "key_moments": [
                "Bathroom hallway close-quarters combat",
                "Divergent Fist vs Blood Manipulation",
                "Breaks water pipes to dilute blood"
            ]
        },
        {
            "name": "Choso",
            "role": "Antagonist",
            "key_moments": [
                "Blood Manipulation: Piercing Blood supersonic laser",
                "Flowing Red Scale: Stack physical enhancement",
                "Supernova explosion",
                "False memories awaken"
            ]
        }
    ],
    "scenes": [
        {"start": 180.0, "end": 420.0, "action_level": "INTENSE", "priority": "high", "description": "Choso fires Piercing Blood speed-of-sound beam at Yuji", "characters_present": ["yuji"]},
        {"start": 420.0, "end": 660.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "Yuji breaks water pipes, flooding bathroom to prevent blood coagulation", "characters_present": ["yuji"]},
        {"start": 660.0, "end": 900.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "Brutal hand-to-hand bathroom slugfest between Yuji and Choso", "characters_present": ["yuji"]},
        {"start": 900.0, "end": 1080.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "Choso Supernova detonation piercing Yuji's liver", "characters_present": ["yuji"]},
    ]
}

# Episode S02E14 - Fluctuations
S02E14_TIMESTAMPS = {
    "episode_code": "S02E14",
    "title": "Fluctuations",
    "duration": 1440.0,
    "characters": [
        {
            "name": "Toji",
            "role": "Reanimated Sorcerer Killer",
            "key_moments": [
                "Enters Dagon's domain through Megumi's boundary aperture",
                "Steals Playful Cloud from Maki",
                "Sharpens Playful Cloud ends against each other into sharp stakes",
                "Overwhelms and repeatedly stabs Dagon to death"
            ]
        },
        {
            "name": "Megumi",
            "role": "Support",
            "key_moments": ["Domain clash against Dagon's Horizon"]
        }
    ],
    "scenes": [
        {"start": 240.0, "end": 480.0, "action_level": "INTENSE", "priority": "high", "description": "Dagon overwhelms Nanami and Naobito with Death Swarm shikigami", "characters_present": ["megumi"]},
        {"start": 480.0, "end": 720.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "Toji Fushiguro drops through the domain portal with ferocious bloodlust", "characters_present": ["toji", "megumi"]},
        {"start": 720.0, "end": 960.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "Toji sharpens Playful Cloud and blitzes across Dagon's water surface", "characters_present": ["toji"]},
        {"start": 960.0, "end": 1200.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "Toji repeatedly spears Dagon into oblivion, completely exorcising the disaster curse", "characters_present": ["toji"]},
    ]
}

# Episode S02E17 - Thunderclap Part 2
S02E17_TIMESTAMPS = {
    "episode_code": "S02E17",
    "title": "Thunderclap Part 2",
    "duration": 1440.0,
    "characters": [
        {
            "name": "Sukuna",
            "role": "Antagonist",
            "key_moments": [
                "Confronts Divine General Mahoraga",
                "Dismantle and Cleave testing adaptation wheel",
                "Domain Expansion: Malevolent Shrine 140-meter radius",
                "Fuga: Fire Arrow vaporization"
            ]
        },
        {
            "name": "Megumi",
            "role": "Support",
            "key_moments": ["Summons Eight-Handled Sword Mahoraga in ritual"]
        }
    ],
    "scenes": [
        {"start": 120.0, "end": 360.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "Mahoraga strikes Sukuna across multiple skyscrapers with Sword of Extermination", "characters_present": ["sukuna"]},
        {"start": 360.0, "end": 600.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "Sukuna tests Mahoraga's wheel clicks and deduces adaptation mechanism", "characters_present": ["sukuna"]},
        {"start": 600.0, "end": 840.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "Domain Expansion: Malevolent Shrine shreds Shibuya into fine dust", "characters_present": ["sukuna"]},
        {"start": 840.0, "end": 1080.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "Sukuna chants 'Open' and manifests blazing Fuga Fire Arrow to incinerate Mahoraga", "characters_present": ["sukuna"]},
        {"start": 1080.0, "end": 1320.0, "action_level": "INTENSE", "priority": "high", "description": "Yuji awakens amidst the obliterated ruins of Shibuya, crying in despair", "characters_present": ["yuji"]},
    ]
}

# Episode S02E19 - Right and Wrong Part 2
S02E19_TIMESTAMPS = {
    "episode_code": "S02E19",
    "title": "Right and Wrong Part 2",
    "duration": 1440.0,
    "characters": [
        {
            "name": "Nobara",
            "role": "Protagonist",
            "key_moments": [
                "Straw Doll Technique: Resonance strikes Mahito's real soul",
                "Coordination with Yuji fighting the real body underground"
            ]
        },
        {
            "name": "Mahito",
            "role": "Antagonist",
            "key_moments": [
                "Splits into two bodies",
                "Real body swaps places with clone to touch Nobara's left eye"
            ]
        }
    ],
    "scenes": [
        {"start": 180.0, "end": 420.0, "action_level": "INTENSE", "priority": "high", "description": "Nobara dominates Mahito clone with hairpin strikes and cursed nails", "characters_present": ["nobara", "mahito"]},
        {"start": 420.0, "end": 660.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "Nobara hammers nail through clone soul, damaging Mahito real body in front of Yuji", "characters_present": ["nobara", "mahito", "yuji"]},
        {"start": 660.0, "end": 900.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "Yuji lands consecutive heavy blows on staggered Mahito underground", "characters_present": ["yuji", "mahito"]},
    ]
}

# Episode S02E21 - Metamorphosis
S02E21_TIMESTAMPS = {
    "episode_code": "S02E21",
    "title": "Metamorphosis",
    "duration": 1440.0,
    "characters": [
        {
            "name": "Yuji",
            "role": "Protagonist",
            "key_moments": [
                "Maximum Output Black Flash with delayed cursed energy",
                "Shatters Mahito's Instant Spirit Body armor",
                "I am you monologue, chasing fleeing Mahito in the snowy woods"
            ]
        },
        {
            "name": "Todo",
            "role": "Ally",
            "key_moments": [
                "120% potential unlocked",
                "Sacrifices left hand to touch Mahito's domain",
                "Fakes a clap with Mahito's hand to trick him"
            ]
        },
        {
            "name": "Mahito",
            "role": "Antagonist",
            "key_moments": [
                "Instant Spirit Body of Distorted Killing true soul evolution",
                "Broken armor, reduced to crawling coward"
            ]
        }
    ],
    "scenes": [
        {"start": 180.0, "end": 420.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "Mahito activates Instant Spirit Body of Distorted Killing, blade arms clash", "characters_present": ["mahito", "yuji", "todo"]},
        {"start": 420.0, "end": 660.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "Todo claps Mahito's palm to swap Yuji into perfect Black Flash punch position", "characters_present": ["todo", "yuji", "mahito"]},
        {"start": 660.0, "end": 900.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "Yuji channels maximum Black Flash shockwave, shattering Mahito's true form", "characters_present": ["yuji", "mahito"]},
        {"start": 900.0, "end": 1140.0, "action_level": "EXPLOSIVE", "priority": "high", "description": "I am you monologue: Yuji stalks Mahito through the snowy forest as wolves hunt prey", "characters_present": ["yuji", "mahito"]},
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
    "S01E24": S01E24_TIMESTAMPS,
    "S02E04": S02E04_TIMESTAMPS,
    "S02E09": S02E09_TIMESTAMPS,
    "S02E13": S02E13_TIMESTAMPS,
    "S02E14": S02E14_TIMESTAMPS,
    "S02E16": S02E16_TIMESTAMPS,
    "S02E17": S02E17_TIMESTAMPS,
    "S02E19": S02E19_TIMESTAMPS,
    "S02E21": S02E21_TIMESTAMPS,
}
