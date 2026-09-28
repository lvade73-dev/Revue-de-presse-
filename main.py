# -*- coding: utf-8 -*-
"""
Revue de presse quotidienne multi-sources.

Pipeline : flux RSS -> filtrage 24h -> résumé par LLM -> fichier Markdown daté.

Usage :
    python main.py              # génère le brief du jour
    python main.py --dry-run    # collecte seulement, sans appel LLM (test des flux)
"""

import argparse
import os
import smtplib
import sys
import time
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path
from zoneinfo import ZoneInfo

import feedparser
import requests

from sources import SOURCES, MAX_PAR_FLUX, FENETRE_HEURES

# --------------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------------

TZ = ZoneInfo("Europe/Paris")
DOSSIER_SORTIE = Path("briefs")

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-3.6-flash:generateContent"
)

PROMPT = """Tu es rédacteur en chef d'une revue de presse internationale quotidienne.

Voici les dépêches collectées ce matin sur des flux RSS d'agences et de médias \
du monde entier. Elles sont brutes, redondantes et inégales.

Ta mission : produire une revue de presse en français, dense et factuelle.

RÈGLES
1. Sélectionne les 12 à 15 sujets les plus importants, en équilibrant les zones \
géographiques. Ignore le people, le sport, la météo et les contenus promotionnels.
2. Dédoublonne : si plusieurs sources couvrent le même événement, fais-en un seul \
item et cite la source la plus complète.
3. Écris en français, y compris pour les dépêches en anglais.
4. Chaque item : un titre court en gras, puis 2 phrases factuelles maximum, puis \
le lien source entre parenthèses.
5. Reste neutre. Pas de commentaire éditorial, pas de superlatifs.
6. Si une information est présentée comme non confirmée dans la source, dis-le.

FORMAT DE SORTIE (Markdown strict, rien d'autre)

## À retenir

- 5 lignes maximum, une phrase chacune, les faits marquants du jour.

## Europe

- **Titre de l'item** — Deux phrases factuelles. ([Nom source](url))

## Afrique

(même structure)

## Amériques

(même structure)

## Moyen-Orient

(même structure)

## Asie

(même structure)

Si une zone n'a aucune actualité notable, écris "Rien de notable." sous son titre.

DÉPÊCHES COLLECTÉES :

{depeches}
"""


# --------------------------------------------------------------------------
# 1. Collecte
# --------------------------------------------------------------------------

def _date_entree(entry):
    """Retourne la date de publication d'une entrée RSS, ou None."""
    for champ in ("published_parsed", "updated_parsed"):
        valeur = entry.get(champ)
        if valeur:
            return datetime.fromtimestamp(time.mktime(valeur), tz=timezone.utc)
    return None


def _nettoyer(texte, longueur=300):
    """Supprime le HTML basique et tronque."""
    if not texte:
        return ""
    import re
    texte = re.sub(r"<[^>]+>", " ", texte)
    texte = re.sub(r"\s+", " ", texte).strip()
    return texte[:longueur]


def collecter():
    """Parcourt tous les flux et retourne un dict {zone: [articles]}."""
    limite = datetime.now(timezone.utc) - timedelta(hours=FENETRE_HEURES)
    resultat = {}

    for zone, flux in SOURCES.items():
        articles = []
        for nom, url in flux:
            try:
                parsed = feedparser.parse(url, agent="Mozilla/5.0 (revue-presse)")
            except Exception as exc:
                print(f"  [!] {nom} : erreur réseau ({exc})", file=sys.stderr)
                continue

            if parsed.bozo and not parsed.entries:
                print(f"  [!] {nom} : flux illisible", file=sys.stderr)
                continue

            gardees = 0
            for entry in parsed.entries:
                if gardees >= MAX_PAR_FLUX:
                    break
                date = _date_entree(entry)
                if date and date < limite:
                    continue
                titre = _nettoyer(entry.get("title", ""), 200)
                if not titre:
                    continue
                articles.append({
                    "source": nom,
                    "titre": titre,
                    "resume": _nettoyer(entry.get("summary", "")),
                    "lien": entry.get("link", ""),
                })
                gardees += 1

            print(f"  {nom:32s} {gardees:3d} articles")

        resultat[zone] = articles

    return resultat


def formater_depeches(collecte):
    """Met la collecte en forme texte pour le prompt."""
    blocs = []
    for zone, articles in collecte.items():
        if not articles:
            continue
        blocs.append(f"\n===== ZONE : {zone} =====")
        for a in articles:
            blocs.append(
                f"[{a['source']}] {a['titre']}\n{a['resume']}\nURL: {a['lien']}"
            )
    return "\n\n".join(blocs)


# --------------------------------------------------------------------------
# 2. Résumé par LLM
# --------------------------------------------------------------------------
def resumer(depeches):
    """Appelle l'API Gemini, avec réessais et modèle de secours."""
    cle = os.environ.get("GEMINI_API_KEY")
    if not cle:
        raise SystemExit("Variable d'environnement GEMINI_API_KEY absente.")

    payload = {
        "contents": [{"parts": [{"text": PROMPT.format(depeches=depeches)}]}],
        "generationConfig": {"temperature": 0.3, "maxOutputTokens": 16000},
    }

    base = "https://generativelanguage.googleapis.com/v1beta/models/"
    modeles = ["gemini-3.8-flash", "gemini-3.6-flash"]
    attentes = [10, 30, 60]
    
    for modele in modeles:
        for essai, pause in enumerate(attentes, start=1):
            reponse = requests.post(
                base + modele + ":generateContent",
                headers={"x-goog-api-key": cle, "Content-Type": "application/json"},
                json=payload,
                timeout=120,
            )

            if reponse.status_code == 200:
                candidat = reponse.json()["candidates"][0]
                print(f"OK via {modele} (essai {essai})", flush=True)
                return candidat["content"]["parts"][0]["text"].strip()

            print(f"{modele} essai {essai} : HTTP {reponse.status_code}", flush=True)

            # 503/429 = surcharge passagère, on réessaie. Autre code = inutile d'insister.
            if reponse.status_code not in (429, 500, 502, 503, 504):
                print(reponse.text[:800], flush=True)
                break

            if essai < len(attentes):
                time.sleep(pause)

        print(f"Bascule vers le modèle suivant.", flush=True)

    raise SystemExit("Tous les modèles ont échoué.")


# --------------------------------------------------------------------------
# 3. Écriture et envoi
# --------------------------------------------------------------------------

def ecrire(markdown, collecte):
    """Écrit le fichier daté et met à jour dernier.md."""
    maintenant = datetime.now(TZ)
    total = sum(len(v) for v in collecte.values())

    entete = (
        f"# Revue de presse — {maintenant.strftime('%d/%m/%Y')}\n\n"
        f"*Généré le {maintenant.strftime('%d/%m/%Y à %H:%M')} "
        f"à partir de {total} dépêches.*\n\n---\n\n"
    )
    contenu = entete + markdown + "\n"

    DOSSIER_SORTIE.mkdir(exist_ok=True)
    chemin = DOSSIER_SORTIE / f"{maintenant.strftime('%Y-%m-%d')}.md"
    chemin.write_text(contenu, encoding="utf-8")

    # Raccourci toujours à jour, pratique en favori sur le téléphone
    Path("dernier.md").write_text(contenu, encoding="utf-8")

    print(f"\n[OK] Écrit : {chemin}")
    return chemin, contenu


def envoyer_mail(contenu):
    """Envoie le brief par mail si les variables SMTP sont définies."""
    exp = os.environ.get("MAIL_EXPEDITEUR")
    mdp = os.environ.get("MAIL_MOT_DE_PASSE")
    dest = os.environ.get("MAIL_DESTINATAIRE")

    if not all([exp, mdp, dest]):
        print("[i] Envoi mail désactivé (variables SMTP absentes).")
        return

    msg = EmailMessage()
    msg["Subject"] = f"Revue de presse — {datetime.now(TZ).strftime('%d/%m/%Y')}"
    msg["From"] = exp
    msg["To"] = dest
    msg.set_content(contenu)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as serveur:
            serveur.login(exp, mdp)
            serveur.send_message(msg)
        print(f"[OK] Mail envoyé à {dest}")
    except Exception as exc:
        print(f"[!] Échec de l'envoi mail : {exc}", file=sys.stderr)


# --------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Teste les flux sans appeler le LLM")
    args = parser.parse_args()

    print("Collecte des flux RSS...\n")
    collecte = collecter()
    total = sum(len(v) for v in collecte.values())
    print(f"\n{total} articles collectés.")

    if total < 10:
        raise SystemExit("Trop peu d'articles, génération annulée.")

    depeches = formater_depeches(collecte)

    if args.dry_run:
        Path("collecte_test.txt").write_text(depeches, encoding="utf-8")
        print("[OK] Mode test : collecte écrite dans collecte_test.txt")
        return

    print("Génération du résumé...")
    markdown = resumer(depeches)
    _, contenu = ecrire(markdown, collecte)
    envoyer_mail(contenu)


if __name__ == "__main__":
    main()
