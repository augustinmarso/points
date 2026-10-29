"""Fond d'écran : une vanité (tableau du domaine public, une différente chaque jour) voilée
d'un point par jour d'une vie de MM_YEARS ans. Aucun texte, aucun chiffre.
Pas de point = jour vécu, point corail = aujourd'hui, point clair = jour restant.
Usage : MM_BIRTH=AAAA-MM-JJ python mm.py <dossier_sortie> [--set]"""
import ctypes, math, os, sys, urllib.parse, urllib.request
from datetime import date, datetime
from PIL import Image, ImageDraw, ImageEnhance, ImageOps

LEFT, TODAY = (235, 230, 220, 90), (242, 148, 111, 255)
# nom → (largeur, hauteur, zone des points x0,y0,x1,y1) ; téléphone : haut libre pour l'horloge
FORMATS = {"desktop": (3840, 2160, (.06, .1, .94, .9)), "phone": (1290, 2796, (.08, .3, .92, .9))}
PAINTINGS = [  # Wikimedia Commons, domaine public, ≥ 3000 px
    "Pieter Claesz, Still Life with a Skull and a Writing Quill.jpg",
    "Harmen Steenwijck - Vanitas Still-Life - WGA21768.jpg",
    "Adriaen van Utrecht - Vanitas Still-Life with a Bouquet, a Skull and Precious Objects.jpg",
    "Edwaert Collier - Vanitas - Still Life with Books and Manuscripts and a Skull - Google Art Project.jpg",
    "Cornelis Norbertus Gijsbrechts - Vanitas still life with a skull, sheet music, violin, globe, candle, hourglass and playing cards, all on a draped table.jpg",
    "Joris van Son - A vanitas still-life with a skull, a pistol, a lute with broken strings, a flute.jpg",
    "Guercino - A vanitas still life with a skull atop a book, an hourglass and two glass vases of flowers.jpg",
    "Franciscus Gijsbrechts - Vanitas still life with a skull, silver-gilt tableware and musical instruments on a marble table.jpg",
    "Hendrick Andriessen - Vanitas still life with a skull, a broken Roemer.jpg",
    "Pseudo-Roestraten - Vanitas still life.jpg",
    "Carstian Luyckx - Vanitas Still Life with Musical Instruments, Sheet Music, Books, a Skeleton, Skulls and Armour.jpg",
    "Vanitas Still Life MET DP146494.jpg",
    "Pieter Claesz and workshop - Vanitas 6002511.jpg",
    "Carstian Luyckx - Vanitas still life with a skull, a lira da braccia and bow, a deck of cards, dice, a musical manuscript and other objects on a partially draped table.jpg",
]


def today():
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Europe/Paris")).date()
    except Exception:  # Windows sans tzdata : l'horloge locale est déjà à Paris
        return date.today()


def counts(birth, years, now):
    end = birth.replace(year=birth.year + years)
    total = (end - birth).days
    lived = min(max((now - birth).days, 0), total)
    return total, lived


def painting(n, cache):
    name = PAINTINGS[n % len(PAINTINGS)]
    path = os.path.join(cache, f"{n % len(PAINTINGS):02d}.jpg")
    if not os.path.exists(path):
        os.makedirs(cache, exist_ok=True)
        url = "https://commons.wikimedia.org/wiki/Special:FilePath/" + urllib.parse.quote(name) + "?width=3840"
        req = urllib.request.Request(url, headers={"User-Agent": "mm-wallpaper/1.0 (personal wallpaper)"})
        data = urllib.request.urlopen(req, timeout=60).read()
        with open(path + ".part", "wb") as f:
            f.write(data)
        os.replace(path + ".part", path)
    return Image.open(path).convert("RGB")


def render(w, h, box, total, lived, art, ss=2):
    W, H = w * ss, h * ss
    img = ImageEnhance.Brightness(ImageOps.fit(art, (W, H), Image.LANCZOS)).enhance(.62).convert("RGBA")
    veil = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(veil)
    x0, y0, x1, y1 = box[0] * W, box[1] * H, box[2] * W, box[3] * H
    bw, bh = x1 - x0, y1 - y0
    cols = math.ceil(math.sqrt(total * bw / bh))
    rows = math.ceil(total / cols)
    s = min(bw / cols, bh / rows)
    ox, oy = x0 + (bw - cols * s) / 2, y0 + (bh - rows * s) / 2
    r = s * .3
    for i in range(lived, total):
        cx, cy = ox + (i % cols + .5) * s, oy + (i // cols + .5) * s
        rr = r * 1.8 if i == lived else r
        d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=TODAY if i == lived else LEFT)
    return Image.alpha_composite(img, veil).convert("RGB").resize((w, h), Image.LANCZOS)


def main():
    out = sys.argv[1]
    birth = date.fromisoformat(os.environ["MM_BIRTH"])
    total, lived = counts(birth, int(os.environ.get("MM_YEARS", 80)), today())
    assert counts(date(2000, 1, 1), 1, date(2000, 1, 11)) == (366, 10)
    art = painting(lived, os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache"))
    os.makedirs(out, exist_ok=True)
    for name, (w, h, box) in FORMATS.items():
        render(w, h, box, total, lived, art).save(os.path.join(out, f"{name}.jpg"), quality=92)
    if "--set" in sys.argv:  # SPI_SETDESKWALLPAPER, écrit dans le profil + notifie
        ctypes.windll.user32.SystemParametersInfoW(20, 0, os.path.abspath(os.path.join(out, "desktop.jpg")), 3)


if __name__ == "__main__":
    main()
