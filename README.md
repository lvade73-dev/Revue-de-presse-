# Revue de presse quotidienne

Génère chaque matin un fichier Markdown résumant l'actualité internationale,
à partir d'une vingtaine de flux RSS répartis sur cinq zones géographiques.
Entièrement gratuit, sans serveur.

---

## Mise en place (environ 20 minutes)

### 1. Clé API Gemini

Va sur https://aistudio.google.com/apikey → **Create API key**.
Le niveau gratuit suffit largement : ce script fait un appel par jour.
Copie la clé, tu en auras besoin à l'étape 3.

### 2. Dépôt GitHub

Crée un dépôt **privé** (par exemple `revue-presse`), puis dépose-y ces fichiers
en conservant l'arborescence :

```
revue-presse/
├── main.py
├── sources.py
├── requirements.txt
├── README.md
└── .github/
    └── workflows/
        └── revue.yml
```

### 3. Secrets

Dans le dépôt : **Settings → Secrets and variables → Actions → New repository secret**.

Obligatoire :

| Nom | Valeur |
|---|---|
| `GEMINI_API_KEY` | la clé de l'étape 1 |

Optionnel, pour recevoir le brief par mail :

| Nom | Valeur |
|---|---|
| `MAIL_EXPEDITEUR` | ton adresse Gmail |
| `MAIL_MOT_DE_PASSE` | un **mot de passe d'application** Google (pas ton mot de passe habituel) |
| `MAIL_DESTINATAIRE` | l'adresse qui reçoit |

Le mot de passe d'application se crée sur https://myaccount.google.com/apppasswords
(nécessite la validation en deux étapes activée).

Si ces trois secrets sont absents, le script écrit simplement le fichier sans envoyer de mail.

### 4. Premier lancement

Onglet **Actions → Revue de presse quotidienne → Run workflow**.
Compte deux à trois minutes. Le fichier apparaît ensuite dans `briefs/`.

Ensuite, ça tourne tout seul à 07h30 (heure de Paris, été).

---

## Utilisation au quotidien

- **`dernier.md`** à la racine contient toujours le brief le plus récent.
  Mets son URL GitHub en favori sur ton téléphone : un clic, tu lis.
- **`briefs/AAAA-MM-JJ.md`** conserve l'historique complet, jour par jour.

---

## Tester en local

```bash
pip install -r requirements.txt

# Vérifier que les flux répondent, sans consommer de quota LLM
python main.py --dry-run

# Génération complète
export GEMINI_API_KEY="ta_clé"
python main.py
```

Le mode `--dry-run` écrit `collecte_test.txt` avec les dépêches brutes.
C'est ce qu'il faut lancer après avoir modifié `sources.py`.

---

## Personnalisation

**Changer l'heure** — dans `revue.yml`, la ligne `cron: "30 5 * * *"` est en UTC.
Retranche 2 heures en été, 1 heure en hiver, pour obtenir l'heure de Paris.
GitHub Actions peut décaler l'exécution de 5 à 20 minutes aux heures de pointe,
c'est normal.

**Ajouter ou retirer une source** — édite `sources.py`. Chaque entrée est un
couple `("Nom affiché", "url du flux")`. Lance `--dry-run` pour vérifier que le
nouveau flux répond avant de committer.

**Changer le format ou la longueur** — tout est dans la constante `PROMPT` de
`main.py`. Le nombre d'items, le ton, la structure des sections : c'est du texte,
modifie-le librement.

**Filtrer des thèmes** — ajoute une consigne dans le prompt, par exemple :
« Accorde une place particulière à l'actualité économique et réglementaire. »

---

## En cas de problème

| Symptôme | Cause probable |
|---|---|
| `Trop peu d'articles` | plusieurs flux sont tombés — lance `--dry-run` pour identifier lesquels |
| `[!] Nom : flux illisible` | l'URL a changé ou le site bloque les robots ; retire la source |
| Erreur API 429 | quota Gemini dépassé, rare avec un appel par jour |
| Le workflow ne se déclenche plus | GitHub désactive les crons après 60 jours d'inactivité du dépôt ; un commit le réactive |

---

## Coût

Zéro. GitHub Actions offre 2 000 minutes par mois, ce script en consomme environ
60. Le niveau gratuit de Gemini couvre très largement un appel quotidien.
