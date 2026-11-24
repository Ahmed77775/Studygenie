"""What StudyGenie asks the local model, and how it reads the replies.

Plain functions with no UI imports, used by app/ai_service.py."""

import json
import re

MODEL = "gemma3:4b"   # Ollama model for chat, photos, flashcards and quizzes

KEEP_ALIVE = "30m"    # keeps the model loaded between requests

CHAT_OPTIONS = {"temperature": 0.4, "num_predict": 650}

PHOTO_OPTIONS = {"temperature": 0.3, "num_predict": 900}

SET_OPTIONS = {"temperature": 0.4, "num_predict": 2000}  # generous: Indian-language scripts use many tokens

HISTORY_TURNS = 12    # earlier messages sent with each chat question

# --- Teaching language -------------------------------------------------------
# Naming the language in its own script and stating the script keeps a small
# model from drifting (without it, Malayalam replies came back in Tamil).

LANGUAGE_INFO = {  # name: (native name, script, speech-recognition code)
    "English": ("English", "Latin", "en-IN"),
    "Hindi": ("हिन्दी", "Devanagari", "hi-IN"),
    "Telugu": ("తెలుగు", "Telugu", "te-IN"),
    "Urdu": ("اردو", "Urdu (Perso-Arabic)", "ur-IN"),
    "Tamil": ("தமிழ்", "Tamil", "ta-IN"),
    "Kannada": ("ಕನ್ನಡ", "Kannada", "kn-IN"),
    "Malayalam": ("മലയാളം", "Malayalam", "ml-IN"),
    "Bengali": ("বাংলা", "Bengali", "bn-IN"),
    "Marathi": ("मराठी", "Devanagari", "mr-IN"),
}


def language_rule(language):
    """The instruction that makes the model teach in `language`."""
    if language not in LANGUAGE_INFO or language == "English":
        return "Reply in English. "
    native, script, _ = LANGUAGE_INFO[language]
    # Worded positively on purpose: naming "transliteration" made the model add one.
    return (f"Write your entire reply in {language} ({native}), using only the {script} script, and explain "
            f"naturally, the way a good native-speaking teacher would. Keep formulas, units and standard "
            f"technical terms as they are. ")


_BRACKETED = re.compile(r"\s*\(([^()]{30,})\)")
_TRANSLATION_LINE = re.compile(r"^\s*[*_]*\s*(translation|transliteration|in english)\s*[*_]*\s*:.*$",
                               re.IGNORECASE | re.MULTILINE)


def _mostly_latin(text):
    letters = [ch for ch in text if ch.isalpha()]
    return bool(letters) and sum(ch.isascii() for ch in letters) / len(letters) > 0.8


def clean_reply(text, language):
    """Removes English translations/transliterations a small model sometimes
    tacks onto a non-English reply: long bracketed passages that are mostly
    Latin letters, and 'Translation: …' lines. Short brackets such as (CO₂)
    and English replies are left alone."""
    if not text or language == "English" or language not in LANGUAGE_INFO:
        return text
    paragraphs = [p for p in re.split(r"\n\s*\n", text) if p.strip()]
    # Translations come after the real answer: drop the trailing run of
    # mostly-English paragraphs ("(Translation: …", "Essentially: …"),
    # keeping code blocks, as long as some native-language text remains.
    native = [i for i, p in enumerate(paragraphs) if not _mostly_latin(p)]
    if native:
        tail = paragraphs[native[-1] + 1:]
        paragraphs = paragraphs[:native[-1] + 1] + [p for p in tail if p.lstrip().startswith("```")]
    # A whole bracketed paragraph elsewhere (often with brackets inside, like (H₂O)).
    paragraphs = [p for p in paragraphs
                  if not (p.strip().startswith("(") and p.strip().rstrip(".!").endswith(")") and _mostly_latin(p))]
    text = "\n\n".join(paragraphs)
    text = _BRACKETED.sub(lambda m: "" if _mostly_latin(m.group(1)) else m.group(0), text)
    text = _TRANSLATION_LINE.sub("", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


# Tested 3 runs each with gemma3:4b: these still mix in other scripts and
# languages, so the app labels them instead of claiming they work.
UNRELIABLE_LANGUAGES = ("Kannada", "Malayalam")

EXPERIMENTAL = " (experimental)"

LANGUAGE_WARNING = ("Kannada and Malayalam answers from this AI model often mix in other languages. "
                    "A larger model (for example gemma3:12b) handles them better.")


def language_label(language):
    """How a language appears in menus: unreliable ones say so."""
    return language + EXPERIMENTAL if language in UNRELIABLE_LANGUAGES else language


def language_from_label(label):
    return (label or "").replace(EXPERIMENTAL, "").strip()


# Tested 3 runs each with gemma3:4b: these still mix in other scripts and
# languages, so the app labels them instead of claiming they work.
UNRELIABLE_LANGUAGES = ("Kannada", "Malayalam")

EXPERIMENTAL = " (experimental)"

LANGUAGE_WARNING = ("Kannada and Malayalam answers from this AI model often mix in other languages. "
                    "A larger model (for example gemma3:12b) handles them better.")


def language_label(language):
    """How a language appears in menus: unreliable ones say so."""
    return language + EXPERIMENTAL if language in UNRELIABLE_LANGUAGES else language


def language_from_label(label):
    return (label or "").replace(EXPERIMENTAL, "").strip()


# Tested 3 runs each with gemma3:4b: these still mix in other scripts and
# languages, so the app labels them instead of claiming they work.
UNRELIABLE_LANGUAGES = ("Kannada", "Malayalam")

EXPERIMENTAL = " (experimental)"

LANGUAGE_WARNING = ("Kannada and Malayalam answers from this AI model often mix in other languages. "
                    "A larger model (for example gemma3:12b) handles them better.")


def language_label(language):
    """How a language appears in menus: unreliable ones say so."""
    return language + EXPERIMENTAL if language in UNRELIABLE_LANGUAGES else language


def language_from_label(label):
    return (label or "").replace(EXPERIMENTAL, "").strip()


def speech_code(language):
    """The speech-recognition language code for a teaching language."""
    return LANGUAGE_INFO.get(language, LANGUAGE_INFO["English"])[2]


def chat_system_prompt(subject, language, mode):
    return (
        f"You are StudyGenie, a warm, accurate study companion for {subject}. "
        + language_rule(language) +
        f"Response mode: {mode}. Use short sections, concrete examples, and clear steps. "
        "Do not invent facts. Keep answers focused and under ~180 words unless the learner "
        "explicitly asks for more depth — brevity keeps things fast and easy to study from."
    )


PHOTO_PROMPTS = {
    "explain": ("Look at the photo (a textbook page, worksheet or question). Start with one line "
                "saying what it shows. If it contains a question or problem, solve it step by step. "
                "Otherwise explain the key ideas simply, with one concrete example. "
                "Use short sections. Keep it under ~250 words."),
    "notes": ("Turn the photo into concise study notes: a title line, then 4-8 bullet points "
              "of the key facts, definitions and formulas, then a one-line summary. "
              "Only include what the photo actually shows."),
}

TOPIC_LINE = ("Your very first line must be exactly 'Topic: <the specific topic, at most six words>', "
              "then a blank line, then the rest of your reply. ")


def photo_system_prompt(mode, subject, language, detect_topic=False):
    return (f"You are StudyGenie, a warm, accurate tutor for {subject}. "
            + language_rule(language) +
            "If the photo is unreadable or not study material, say so briefly. "
            "Do not invent text that is not in the photo. "
            + (TOPIC_LINE if detect_topic else "") + PHOTO_PROMPTS[mode])


def split_topic_line(text):
    """('Topic: Ohm's law\\n\\nbody...') -> ("Ohm's law", "body..."). Text without
    a topic line comes back unchanged with an empty topic."""
    match = re.match(r"^\s*\**\s*topic\s*\**\s*:\s*\**\s*(.+?)\**\s*(?:\n|$)", text, flags=re.IGNORECASE)
    if not match:
        return "", text.strip()
    return match.group(1).strip().rstrip("."), text[match.end():].strip()


def _written_in(language):
    if language not in LANGUAGE_INFO or language == "English":
        return "in English"
    native, script, _ = LANGUAGE_INFO[language]
    return f"in {language} ({native}), using only the {script} script"


def study_set_instruction(kind, subject, language):
    if kind == "flashcards":
        return ("Return ONLY valid JSON: an array of exactly 6 objects with keys question, answer, subject. "
                f"Write every question and answer {_written_in(language)}. Subject focus: {subject}. "
                "Keep each flashcard short, accurate, and exam-ready. Source material:")
    return ("Return ONLY valid JSON: an array of exactly 5 objects with keys question, "
            "options (array of exactly 4 strings, without A/B/C/D labels), "
            "answer (the full text of the correct option, copied exactly), explanation. "
            f"Write everything {_written_in(language)}. Subject focus: {subject}. "
            "Make fair, unambiguous multiple-choice questions. Source material:")


def extract_json(text):
    """Pulls the JSON list out of a model reply (code fences and chatter allowed)."""
    clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)
    start, end = clean.find("["), clean.rfind("]")
    if start < 0 or end < start:
        raise ValueError("The model did not return a JSON list. Please try once more.")
    result = json.loads(clean[start:end + 1])
    if not isinstance(result, list) or not result:
        raise ValueError("The generated study set was empty.")
    return result


def valid_flashcards(items):
    return [item for item in items if isinstance(item, dict) and item.get("question") and item.get("answer")]


_OPTION_LABEL = re.compile(r"^\s*\(?([A-Da-d])\s*[\).:\-]\s*")


def normalize_quiz_item(item):
    """Repairs a common model habit: options labelled "A) …" and the answer
    given as a letter ("B") instead of the option's text."""
    if not isinstance(item, dict) or not isinstance(item.get("options"), list):
        return item
    options = [str(option).strip() for option in item["options"]]
    if options and all(_OPTION_LABEL.match(option) for option in options):
        options = [_OPTION_LABEL.sub("", option, count=1) for option in options]
    answer = str(item.get("answer", "")).strip()
    if answer not in options:
        letter = re.fullmatch(r"\(?([A-Da-d])\)?[\).:]?", answer)
        if letter and "ABCD".index(letter.group(1).upper()) < len(options):
            answer = options["ABCD".index(letter.group(1).upper())]
        elif _OPTION_LABEL.match(answer) and _OPTION_LABEL.sub("", answer, count=1) in options:
            answer = _OPTION_LABEL.sub("", answer, count=1)
    return {**item, "options": options, "answer": answer}


def valid_quiz(items):
    items = [normalize_quiz_item(item) for item in items]
    return [item for item in items if isinstance(item, dict) and item.get("question")
            and isinstance(item.get("options"), list) and item.get("answer") in item.get("options", [])]


def short_topic(text, limit=60):
    """A topic label from free text: its first line, trimmed to a word boundary."""
    line = (text or "").strip().splitlines()[0] if (text or "").strip() else ""
    if len(line) <= limit:
        return line
    return line[:limit].rsplit(" ", 1)[0] + "…"
