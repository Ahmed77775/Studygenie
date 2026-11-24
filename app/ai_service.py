"""Background AI calls for the Flet screens.

Each call runs on its own thread and reports back through callbacks, so
the interface never freezes. Prompts and reply parsing come from
app/prompts.py. Errors reach the user as
plain sentences; the technical detail goes to the console."""

import logging
import threading

from . import prompts
from .deps import chat

log = logging.getLogger("studygenie.ai")


def friendly_error(exc):
    """A sentence a student can act on, instead of a Python traceback."""
    text = f"{type(exc).__name__}: {exc}".lower()
    if chat is None:
        return "The Ollama package isn't installed. Run: pip install ollama"
    if "not found" in text and ("model" in text or prompts.MODEL in text):
        return f"The {prompts.MODEL} model isn't installed yet. Run: ollama pull {prompts.MODEL}"
    if any(word in text for word in ("connect", "refused", "unreachable", "timed out", "timeout")):
        return "StudyGenie can't reach Ollama. Make sure the Ollama app is running, then try again."
    if "json" in text or "did not return" in text or "empty" in text:
        return "Genie's reply came back incomplete. Please try once more."
    return "Genie couldn't finish that. Please try again in a moment."


def _run(target):
    threading.Thread(target=target, daemon=True).start()


def available():
    return chat is not None


def ask(question, history, subject, language, mode, image_bytes=None,
        on_piece=None, on_done=None, on_error=None):
    """Streams an AI Teacher answer. `history` is a list of earlier
    {"role", "content"} messages; an optional image is sent with the question."""
    def work():
        try:
            if chat is None:
                raise RuntimeError("ollama missing")
            user = {"role": "user", "content": question}
            if image_bytes:
                user["images"] = [image_bytes]
            messages = ([{"role": "system", "content": prompts.chat_system_prompt(subject, language, mode)}]
                        + history[-prompts.HISTORY_TURNS:] + [user])
            pieces = []
            for chunk in chat(model=prompts.MODEL, messages=messages, stream=True,
                              keep_alive=prompts.KEEP_ALIVE, options=prompts.CHAT_OPTIONS):
                piece = chunk.get("message", {}).get("content", "")
                if piece:
                    pieces.append(piece)
                    on_piece and on_piece(piece)
            answer = prompts.clean_reply("".join(pieces).strip(), language)
            if not answer:
                raise ValueError("empty answer")
            on_done and on_done(answer)
        except Exception as exc:
            log.exception("AI Teacher request failed")
            on_error and on_error(friendly_error(exc))
    _run(work)


def read_photo(image_bytes, mode, subject, language, on_piece=None, on_done=None, on_error=None):
    """Streams a reading of a photo. on_done(topic, text) gets the detected
    topic (may be "") and the reply without its topic line."""
    def work():
        try:
            if chat is None:
                raise RuntimeError("ollama missing")
            messages = [{"role": "system",
                         "content": prompts.photo_system_prompt(mode, subject, language, detect_topic=True)},
                        {"role": "user", "content": "Here is my photo.", "images": [image_bytes]}]
            pieces = []
            for chunk in chat(model=prompts.MODEL, messages=messages, stream=True,
                              keep_alive=prompts.KEEP_ALIVE, options=prompts.PHOTO_OPTIONS):
                piece = chunk.get("message", {}).get("content", "")
                if piece:
                    pieces.append(piece)
                    on_piece and on_piece("".join(pieces))
            topic, body = prompts.split_topic_line("".join(pieces))
            body = prompts.clean_reply(body, language)
            if not body:
                raise ValueError("empty answer")
            on_done and on_done(topic, body)
        except Exception as exc:
            log.exception("Photo Study request failed")
            on_error and on_error(friendly_error(exc))
    _run(work)


def generate_set(kind, source, subject, language, on_done=None, on_error=None):
    """Makes flashcards or a quiz from `source` text. on_done(items) gets
    only well-formed items; one automatic retry covers a malformed reply."""
    def work():
        try:
            if chat is None:
                raise RuntimeError("ollama missing")
            messages = [{"role": "system", "content": prompts.study_set_instruction(kind, subject, language)},
                        {"role": "user", "content": source}]
            last_error = None
            for _attempt in range(2):
                try:
                    reply = chat(model=prompts.MODEL, messages=messages, keep_alive=prompts.KEEP_ALIVE,
                                 options=prompts.SET_OPTIONS)
                    items = prompts.extract_json(reply["message"]["content"])
                    valid = prompts.valid_flashcards(items) if kind == "flashcards" else prompts.valid_quiz(items)
                    if valid:
                        on_done and on_done(valid)
                        return
                    last_error = ValueError("empty set")
                except Exception as exc:
                    last_error = exc
            raise last_error
        except Exception as exc:
            log.exception("Study set generation failed")
            on_error and on_error(friendly_error(exc))
    _run(work)
