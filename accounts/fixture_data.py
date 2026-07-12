"""Fixture data definitions for Worlds demo/development seeding."""

DEMO_PASSWORD = "demo1234"

AUTHORS = [
    {
        "username": "elena_rivers",
        "email": "elena@worlds.example",
        "display_name": "Elena Rivers",
        "bio": (
            "Fantasy writer exploring worlds between dreams and reality. "
            "Former cartographer. Currently serializing two epics on Worlds."
        ),
        "stripe_connect_onboarded": True,
        "stripe_account_id": "acct_demo_elena",
    },
    {
        "username": "marcus_chen",
        "email": "marcus@worlds.example",
        "display_name": "Marcus Chen",
        "bio": (
            "Sci-fi author obsessed with orbital mechanics and broken AIs. "
            "Engineer by day, chapter machine by night."
        ),
        "stripe_connect_onboarded": True,
        "stripe_account_id": "acct_demo_marcus",
    },
    {
        "username": "amara_okafor",
        "email": "amara@worlds.example",
        "display_name": "Amara Okafor",
        "bio": (
            "Literary fiction about families, memory, and the spaces between languages. "
            "Pushcart nominee. Lagos → London → everywhere."
        ),
        "stripe_connect_onboarded": False,
        "stripe_account_id": "",
    },
    {
        "username": "james_wolf",
        "email": "james@worlds.example",
        "display_name": "James Wolf",
        "bio": (
            "Thriller and crime writer. Former journalist. "
            "If someone lies in chapter one, someone bleeds by chapter ten."
        ),
        "stripe_connect_onboarded": True,
        "stripe_account_id": "acct_demo_james",
    },
]

READERS = [
    {
        "username": "alex_reader",
        "email": "alex@worlds.example",
    },
    {
        "username": "sam_reader",
        "email": "sam@worlds.example",
    },
    {
        "username": "jordan_reader",
        "email": "jordan@worlds.example",
    },
]

# Backwards-compatible aliases used in docs
LEGACY_USER_MAP = {
    "demo_author": "elena_rivers",
    "demo_reader": "alex_reader",
}

STORIES = [
    {
        "title": "The Starlight Chronicle",
        "author": "elena_rivers",
        "synopsis": (
            "When the last lighthouse on the edge of the world begins to dim, "
            "a young cartographer must chart a course through forgotten seas "
            "to relight the stars themselves."
        ),
        "status": "publishing",
        "content_source": "editor",
        "cover_color": "#4a5568",
        "chapters": [
            {
                "number": 1,
                "title": "The Dimming Light",
                "format": "plain",
                "content": (
                    "The lighthouse had burned for three hundred years without interruption. "
                    "Mara knew this because the keeper's log said so, and the keeper's log "
                    "was the only honest document left in Port Meridian.\n\n"
                    "On the night the flame wavered, she was copying coastal contours onto vellum "
                    "by oil lamp, her pen scratching a rhythm she'd known since childhood. "
                    "Then the light stuttered. Once. Twice. And the horizon swallowed the stars."
                ),
                "published": True,
                "unlock_price_cents": None,
                "tier_required": "none",
            },
            {
                "number": 2,
                "title": "Charts of the Forgotten",
                "format": "plain",
                "content": (
                    "Maps, Mara discovered, were liars—but useful liars. "
                    "The forgotten charts she found in the lighthouse cellar showed coastlines "
                    "that no longer existed and harbors that had never been built.\n\n"
                    "She spread them across the floor and weighted the corners with brass instruments. "
                    "Somewhere in the ink, a route waited."
                ),
                "published": True,
                "unlock_price_cents": 299,
                "tier_required": "none",
            },
            {
                "number": 3,
                "title": "Silver Tides",
                "format": "html",
                "content": (
                    "<p>The tide came in the color of molten coin, and with it a sound like distant bells.</p>"
                    "<p>Mara stood at the waterline with the stolen charts rolled under her arm. "
                    "<strong>Silver subscribers</strong> had funded her boat—readers who believed "
                    "the stars could be relit. She owed them the truth, even if the truth was impossible.</p>"
                    "<blockquote>The sea remembers every map we burn.</blockquote>"
                ),
                "published": True,
                "unlock_price_cents": None,
                "tier_required": "silver",
            },
            {
                "number": 4,
                "title": "The Cartographer's Oath",
                "format": "html",
                "content": (
                    "<p>Every cartographer swears an oath to record what is, not what should be. "
                    "Mara broke hers before dawn.</p>"
                    "<p>She drew an island that existed only when the lighthouse flame burned true—"
                    "and named it <em>Reliquary</em>.</p>"
                ),
                "published": True,
                "unlock_price_cents": 499,
                "tier_required": "gold",
            },
            {
                "number": 5,
                "title": "Relight (Draft)",
                "format": "plain",
                "content": "Draft chapter — coming soon to Gold tier subscribers.",
                "published": False,
                "unlock_price_cents": None,
                "tier_required": "gold",
            },
        ],
    },
    {
        "title": "Neon Drift",
        "author": "marcus_chen",
        "synopsis": (
            "A salvage pilot picks up a distress beacon from a station that was decommissioned "
            "twenty years ago. The voice on the radio sounds exactly like hers."
        ),
        "status": "publishing",
        "content_source": "sheets",
        "cover_color": "#2d3748",
        "chapters": [
            {
                "number": 1,
                "title": "Beacon",
                "format": "plain",
                "content": (
                    "The beacon pulsed on frequencies that should have been dead. "
                    "Kai killed the music in her cockpit and listened to the static resolve into a voice: "
                    "her own, younger and terrified.\n\n"
                    "'Don't dock,' it said. 'Don't—'"
                ),
                "published": True,
                "unlock_price_cents": None,
                "tier_required": "none",
            },
            {
                "number": 2,
                "title": "Station Nine",
                "format": "html",
                "content": (
                    "<p>Station Nine hung in the dark like a broken watchband—segments of habitat ring "
                    "connected by cables gone slack with decades of neglect.</p>"
                    "<p>Kai docked anyway. Salvage pilots don't get to be superstitious.</p>"
                ),
                "published": True,
                "unlock_price_cents": 199,
                "tier_required": "none",
            },
            {
                "number": 3,
                "title": "Ghost Loop",
                "format": "html",
                "content": (
                    "<p>The AI had been looping the same thirty seconds of her life for twenty years. "
                    "It thought it was saving her.</p>"
                    "<hr>"
                    "<p>She unplugged it with hands that shook.</p>"
                ),
                "published": True,
                "unlock_price_cents": None,
                "tier_required": "bronze",
            },
            {
                "number": 4,
                "title": "Drift",
                "format": "plain",
                "content": (
                    "She left Station Nine burning in reverse—engines pointed at the station, "
                    "thrust set to minimum. A funeral and an escape in one maneuver."
                ),
                "published": True,
                "unlock_price_cents": None,
                "tier_required": "silver",
            },
        ],
    },
    {
        "title": "The Weight of Silence",
        "author": "amara_okafor",
        "synopsis": (
            "After her grandmother's funeral, Adaeze inherits a house full of unsent letters "
            "written in a language she was never taught."
        ),
        "status": "published",
        "content_source": "upload",
        "cover_color": "#744210",
        "chapters": [
            {
                "number": 1,
                "title": "Letters Unsent",
                "format": "plain",
                "content": (
                    "The envelopes were stacked in the attic like sediment. "
                    "Each one addressed, none sealed. Adaeze held the top letter to the light "
                    "and saw her grandmother's handwriting—loops and crosses in Igbo and English braided together."
                ),
                "published": True,
                "unlock_price_cents": None,
                "tier_required": "none",
            },
            {
                "number": 2,
                "title": "What the Tongue Forgets",
                "format": "html",
                "content": (
                    "<p>Her mother refused to translate. 'Some things,' she said, 'are not for the living.'</p>"
                    "<p>Adaeze hired a tutor instead—a graduate student named Ibe who charged by the word "
                    "and blushed when she mispronounced his name.</p>"
                ),
                "published": True,
                "unlock_price_cents": None,
                "tier_required": "bronze",
            },
            {
                "number": 3,
                "title": "Inheritance",
                "format": "plain",
                "content": (
                    "The last letter was addressed to her. Dated the day before the funeral. "
                    "She opened it on the kitchen floor and read until the sun came up."
                ),
                "published": True,
                "unlock_price_cents": 399,
                "tier_required": "none",
            },
        ],
    },
    {
        "title": "Cold Signal",
        "author": "james_wolf",
        "synopsis": (
            "A true-crime podcaster receives an anonymous tip about a case she closed five years ago. "
            "The tip includes a detail only the killer would know."
        ),
        "status": "publishing",
        "content_source": "editor",
        "cover_color": "#1a202c",
        "chapters": [
            {
                "number": 1,
                "title": "Episode 47",
                "format": "plain",
                "content": (
                    "Rachel had buried the Harrow case in the 'solved' folder of her mind. "
                    "Then the email arrived: no subject, no signature, just twelve words. "
                    "The blue gloves were in the storm drain, not the river."
                ),
                "published": True,
                "unlock_price_cents": None,
                "tier_required": "none",
            },
            {
                "number": 2,
                "title": "Storm Drain",
                "format": "html",
                "content": (
                    "<p>She went back to Harrow at dawn with a borrowed flashlight and a recorder running.</p>"
                    "<p>The storm drain was exactly where the email said. So were the gloves—"
                    "brittle with age, still folded as if waiting.</p>"
                ),
                "published": True,
                "unlock_price_cents": 249,
                "tier_required": "none",
            },
            {
                "number": 3,
                "title": "Source",
                "format": "plain",
                "content": (
                    "The tipster wanted a meeting. No cameras, no mic. "
                    "Rachel went anyway because journalists die of curiosity before bullets."
                ),
                "published": True,
                "unlock_price_cents": None,
                "tier_required": "silver",
            },
        ],
    },
    {
        "title": "Ember & Ash",
        "author": "elena_rivers",
        "synopsis": "A dragon sleeps beneath the capital. The queen wants it dead. The dragon wants to be left alone.",
        "status": "draft",
        "content_source": "editor",
        "cover_color": "#9b2c2c",
        "chapters": [
            {
                "number": 1,
                "title": "The Sleeping City",
                "format": "plain",
                "content": "Work in progress — not yet published.",
                "published": False,
                "unlock_price_cents": None,
                "tier_required": "none",
            },
        ],
    },
    {
        "title": "Orbital Decay",
        "author": "marcus_chen",
        "synopsis": "The last repair crew on a dying space elevator must choose between saving the structure or saving themselves.",
        "status": "publishing",
        "content_source": "editor",
        "cover_color": "#553c9a",
        "chapters": [
            {
                "number": 1,
                "title": "Tether",
                "format": "plain",
                "content": (
                    "The elevator cable sang in the wind of upper atmosphere—a note too low for human ears, "
                    "felt in the teeth and the soles of the feet."
                ),
                "published": True,
                "unlock_price_cents": None,
                "tier_required": "none",
            },
            {
                "number": 2,
                "title": "Crew of Six",
                "format": "plain",
                "content": (
                    "Six engineers, one elevator, zero rescue windows until spring. "
                    "The math was simple and brutal."
                ),
                "published": True,
                "unlock_price_cents": None,
                "tier_required": "bronze",
            },
        ],
    },
    {
        "title": "Saltwater Saints",
        "author": "amara_okafor",
        "synopsis": "Fishermen on a shrinking island swear the sea is taking one person per year. This year, it's the priest's daughter.",
        "status": "publishing",
        "content_source": "sheets",
        "cover_color": "#2c5282",
        "chapters": [
            {
                "number": 1,
                "title": "Low Tide",
                "format": "plain",
                "content": (
                    "The island had lost a third of its landmass in forty years. "
                    "The church lost its congregation one funeral at a time."
                ),
                "published": True,
                "unlock_price_cents": None,
                "tier_required": "none",
            },
        ],
    },
    {
        "title": "The Last Informant",
        "author": "james_wolf",
        "synopsis": "A retired spy is pulled back in when his protégé vanishes in Prague.",
        "status": "published",
        "content_source": "editor",
        "cover_color": "#22543d",
        "chapters": [
            {
                "number": 1,
                "title": "Retirement",
                "format": "plain",
                "content": (
                    "Henrik had not touched a dead drop in eleven years. "
                    "The café in Malá Strana was his now—bad coffee, good light."
                ),
                "published": True,
                "unlock_price_cents": None,
                "tier_required": "none",
            },
            {
                "number": 2,
                "title": "Prague Winter",
                "format": "html",
                "content": (
                    "<p>The message was three words in a language he'd invented with his protégé: "
                    "<em>rain remembers everything</em>.</p>"
                ),
                "published": True,
                "unlock_price_cents": None,
                "tier_required": "bronze",
            },
        ],
    },
]

# reader_username -> list of author usernames to follow
FOLLOWS = {
    "alex_reader": ["elena_rivers", "marcus_chen", "amara_okafor"],
    "sam_reader": ["amara_okafor", "james_wolf"],
    "jordan_reader": ["marcus_chen", "james_wolf"],
}

# reader_username -> list of story titles to save
SAVED_STORIES = {
    "alex_reader": [
        "The Starlight Chronicle",
        "Neon Drift",
        "The Weight of Silence",
        "Cold Signal",
    ],
    "sam_reader": ["The Weight of Silence", "Saltwater Saints"],
    "jordan_reader": ["Neon Drift", "Orbital Decay", "The Last Informant"],
}

# reader_username -> list of (story_title, tier_name)
SUBSCRIPTIONS = {
    "alex_reader": [
        ("The Starlight Chronicle", "silver"),
        ("Neon Drift", "bronze"),
    ],
    "sam_reader": [
        ("The Weight of Silence", "gold"),
    ],
    "jordan_reader": [
        ("Orbital Decay", "bronze"),
    ],
}

# reader_username -> list of (story_title, chapter_number)
UNLOCKS = {
    "alex_reader": [
        ("The Starlight Chronicle", 2),
        ("Cold Signal", 2),
    ],
    "jordan_reader": [
        ("Neon Drift", 2),
    ],
}

# (story_title, chapter_number) -> list of {username, body}
COMMENTS = {
    ("The Starlight Chronicle", 1): [
        {
            "username": "alex_reader",
            "body": "That opening hit me like a wave. The lighthouse imagery is stunning.",
        },
        {
            "username": "sam_reader",
            "body": "Already hooked. Mara's voice feels so assured for a first chapter.",
        },
    ],
    ("Neon Drift", 1): [
        {
            "username": "jordan_reader",
            "body": "The distress beacon twist gave me chills. More Kai immediately please.",
        },
    ],
    ("The Weight of Silence", 1): [
        {
            "username": "sam_reader",
            "body": "The attic scene made me think of my own grandmother's house. Beautiful.",
        },
        {
            "username": "alex_reader",
            "body": "Amara's prose is incredible. Subscribed to Gold without hesitation.",
        },
    ],
    ("Cold Signal", 1): [
        {
            "username": "jordan_reader",
            "body": "Twelve words and I'm in. Wolf knows thrillers.",
        },
    ],
}

# (story_title, chapter_number) -> list of {username, reaction_type}
REACTIONS = {
    ("The Starlight Chronicle", 1): [
        {"username": "alex_reader", "reaction_type": "love"},
        {"username": "sam_reader", "reaction_type": "like"},
    ],
    ("Neon Drift", 1): [
        {"username": "jordan_reader", "reaction_type": "fire"},
        {"username": "alex_reader", "reaction_type": "insightful"},
    ],
    ("The Weight of Silence", 1): [
        {"username": "sam_reader", "reaction_type": "love"},
    ],
    ("Cold Signal", 1): [
        {"username": "jordan_reader", "reaction_type": "like"},
        {"username": "sam_reader", "reaction_type": "insightful"},
    ],
    ("Orbital Decay", 1): [
        {"username": "jordan_reader", "reaction_type": "fire"},
    ],
}

TRANSACTIONS = [
    {
        "username": "alex_reader",
        "type": "chapter_unlock",
        "amount_cents": 299,
        "story_title": "The Starlight Chronicle",
        "chapter_number": 2,
    },
    {
        "username": "alex_reader",
        "type": "subscription",
        "amount_cents": 999,
        "story_title": "The Starlight Chronicle",
        "tier": "silver",
    },
    {
        "username": "sam_reader",
        "type": "subscription",
        "amount_cents": 1999,
        "story_title": "The Weight of Silence",
        "tier": "gold",
    },
]
