from typing import List
from i18n import tr
from PIL import Image, ImageDraw, ImageFont

class Logo:
    def __init__(self, language: str = "ja"):
        self.image: Image
        self.imageDraw: ImageDraw
        self.fontMain: ImageFont
        self.fontSub: ImageFont
        self.language = language

    def execute(self):
        self.imageDraw = ImageDraw.Draw(self.image)

        if self.language == "ja":
            self.imageDraw.text((520, 450), tr(self.language, "logo_text"), "#8ffff0", self.fontMain)
        elif self.language == "en":
            self.imageDraw.text((510, 450), tr(self.language, "logo_text"), "#8ffff0", self.fontMain)