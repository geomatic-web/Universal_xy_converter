# Universal XY Converter - Extension QGIS

[![QGIS Plugin](https://img.shields.io/badge/QGIS-Plugin-green)](https://plugins.qgis.org/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

Extension universelle de conversion de coordonnées pour QGIS.

## ✨ Fonctionnalités

- 🔄 **Conversion simple** entre tous les CRS disponibles dans QGIS (200+ systèmes)
- 🇧🇫 **Support prioritaire du BFTM** (Burkina Faso Transverse Mercator)
- 📊 **Traitement batch CSV** : convertissez des fichiers entiers
- 🖱️ **Sélection interactive** : cliquez sur la carte pour convertir
- 💾 **Export direct** de couches vectorielles vers n'importe quel CRS
- 🔧 **CRS personnalisés** via chaînes PROJ
- ✅ **Validation des limites** du Burkina Faso

## 📥 Installation

### Depuis le dépôt GitHub
1. Téléchargez le fichier ZIP
2. Dans QGIS : `Extensions` → `Installer/Gérer les extensions` → `Installer à partir d'un ZIP`

### Installation manuelle
1. Copiez le dossier `Universal_xy_converter` dans :
   - **Windows**: `C:\Users\VOTRE_NOM\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\`
   - **Linux**: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
   - **Mac**: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`
2. Activez l'extension dans QGIS

## 🚀 Utilisation

1. Lancez l'extension depuis le menu `Extensions` → `Universal XY Converter`
2. Choisissez la direction de conversion (vers/depuis BFTM ou entre 2 systèmes)
3. Sélectionnez vos CRS source et cible
4. Entrez les coordonnées et cliquez sur "Convertir"

## 📋 Systèmes supportés

- WGS 84 (degrés et UTM zones 1-60)
- BFTM (Burkina Faso)
- Adindan, Clarke 1880
- ETRS89, RGF93 (Europe)
- NAD83 (Amérique)
- GDA2020 (Australie)
- Et tous les CRS disponibles dans QGIS...

## 👨‍💻 Développement

```bash
git clone https://github.com/votre_nom/Universal_xy_converter.git
cd Universal_xy_converter
