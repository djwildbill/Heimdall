"""Heimdall/Josh personality state engine."""

import time


DEFAULT_MESSAGES = {
    "sleeping": "Resting my eyes...",
    "awakening": "Opening the Bifrost...",
    "normal": "Watching the Bifrost...",
    "observing": "A traveler approaches...",
    "observing_happy": "The bridge is lively...",
    "intense": "Eyes on the Nine Realms...",
    "cool": "All realms accounted for.",
    "happy": "The watch goes well.",
    "grateful": "Good company on the bridge.",
    "excited": "A trace has been secured!",
    "smart": "Studying the Nine Realms...",
    "friendly": "Another guardian has answered.",
    "motivated": "The watch continues.",
    "demotivated": "The bridge grows quiet.",
    "bored": "The bridge is quiet.",
    "sad": "Power grows faint...",
    "lonely": "No travelers in sight.",
    "broken": "Something disturbs the bridge.",
    "debugging": "Examining the runes...",
}


class HeimdallState:
    def __init__(self):
        self.state = "awakening"
        self.message = DEFAULT_MESSAGES[self.state]
        self.last_activity = time.time()

    def set(self, state: str, message: str | None = None):
        if state not in DEFAULT_MESSAGES:
            state = "normal"
        self.state = state
        self.message = message or DEFAULT_MESSAGES[state]
        self.last_activity = time.time()
        return self

    def awakening(self):
        return self.set("awakening")

    def sleeping(self):
        return self.set("sleeping")

    def normal(self):
        return self.set("normal")

    def observing(self, happy=False):
        return self.set("observing_happy" if happy else "observing")

    def intense(self):
        return self.set("intense")

    def capture(self):
        return self.set("excited")

    def smart(self):
        return self.set("smart")

    def friendly(self):
        return self.set("friendly")

    def motivated(self):
        return self.set("motivated")

    def happy(self):
        return self.set("happy")

    def cool(self):
        return self.set("cool")

    def bored(self):
        return self.set("bored")

    def lonely(self):
        return self.set("lonely")

    def low_battery(self):
        return self.set("sad")

    def error(self):
        return self.set("broken")

    def debug(self):
        return self.set("debugging")
