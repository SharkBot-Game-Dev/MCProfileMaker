from generate import MinecraftProfileMaker

from plugins import favoriteServer, logo

gen = MinecraftProfileMaker(
    ["sakura.png", "monster_steve.jpeg", "cow.jpg"],
    ["gg sans Bold.ttf", "gg sans Medium.ttf", "gg sans Regular.ttf", "gg sans Semibold.ttf", "discordfont.ttf"],
    [favoriteServer.FavoriteServer(["mc.hypixel.net", "play.donutsmp.net", "example.com"]), logo.Logo("en")]
)
gen.generate("modoggu123", "cow.jpg", "discordfont.ttf", "file")