"""The local profile: avatar choices and PIN hashing."""

import hashlib

PIN_SALT = "studygenie-local-v1"  # changing this would lock out existing PINs
AVATARS = ("🦊", "🐼", "🦉", "🐙", "🐝", "🚀", "🌸", "🧠")


def hash_pin(pin):
    return hashlib.sha256((PIN_SALT + pin).encode("utf-8")).hexdigest()
