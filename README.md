**Powerful QGIS extension for converting geographic coordinates between 200+ projection systems**, with native support for the **BFTM (Burkina Faso Transverse Mercator)** system.
 
[![QGIS Plugin](https://img.shields.io/badge/QGIS-Plugin-brightgreen)](https://github.com/geomatic-web/universal-map2web)
[![Version](https://img.shields.io/badge/version-2.0.0-blue)](https://github.com/geomatic-web/universal_map2web)
[![License](https://img.shields.io/badge/license-GPLv2-orange)](https://github.com/geomatic-web/universal_map2web)

## Video Tutorial
 
https://www.youtube.com/watch?v=PlOYuNvz2ZM
 
## Documentation
 
[The complete user manual is available here (PDF)](User_manuel_QGIS_Plugin_XY_converter.pdf)
## Features
✅ **Conversion between 200+ coordinate systems**
✅ **Batch processing of CSV files** (bulk import/export)
✅ **Interactive map selection** (click to retrieve coordinates)
✅ **Custom CRS** (PROJ strings)
✅ **Native support for local systems** such as **BFTM (Burkina Faso)**
✅ **Multi-format export**: CSV, GeoJSON, KML, Shapefile
✅ **Intuitive user interface** integrated into QGIS
✅ **Conversion history** for quick access

---
 
## Installation
 
### Method 1: From the official QGIS repository (recommended)
 
1. Open **QGIS**
2. Go to **Plugins → Manage and Install Plugins**
3. Search for **"Universal XY Converter"**
4. Click **Install**
### Method 2: Manual installation from a ZIP file
 
1. Download the ZIP file from the following address:
   🔗 **https://plugins.qgis.org/plugins/universal_xy_converter/version/1.1.0/download/**
2. In QGIS, go to **Plugins → Manage and Install Plugins**
3. Click **Install from ZIP**
4. Select the downloaded ZIP file
5. Confirm the installation
### Method 3: From source
 
```bash
# Clone the repository
git clone https://github.com/geomatic-web/Universal_xy_converter.git
 
# Copy the folder into the QGIS plugins directory
cp -r Universal_xy_converter ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/
