"""Josh's Heimdall personality faces.

The state names intentionally mirror the useful emotional/state vocabulary from
Pwnagotchi while keeping the personality layer owned by Heimdall.
"""

FACES = {
    "sleeping": "(⇀‿‿↼)",
    "awakening": "(≖‿‿≖)",
    "normal": "(◕‿‿◕)",
    "observing": "( ⚆⚆)",
    "observing_happy": "( ◕‿◕)",
    "intense": "(°▃▃°)",
    "cool": "(⌐■_■)",
    "happy": "(•‿‿•)",
    "grateful": "(^‿‿^)",
    "excited": "(ᵔ◡◡ᵔ)",
    "smart": "(✜‿‿✜)",
    "friendly": "(♥‿‿♥)",
    "motivated": "(☼‿‿☼)",
    "demotivated": "(≖__≖)",
    "bored": "(-__-)",
    "sad": "(╥☁╥ )",
    "lonely": "(ب__ب)",
    "broken": "(☓‿‿☓)",
    "debugging": "(#__#)",
}


def get_face(state: str) -> str:
    """Return the face for a Heimdall/Josh state."""
    return FACES.get(state, FACES["normal"])
