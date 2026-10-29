"""Une photo Google Photos par semaine vécue, en noir et blanc et volontairement dégradée.
Source : export Google Takeout (Google Photos), en .zip ou décompressé. Tout reste en local :
les vignettes vont dans le fond d'écran Lively, jamais dans le dépôt public.
Usage : python photos.py <dossier de l'export Takeout>"""
import io, json, os, re, sys, zipfile
from datetime import date, datetime, timezone
from PIL import Image, ImageFilter, ImageOps, ImageStat

LIVELY = os.path.join(os.environ["LOCALAPPDATA"], "Lively Wallpaper", "Library", "wallpapers", "points-mm")
EXT = (".jpg", ".jpeg", ".png", ".heic", ".webp")
SKIP = re.compile(r"screenshot|capture|screen_?record|scan|whatsapp image|img-\d{8}-wa", re.I)  # pas des souvenirs
SIDE = 220  # px du plus grand côté de la vignette
QUALITY = 22  # JPEG volontairement très compressé

try:  # photos d'iPhone
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass


def sources(root):
    """→ (nom, lecteur d'octets) pour chaque fichier, dans les .zip comme dans les dossiers."""
    for dirpath, _, files in os.walk(root):
        for f in files:
            p = os.path.join(dirpath, f)
            if f.lower().endswith(".zip"):
                z = zipfile.ZipFile(p)
                for n in z.namelist():
                    if not n.endswith("/"):
                        yield n, (lambda z=z, n=n: z.read(n))
            else:
                yield p, (lambda p=p: open(p, "rb").read())


def add_years(d, n):
    try:
        return d.replace(year=d.year + n)
    except ValueError:  # 29 février
        return d.replace(year=d.year + n, day=28)


def week_of(birth, d):
    """Même découpage que mm.counts : 52 semaines par an depuis l'anniversaire."""
    y = 0
    while add_years(birth, y + 1) <= d:
        y += 1
    return y * 52 + min((d - add_years(birth, y)).days // 7, 51)


def taken(img, meta):
    exif = img.getexif().get_ifd(0x8769).get(36867) or img.getexif().get(306)  # DateTimeOriginal, DateTime
    if exif:
        try:
            return datetime.strptime(exif[:19], "%Y:%m:%d %H:%M:%S").date()
        except ValueError:
            pass
    if meta:  # fiche .json de Takeout
        ts = int(meta.get("photoTakenTime", {}).get("timestamp", 0))
        if ts:
            return datetime.fromtimestamp(ts, timezone.utc).date()
    return None


def score(img):
    """Plus haut = meilleur souvenir : appareil photo, net, bien exposé, assez grand."""
    g = ImageOps.grayscale(img)
    g.thumbnail((256, 256))
    mean = ImageStat.Stat(g).mean[0]
    if mean < 25 or mean > 235:  # noir ou blanc
        return None
    sharp = ImageStat.Stat(g.filter(ImageFilter.FIND_EDGES)).var[0]
    camera = 1.5 if img.getexif().get(271) else 1  # marque de l'appareil
    exposure = 1 - abs(mean - 128) / 128
    return sharp * camera * (.5 + exposure) * min(img.width * img.height / 2e6, 1)


def degrade(img):
    g = ImageOps.grayscale(ImageOps.exif_transpose(img))
    g.thumbnail((SIDE, SIDE), Image.LANCZOS)
    small = g.resize((max(g.width // 2, 1), max(g.height // 2, 1)), Image.BILINEAR)  # perte de détail
    return ImageOps.autocontrast(small.resize(g.size, Image.BILINEAR), cutoff=1)


def main():
    root = sys.argv[1]
    birth = date.fromisoformat(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "naissance.txt"),
                                    encoding="utf-8-sig").read().strip())
    today = date.today()
    assert week_of(date(2000, 1, 1), date(2000, 1, 15)) == 2 and week_of(date(2000, 1, 1), date(2000, 12, 31)) == 51

    entries = list(sources(root))
    metas = {}  # titre d'origine → fiche .json
    for name, read in entries:
        if name.lower().endswith(".json"):
            try:
                m = json.loads(read())
                if "title" in m:
                    metas[os.path.basename(m["title"])] = m
            except (ValueError, UnicodeDecodeError):
                pass

    best = {}  # semaine → (score, nom, lecteur)
    seen = 0
    for name, read in entries:
        base = os.path.basename(name)
        if not base.lower().endswith(EXT) or SKIP.search(base):
            continue
        try:
            img = Image.open(io.BytesIO(read()))
            img.draft("RGB", (512, 512))  # décodage JPEG rapide en petit
            d = taken(img, metas.get(base))
            if not d or not birth <= d <= today:
                continue
            s = score(img.convert("RGB"))
        except Exception as e:
            print(f"ignorée : {base} ({e})", file=sys.stderr)
            continue
        seen += 1
        wk = week_of(birth, d)
        if s is not None and s > best.get(wk, (-1,))[0]:
            best[wk] = (s, name, read)

    out = os.path.join(LIVELY, "photos")
    os.makedirs(out, exist_ok=True)
    for f in os.listdir(out):
        os.remove(os.path.join(out, f))
    for wk, (_, name, read) in best.items():
        degrade(Image.open(io.BytesIO(read()))).save(os.path.join(out, f"{wk}.jpg"), quality=QUALITY)
    with open(os.path.join(LIVELY, "photos.js"), "w", encoding="utf-8") as f:
        f.write(f"window.MM_PHOTOS = {json.dumps(sorted(best))};\n")
    print(f"{seen} photos datées lues, {len(best)} semaines illustrées sur {week_of(birth, today) + 1} vécues")


if __name__ == "__main__":
    main()
