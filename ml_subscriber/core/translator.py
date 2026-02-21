"""Translation module for translating article content."""

import abc
import logging
from typing import Optional

import deepl
from deep_translator import GoogleTranslator as GoogleTranslatorLib
from deep_translator.exceptions import (
    TranslationNotFound,
    RequestError,
    TooManyRequests,
    NotValidPayload,
    LanguageNotSupportedException,
    InvalidSourceOrTargetLanguage,
    ElementNotFoundInGetRequest,
)

logger = logging.getLogger(__name__)


class Translator(abc.ABC):
    """Abstract base class for translators."""

    @abc.abstractmethod
    def translate(self, text: str) -> str:
        """
        Translates text to the target language.

        Args:
            text: The text to translate.

        Returns:
            The translated text.
        """
        raise NotImplementedError


class DeepLTranslator(Translator):
    """Translator using DeepL API."""

    def __init__(self, api_key: str, target_lang: str = "ZH"):
        """
        Initializes the DeepL translator.

        Args:
            api_key: The DeepL API key.
            target_lang: The target language code (default: "ZH" for Chinese).
        """
        self.translator = deepl.Translator(api_key)
        self.target_lang = target_lang

    def translate(self, text: str) -> str:
        """
        Translates text using DeepL API.

        Args:
            text: The text to translate.

        Returns:
            The translated text.
        """
        if not text or not text.strip():
            return text

        try:
            result = self.translator.translate_text(
                text,
                target_lang=self.target_lang
            )
            return result.text
        except deepl.DeepLException as e:
            logger.exception("DeepL translation error: %s", e)
            return text


class GoogleFreeTranslator(Translator):
    """Free translator using Google Translate via deep-translator library."""

    def __init__(self, target_lang: str = "zh-CN"):
        """
        Initializes the Google free translator.

        Args:
            target_lang: The target language code (default: "zh-CN" for Simplified Chinese).
        """
        self.target_lang = target_lang

    def translate(self, text: str) -> str:
        """
        Translates text using Google Translate (free).

        Args:
            text: The text to translate.

        Returns:
            The translated text.
        """
        if not text or not text.strip():
            return text

        try:
            translator = GoogleTranslatorLib(source='auto', target=self.target_lang)
            result = translator.translate(text)
            return result if result else text
        except TranslationNotFound:
            logger.warning(f"Google translation not found for: {text[:50]}...")
            return text
        except (
            RequestError,
            TooManyRequests,
            NotValidPayload,
            LanguageNotSupportedException,
            InvalidSourceOrTargetLanguage,
            ElementNotFoundInGetRequest,
        ) as e:
            logger.exception("Google translation error: %s", e)
            return text


class NoOpTranslator(Translator):
    """A no-op translator that returns the original text."""

    def translate(self, text: str) -> str:
        """Returns the original text without translation."""
        return text


def create_translator(
    deepl_api_key: Optional[str] = None,
    use_free: bool = True,
    target_lang: Optional[str] = None
) -> Translator:
    """
    Factory function to create a translator.

    Priority:
    1. DeepL (if API key provided)
    2. Google Free Translator (if use_free=True)
    3. NoOpTranslator (fallback)

    Args:
        deepl_api_key: The DeepL API key. If provided, uses DeepL.
        use_free: Whether to use free Google translator when no API key. Default True.
        target_lang: The target language code. Defaults vary by translator.

    Returns:
        A Translator instance.
    """
    if deepl_api_key:
        lang = target_lang or "ZH"
        return DeepLTranslator(deepl_api_key, lang)
    
    if use_free:
        lang = target_lang or "zh-CN"
        return GoogleFreeTranslator(lang)
    
    return NoOpTranslator()
