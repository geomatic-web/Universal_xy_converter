# Universal XY Converter - QGIS Plugin
**Extension QGIS puissante pour la conversion de coordonnées géographiques entre **200+ systèmes de projection**, avec prise en charge native du système **BFTM (Burkina Faso Transverse Mercator)**.
[![QGIS Plugin](https://img.shields.io/badge/QGIS-Plugin-brightgreen)](https://github.com/geomatic-web/universal-map2web)
[![Version](https://img.shields.io/badge/version-1.1.0-blue)](https://github.com/geomatic-web/universal_map2web)
[![License](https://img.shields.io/badge/license-GPLv2-orange)](https://github.com/geomatic-web/universal_map2web)
<h2>Video Tutorial</h2>
https://youtu.be/PlOYuNvz2ZM

---
## Fonctionnalités

✅ **Conversion entre 200+ systèmes de coordonnées**  
✅ **Traitement batch de fichiers CSV** (import/export en masse)  
✅ **Sélection interactive sur carte** (clic pour récupérer les coordonnées)  
✅ **CRS personnalisés** (chaînes PROJ)  
✅ **Support natif des systèmes locaux** comme le **BFTM (Burkina Faso)**  
✅ **Export multi-formats** : CSV, GeoJSON, KML, Shapefile  
✅ **Interface utilisateur intuitive** intégrée à QGIS  
✅ **Historique des conversions** pour un accès rapide  

---
## Installation

### Méthode 1 : Depuis le dépôt officiel QGIS (recommandée)

1. Ouvrez **QGIS**
2. Allez dans **Extensions → Gérer les extensions**
3. Recherchez **"Universal XY Converter"**
4. Cliquez sur **Installer**

### Méthode 2 : Installation manuelle depuis un ZIP

1. Téléchargez le fichier ZIP à l'adresse suivante :  
   🔗 **https://plugins.qgis.org/plugins/universal_xy_converter/version/1.1.0/download/**
2. Dans QGIS, allez dans **Extensions → Gérer les extensions**
3. Cliquez sur **Installer depuis un ZIP**
4. Sélectionnez le fichier ZIP depuis votre dossier de téléchargement
5. Validez l'installation

### Méthode 3 : Depuis le code source

```bash
# Cloner le dépôt
git clone https://github.com/geomatic-web/Universal_xy_converter.git

# Copier le dossier dans le répertoire des plugins QGIS
cp -r Universal_xy_converter ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/
