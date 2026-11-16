"""Named settings stored locally in Graffy's preferences."""

import json

from PyQt6.QtCore import QSettings


def load_settings(key):
    settings = QSettings("Graffy", "Graffy")
    try:
        values = json.loads(settings.value(key, "{}", type=str))
    except (TypeError, ValueError):
        return {}
    return values if isinstance(values, dict) else {}


def store_settings(key, values):
    QSettings("Graffy", "Graffy").setValue(key, json.dumps(values))
