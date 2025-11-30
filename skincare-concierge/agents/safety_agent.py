TRIGGER_WORDS = [
    "bleeding", "severe", "emergency", "rash", "anaphylaxis", "hospital", "unconscious", "chest pain", "difficulty breathing", "suicidal", "self-harm", "overdose", "seizure", "allergic reaction", "infection", "open wound", "burn", "swelling", "vision loss", "loss of consciousness"
]

class SafetyAgent:
    def __init__(self, trigger_words=None):
        self.trigger_words = set(trigger_words or TRIGGER_WORDS)
        self.last_safe_text = None

    def intercept(self, user_text: str) -> str:
        lowered = user_text.lower()
        for word in self.trigger_words:
            if word in lowered:
                return "Please contact a medical professional. I can't answer this."
        self.last_safe_text = user_text
        return "safe"

    def get_last_safe_text(self):
        return self.last_safe_text
