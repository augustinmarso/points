"""Fond d'écran memento mori : un point par jour d'une vie de MM_YEARS ans, en blocs de 10 ans,
sur fond noir (ou, en option, sur un tableau : vanité ou Passion du Christ, domaine public).
Point sombre = jour vécu, point corail = aujourd'hui, point clair = jour restant ; seul texte : % de vie vécue.
PC   : python mm.py out --set [--toggle] → out/desktop.jpg ; fond noir, ou tableau changé toutes
       les 30 min si le fichier avec-tableau existe (--toggle l'inverse).
Site : python mm.py site --all → {desktop,phone}.jpg (noir), {desktop,phone}-<k>.jpg (carrousel), carousel.json.
Date de naissance : variable MM_BIRTH (GitHub) ou fichier naissance.txt (PC, non versionné)."""
import ctypes, hashlib, json, math, os, shutil, sys, time, urllib.error, urllib.parse, urllib.request
from datetime import date, datetime
from PIL import Image, ImageDraw, ImageEnhance, ImageFont, ImageOps

TODAY, BG = (242, 148, 111), (11, 11, 12)
# nom → (largeur, hauteur, part max de la largeur et de la hauteur pour la grille,
#        blocs de 10 ans en colonnes × lignes, part du haut laissée libre : horloge du téléphone)
FORMATS = {"desktop": (3840, 2160, .6, .55, (2, 4), 0), "phone": (1290, 2796, .8, .55, (1, 8), .28)}
VANITES = [  # Wikimedia Commons, domaine public, ≥ 2500 px
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
PASSION = [
    "The Body of the Dead Christ in the Tomb (Holbein der Jüngere) Basel.jpg",
    "The Dead Christ and Three Mourners by Andrea Mantegna. Pinacoteca di Brera in Milan.jpg",
    "F8099 Louvre Ph de Champaigne christ mort INV1128 rwk.jpg",
    "Le Transport du Christ vers le tombeau - Titien - Musée du Louvre Peintures INV 749 ; MR 516.jpg",
    "The Crowning with Thorns-Caravaggio (1602).jpg",
    "The Entombment of Christ-Caravaggio (c.1602-3).jpg",
    "The Flagellation of Christ-Caravaggio (1607).jpg",
    "El Descendimiento, by Rogier van der Weyden, from Prado in Google Earth.jpg",
    "Kruisdraging, Hieronymus Bosch, ca. 1510, Koninklijk Museum voor Schone Kunsten Gent, 1902-H.jpg",
    "Peter Paul Rubens - Raising of the Cross - 1610.jpg",
    "Antonello da Messina, Ecce Homo, 1473.jpg",
    "Isenheimer Altar (Colmar) jm01221 (retouched).jpg",
]
# vanité et Passion en alternance
PAINTINGS = [p for pair in zip(VANITES, PASSION) for p in pair] + VANITES[len(PASSION):]


def now():
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Europe/Paris"))
    except Exception:  # Windows sans tzdata : l'horloge locale est déjà à Paris
        return datetime.now()


def counts(birth, years, today):
    """→ (années, semaine en cours depuis la naissance à 52 semaines/an, % de jours vécus)."""
    total = (birth.replace(year=birth.year + years) - birth).days
    pct = 100 * min(max((today - birth).days, 0), total) / total
    y = 0  # anniversaires passés
    while y < years and birth.replace(year=birth.year + y + 1) <= today:
        y += 1
    if y == years:
        return years, years * 52, pct
    wk = min(max((today - birth.replace(year=birth.year + y)).days // 7, 0), 51)  # 52 sem. + 1 ou 2 jours
    return years, y * 52 + wk, pct


def painting(k, cache, download=True):
    name = PAINTINGS[k % len(PAINTINGS)]
    path = os.path.join(cache, hashlib.md5(name.encode()).hexdigest()[:12] + ".jpg")
    if not os.path.exists(path):
        if not download:
            raise FileNotFoundError(name)
        os.makedirs(cache, exist_ok=True)
        url = "https://commons.wikimedia.org/wiki/Special:FilePath/" + urllib.parse.quote(name) + "?width=3840"
        req = urllib.request.Request(url, headers={"User-Agent": "mm-wallpaper/1.0 (personal wallpaper)"})
        for attempt in range(5):  # Wikimedia limite le débit (429) : on patiente ; ensuite tout reste en cache
            try:
                data = urllib.request.urlopen(req, timeout=120).read()
                break
            except urllib.error.HTTPError as e:
                if e.code != 429 or attempt == 4:
                    raise
                time.sleep(60 * (attempt + 1))
        with open(path + ".part", "wb") as f:
            f.write(data)
        os.replace(path + ".part", path)
        time.sleep(5)
    return Image.open(path).convert("RGB")


def render(w, h, fw, fh, grid, top, life, art, ss=2):
    """life = (années, semaine en cours comptée depuis la naissance, % vécu) ; une ligne = une année de 52 semaines."""
    W, H = w * ss, h * ss
    years, now_wk, pct = life
    # les points ne sont pas posés dessus : ils éclaircissent (restants) ou assombrissent (vécus) le fond lui-même
    if art:
        z = 1.2  # zoom : le tableau déborde de l'écran, ce qui coupe aussi les bords sombres du scan
        src = ImageOps.fit(art, (round(W * z), round(H * z)), Image.LANCZOS)
        src = src.crop(((src.width - W) // 2, (src.height - H) // 2, (src.width - W) // 2 + W, (src.height - H) // 2 + H))
        base, light, dark = (ImageEnhance.Brightness(src).enhance(k) for k in (.55, 1.45, .12))
    else:
        base, light, dark = (Image.new("RGB", (W, H), c) for c in (BG, (120, 119, 116), (48, 48, 52)))
    m_left, m_lived = Image.new("L", (W, H)), Image.new("L", (W, H))
    d_left, d_lived = ImageDraw.Draw(m_left), ImageDraw.Draw(m_lived)
    gc, gr = grid  # blocs de 10 ans (10 lignes × 52 semaines), en colonnes × lignes
    g = 2  # espace entre dizaines, en points (repris dans layout.json → page web)
    s = min(W * fw / (gc * 52 + (gc - 1) * g), H * fh / (gr * 10 + (gr - 1) * g))
    gap, blk_w, blk_h = g * s, 52 * s, 10 * s
    tot_w, tot_h = gc * blk_w + (gc - 1) * gap, gr * blk_h + (gr - 1) * gap
    ox, oy = (W - tot_w) / 2, H * top + (H * (1 - top) - tot_h) / 2  # centré sous la zone réservée
    r = s * .32

    def center(i):
        y, wk = divmod(i, 52)
        j = y // 10  # dizaine
        bx, by = ox + (j % gc) * (blk_w + gap), oy + (j // gc) * (blk_h + gap)
        return bx + (wk + .5) * s, by + (y % 10 + .5) * s

    for i in range(years * 52):
        cx, cy = center(i)
        (d_lived if i < now_wk else d_left).ellipse((cx - r, cy - r, cx + r, cy + r), fill=255)
    img = Image.composite(light, base, m_left.point(lambda v: v * .9))
    img = Image.composite(dark, img, m_lived.point(lambda v: v * .9))
    d = ImageDraw.Draw(img)
    if now_wk < years * 52:
        cx, cy = center(now_wk)
        d.ellipse((cx - r * 1.5, cy - r * 1.5, cx + r * 1.5, cy + r * 1.5), fill=TODAY)
    # seul texte : la part de vie déjà vécue, sans légende
    font = ImageFont.truetype(os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", "ScoutieSans-Regular.ttf"),
                              round(min(W, H) * .016))
    d.text((W / 2, oy + tot_h + gap * 3), f"{pct:.2f}".replace(".", ",") + " %", font=font, fill=(235, 230, 220), anchor="mt")
    return img.resize((w, h), Image.LANCZOS)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, sys.argv[1])
    cache = os.path.join(here, "cache")
    flag = os.path.join(here, "avec-tableau")  # absent = fond noir (par défaut)
    if "--toggle" in sys.argv:  # raccourci « Tableau oui-non » du PC
        os.remove(flag) if os.path.exists(flag) else open(flag, "w").close()
    raw = os.environ.get("MM_BIRTH") or open(os.path.join(here, "naissance.txt"), encoding="utf-8-sig").read()
    t = now()
    life = counts(date.fromisoformat(raw.strip()), int(os.environ.get("MM_YEARS", 80)), t.date())
    assert counts(date(2000, 1, 1), 80, date(2000, 1, 15))[1] == 2
    assert counts(date(2000, 1, 1), 80, date(2001, 1, 1))[1] == 52
    assert counts(date(2000, 1, 1), 80, date(2000, 12, 31))[1] == 51
    assert counts(date(2000, 1, 1), 1, date(2030, 1, 1))[1:] == (52, 100)
    os.makedirs(out, exist_ok=True)
    n = len(PAINTINGS)

    if "--all" in sys.argv:
        for fmt, (w, h, fw, fh, grid, top) in FORMATS.items():  # fond noir = image par défaut
            path = os.path.join(out, f"{fmt}.jpg")
            render(w, h, fw, fh, grid, top, life, None).save(path, quality=90)
            shutil.copy(path, os.path.join(out, f"{fmt}-plain.jpg"))  # ancienne adresse, gardée
        ids = []
        for k in range(n):
            try:
                art = painting(k, cache, download=False)  # seulement les tableaux versionnés dans cache/
            except Exception as e:  # un tableau absent ne bloque pas le reste du site
                print(f"tableau {k} ignoré : {e}", file=sys.stderr)
                continue
            for fmt, (w, h, fw, fh, grid, top) in FORMATS.items():
                render(w, h, fw, fh, grid, top, life, art).save(os.path.join(out, f"{fmt}-{k}.jpg"), quality=88)
            ids.append(k)
        with open(os.path.join(out, "carousel.json"), "w") as f:
            json.dump({"ids": ids}, f)
        with open(os.path.join(out, "layout.json"), "w") as f:  # la page retrouve quel point est survolé
            json.dump({"years": life[0], "gap": 2, **{fmt: dict(zip(("W", "H", "fw", "fh", "grid", "top"), v))
                                                     for fmt, v in FORMATS.items()}}, f)
        return

    w, h, fw, fh, grid, top = FORMATS["desktop"]
    plain = not os.path.exists(flag)
    k = t.toordinal() * 48 + t.hour * 2 + t.minute // 30  # nouveau tableau toutes les 30 min
    art = None if plain else painting(k, cache)
    pc = os.path.join(out, "desktop.jpg")
    render(w, h, fw, fh, grid, top, life, art).save(pc + ".tmp.jpg", quality=92)
    os.replace(pc + ".tmp.jpg", pc)
    if "--set" in sys.argv:  # SPI_SETDESKWALLPAPER, écrit dans le profil + notifie
        ctypes.windll.user32.SystemParametersInfoW(20, 0, pc, 3)


if __name__ == "__main__":
    main()
