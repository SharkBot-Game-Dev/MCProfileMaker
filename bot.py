import discord
from discord.ext import commands
import dotenv
import os

import asyncio

from generate import MinecraftProfileMaker
from plugins import favoriteServer

dotenv.load_dotenv()

intents = discord.Intents.none()
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

@bot.event
async def setup_hook():
    # await bot.tree.sync()
    # print("スラッシュコマンドを同期しました。")
    print("起動中..")

@bot.event
async def on_ready():
    print("起動しました。")
    await bot.change_presence(activity=discord.CustomActivity("/build", emoji="⛏️"))

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
        await interaction.response.defer(ephemeral=True)

        try:

            msg = await interaction.message.reply("生成中..")

            assert isinstance(self.background_image.component, discord.ui.Select)
            assert isinstance(self.favoriteServerIps.component, discord.ui.TextInput)

            plugins = []
            favoriteServerIpsValue = self.favoriteServerIps.component.value
            if favoriteServerIpsValue:
                plugins.append(favoriteServer.FavoriteServer(favoriteServerIpsValue.split("\n")))

            profileMaker = MinecraftProfileMaker(
                ["sakura.png", "monster_steve.jpeg", "cow.jpg"],
                ["gg sans Bold.ttf", "gg sans Medium.ttf", "gg sans Regular.ttf", "gg sans Semibold.ttf", "discordfont.ttf"],
                plugins
            )

            image = await asyncio.to_thread(profileMaker.generate, self.mcid, self.background_image.component.values[0], "discordfont.ttf", "io")

            file = discord.File(image, filename="profile.png")

            await interaction.message.edit(attachments=[file])
            await msg.delete()

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

@bot.tree.command(name="build", description="プロフィールカードを生成します。")
async def build(interaction: discord.Interaction, mcid: str):
    await interaction.response.defer()

    try:

        profileMaker = MinecraftProfileMaker(
            ["sakura.png", "monster_steve.jpeg", "cow.jpg"],
            ["gg sans Bold.ttf", "gg sans Medium.ttf", "gg sans Regular.ttf", "gg sans Semibold.ttf", "discordfont.ttf"],
            []
        )

        image = await asyncio.to_thread(profileMaker.generate, mcid, "sakura.png", "discordfont.ttf", "io")

        file = discord.File(image, filename="profile.png")

        view = discord.ui.View(timeout=None)
        view.add_item(discord.ui.Button(label="編集する", custom_id=f"edit_profile+{mcid}", emoji="🖊️"))

        await interaction.followup.send(file=file, view=view, content="生成しました！")

        image.close()
    except:
        return

bot.run(os.environ.get('DISCORD_TOKEN'))