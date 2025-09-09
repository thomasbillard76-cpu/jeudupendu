# app.py
from flask import Flask, render_template, request, redirect, url_for, session
import random
import unicodedata
import os

app = Flask(__name__)
app.secret_key = "change_this_for_production"  # pour le dev c'est ok, change en prod

DICTIONARY_FILE = os.path.join(os.path.dirname(__file__), "dictionnaire.txt")
MAX_LIVES = 5

# Normalisation d'un caractère (garde la longueur 1 sauf pour quelques ligatures)
def normalize_char_charwise(c: str) -> str:
    c = c.lower()
    # ligatures spéciales traitées explicitement (on renvoie "oe" ou "ae" si présentes)
    ligatures = {"œ": "oe", "æ": "ae"}
    if c in ligatures:
        return ligatures[c]
    nk = unicodedata.normalize("NFD", c)
    # on retire les marques diacritiques (accents)
    return "".join(ch for ch in nk if unicodedata.category(ch) != "Mn")

def choose_word():
    with open(DICTIONARY_FILE, "r", encoding="utf-8") as f:
        words = [line.strip() for line in f if line.strip()]
    return random.choice(words) if words else "test"

@app.route("/")
def index():
    return "Hello fonctionne!"

@app.route("/start", methods=["POST"])
def start():
    # récupération du nom
    player = request.form.get("player", "").strip() or "Joueur"
    word = choose_word()  # mot original (avec accents)
    # préparation des structures de jeu
    revealed = []
    norm_chars = []
    for ch in word:
        # si ce n'est pas une lettre (espace, -, ' etc) on l'affiche tout de suite
        if ch.isalpha():
            revealed.append("_")
        else:
            revealed.append(ch)
        norm_chars.append(normalize_char_charwise(ch))
    session["player"] = player
    session["word"] = word
    session["revealed"] = revealed
    session["norm_chars"] = norm_chars
    session["lives"] = MAX_LIVES
    session["guessed"] = []  # liste des normalisations déjà jouées (ex: 'e', 'a', ...)
    session["status"] = "playing"  # playing / won / lost
    return redirect(url_for("game"))

@app.route("/game")
def game():
    if "word" not in session:
        return redirect(url_for("index"))
    # alphabet A-Z
    alphabet = [chr(i) for i in range(ord("A"), ord("Z") + 1)]
    # map letter -> normalized version (pour savoir si bouton est déjà désactivé)
    alphabet_norm = {letter.lower(): normalize_char_charwise(letter.lower()) for letter in alphabet}
    # hangman stage index (0 = 0 erreurs, ... up to MAX_LIVES)
    wrong = MAX_LIVES - session.get("lives", MAX_LIVES)
    return render_template(
        "game.html",
        player=session.get("player"),
        revealed=session.get("revealed"),
        lives=session.get("lives"),
        guessed=session.get("guessed"),
        status=session.get("status"),
        alphabet=alphabet,
        alphabet_norm=alphabet_norm,
        wrong=wrong,
    )

@app.route("/guess", methods=["POST"])
def guess():
    if "word" not in session or session.get("status") != "playing":
        return redirect(url_for("game"))
    letter = request.form.get("letter", "").strip().lower()
    if not letter or len(letter) != 1 or not letter.isalpha():
        return redirect(url_for("game"))
    guessed = session.get("guessed", [])
    letter_norm = normalize_char_charwise(letter)
    if letter_norm in guessed:
        return redirect(url_for("game"))  # déjà joué
    guessed.append(letter_norm)
    session["guessed"] = guessed

    # recherche dans chaque position : si la normalisation du caractère contient la
    # normalisation du 'guess' => on dévoile le caractère original
    found = False
    revealed = session.get("revealed")
    norm_chars = session.get("norm_chars")
    word = session.get("word")
    for i, norm in enumerate(norm_chars):
        # norm peut être 'e', 'oe', 'ae', ...
        if letter_norm in norm:
            revealed[i] = word[i]
            found = True

    if not found:
        session["lives"] = session.get("lives", MAX_LIVES) - 1

    # mise à jour du statut
    if "_" not in revealed:
        session["status"] = "won"
    elif session.get("lives", 0) <= 0:
        session["status"] = "lost"

    session["revealed"] = revealed
    return redirect(url_for("game"))

@app.route("/restart", methods=["POST"])
def restart():
    # on efface uniquement les clés liées à la partie pour garder éventuellement le nom
    for k in ["word", "revealed", "norm_chars", "lives", "guessed", "status"]:
        session.pop(k, None)
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
