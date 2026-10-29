"""Envoie dans Anki chaque citation affichée sur le fond d'écran (nouvelle à 0 h, 8 h et 16 h).
Recto : la citation. Verso : le philosophe, le thème, la source. Via AnkiConnect ; Anki fermé = on
réessaie au passage suivant (tâche planifiée « Fond points », toutes les 30 min). Jamais de doublon."""
import json, os, sys, urllib.request
from datetime import date, datetime

HERE = os.path.dirname(os.path.abspath(__file__))
DECK = "Philosophie & spiritualité::Memento mori"
STATE = os.path.join(HERE, "citations-anki.json")  # dernier créneau envoyé (local, non versionné)
RATTRAPAGE = 9  # créneaux manqués repris au plus (3 jours)


def creneau(now):
    """Même calcul que la page : jour local depuis 1970 × 3 + tiers de journée."""
    return (now.date() - date(1970, 1, 1)).days * 3 + now.hour // 8


def anki(action, **params):
    req = urllib.request.Request("http://127.0.0.1:8765", json.dumps({"action": action, "version": 6, "params": params}).encode())
    r = json.load(urllib.request.urlopen(req, timeout=5))
    if r.get("error"):
        raise RuntimeError(r["error"])
    return r["result"]


def main():
    assert creneau(datetime(1970, 1, 2, 9)) == 4
    data = json.load(open(os.path.join(HERE, "citations.json"), encoding="utf-8"))
    cites, debut = data["liste"], data["debut"]  # la 1re citation s'affiche au créneau `debut`
    now = creneau(datetime.now())
    try:
        last = json.load(open(STATE))["dernier"]
    except (OSError, ValueError, KeyError):
        last = now - 1
    todo = range(max(last + 1, now - RATTRAPAGE + 1), now + 1)
    if not todo:
        return
    try:
        models = anki("modelNames")
    except OSError:
        return  # Anki fermé
    model = next((m for m in ("Basique", "Basic") if m in models), models[0])
    recto, verso = anki("modelFieldNames", modelName=model)[:2]
    anki("createDeck", deck=DECK)
    for c in todo:
        q = cites[(c - debut) % len(cites)]
        try:
            anki("addNote", note={"deckName": DECK, "modelName": model, "tags": ["memento-mori", "citation"],
                                  "fields": {recto: f"« {q['c']} »", verso: f"<b>{q['a']}</b><br>{q['t']}<br><small>{q['s']}</small>"},
                                  "options": {"allowDuplicate": False, "duplicateScope": "deck"}})
        except RuntimeError as e:
            if "duplicate" not in str(e).lower():  # déjà dans Anki : rien à faire
                print(e, file=sys.stderr)
                return
        with open(STATE, "w") as f:
            json.dump({"dernier": c}, f)


if __name__ == "__main__":
    main()
