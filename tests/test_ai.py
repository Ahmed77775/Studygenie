import json
import unittest

from app.prompts import extract_json as extract


class ExtractJsonTests(unittest.TestCase):
    def test_plain_list(self):
        self.assertEqual(extract('[{"question": "q", "answer": "a"}]'), [{"question": "q", "answer": "a"}])

    def test_markdown_code_fence(self):
        text = '```json\n[{"question": "q", "answer": "a"}]\n```'
        self.assertEqual(extract(text), [{"question": "q", "answer": "a"}])

    def test_chatter_around_the_list(self):
        text = 'Sure! Here are your cards:\n[{"question": "q", "answer": "a"}]\nGood luck!'
        self.assertEqual(len(extract(text)), 1)

    def test_unicode_content_survives(self):
        text = '[{"question": "प्रकाश संश्लेषण क्या है?", "answer": "ऊर्जा"}]'
        self.assertEqual(extract(text)[0]["answer"], "ऊर्जा")

    def test_no_list_raises(self):
        with self.assertRaises(ValueError):
            extract('{"question": "q"}')

    def test_empty_list_raises(self):
        with self.assertRaises(ValueError):
            extract("[]")

    def test_truncated_reply_raises(self):
        # A reply cut off mid-way (e.g. by the token cap) must fail loudly
        # so the retry kicks in, not produce half a deck.
        with self.assertRaises(json.JSONDecodeError):
            extract('[{"question": "q", "answer": "a"}, {"question": "q2"] ')


class PromptHelperTests(unittest.TestCase):
    def test_split_topic_line(self):
        from app.prompts import split_topic_line
        self.assertEqual(split_topic_line("Topic: Ohm's law\n\nV = IR."), ("Ohm's law", "V = IR."))
        self.assertEqual(split_topic_line("**Topic:** Linear equations.\nSolve it"), ("Linear equations", "Solve it"))
        self.assertEqual(split_topic_line("No topic here"), ("", "No topic here"))

    def test_short_topic(self):
        from app.prompts import short_topic
        self.assertEqual(short_topic("Photosynthesis\nmore lines"), "Photosynthesis")
        self.assertTrue(short_topic("word " * 30).endswith("…"))
        self.assertEqual(short_topic(""), "")


class QuizRepairTests(unittest.TestCase):
    def test_letter_answer_and_labelled_options(self):
        # What gemma3:4b actually returned for a Hindi quiz.
        from app.prompts import valid_quiz
        item = {"question": "ओम का नियम?", "options": ["A) I ∝ V", "B) I = V/R", "C) V ∝ R", "D) V = IR"],
                "answer": "B", "explanation": ""}
        [fixed] = valid_quiz([item])
        self.assertEqual(fixed["options"], ["I ∝ V", "I = V/R", "V ∝ R", "V = IR"])
        self.assertEqual(fixed["answer"], "I = V/R")

    def test_labelled_answer(self):
        from app.prompts import normalize_quiz_item
        item = {"question": "q", "options": ["(a) one", "(b) two", "(c) three", "(d) four"], "answer": "(c) three"}
        self.assertEqual(normalize_quiz_item(item)["answer"], "three")

    def test_good_items_untouched_and_bad_rejected(self):
        from app.prompts import valid_quiz
        good = {"question": "q", "options": ["Volt", "Ohm", "Amp", "Watt"], "answer": "Ohm"}
        self.assertEqual(valid_quiz([good]), [good])
        self.assertEqual(valid_quiz([{"question": "q", "options": ["x", "y"], "answer": "z"}]), [])
        # An option that merely starts with a capital letter and a dot isn't a label to strip.
        mixed = {"question": "q", "options": ["A. Einstein", "Newton", "Bohr", "Curie"], "answer": "Newton"}
        self.assertEqual(valid_quiz([mixed])[0]["options"][0], "A. Einstein")


class LanguageRuleTests(unittest.TestCase):
    def test_every_listed_language_has_a_rule_and_speech_code(self):
        from app.content import ContentMixin
        from app.prompts import LANGUAGE_INFO, language_rule, speech_code
        for language in ContentMixin.LANGUAGES:
            self.assertIn(language, LANGUAGE_INFO)
            self.assertTrue(speech_code(language).endswith("-IN"))
        rule = language_rule("Malayalam")
        self.assertIn("മലയാളം", rule)
        self.assertIn("Malayalam script", rule)
        self.assertNotIn("translitera", rule)  # naming it made the model add one
        self.assertEqual(language_rule("English"), "Reply in English. ")
        self.assertEqual(speech_code("Klingon"), "en-IN")

    def test_clean_reply_strips_tacked_on_english(self):
        from app.prompts import clean_reply
        tamil = ("ஒளிச்சேர்க்கை என்பது ஒரு செயல்முறை (CO₂). "
                 "(Olichaikkai enna thavarangal solai uyarthai karban diaryakottai matt)")
        self.assertEqual(clean_reply(tamil, "Tamil"), "ஒளிச்சேர்க்கை என்பது ஒரு செயல்முறை (CO₂).")
        hindi = "प्रकाश संश्लेषण एक प्रक्रिया है।\n\nTranslation: Photosynthesis is a process."
        self.assertEqual(clean_reply(hindi, "Hindi"), "प्रकाश संश्लेषण एक प्रक्रिया है।")
        english = "Plants make food (this happens in the chloroplasts of leaf cells)."
        self.assertEqual(clean_reply(english, "English"), english)
        # What Urdu actually produced: a bracketed English paragraph with brackets inside it.
        urdu = ("فوٹوسینتھیز ایک ایسا عمل ہے (CO₂)۔\n\n"
                "(Okay, listen! Photosynthesis is a process in which plants convert water (H₂O) and "
                "carbon dioxide (CO₂) into glucose (C₆H₁₂O₆).)")
        self.assertEqual(clean_reply(urdu, "Urdu"), "فوٹوسینتھیز ایک ایسا عمل ہے (CO₂)۔")
        # Seen from the model: a translation spanning paragraphs, and an unbracketed one.
        hindi_multi = ("ज़रूर, मैं समझाता हूँ।\n\nप्रकाश संश्लेषण एक प्रक्रिया है।\n\n"
                       "(Translation: Certainly, I will explain.\n\nPhotosynthesis is a process (glucose).)")
        self.assertEqual(clean_reply(hindi_multi, "Hindi"), "ज़रूर, मैं समझाता हूँ।\n\nप्रकाश संश्लेषण एक प्रक्रिया है।")
        tamil_plain = "ஒளிச்சேர்க்கை ஒரு செயல்முறை.\n\nEssentially: Photosynthesis is the process plants use."
        self.assertEqual(clean_reply(tamil_plain, "Tamil"), "ஒளிச்சேர்க்கை ஒரு செயல்முறை.")
        # A trailing code block in a non-English answer is kept.
        code = "इस कोड को देखें:\n\n```python\nprint('hello')\n```"
        self.assertEqual(clean_reply(code, "Hindi"), code)
        # A reply that is entirely English (the model ignored the language) is left as is.
        self.assertEqual(clean_reply("Plants make food from light.", "Hindi"), "Plants make food from light.")
        native_bracket = "ಇದು ಒಂದು ಪ್ರಕ್ರಿಯೆ (ಸಸ್ಯಗಳು ಸೂರ್ಯನ ಬೆಳಕನ್ನು ಬಳಸಿ ಆಹಾರವನ್ನು ತಯಾರಿಸುತ್ತವೆ)"
        self.assertEqual(clean_reply(native_bracket, "Kannada"), native_bracket)


if __name__ == "__main__":
    unittest.main()
