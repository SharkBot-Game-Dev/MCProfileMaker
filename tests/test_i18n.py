"""Offline regression checks; Discord, database, and skin APIs are mocked."""
import io
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from PIL import Image, ImageDraw

# Import without loading credentials or requiring a running PostgreSQL server.
with patch.dict(os.environ, {"DATABASE_URL": "postgresql+asyncpg://test:test@localhost/test"}), \
     patch("sqlalchemy.ext.asyncio.create_async_engine", return_value=AsyncMock()):
    import bot

from generate import MinecraftProfileMaker
from i18n import TEXTS, tr
from plugins.favoriteServer import FavoriteServer


class LocalizationTests(unittest.IsolatedAsyncioTestCase):
    async def test_commands_and_editor(self):
        self.assertEqual(TEXTS['ja'].keys(), TEXTS['en'].keys())
        translator = bot.CommandTranslator()
        for command in bot.bot.tree.get_commands():
            payload = await command.get_translated_payload(bot.bot.tree, translator)
            for locale, language in [('ja', 'ja'), ('en-US', 'en')]:
                self.assertEqual(payload['description_localizations'][locale], tr(language, 'cmd_' + command.name))
                self.assertTrue(payload['options'][0]['description_localizations'][locale])
        for language in ('ja', 'en'):
            modal = bot.ProfileCardEdit('TestUser', language)
            self.assertEqual(modal.title, tr(language, 'edit'))
            self.assertEqual(modal.background_image.component.options[0].label, tr(language, bot.BACKGROUNDS[0]))
            self.assertEqual(len(modal.to_components()), 2)
            view = bot.ProfileView('TestUser', language)
            self.assertEqual(view.children[0].item.label, tr(language, 'edit'))

    async def test_language_preference_and_save(self):
        for language in ('ja', 'en'):
            session = AsyncMock()
            session.get.return_value = SimpleNamespace(language=language)
            context = AsyncMock()
            context.__aenter__.return_value = session
            interaction = SimpleNamespace(user=SimpleNamespace(id=123), locale=bot.discord.Locale.japanese,
                                          response=AsyncMock(), edit_original_response=AsyncMock())
            with patch.object(bot, 'SessionLocal', return_value=context):
                self.assertEqual(await bot.get_language(interaction), language)
            session.get.return_value = None
            interaction.locale = bot.discord.Locale.american_english
            with patch.object(bot, 'SessionLocal', return_value=context):
                self.assertEqual(await bot.get_language(interaction), 'en')
            session.begin = lambda: AsyncMock()
            with patch.object(bot, 'SessionLocal', return_value=context):
                await bot.language_command.callback(interaction, bot.app_commands.Choice(name=language, value=language))
            saved = session.merge.call_args.args[0]
            self.assertEqual((saved.user_id, saved.language), ('123', language))
            self.assertEqual(interaction.edit_original_response.call_args.kwargs['embed'].description, tr(language, 'language_saved'))

    async def test_image_labels(self):
        skin = io.BytesIO()
        Image.new('RGBA', (100, 200), (60, 150, 60, 255)).save(skin, 'PNG')
        for language in ('ja', 'en'):
            plugin = FavoriteServer(['example.org'], language)
            maker = MinecraftProfileMaker(bot.BACKGROUNDS, bot.FONTS, [plugin], language=language)
            player = SimpleNamespace(json=lambda: {'id': 'a' * 32})
            skin_response = SimpleNamespace(content=skin.getvalue())
            draw_text = ImageDraw.ImageDraw.text
            labels = []

            def record(draw, xy, text, *args, **kwargs):
                labels.append(text)
                return draw_text(draw, xy, text, *args, **kwargs)

            with patch('generate.requests.get', side_effect=[player, skin_response]), \
                 patch.object(ImageDraw.ImageDraw, 'text', record):
                output = maker.generate('TestUser', bot.BACKGROUNDS[0], 'discordfont.ttf', 'io')
            self.assertIn(tr(language, 'favorite_servers'), labels)
            with Image.open(output) as image:
                self.assertEqual(image.size, (800, 500))
            output.close()


if __name__ == '__main__':
    unittest.main()
