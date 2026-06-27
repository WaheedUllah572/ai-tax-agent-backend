import os
import json

CALENDAR_TOKEN_PATH = "calendar_token.json"


def save_calendar_tokens(tokens: dict):
    with open(CALENDAR_TOKEN_PATH, "w") as f:
        json.dump(tokens, f, indent=4)


def load_calendar_tokens():
    if not os.path.exists(CALENDAR_TOKEN_PATH):
        return None

    with open(CALENDAR_TOKEN_PATH, "r") as f:
        return json.load(f)