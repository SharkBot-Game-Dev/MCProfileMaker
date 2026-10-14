import re

import discord
from discord.ext import commands, tasks
import dotenv
import os

import asyncio

from generate import MinecraftProfileMaker
from plugins import favoriteServer

import json

dotenv.load_dotenv()

intents = discord.Intents.none()
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

PROFILE_SETTING = {}

@bot.event
async def setup_hook():
    # await bot.tree.sync()
    # print("スラッシュコマンドを同期しました。")
    print("起動中..")

    try:
        with open("save.json", mode="r") as f:
            global PROFILE_SETTING
            PROFILE_SETTING = json.load(f)
    except:
        PROFILE_SETTING = {}
        pass

@tasks.loop(minutes=5)
async def save_loop():
    with open("save.json", mode="w") as f:
        json.dump(PROFILE_SETTING, f)

@bot.event
async def on_ready():
    print("起動しました。")
    await bot.change_presence(activity=discord.CustomActivity("/build", emoji="⛏️"))

    save_loop.start()

class ProfileCardEdit(discord.ui.Modal):
    def __init__(self, mcid: str):
        super().__init__(title="編集する", timeout=180)

        self.mcid = mcid

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
        description="お気に入りのサーバーのIPを入力してください。",
        component=discord.ui.TextInput(
            style=discord.TextStyle.long,
            required=False,
            placeholder="空の場合は指定しない。\n改行で区切れます。",
            max_length=100,
        ),
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message(embed=discord.Embed(description="<a:loading:1559738064098689217> 生成しています...", color=discord.Color.blue()))

        try:
            assert isinstance(self.background_image.component, discord.ui.Select)
            assert isinstance(self.favoriteServerIps.component, discord.ui.TextInput)

            PROFILE_SETTING[self.mcid + f"_{interaction.user.id}"] = {}

            plugins = []
            favoriteServerIpsValue = self.favoriteServerIps.component.value
            if favoriteServerIpsValue:
                plugins.append(favoriteServer.FavoriteServer(favoriteServerIpsValue.split("\n")))

                PROFILE_SETTING[self.mcid + f"_{interaction.user.id}"]["favoriteServerIps"] = favoriteServerIpsValue.split("\n")

            profileMaker = MinecraftProfileMaker(
                ["sakura.png", "monster_steve.jpeg", "cow.jpg"],
                ["gg sans Bold.ttf", "gg sans Medium.ttf", "gg sans Regular.ttf", "gg sans Semibold.ttf", "discordfont.ttf"],
                plugins
            )

            image = await asyncio.to_thread(profileMaker.generate, self.mcid, self.background_image.component.values[0], "discordfont.ttf", "io")

            PROFILE_SETTING[self.mcid + f"_{interaction.user.id}"]["background"] = self.background_image.component.values[0]

            file = discord.File(image, filename="profile.png")

            view = discord.ui.View(timeout=None)
            view.add_item(discord.ui.Button(label="編集する", custom_id=f"edit_profile+{self.mcid}", emoji="🖊️"))

            await interaction.edit_original_response(attachments=[file], view=view, embed=discord.Embed(description="<:check:1559738484716212374> 生成しました！", color=discord.Color.green()))

            image.close()
        except:
            return

@bot.event
async def on_interaction(interaction: discord.Interaction):
    try:
        if interaction.data["component_type"] == 2:
            try:
                custom_id = interaction.data["custom_id"]
            except:
                return
            if custom_id.startswith("edit_profile+"):
                mcid = custom_id.split("+")[1]
                await interaction.response.send_modal(ProfileCardEdit(mcid))
    except:
        return

MCID_RE = re.compile(r"^[a-zA-Z0-9_]{3,16}$")

@bot.tree.command(name="build", description="プロフィールカードを生成します。")
async def build(interaction: discord.Interaction, mcid: str):
    await interaction.response.send_message(embed=discord.Embed(description="<a:loading:1559738064098689217> 生成しています...", color=discord.Color.blue()))

    if not MCID_RE.search(mcid):
        await interaction.edit_original_response(embed=discord.Embed(title="不正なMCIDです。", description=f"正しいMCIDを入力してください。", color=discord.Color.red()))
        return

    try:
        profileSetting = PROFILE_SETTING.get(f"{mcid}_{interaction.user.id}")

        plugins = []
        background = "sakura.png"
        if profileSetting:
            favoriteServerIps = profileSetting.get('favoriteServerIps')
            if favoriteServerIps:
                plugins.append(favoriteServer.FavoriteServer(favoriteServerIps))

            background = profileSetting.get('background', 'sakura.png')

        profileMaker = MinecraftProfileMaker(
            ["sakura.png", "monster_steve.jpeg", "cow.jpg"],
            ["gg sans Bold.ttf", "gg sans Medium.ttf", "gg sans Regular.ttf", "gg sans Semibold.ttf", "discordfont.ttf"],
            plugins
        )

        image = await asyncio.to_thread(profileMaker.generate, mcid, background, "discordfont.ttf", "io")

        file = discord.File(image, filename="profile.png")

        view = discord.ui.View(timeout=None)
        view.add_item(discord.ui.Button(label="編集する", custom_id=f"edit_profile+{mcid}", emoji="🖊️"))

        await interaction.edit_original_response(attachments=[file], view=view, embed=discord.Embed(description="<:check:1559738484716212374> 生成しました！", color=discord.Color.green()))

        image.close()
    except Exception as e:
        await interaction.edit_original_response(embed=discord.Embed(title="エラーが発生しました。", description=f"```{e}```", color=discord.Color.red()))
        return

bot.run(os.environ.get('DISCORD_TOKEN'))