from typing import List
from i18n import tr
from PIL import Image, ImageDraw, ImageFont

class FavoriteServer:
    def __init__(self, server_ips: List[str], language: str = "ja"):
        self.image: Image
        self.imageDraw: ImageDraw
        self.fontMain: ImageFont
        self.fontSub: ImageFont
        self.server_ips = server_ips
        self.language = language

        self.serverIcons = {
            "mc.hypixel.net": "images/hypixel.jpg",
            "donutsmp.net": "images/donutsmp.jpg",
            "play.donutsmp.net": "images/donutsmp.jpg",
        }

    def execute(self):
        self.imageDraw = ImageDraw.Draw(self.image)

        self.imageDraw.text((230, 85), tr(self.language, "favorite_servers"), "#ffffff", self.fontMain)

        H = 90
        for ips in self.server_ips:
            H += 30

            serverIcon = self.serverIcons.get(ips)
            if serverIcon:
                serverIconImage = Image.open(serverIcon)

                serverIconImage = serverIconImage.resize((26, 26))

                self.image.paste(serverIconImage, (230, H + 10))

                self.imageDraw.text((255, H), ips, "#ffffff", self.fontMain)
            else:
                self.imageDraw.text((230, H), ips, "#ffffff", self.fontMain)