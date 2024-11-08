# Téléchargeur Sentinel-2 Maroc

Un outil automatisé pour télécharger des images satellites Sentinel-2 couvrant le territoire marocain via l'API Copernicus Data Space Ecosystem.

## 📋 Table des matières

- [Aperçu](#aperçu)
- [Fonctionnalités](#fonctionnalités)
- [Prérequis](#prérequis)
- [Installation](#installation)
- [Utilisation](#utilisation)
- [Configuration](#configuration)
- [Structure des données](#structure-des-données)
- [Sécurité](#sécurité)


## 🎯 Aperçu

Cet outil permet d'automatiser le téléchargement d'images satellites Sentinel-2 pour trois régions distinctes du Maroc, en gérant automatiquement l'authentification, la recherche et l'organisation des données.

## ✨ Fonctionnalités

### Découpage Géographique
- **Nord** : 35.92°N à 32°N
- **Centre** : 32°N à 28°N
- **Sud** : 28°N à 20.70°N

### Principales caractéristiques
- 🔐 Authentification sécurisée via l'API Copernicus
- 🔍 Recherche personnalisée par période
- ☁️ Filtrage par couverture nuageuse
- 📥 Téléchargement automatisé avec reprise
- 📊 Barre de progression en temps réel
- 📁 Organisation structurée des données

## 🔧 Prérequis

- Compte Copernicus Data Space Ecosystem
- Python 3.7+
- Connexion Internet stable

## 💻 Installation

```bash
git clone https://github.com/allamed/sentinel_2_downloader
pip install -r requirements.txt
```

## 🚀 Utilisation

```python
python download_sentinel.py
```

### Exemple de configuration
```python
date_debut = "2023-06-01"
date_fin = "2023-06-30"
couverture_nuageuse_max = 30
dossier_sortie = "morocco_sentinel_data"
```

## 📁 Structure des données

```
morocco_sentinel_data/
├── nord/
│   └── YYYY-MM-DD/
├── centre/
│   └── YYYY-MM-DD/
└── sud/
    └── YYYY-MM-DD/
```

## 🔒 Sécurité

- Masquage des identifiants lors de la saisie
- Gestion sécurisée des jetons d'authentification
- Journalisation des erreurs
- Vérification de l'intégrité des données

## 🛠 Robustesse

- Gestion des interruptions
- Reconnexion automatique
- Vérification des téléchargements
- Création automatique des dossiers

