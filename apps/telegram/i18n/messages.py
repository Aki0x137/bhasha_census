"""Localized message strings for the Telegram bot (FR-005).

Supports English (en) and Hindi (hi) for MVP.
Add more locales by extending MESSAGES dict.
"""
from __future__ import annotations

MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        # Consent
        "consent_prompt": (
            "Welcome to the Bhasaha Census bot.\n\n"
            "To complete enrollment, I need to collect:\n"
            "• Basic census information (name, age, gender, location)\n"
            "• A selfie or short video (liveness check)\n"
            "• A voice sample\n"
            "• A photo of your identity document\n\n"
            "Your data is stored securely and used only for this census.\n\n"
            "Do you consent? Reply *Yes* to continue or *No* to exit."
        ),
        "consent_accepted": "Thank you! Let's begin. I'll ask you a few questions.",
        "consent_declined": "Understood. Your data will not be collected. Goodbye.",
        # Census questions
        "ask_name": "What is your full name?",
        "ask_dob": "What is your date of birth or age? (e.g. 1990-05-12 or 34)",
        "ask_gender": "What is your gender? (e.g. Male / Female / Other)",
        "ask_locality": "What is your current locality or address?",
        "ask_household": "How many people live in your household (including yourself)?",
        "confirm_profile": (
            "Please confirm your details:\n\n"
            "Name: {full_name}\n"
            "DOB/Age: {dob_or_age}\n"
            "Gender: {gender}\n"
            "Locality: {locality}\n"
            "Household size: {household_size}\n\n"
            "Reply *Confirm* to proceed or *Edit* to restart."
        ),
        "profile_confirmed": "Great! Moving to identity verification.",
        # Challenges
        "presence_challenge_prompt": (
            "Challenge: {prompt_text}\n\n"
            "Please take a photo or short video and send it.\n"
            "You have {time_limit_s} seconds and {max_attempts} attempt(s)."
        ),
        "challenge_retry": "I couldn't verify that. Please try again ({attempts_left} attempt(s) left).",
        "challenge_multi_face": "Multiple faces detected. Please ensure only you are in the frame and try again.",
        "challenge_failed": "Challenge failed after all attempts. Moving to review.",
        "challenge_passed": "✓ Verification step passed!",
        "speech_challenge_prompt": "Please say the following phrase and send it as a voice message:\n\n*{phrase}*",
        "speech_match_ok": "✓ Voice response matched.",
        "speech_mismatch": "Voice response didn't match. Try again ({attempts_left} left).",
        # Document
        "doc_capture_prompt": "Please take a clear photo of your identity document and send it.",
        "doc_readable": "✓ Document read successfully.",
        "doc_unreadable": "I couldn't read the document clearly. Please try again ({attempts_left} left).",
        "doc_retry_exhausted": "Document could not be verified. Your case will be reviewed manually.",
        # Verdict
        "verdict_approved": "✅ Enrollment approved!\n\nReason: {reasons}",
        "verdict_needs_review": "🔍 Your enrollment needs manual review.\n\nReason: {reasons}",
        "verdict_rejected": "❌ Enrollment rejected.\n\nReason: {reasons}",
        "verdict_needs_more_evidence": "⚠️ More information needed to complete enrollment.\n\nReason: {reasons}",
        # Generic
        "session_resumed": "Welcome back! Resuming your enrollment session.",
        "unexpected_error": "Something went wrong. Please try again or contact support.",
        "media_error": "I couldn't process the media you sent. Please try again.",
    },
    "hi": {
        # Consent
        "consent_prompt": (
            "भाषा जनगणना बॉट में आपका स्वागत है।\n\n"
            "नामांकन पूरा करने के लिए मुझे चाहिए:\n"
            "• बुनियादी जनगणना जानकारी\n"
            "• सेल्फी या छोटा वीडियो (लाइवनेस जांच)\n"
            "• आवाज़ का नमूना\n"
            "• पहचान दस्तावेज़ की फोटो\n\n"
            "क्या आप सहमत हैं? *हाँ* या *नहीं* उत्तर दें।"
        ),
        "consent_accepted": "धन्यवाद! शुरू करते हैं।",
        "consent_declined": "ठीक है। आपका डेटा संग्रहीत नहीं किया जाएगा।",
        "ask_name": "आपका पूरा नाम क्या है?",
        "ask_dob": "आपकी जन्मतिथि या आयु क्या है?",
        "ask_gender": "आपका लिंग क्या है?",
        "ask_locality": "आपका वर्तमान क्षेत्र या पता क्या है?",
        "ask_household": "आपके घर में कितने लोग रहते हैं?",
        "confirm_profile": (
            "कृपया अपनी जानकारी की पुष्टि करें:\n\n"
            "नाम: {full_name}\n"
            "DOB/आयु: {dob_or_age}\n"
            "लिंग: {gender}\n"
            "क्षेत्र: {locality}\n"
            "परिवार: {household_size}\n\n"
            "*पुष्टि* या *संपादन* उत्तर दें।"
        ),
        "profile_confirmed": "बढ़िया! पहचान सत्यापन पर आगे बढ़ रहे हैं।",
        "presence_challenge_prompt": "चुनौती: {prompt_text}\n\nफोटो या वीडियो भेजें।",
        "challenge_retry": "सत्यापन नहीं हो सका। फिर कोशिश करें ({attempts_left} बचे)।",
        "challenge_multi_face": "एक से अधिक चेहरे मिले। केवल आप फ्रेम में हों।",
        "challenge_failed": "चुनौती विफल। समीक्षा पर जाएँगे।",
        "challenge_passed": "✓ चरण पूरा!",
        "speech_challenge_prompt": "यह वाक्य बोलें और वॉइस मेसेज भेजें:\n\n*{phrase}*",
        "speech_match_ok": "✓ आवाज़ मिली।",
        "speech_mismatch": "आवाज़ नहीं मिली। फिर कोशिश करें ({attempts_left} बचे)।",
        "doc_capture_prompt": "अपने पहचान दस्तावेज़ की स्पष्ट फोटो भेजें।",
        "doc_readable": "✓ दस्तावेज़ पढ़ा गया।",
        "doc_unreadable": "दस्तावेज़ स्पष्ट नहीं। फिर कोशिश करें ({attempts_left} बचे)।",
        "doc_retry_exhausted": "दस्तावेज़ सत्यापित नहीं हो सका। मैनुअल समीक्षा होगी।",
        "verdict_approved": "✅ नामांकन स्वीकृत!\n\nकारण: {reasons}",
        "verdict_needs_review": "🔍 मैनुअल समीक्षा आवश्यक।\n\nकारण: {reasons}",
        "verdict_rejected": "❌ नामांकन अस्वीकृत।\n\nकारण: {reasons}",
        "verdict_needs_more_evidence": "⚠️ अधिक जानकारी चाहिए।\n\nकारण: {reasons}",
        "session_resumed": "वापस आपका स्वागत है! नामांकन जारी है।",
        "unexpected_error": "कुछ गलत हुआ। फिर कोशिश करें।",
        "media_error": "मीडिया प्रोसेस नहीं हो सका। फिर भेजें।",
    },
}

_DEFAULT_LOCALE = "en"


def get_message(key: str, locale: str = "en", **kwargs: str | int) -> str:
    lang = MESSAGES.get(locale, MESSAGES[_DEFAULT_LOCALE])
    template = lang.get(key, MESSAGES[_DEFAULT_LOCALE].get(key, key))
    if kwargs:
        try:
            return template.format(**kwargs)
        except KeyError:
            return template
    return template
