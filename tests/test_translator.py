import unittest
from unittest.mock import patch, MagicMock
from ml_subscriber.core.translator import (
    DeepLTranslator,
    GoogleFreeTranslator,
    NoOpTranslator,
    create_translator
)
from deep_translator.exceptions import RequestError, TranslationNotFound


class TestNoOpTranslator(unittest.TestCase):
    """Tests for NoOpTranslator."""

    def test_translate_returns_original_text(self):
        """Test that NoOpTranslator returns the original text."""
        translator = NoOpTranslator()
        text = "Hello, world!"
        result = translator.translate(text)
        self.assertEqual(result, text)

    def test_translate_empty_string(self):
        """Test that NoOpTranslator handles empty strings."""
        translator = NoOpTranslator()
        result = translator.translate("")
        self.assertEqual(result, "")


class TestDeepLTranslator(unittest.TestCase):
    """Tests for DeepLTranslator."""

    @patch('deepl.Translator')
    def test_translate_success(self, mock_translator_class):
        """Test successful translation."""
        mock_translator = MagicMock()
        mock_result = MagicMock()
        mock_result.text = "你好，世界！"
        mock_translator.translate_text.return_value = mock_result
        mock_translator_class.return_value = mock_translator

        translator = DeepLTranslator("test_api_key")
        result = translator.translate("Hello, world!")

        self.assertEqual(result, "你好，世界！")
        mock_translator.translate_text.assert_called_once_with(
            "Hello, world!",
            target_lang="ZH"
        )

    @patch('deepl.Translator')
    def test_translate_with_custom_target_lang(self, mock_translator_class):
        """Test translation with custom target language."""
        mock_translator = MagicMock()
        mock_result = MagicMock()
        mock_result.text = "Hallo, Welt!"
        mock_translator.translate_text.return_value = mock_result
        mock_translator_class.return_value = mock_translator

        translator = DeepLTranslator("test_api_key", target_lang="DE")
        result = translator.translate("Hello, world!")

        self.assertEqual(result, "Hallo, Welt!")
        mock_translator.translate_text.assert_called_once_with(
            "Hello, world!",
            target_lang="DE"
        )

    @patch('deepl.Translator')
    def test_translate_empty_string(self, mock_translator_class):
        """Test that empty strings are returned without API call."""
        mock_translator = MagicMock()
        mock_translator_class.return_value = mock_translator

        translator = DeepLTranslator("test_api_key")
        result = translator.translate("")

        self.assertEqual(result, "")
        mock_translator.translate_text.assert_not_called()

    @patch('deepl.Translator')
    def test_translate_whitespace_only(self, mock_translator_class):
        """Test that whitespace-only strings are returned without API call."""
        mock_translator = MagicMock()
        mock_translator_class.return_value = mock_translator

        translator = DeepLTranslator("test_api_key")
        result = translator.translate("   ")

        self.assertEqual(result, "   ")
        mock_translator.translate_text.assert_not_called()

    @patch('deepl.Translator')
    @patch('deepl.DeepLException', Exception)
    def test_translate_error_returns_original(self, mock_translator_class):
        """Test that translation errors return the original text."""
        import deepl
        mock_translator = MagicMock()
        mock_translator.translate_text.side_effect = deepl.DeepLException("API Error")
        mock_translator_class.return_value = mock_translator

        translator = DeepLTranslator("test_api_key")
        result = translator.translate("Hello, world!")

        self.assertEqual(result, "Hello, world!")


class TestGoogleFreeTranslator(unittest.TestCase):
    """Tests for GoogleFreeTranslator."""

    @patch('ml_subscriber.core.translator.GoogleTranslatorLib')
    def test_translate_success(self, mock_translator_class):
        """Test successful translation."""
        mock_translator = MagicMock()
        mock_translator.translate.return_value = "你好，世界！"
        mock_translator_class.return_value = mock_translator

        translator = GoogleFreeTranslator()
        result = translator.translate("Hello, world!")

        self.assertEqual(result, "你好，世界！")
        mock_translator_class.assert_called_once_with(source='auto', target='zh-CN')

    @patch('ml_subscriber.core.translator.GoogleTranslatorLib')
    def test_translate_with_custom_target_lang(self, mock_translator_class):
        """Test translation with custom target language."""
        mock_translator = MagicMock()
        mock_translator.translate.return_value = "Hallo, Welt!"
        mock_translator_class.return_value = mock_translator

        translator = GoogleFreeTranslator(target_lang="de")
        result = translator.translate("Hello, world!")

        self.assertEqual(result, "Hallo, Welt!")
        mock_translator_class.assert_called_once_with(source='auto', target='de')

    def test_translate_empty_string(self):
        """Test that empty strings are returned without API call."""
        translator = GoogleFreeTranslator()
        result = translator.translate("")
        self.assertEqual(result, "")

    def test_translate_whitespace_only(self):
        """Test that whitespace-only strings are returned without API call."""
        translator = GoogleFreeTranslator()
        result = translator.translate("   ")
        self.assertEqual(result, "   ")

    @patch('ml_subscriber.core.translator.GoogleTranslatorLib')
    def test_translate_error_returns_original(self, mock_translator_class):
        """Test that translation errors return the original text."""
        mock_translator = MagicMock()
        mock_translator.translate.side_effect = RequestError("Network error")
        mock_translator_class.return_value = mock_translator

        translator = GoogleFreeTranslator()
        result = translator.translate("Hello, world!")

        self.assertEqual(result, "Hello, world!")

    @patch('ml_subscriber.core.translator.GoogleTranslatorLib')
    @patch('ml_subscriber.core.translator.logger')
    def test_translate_translation_not_found(self, mock_logger, mock_translator_class):
        """Test that TranslationNotFound is logged as a warning and original text returned."""
        mock_translator = MagicMock()
        mock_translator.translate.side_effect = TranslationNotFound("Not found")
        mock_translator_class.return_value = mock_translator

        translator = GoogleFreeTranslator()
        result = translator.translate("Hello, world!")

        self.assertEqual(result, "Hello, world!")
        mock_logger.warning.assert_called_once()


class TestCreateTranslator(unittest.TestCase):
    """Tests for create_translator factory function."""

    def test_create_translator_with_use_free_false(self):
        """Test that NoOpTranslator is returned when use_free is False."""
        translator = create_translator(use_free=False)
        self.assertIsInstance(translator, NoOpTranslator)

    def test_create_translator_default_uses_free(self):
        """Test that GoogleFreeTranslator is returned by default (no API key)."""
        translator = create_translator()
        self.assertIsInstance(translator, GoogleFreeTranslator)

    def test_create_translator_with_use_free_true(self):
        """Test that GoogleFreeTranslator is returned when use_free=True."""
        translator = create_translator(use_free=True)
        self.assertIsInstance(translator, GoogleFreeTranslator)

    @patch('deepl.Translator')
    def test_create_translator_with_api_key(self, mock_translator_class):
        """Test that DeepLTranslator is returned when API key is provided."""
        translator = create_translator(deepl_api_key="test_api_key")
        self.assertIsInstance(translator, DeepLTranslator)

    @patch('deepl.Translator')
    def test_create_translator_with_custom_target_lang_deepl(self, mock_translator_class):
        """Test that custom target language is passed to DeepLTranslator."""
        translator = create_translator(deepl_api_key="test_api_key", target_lang="DE")
        self.assertIsInstance(translator, DeepLTranslator)
        self.assertEqual(translator.target_lang, "DE")

    def test_create_translator_with_custom_target_lang_google(self):
        """Test that custom target language is passed to GoogleFreeTranslator."""
        translator = create_translator(use_free=True, target_lang="ja")
        self.assertIsInstance(translator, GoogleFreeTranslator)
        self.assertEqual(translator.target_lang, "ja")


if __name__ == '__main__':
    unittest.main()
