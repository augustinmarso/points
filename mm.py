"""Fond d'écran : une vanité (tableau du domaine public, une différente chaque jour) tramée
sur toute la page d'un point par jour d'une vie de MM_YEARS ans. Aucun texte, aucun chiffre.
Point sombre = jour vécu, point corail = aujourd'hui, point clair = jour restant.
Écrit desktop/phone.jpg (avec tableau) et desktop/phone-plain.jpg (sans).
Usage : python mm.py <dossier_sortie> [--set] [--toggle]
Date de naissance : variable MM_BIRTH (GitHub) ou fichier naissance.txt (PC, non versionné).
--set applique le fond Windows ; sans tableau si le fichier sans-tableau existe ; --toggle l'inverse."""
import ctypes, math, os, sys, urllib.parse, urllib.request
from datetime import date, datetime
from PIL import Image, ImageDraw, ImageEnhance, ImageOps

TODAY, BG = (242, 148, 111, 255), (11, 11, 12)
FORMATS = {"desktop": (3840, 2160), "phone": (1290, 2796)}
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


def render(w, h, total, lived, art, ss=2):
    W, H = w * ss, h * ss
    # les points ne sont pas posés dessus : ils éclaircissent (restants) ou assombrissent (vécus) le fond lui-même
    if art:
        src = ImageOps.fit(art, (W, H), Image.LANCZOS)
        base, light, dark = (ImageEnhance.Brightness(src).enhance(k) for k in (.6, 1.1, .3))
    else:
        base, light, dark = (Image.new("RGB", (W, H), c) for c in (BG, (46, 46, 48), (20, 20, 22)))
    m_left, m_lived = Image.new("L", (W, H)), Image.new("L", (W, H))
    d_left, d_lived = ImageDraw.Draw(m_left), ImageDraw.Draw(m_lived)
    cols = math.ceil(math.sqrt(total * W / H))  # grille sur toute la page
    rows = math.ceil(total / cols)
    sx, sy = W / cols, H / rows
    r = min(sx, sy) * .32
    for i in range(total):
        cx, cy = (i % cols + .5) * sx, (i // cols + .5) * sy
        (d_lived if i < lived else d_left).ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
    img = Image.composite(light, base, m_left.point(lambda v: v * .55))
    img = Image.composite(dark, img, m_lived.point(lambda v: v * .6))
    cx, cy, rr = (lived % cols + .5) * sx, (lived // cols + .5) * sy, r * 1.6
    ImageDraw.Draw(img).ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=TODAY[:3])
    return img.resize((w, h), Image.LANCZOS)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, sys.argv[1])
    flag = os.path.join(here, "sans-tableau")
    if "--toggle" in sys.argv:  # raccourci « Tableau oui-non » du PC
        os.remove(flag) if os.path.exists(flag) else open(flag, "w").close()
    raw = os.environ.get("MM_BIRTH") or open(os.path.join(here, "naissance.txt"), encoding="utf-8-sig").read()
    birth = date.fromisoformat(raw.strip())
    total, lived = counts(birth, int(os.environ.get("MM_YEARS", 80)), today())
    assert counts(date(2000, 1, 1), 1, date(2000, 1, 11)) == (366, 10)
    art = painting(lived, os.path.join(here, "cache"))
    os.makedirs(out, exist_ok=True)
    for name, (w, h) in FORMATS.items():
        render(w, h, total, lived, art).save(os.path.join(out, f"{name}.jpg"), quality=92)
        render(w, h, total, lived, None).save(os.path.join(out, f"{name}-plain.jpg"), quality=92)
    if "--set" in sys.argv:  # SPI_SETDESKWALLPAPER, écrit dans le profil + notifie
        pc = "desktop-plain.jpg" if os.path.exists(flag) else "desktop.jpg"
        ctypes.windll.user32.SystemParametersInfoW(20, 0, os.path.join(out, pc), 3)


if __name__ == "__main__":
    main()
