import asyncio
import logging
import os
import re

import discord
from discord.ext import commands
from dotenv import load_dotenv
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from generate import MinecraftProfileMaker
from models.base import Base
from models.mcid import MCID
from models.profile import Profile
from plugins import favoriteServer

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MCID_RE = re.compile(r"[a-zA-Z0-9_]{3,16}\Z")
BACKGROUNDS = ["sakura.png", "monster_steve.jpeg", "cow.jpg"]
FONTS = ["gg sans Bold.ttf", "gg sans Medium.ttf", "gg sans Regular.ttf", "gg sans Semibold.ttf", "discordfont.ttf"]

engine = create_async_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


def status_embed(message: str, *, error: bool = False) -> discord.Embed:
    return discord.Embed(description=message, color=discord.Color.red() if error else discord.Color.green())


async def render_card(interaction: discord.Interaction, mcid: str, background: str, ips: list[str]):
    plugins = [favoriteServer.FavoriteServer(ips)] if ips else []
    maker = MinecraftProfileMaker(BACKGROUNDS, FONTS, plugins)
    image = await asyncio.to_thread(maker.generate, mcid, background, "discordfont.ttf", "io")
    try:
        image.seek(0)
        file = discord.File(image, filename="profile.png")
        await interaction.edit_original_response(
            content=None,
            embed=status_embed("生成しました！"),
            attachments=[file],
            view=ProfileView(mcid),
        )
    finally:
        image.close()


class ProfileCardEdit(discord.ui.Modal):
    background_image = discord.ui.Label(
        text="背景画像を選択",
        description="背景画像を選択してください。",
        component=discord.ui.Select(
            options=[
                discord.SelectOption(label="桜の画像", value="sakura.png"),
                discord.SelectOption(label="モンスターの画像", value="monster_steve.jpeg"),
                discord.SelectOption(label="牛の画像", value="cow.jpg"),
            ],
            required=True,
            max_values=1,
        ),
    )
    favoriteServerIps = discord.ui.Label(
        text="お気に入りのサーバーのIP",
        description="改行で区切って入力してください。",
        component=discord.ui.TextInput(
            style=discord.TextStyle.long,
            required=False,
            placeholder="空の場合は指定しない。\n改行で区切れます。",
            max_length=100,
        ),
    )

    def __init__(self, mcid: str):
        super().__init__(title="編集する", timeout=180)
        self.mcid = mcid

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

            await render_card(interaction, self.mcid, background, ips)
        except Exception:
            logger.exception("プロフィール編集に失敗しました")
            await interaction.edit_original_response(embed=status_embed("保存または画像生成に失敗しました。ログを確認してください。", error=True))


class MCProfileCardBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.none()
        intents.guilds = True
        super().__init__(command_prefix="!", help_command=None, intents=intents)

    async def setup_hook(self):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
            
        self.add_dynamic_items(EditProfileButton)
        await self.tree.sync()

    async def close(self):
        try:
            await super().close()
        finally:
            await engine.dispose()


class EditProfileButton(discord.ui.DynamicItem[discord.ui.Button], template=r"edit_profile\+(?P<mcid>[a-zA-Z0-9_]{3,16})"):
    def __init__(self, mcid: str):
        super().__init__(discord.ui.Button(label="編集する", custom_id=f"edit_profile+{mcid}", emoji="🖊️"))
        self.mcid = mcid

    @classmethod
    async def from_custom_id(cls, interaction: discord.Interaction, item: discord.ui.Button, match: re.Match[str]):
        return cls(match.group("mcid"))

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(ProfileCardEdit(self.mcid))


class ProfileView(discord.ui.View):
    def __init__(self, mcid: str):
        super().__init__(timeout=None)
        self.add_item(EditProfileButton(mcid))


bot = MCProfileCardBot()


@bot.event
async def on_ready():
    logger.info("起動しました: %s", bot.user)
    await bot.change_presence(activity=discord.CustomActivity("/build", emoji="⛏️"))


@bot.tree.command(name="mcid", description="デフォルトのMCIDを登録します。")
async def mcid_command(interaction: discord.Interaction, mcid: str):
    if not MCID_RE.fullmatch(mcid):
        await interaction.response.send_message(embed=status_embed("正しいMCIDを入力してください。", error=True), ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    try:
        async with SessionLocal() as session:
            async with session.begin():
                row = await session.scalar(select(MCID).where(MCID.user_id == str(interaction.user.id)).with_for_update())
                if row is None:
                    session.add(MCID(user_id=str(interaction.user.id), mcid=mcid))
                    message = "登録しました！"
                else:
                    row.mcid = mcid
                    message = "登録を更新しました！"
        await interaction.edit_original_response(embed=status_embed(message))
    except Exception:
        logger.exception("MCID登録に失敗しました")
        await interaction.edit_original_response(embed=status_embed("登録に失敗しました。", error=True))


@bot.tree.command(name="build", description="プロフィールカードを生成します。")
async def build(interaction: discord.Interaction, mcid: str | None = None):
    await interaction.response.defer(thinking=True)
    try:
        async with SessionLocal() as session:
            if mcid is None:
                row = await session.scalar(select(MCID).where(MCID.user_id == str(interaction.user.id)))
                mcid = row.mcid if row is not None else None

            if mcid is None or not MCID_RE.fullmatch(mcid):
                await interaction.edit_original_response(embed=status_embed("正しいMCIDを指定するか、/mcid で登録してください。", error=True))
                return

            profile = await session.scalar(select(Profile).where(
                Profile.user_id == str(interaction.user.id), Profile.mcid == mcid
            ))
            background = profile.background if profile and profile.background else BACKGROUNDS[0]
            ips = list(profile.favoriteServerIps or []) if profile else []

        await render_card(interaction, mcid, background, ips)
    except Exception:
        logger.exception("カード生成に失敗しました")
        await interaction.edit_original_response(embed=status_embed("画像生成に失敗しました。ログを確認してください。", error=True))


if __name__ == "__main__":
    bot.run(os.environ["DISCORD_TOKEN"])
