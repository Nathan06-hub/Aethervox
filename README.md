# Æther ⏳🛡️

> **Système intelligent et autonome de gestion des sessions d'études, de divertissement et de discipline numérique pour Windows.**
>
> 🚧 **Statut : Projet en développement actif** (Modules d'architecture et de persistance finalisés — moteurs de planification et sentinelle en cours de développement).

[![Python](https://img.shields.io/badge/Python-3.12-blue.svg?logo=python)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D6.svg?logo=windows)](https://www.microsoft.com/windows)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Architecture: Modular](https://img.shields.io/badge/Architecture-Modular-success.svg)](#architecture)

---

## 🎯 Le Problème & La Solution

En tant qu'étudiant universitaire, l'emploi du temps change chaque semaine et les distractions sur ordinateur (jeux, réseaux sociaux, flux continus) empiètent souvent sur le temps de révision personnel et le repos.

**Æther** est un assistant de discipline locale qui :
1. **S'adapte à ton rythme chaque semaine** : Reçoit ton programme hebdomadaire de cours (par exemple chaque dimanche) et planifie dynamiquement tes créneaux de travail personnel et de détente.
2. **Surveille en arrière-plan** : Démarre avec Windows, s'installe discrètement dans la barre des tâches (System Tray) et envoie des notifications avant chaque session.
3. **Applique la discipline** : Détecte et bloque (ou ferme) les applications distrayantes définies dans ta liste noire pendant les créneaux d'étude.

---

## 🏗️ Architecture du Projet

Le projet suit une **architecture modulaire en couche `src/`**, garantissant la maintenabilité, l'extensibilité et la testabilité de chaque composant :

```text
Aethervox/
├── src/
│   └── aether/
│       ├── core/       # Configuration globale, logging, constantes
│       ├── storage/    # Base de données SQLite locale & gestion des modèles
│       ├── engine/     # Algorithme de planification dynamique de l'emploi du temps
│       ├── system/     # Sentinelle OS (surveillance psutil, notifications Windows, blocage)
│       ├── daemon/     # Exécution en tâche de fond, System Tray, autostart Windows
│       └── ui/         # Interface graphique Desktop moderne (CustomTkinter)
├── tests/              # Suite de tests unitaires (pytest)
├── pyproject.toml      # Métadonnées et configuration standard du package
├── requirements.txt    # Dépendances de production
└── requirements-dev.txt# Dépendances d'outillage & tests
```

---

## 🗺️ Feuille de Route Modulaire

- [x] **Module 0 : Initialisation & Structure professionnelle** (Architecture, venv, packaging, Git)
- [x] **Module 1 : Modèle & Persistance** (Base SQLite WAL, Pydantic v2, DAO/Repositories complets)
- [ ] **Module 2 : Moteur de Planification** (Algorithme de génération sous contraintes)
- [ ] **Module 3 : Sentinelle Système** (Surveillance des processus et notifications toast)
- [ ] **Module 4 : Démon Tray & Autostart** (Intégration barre des tâches et démarrage Windows)
- [ ] **Module 5 : Interface Graphique Desktop** (Dashboard CustomTkinter)

---

## 🚀 Démarrage Rapide

### Prérequis
- Windows 10 ou 11
- Python 3.12+
- Git

### Installation

1. **Cloner le dépôt :**
   ```powershell
   git clone https://github.com/Nathan06-hub/Aethervox.git
   cd Aethervox
   ```

2. **Créer et activer l'environnement virtuel :**
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

3. **Installer les dépendances :**
   ```powershell
   pip install -r requirements.txt
   ```

4. **Lancer Æther :**
   ```powershell
   python -m aether
   ```

---

## 🧪 Tests

Pour exécuter les tests unitaires :
```powershell
pytest
```

---

## 📄 Licence

Ce projet est sous licence [MIT](LICENSE).
