import io
from typing import List, Literal

from PIL import Image, ImageDraw, ImageFont

import requests

class BackgroundNotfound(Exception):
    def __init__(self, *args):
        super().__init__(*args)

class FontNotfound(Exception):
    def __init__(self, *args):
        super().__init__(*args)

SaveType = Literal["file", "io"]

class MinecraftProfileMaker:
    def __init__(self, backgrounds: List[str], fonts: List[str]):
        self.backgrounds = backgrounds
        self.fonts = fonts

        self.W = 800
        self.H = 500

    def generate(self, username: str, background: str, font: str, save_type: SaveType = "file"):
        if background not in self.backgrounds:
            raise BackgroundNotfound("その背景画像はありません。")

        if font not in self.fonts:
            raise FontNotfound("そのフォントはありません。")

        try:
            font_main = ImageFont.truetype(f"fonts/{font}", 24)
            font_sub = ImageFont.truetype(f"fonts/{font}", 16)
        except Exception:
            font_main = ImageFont.load_default()
            font_sub = ImageFont.load_default()

        playerRes = requests.get('https://api.mojang.com/users/profiles/minecraft/' + username).json()
        playerSkin = requests.get('https://mc-heads.net/body/' + playerRes["id"] + "/200")

        playerSkinIo = io.BytesIO(playerSkin.content)

        playerSkinImage = Image.open(playerSkinIo)

        image = Image.open("background/" + background)

        image = image.resize((self.W, self.H))

        image.paste(playerSkinImage, (10, 10), playerSkinImage)

        overlay = Image.new("RGBA", (self.W, self.H), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)

        overlay_draw.rounded_rectangle(
            (220, 15, self.W - 20, self.H - 15),
            radius=20,
            fill=(0, 0, 0, 160),
        )

        image = Image.alpha_composite(image, overlay)

        draw = ImageDraw.Draw(image)
        draw.text((230, 25), username, "#ffffff", font_main)
        draw.text((230, 55), playerRes["id"], "#ffffff", font_sub)

        if save_type == "file":
            image.save("profile.png")
        else:
            io_profile = io.BytesIO()
            image.save(io_profile, "png")
            io_profile.seek(0)
            return io_profile

if __name__ == "__main__":
    gen = MinecraftProfileMaker(["sakura.png"], ["gg sans Bold.ttf", "gg sans Medium.ttf", "gg sans Regular.ttf", "gg sans Semibold.ttf"])
    gen.generate("modoggu123", "sakura.png", "gg sans Medium.ttf", "file")