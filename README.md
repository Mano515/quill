# ✏️ Quill — PDF Editor

Un éditeur PDF complet avec interface web, API REST et CLI.  
Fusionne, divise, annote, signe, chiffre, extrait, convertit — le tout en local, sans aucune donnée envoyée vers un service tiers.

---

## Aperçu

- **Interface web** — glisser-déposer, aperçu en temps réel, édition de texte au clic
- **API REST** — FastAPI, clé API, entièrement documentée sur `/docs`
- **CLI** — toutes les fonctionnalités disponibles en ligne de commande

---

## Installation

**Prérequis :** Python 3.10+

```bash
git clone https://github.com/Mano515/quill
cd quill
pip install -e .
```

**Options supplémentaires :**

```bash
pip install -e ".[ocr]"      # OCR (Tesseract requis)
pip install -e ".[convert]"  # PDF → Markdown avec pymupdf4llm
pip install -e ".[all]"      # Tout installer
```

> **OCR** nécessite aussi [Tesseract](https://github.com/tesseract-ocr/tesseract) installé sur votre système.

---

## Lancement

```bash
quill-server
```

Ouvrez ensuite **http://localhost:8080** dans votre navigateur.

La clé API est générée automatiquement au premier lancement et sauvegardée dans `.quill_api_key` :

```bash
cat .quill_api_key
```

---

## Fonctionnalités

### 📄 Basique
| Outil | Description |
|---|---|
| Fusionner | Combiner plusieurs PDFs en un seul |
| Diviser | Extraire des plages de pages |
| Rotation | Pivoter des pages à 90°/180°/270° |
| Réordonner | Glisser-déposer pour changer l'ordre des pages |
| Supprimer pages | Retirer des pages d'un document |
| Métadonnées | Lire auteur, date, nombre de pages… |
| Extraire texte | Obtenir le contenu textuel brut |

### 🔒 Sécurité
| Outil | Description |
|---|---|
| Chiffrer | Protéger par mot de passe |
| Déchiffrer | Supprimer la protection |

### ✏️ Annotations
| Outil | Description |
|---|---|
| Filigrane texte | Diagonal, opacité et angle configurables |
| Tampon | CONFIDENTIEL, APPROUVÉ… centré sur les pages |
| Ajouter texte | Texte libre positionné au clic sur l'aperçu |
| Insérer image | Logo ou cachet positionné au clic |
| Commentaire | Note collante (sticky note) |
| Numéroter pages | Position, préfixe et numéro de départ configurables |
| **Éditer texte** | Cliquer directement sur du texte dans l'aperçu pour le réécrire |

### 📊 Extraction
| Outil | Description |
|---|---|
| Tableaux | Export CSV ou Excel |
| Images | Toutes les images embarquées en ZIP |
| Liens | Liste de tous les hyperliens |
| Langue | Détection automatique de la langue |

### 📋 Formulaires
| Outil | Description |
|---|---|
| Lister champs | Voir tous les champs interactifs et leurs valeurs |
| Remplir | Remplir les champs avec des données JSON |
| Aplatir | Rendre les champs non modifiables |
| Créer | Générer un PDF interactif depuis zéro |

### 🔍 OCR
| Outil | Description |
|---|---|
| PDF → Cherchable | Reconnaître le texte d'un PDF scanné |
| PDF → Images | Exporter les pages en PNG ou JPEG |

### ✍️ Signatures
| Outil | Description |
|---|---|
| Signer | Apposer un bloc de signature visuel |
| Voir signatures | Lister les signatures du document |

### 🔄 Conversions
| Outil | Description |
|---|---|
| PDF → Images | Pages en PNG ou JPEG |
| Images → PDF | Assembler des images en PDF |
| PDF → Markdown | Conversion structurée |
| PDF → JSON | Mise en page avec positions et polices |

---

## Interface web

### Raccourcis clavier

| Touche | Action |
|---|---|
| `Ctrl + Entrée` | Lancer l'opération active |
| `← / →` | Page précédente / suivante dans l'aperçu |
| `E` | Activer / désactiver le mode édition texte |
| `?` | Afficher l'aide clavier |
| `Échap` | Fermer les fenêtres |

### Édition de texte

L'aperçu est **toujours en mode édition**. Il suffit de :

1. Charger un PDF (glisser-déposer ou sélecteur de fichier)
2. Survoler le texte — les mots se surlignent en violet
3. Cliquer sur un mot ou une phrase pour l'éditer
4. `Entrée` pour valider, `Échap` pour annuler

Le texte original est effacé et remplacé à la même position, avec la même taille de police détectée automatiquement.

### Persistance du fichier

Le PDF chargé est conservé dans **IndexedDB** et se retrouve automatiquement après un rechargement de page. Le bouton **🗑 Tout effacer** dans la sidebar supprime le fichier sauvegardé.

### Chaînage d'opérations

Après chaque résultat PDF, un bouton **⤵ Réutiliser ce résultat** apparaît pour envoyer directement le fichier vers un autre outil sans re-télécharger.

---

## CLI

```bash
# Fusionner
quill merge a.pdf b.pdf -o merged.pdf

# Diviser (pages 1-3 et 5)
quill split doc.pdf -r "1-3,5" -o output/

# Rotation
quill rotate doc.pdf -d 90 -o rotated.pdf

# Filigrane
quill watermark doc.pdf "CONFIDENTIEL" -o watermarked.pdf

# Signer
quill sign doc.pdf -n "Alice Martin" -r "Approbation" -o signed.pdf

# Chiffrer
quill encrypt doc.pdf -p "monmotdepasse" -o protected.pdf

# OCR
quill ocr scan.pdf -l fra+eng -o searchable.pdf
```

```bash
quill --help        # liste toutes les commandes
quill merge --help  # aide détaillée sur une commande
```

---

## API REST

La documentation interactive est disponible sur **http://localhost:8080/docs**.

Toutes les requêtes nécessitent le header `X-API-Key`.

**Exemple :**

```bash
curl -X POST http://localhost:8080/basic/merge \
  -H "X-API-Key: VOTRE_CLE" \
  -F "files=@a.pdf" \
  -F "files=@b.pdf" \
  --output merged.pdf
```

**Édition de texte :**

```bash
curl -X POST http://localhost:8080/edit/replace-text \
  -H "X-API-Key: VOTRE_CLE" \
  -F "file=@doc.pdf" \
  -F "page=1" \
  -F "x0=50" -F "y0=100" -F "x1=200" -F "y1=115" \
  -F "new_text=Nouveau contenu" \
  --output edited.pdf
```

---

## Structure du projet

```
quill/
├── api/
│   ├── app.py          # Application FastAPI — enregistre tous les routeurs
│   ├── auth.py         # Authentification par clé API (header X-API-Key)
│   ├── deps.py         # Helpers partagés : workdir(), pdf_response(), parse_pages()
│   └── routes/         # Un fichier par groupe de fonctionnalités
│       ├── basic.py
│       ├── annotations.py
│       ├── edit.py     # POST /edit/replace-text
│       ├── extraction.py
│       ├── forms.py
│       ├── ocr.py
│       ├── security.py
│       ├── sign.py
│       └── convert.py
├── features/           # Logique métier pure (sans dépendance FastAPI)
│   ├── basic.py
│   ├── annotations.py
│   ├── edit.py         # Remplacement de texte via PyMuPDF
│   ├── extraction.py
│   ├── forms.py
│   ├── ocr.py
│   ├── security.py
│   ├── sign.py
│   └── convert.py
├── static/
│   └── index.html      # SPA complète (HTML + CSS + JS, zéro dépendance bundlée)
├── cli.py              # Interface ligne de commande (Click)
└── server.py           # Point d'entrée : quill-server → uvicorn sur :8080
tests/
├── conftest.py         # Fixtures partagées (client HTTP, PDF de test)
├── test_api.py         # Tests API end-to-end (~80 tests)
├── test_edit.py        # Tests du remplacement de texte
├── test_e2e_drag_drop.py  # Tests Playwright (drag & drop, rendu PDF)
└── test_sign.py        # Tests unitaires signatures
```

---

## Tests

```bash
pip install -e ".[dev]"
pytest                  # tous les tests
pytest tests/test_api.py           # API uniquement
pytest tests/test_edit.py          # édition texte
pytest -m "not e2e"                # sans les tests Playwright
```

Les tests E2E nécessitent Playwright :

```bash
pip install pytest-playwright
python -m playwright install chromium
pytest -m e2e
```

---

## Licence

MIT
