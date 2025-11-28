"""Translation module for translating article content."""

import abc
from typing import Optional

import deepl


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
            print(f"DeepL translation error: {e}")
            return text


class NoOpTranslator(Translator):
    """A no-op translator that returns the original text."""

    def translate(self, text: str) -> str:
        """Returns the original text without translation."""
        return text


def create_translator(api_key: Optional[str] = None, target_lang: str = "ZH") -> Translator:
    """
    Factory function to create a translator.

    Args:
        api_key: The DeepL API key. If None, returns a NoOpTranslator.
        target_lang: The target language code.

    Returns:
        A Translator instance.
    """
    if api_key:
        return DeepLTranslator(api_key, target_lang)
    return NoOpTranslator()
