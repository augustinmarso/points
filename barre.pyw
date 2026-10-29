"""Compte à rebours du temps restant (vie de MM_YEARS ans), posé dans la barre des tâches Windows.
Petite fenêtre sans cadre ni bouton dans la barre, fond transparent, toujours au premier plan, collée
à gauche de la zone de notification (horloge Windows), sur deux lignes comme elle. Clic droit : fermer.
Date de naissance : naissance.txt."""
import ctypes, os, sys, tkinter as tk
from ctypes import wintypes
from datetime import date, datetime

YEARS = int(os.environ.get("MM_YEARS", 80))
KEY = "#010101"  # couleur rendue transparente

ctypes.windll.kernel32.CreateMutexW(None, False, "memento-mori-barre")
if ctypes.windll.kernel32.GetLastError() == 183:  # déjà lancé
    sys.exit()
ctypes.windll.shcore.SetProcessDpiAwareness(2)  # coordonnées en vrais pixels


def add_years(d, n):
    try:
        return d.replace(year=d.year + n)
    except ValueError:  # 29 février
        return d.replace(year=d.year + n, day=28)


def remaining(now, end):
    y = 0
    while add_years(now, y + 1) <= end:
        y += 1
    rest = end.astimezone() - add_years(now, y).astimezone()  # durée réelle : tient compte de l'heure d'été
    s = rest.seconds
    return f"{y} a {rest.days:03d} j\n{s // 3600:02d}:{s // 60 % 60:02d}:{s % 60:02d}.{rest.microseconds // 1000:03d}"


here = os.path.dirname(os.path.abspath(__file__))
b = date.fromisoformat(open(os.path.join(here, "naissance.txt"), encoding="utf-8-sig").read().strip())
end = add_years(datetime(b.year, b.month, b.day), YEARS)
assert remaining(datetime(2000, 1, 1), datetime(2001, 1, 2, 3, 4, 5)) == "1 a 001 j\n03:04:05.000"

work = wintypes.RECT()
ctypes.windll.user32.SystemParametersInfoW(0x30, 0, ctypes.byref(work), 0)  # SPI_GETWORKAREA
screen_h = ctypes.windll.user32.GetSystemMetrics(1)
bar_top, bar_h = work.bottom, (screen_h - work.bottom) or 48  # barre masquée : hauteur par défaut

root = tk.Tk()
root.withdraw()  # sans cadre posé avant affichage, Tk sous Windows démarre parfois réduit
root.configure(bg=KEY)
label = tk.Label(root, bg=KEY, fg="#ebe6dc", font=("Scoutie Sans", 9), padx=6, justify="right", text=remaining(datetime.now(), end))
label.pack()
label.bind("<Button-3>", lambda e: root.destroy())
root.update_idletasks()
root.overrideredirect(True)
root.attributes("-toolwindow", True)  # pas de bouton dans la barre ; via Tk car il recrée sa fenêtre et perdrait un style posé à la main


def place():  # bord droit collé à la zone de notification, dont la largeur varie avec les icônes
    tray = wintypes.RECT()
    u = ctypes.windll.user32
    u.GetWindowRect(u.FindWindowExW(u.FindWindowW("Shell_TrayWnd", None), None, "TrayNotifyWnd", None), ctypes.byref(tray))
    right = tray.left or u.GetSystemMetrics(0) - 270  # explorer en cours de redémarrage
    root.geometry(f"+{right - root.winfo_reqwidth()}+{bar_top + (bar_h - root.winfo_reqheight()) // 2}")


place()
root.attributes("-transparentcolor", KEY)
root.attributes("-topmost", True)
root.deiconify()


def tick():
    label.config(text=remaining(datetime.now(), end))
    root.after(50, tick)


def stay_on_top():  # la barre des tâches repasse devant quand on clique dessus
    if root.state() == "iconic":  # « Afficher le bureau » (Win+D) la réduit
        root.deiconify()
    place()
    root.attributes("-topmost", True)
    root.lift()
    root.after(1000, stay_on_top)


tick()
root.after(100, stay_on_top)
root.mainloop()
