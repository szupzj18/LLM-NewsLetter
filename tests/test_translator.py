import unittest
from unittest.mock import patch, MagicMock
from ml_subscriber.core.translator import (
    DeepLTranslator,
    NoOpTranslator,
    create_translator
)


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


class TestCreateTranslator(unittest.TestCase):
    """Tests for create_translator factory function."""

    def test_create_translator_without_api_key(self):
        """Test that NoOpTranslator is returned when no API key is provided."""
        translator = create_translator()
        self.assertIsInstance(translator, NoOpTranslator)

    def test_create_translator_with_none_api_key(self):
        """Test that NoOpTranslator is returned when API key is None."""
        translator = create_translator(None)
        self.assertIsInstance(translator, NoOpTranslator)

    @patch('deepl.Translator')
    def test_create_translator_with_api_key(self, mock_translator_class):
        """Test that DeepLTranslator is returned when API key is provided."""
        translator = create_translator("test_api_key")
        self.assertIsInstance(translator, DeepLTranslator)

    @patch('deepl.Translator')
    def test_create_translator_with_custom_target_lang(self, mock_translator_class):
        """Test that custom target language is passed to DeepLTranslator."""
        translator = create_translator("test_api_key", target_lang="DE")
        self.assertIsInstance(translator, DeepLTranslator)
        self.assertEqual(translator.target_lang, "DE")


if __name__ == '__main__':
    unittest.main()
