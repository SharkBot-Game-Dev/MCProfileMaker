import asyncio
import logging
import os
import re

import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from i18n import LANGUAGES, locale_language, tr
from models.language import UserLanguage

from generate import MinecraftProfileMaker
from models.base import Base
from models.mcid import MCID
from models.profile import Profile
from plugins import favoriteServer, logo

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MCID_RE = re.compile(r"[a-zA-Z0-9_]{3,16}\Z")
BACKGROUNDS = ["sakura.png", "monster_steve.jpeg", "cow.jpg", "creeper.jpg", "lava.jpg", "sord.jpg"]
FONTS = ["gg sans Bold.ttf", "gg sans Medium.ttf", "gg sans Regular.ttf", "gg sans Semibold.ttf", "discordfont.ttf"]

engine = create_async_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_language(interaction: discord.Interaction) -> str:
    async with SessionLocal() as session:
        row = await session.get(UserLanguage, str(interaction.user.id))
        return row.language if row and row.language in LANGUAGES else locale_language(interaction.locale)


def localized(key: str) -> app_commands.locale_str:
    return app_commands.locale_str(tr("en", key), key=key)


class CommandTranslator(app_commands.Translator):
    async def translate(self, string, locale, context):
        key = string.extras.get("key")
        return tr(locale_language(locale), key) if key else None


def status_embed(message: str, *, error: bool = False) -> discord.Embed:
    return discord.Embed(description=message, color=discord.Color.red() if error else discord.Color.green())


async def render_card(interaction: discord.Interaction, mcid: str, background: str, ips: list[str], language: str):
    plugins = [favoriteServer.FavoriteServer(ips, language)] if ips else []
    plugins.append(logo.Logo(language))
    maker = MinecraftProfileMaker(BACKGROUNDS, FONTS, plugins, language=language)
    image = await asyncio.to_thread(maker.generate, mcid, background, "discordfont.ttf", "io")
    try:
        image.seek(0)
        file = discord.File(image, filename="profile.png")
        await interaction.edit_original_response(
            content=None,
            embed=status_embed(tr(language, "generated")),
            attachments=[file],
            view=ProfileView(mcid, language),
        )
    finally:
        image.close()


class ProfileCardEdit(discord.ui.Modal):
    def __init__(self, mcid: str, language: str):
        super().__init__(title=tr(language, "edit"), timeout=180)
        self.mcid = mcid
        self.language = language
        self.background_image = discord.ui.Label(
            text=tr(language, "background"),
            description=tr(language, "background_description"),
            component=discord.ui.Select(options=[
                discord.SelectOption(label=tr(language, bg), value=bg) for bg in BACKGROUNDS
            ], required=True, max_values=1),
        )
        self.favoriteServerIps = discord.ui.Label(
            text=tr(language, "servers"), description=tr(language, "servers_description"),
            component=discord.ui.TextInput(style=discord.TextStyle.long, required=False,
                placeholder=tr(language, "servers_placeholder"), max_length=100),
        )
        self.add_item(self.background_image)
        self.add_item(self.favoriteServerIps)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        try:
            assert isinstance(self.background_image.component, discord.ui.Select)
            assert isinstance(self.favoriteServerIps.component, discord.ui.TextInput)
            background = self.background_image.component.values[0]
            ips = [ip.strip() for ip in self.favoriteServerIps.component.value.splitlines() if ip.strip()]

            async with SessionLocal() as session:
                async with session.begin():
                    profile = await session.scalar(
                        select(Profile).where(
                            Profile.user_id == str(interaction.user.id),
                            Profile.mcid == self.mcid,
                        ).with_for_update()
                    )
                    if profile is None:
                        session.add(Profile(
                            user_id=str(interaction.user.id),
                            mcid=self.mcid,
                            background=background,
                            favoriteServerIps=ips,
                        ))
                    else:
                        profile.background = background
                        profile.favoriteServerIps = ips

            await render_card(interaction, self.mcid, background, ips, self.language)
        except Exception:
            logger.exception("プロフィール編集に失敗しました")
            await interaction.edit_original_response(embed=status_embed(tr(self.language, "save_error"), error=True))


class MCProfileCardBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.none()
        intents.guilds = True
        super().__init__(command_prefix="!", help_command=None, intents=intents)

    async def setup_hook(self):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        self.add_dynamic_items(EditProfileButton)
        await self.tree.set_translator(CommandTranslator())
        await self.tree.sync()

    async def close(self):
        try:
            await super().close()
        finally:
            await engine.dispose()


class EditProfileButton(discord.ui.DynamicItem[discord.ui.Button], template=r"edit_profile\+(?P<mcid>[a-zA-Z0-9_]{3,16})"):
    def __init__(self, mcid: str, language: str = "ja"):
        super().__init__(discord.ui.Button(label=tr(language, "edit"), custom_id=f"edit_profile+{mcid}", emoji="🖊️"))
        self.mcid = mcid

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match: re.Match[str]):
        return cls(match.group("mcid"))

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ProfileCardEdit(self.mcid, await get_language(interaction)))


class ProfileView(discord.ui.View):
    def __init__(self, mcid: str, language: str = "ja"):
        super().__init__(timeout=None)
        self.add_item(EditProfileButton(mcid, language))


bot = MCProfileCardBot()


@bot.event
async def on_ready():
    logger.info("起動しました: %s", bot.user)
    await bot.change_presence(activity=discord.CustomActivity("/build", emoji="⛏️"))


@bot.tree.command(name="mcid", description=localized("cmd_mcid"))
@app_commands.describe(mcid=localized("param_mcid"))
async def mcid_command(interaction: discord.Interaction, mcid: str):
    language = await get_language(interaction)
    if not MCID_RE.fullmatch(mcid):
        await interaction.response.send_message(embed=status_embed(tr(language, "invalid_mcid"), error=True), ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    try:
        async with SessionLocal() as session:
            async with session.begin():
                row = await session.scalar(select(MCID).where(MCID.user_id == str(interaction.user.id)).with_for_update())
                if row is None:
                    session.add(MCID(user_id=str(interaction.user.id), mcid=mcid))
                    message = tr(language, "registered")
                else:
                    row.mcid = mcid
                    message = tr(language, "updated")
        await interaction.edit_original_response(embed=status_embed(message))
    except Exception:
        logger.exception("MCID登録に失敗しました")
        await interaction.edit_original_response(embed=status_embed(tr(language, "register_error"), error=True))


@bot.tree.command(name="build", description=localized("cmd_build"))
@app_commands.describe(mcid=localized("param_mcid"))
async def build(interaction: discord.Interaction, mcid: str | None = None):
    language = await get_language(interaction)
    await interaction.response.defer(thinking=True)
    try:
        async with SessionLocal() as session:
            if mcid is None:
                row = await session.scalar(select(MCID).where(MCID.user_id == str(interaction.user.id)))
                mcid = row.mcid if row is not None else None

            if mcid is None or not MCID_RE.fullmatch(mcid):
                await interaction.edit_original_response(embed=status_embed(tr(language, "missing_mcid"), error=True))
                return

            profile = await session.scalar(select(Profile).where(
                Profile.user_id == str(interaction.user.id), Profile.mcid == mcid
            ))
            background = profile.background if profile and profile.background else BACKGROUNDS[0]
            ips = list(profile.favoriteServerIps or []) if profile else []

        await render_card(interaction, mcid, background, ips, language)
    except Exception:
        logger.exception("カード生成に失敗しました")
        await interaction.edit_original_response(embed=status_embed(tr(language, "generate_error"), error=True))


@bot.tree.command(name="language", description=localized("cmd_language"))
@app_commands.describe(language=localized("param_language"))
@app_commands.choices(language=[
    app_commands.Choice(name=localized("language_ja"), value="ja"),
    app_commands.Choice(name=localized("language_en"), value="en"),
])
async def language_command(interaction: discord.Interaction, language: app_commands.Choice[str]):
    await interaction.response.defer(ephemeral=True)
    selected = language.value
    try:
        async with SessionLocal() as session:
            async with session.begin():
                await session.merge(UserLanguage(user_id=str(interaction.user.id), language=selected))
        await interaction.edit_original_response(embed=status_embed(tr(selected, "language_saved")))
    except Exception:
        logger.exception("Failed to save language")
        await interaction.edit_original_response(embed=status_embed(tr(selected, "language_error"), error=True))


@bot.tree.error
async def on_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    logger.error("Command failed", exc_info=(type(error), error, error.__traceback__))
    language = locale_language(interaction.locale)
    try:
        language = await get_language(interaction)
    except Exception:
        logger.exception("Failed to load language")
    embed = status_embed(tr(language, "command_error"), error=True)
    if interaction.response.is_done():
        await interaction.followup.send(embed=embed, ephemeral=True)
    else:
        await interaction.response.send_message(embed=embed, ephemeral=True)


if __name__ == "__main__":
    bot.run(os.environ["DISCORD_TOKEN"])
