# -*- coding: utf-8 -*-
"""
Sources RSS classées par zone géographique.

Pour ajouter une source : ajoute simplement (nom, url) dans la bonne zone.
Pour en désactiver une : commente la ligne avec #
"""

SOURCES = {
    "Europe": [
        ("France Info", "https://www.francetvinfo.fr/titres.rss"),
        ("Le Monde", "https://www.lemonde.fr/international/rss_full.xml"),
        ("RFI Monde", "https://www.rfi.fr/fr/monde/rss"),
        ("RTBF Info", "https://rss.rtbf.be/article/rss/highlight_rtbfinfo_info.xml"),
        ("Euronews", "https://fr.euronews.com/rss?level=theme&name=news"),
        ("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml"),
        ("The Guardian World", "https://www.theguardian.com/world/rss"),
        ("Deutsche Welle", "https://rss.dw.com/rdf/rss-fr-all"),
    ],
    "Afrique": [
        ("RFI Afrique", "https://www.rfi.fr/fr/afrique/rss"),
        ("Jeune Afrique", "https://www.jeuneafrique.com/feed/"),
        ("AllAfrica FR", "https://fr.allafrica.com/tools/headlines/rdf/latest/headlines.rdf"),
        ("BBC Afrique", "https://www.bbc.com/afrique/index.xml"),
    ],
    "Amériques": [
        ("AP News", "https://rsshub.app/apnews/topics/apf-topnews"),
        ("NPR World", "https://feeds.npr.org/1004/rss.xml"),
        ("Radio-Canada Intl", "https://ici.radio-canada.ca/rss/4159"),
        ("France 24 Amériques", "https://www.france24.com/fr/amériques/rss"),
    ],
    "Moyen-Orient": [
        ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
        ("France 24 Moyen-Orient", "https://www.france24.com/fr/moyen-orient/rss"),
        ("Al Arabiya English", "https://english.alarabiya.net/tools/rss"),
    ],
    "Asie": [
        ("NHK World", "https://www3.nhk.or.jp/nhkworld/en/news/feeds/"),
        ("The Hindu International", "https://www.thehindu.com/news/international/feeder/default.rss"),
        ("South China Morning Post", "https://www.scmp.com/rss/91/feed"),
        ("France 24 Asie", "https://www.france24.com/fr/asie-pacifique/rss"),
    ],
}

# Nombre max d'articles retenus par flux (les plus récents)
MAX_PAR_FLUX = 3

# Fenêtre temporelle : on ne garde que les articles des N dernières heures
FENETRE_HEURES = 26
