import os
import csv
import re
from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QComboBox, QGroupBox,
    QGridLayout, QTabWidget, QFileDialog,
    QTextEdit, QProgressBar, QMessageBox,
    QCheckBox, QWidget, QApplication
)
from qgis.PyQt.QtGui import QTextCursor
from qgis.core import (
    QgsCoordinateReferenceSystem, QgsCoordinateTransform,
    QgsProject, QgsPointXY, QgsWkbTypes
)
from qgis.gui import QgsMapToolEmitPoint, QgsRubberBand

try:
    from .batch_processor import BatchProcessor
except ImportError:
    import sys
    sys.path.append(os.path.dirname(__file__))
    from batch_processor import BatchProcessor


class UniversalXYConverterDialog(QDialog):
    def __init__(self, iface, plugin_dir):
        super().__init__()
        self.iface = iface
        self.plugin_dir = plugin_dir
        self.map_tool = None
        self.rubber_band = None
        self.processor = None
        self.setWindowTitle("Universal XY Converter")
        self.setMinimumWidth(700)
        self.setMinimumHeight(750)

        # Définition des systèmes de coordonnées
        self.setup_crs_definitions()

        self.setup_ui()

    # ==================== MÉTHODES DE CONVERSION DMS ====================

    def dms_to_decimal(self, dms_string):
        """Convertit une chaîne DMS (ex: 12°30'15" N ou 12°30'15" O) en degrés décimaux"""
        try:
            if not dms_string or dms_string.strip() == "":
                return None

            dms_string = dms_string.strip().upper()

            # Vérifier si c'est déjà un nombre décimal
            try:
                val = float(dms_string)
                return val
            except ValueError:
                pass

            # Gestion des directions (français ET anglais)
            # Nord / Sud (latitude)
            # Est / Ouest (longitude)
            direction = 1.0

            # Directions négatives (Ouest et Sud)
            if 'S' in dms_string or 'W' in dms_string or 'O' in dms_string:
                direction = -1.0

            # Note: 'N' et 'E' sont positifs par défaut (direction = 1.0)
            # Pas besoin de condition pour N et E car direction reste 1.0

            # Remplacer les symboles par des espaces
            dms_string = dms_string.replace('°', ' ').replace("'", ' ').replace('"', ' ')
            dms_string = dms_string.replace('N', ' ').replace('S', ' ')
            dms_string = dms_string.replace('E', ' ').replace('W', ' ')
            dms_string = dms_string.replace('O', ' ').replace(',', '.')

            # Extraire les nombres
            numbers = re.findall(r"[-+]?\d*\.?\d+", dms_string)
            values = [float(n) for n in numbers if n]

            if len(values) == 0:
                return None
            elif len(values) == 1:
                result = values[0]
            elif len(values) == 2:
                result = values[0] + values[1] / 60.0
            else:
                result = values[0] + values[1] / 60.0 + values[2] / 3600.0

            return result * direction

        except Exception:
            return None

    def decimal_to_dms(self, decimal, is_latitude=True):
        """Convertit un degré décimal en DMS (ex: 12.5° → 12°30'0" N)"""
        try:
            direction = ""
            value = decimal

            if is_latitude:
                if value >= 0:
                    direction = "N"
                else:
                    direction = "S"
                    value = -value
            else:
                if value >= 0:
                    direction = "E"
                else:
                    direction = "W"
                    value = -value

            degrees = int(value)
            minutes_decimal = (value - degrees) * 60
            minutes = int(minutes_decimal)
            seconds = (minutes_decimal - minutes) * 60

            return f"{degrees}°{minutes}'{seconds:.1f}\"{direction}"

        except Exception:
            return str(decimal)

    # ==================== MÉTHODES DE CONVERSION CRS ====================

    def setup_crs_definitions(self):
        """Définit tous les systèmes de coordonnées disponibles."""

        # BFTM (Burkina Faso) - Système officiel
        self.bftm_crs = QgsCoordinateReferenceSystem()
        bftm_proj = (
            "+proj=tmerc "
            "+lat_0=0 "
            "+lon_0=-1.5 "
            "+k=0.9996 "
            "+x_0=600000 "
            "+y_0=0 "
            "+ellps=GRS80 "
            "+towgs84=0,0,0,0,0,0,0 "
            "+units=m "
            "+no_defs"
        )
        self.bftm_crs = QgsCoordinateReferenceSystem.fromProj(bftm_proj)

        if not self.bftm_crs.isValid():
            self.iface.messageBar().pushMessage(
                "Erreur", "Échec de création du CRS BFTM", level=2)

        # Dictionnaire des CRS disponibles
        self.available_crs = {}
        self.available_crs["🇧🇫 BFTM (Burkina Faso) - OFFICIEL"] = self.bftm_crs

        # WGS84
        self.add_crs_if_valid("🌍 WGS 84 (degrés)", "EPSG:4326")
        self.add_crs_if_valid("🌍 WGS 84 (Web Mercator)", "EPSG:3857")

        # UTM Nord
        for zone in range(1, 61):
            self.add_crs_if_valid(f"📐 WGS 84 / UTM zone {zone}N", f"EPSG:326{zone:02d}")

        # UTM Sud
        for zone in range(1, 61):
            self.add_crs_if_valid(f"📐 WGS 84 / UTM zone {zone}S", f"EPSG:327{zone:02d}")

        # Autres systèmes
        other_crs = [
            ("🌍 Adindan (UTM 29N) - Afrique", "EPSG:20137"),
            ("🌍 Adindan (UTM 30N) - Afrique/Burkina", "EPSG:20138"),
            ("🌍 Adindan (UTM 31N) - Afrique", "EPSG:20139"),
            ("🌍 Clarke 1880 (UTM 30N) - Afrique Sud", "EPSG:2234"),
            ("🇪🇺 ETRS89 (degrés) - Europe", "EPSG:4258"),
            ("🇪🇺 ETRS89 / UTM zone 31N - Europe", "EPSG:25831"),
            ("🇪🇺 ETRS89 / UTM zone 32N - Europe", "EPSG:25832"),
            ("🇫🇷 RGF93 / Lambert-93 - France", "EPSG:2154"),
            ("🇬🇧 OSGB 1936 / British National Grid - UK", "EPSG:27700"),
            ("🇺🇸 NAD83 (degrés) - Amérique Nord", "EPSG:4269"),
            ("🇺🇸 NAD83 / UTM zone 10N - USA", "EPSG:26910"),
            ("🇧🇷 SIRGAS 2000 (degrés) - Brésil", "EPSG:4674"),
            ("🇨🇳 CGCS2000 (degrés) - Chine", "EPSG:4490"),
            ("🇦🇺 GDA2020 (degrés) - Australie", "EPSG:7844"),
            ("🗺️ Swiss CH1903+ / LV95 - Suisse", "EPSG:2056"),
        ]
        for name, epsg in other_crs:
            self.add_crs_if_valid(name, epsg)

        self.available_crs["--- Personnalisé (PROJ) ---"] = None

    def add_crs_if_valid(self, name, epsg_code):
        try:
            crs = QgsCoordinateReferenceSystem(epsg_code)
            if crs.isValid():
                self.available_crs[name] = crs
        except BaseException:
            pass

    def setup_ui(self):
        layout = QVBoxLayout()
        self.tabs = QTabWidget()

        self.simple_tab = QWidget()
        self.setup_simple_tab()
        self.tabs.addTab(self.simple_tab, "Conversion simple")

        self.batch_tab = QWidget()
        self.setup_batch_tab()
        self.tabs.addTab(self.batch_tab, "Traitement batch")

        self.interactive_tab = QWidget()
        self.setup_interactive_tab()
        self.tabs.addTab(self.interactive_tab, "Sélection interactive")

        self.about_tab = QWidget()
        self.setup_about_tab()
        self.tabs.addTab(self.about_tab, "📖 Aide")

        layout.addWidget(self.tabs)
        self.setLayout(layout)

    # ==================== CONVERSION SIMPLE ====================

    def setup_simple_tab(self):
        layout = QVBoxLayout()

        # Système source
        source_group = QGroupBox("Système source")
        source_layout = QGridLayout()

        source_layout.addWidget(QLabel("CRS source:"), 0, 0)
        self.source_crs_combo = QComboBox()
        self.populate_crs_combo(self.source_crs_combo)
        self.source_crs_combo.currentIndexChanged.connect(self.on_source_crs_changed)
        source_layout.addWidget(self.source_crs_combo, 0, 1)

        source_layout.addWidget(QLabel("Format source:"), 1, 0)
        self.source_format_combo = QComboBox()
        self.source_format_combo.currentIndexChanged.connect(self.on_source_format_changed)
        source_layout.addWidget(self.source_format_combo, 1, 1)

        self.custom_source_label = QLabel("Chaîne PROJ source:")
        self.custom_source_edit = QLineEdit()
        self.custom_source_edit.setPlaceholderText("ex: +proj=longlat +ellps=clrk80 +towgs84=-118,-14,218")
        self.custom_source_label.setVisible(False)
        self.custom_source_edit.setVisible(False)
        source_layout.addWidget(self.custom_source_label, 2, 0)
        source_layout.addWidget(self.custom_source_edit, 2, 1)

        source_group.setLayout(source_layout)
        layout.addWidget(source_group)

        # Système cible
        target_group = QGroupBox("Système cible")
        target_layout = QGridLayout()

        target_layout.addWidget(QLabel("CRS cible:"), 0, 0)
        self.target_crs_combo = QComboBox()
        self.populate_crs_combo(self.target_crs_combo)
        self.target_crs_combo.currentIndexChanged.connect(self.on_target_crs_changed)
        target_layout.addWidget(self.target_crs_combo, 0, 1)

        target_layout.addWidget(QLabel("Format cible:"), 1, 0)
        self.target_format_combo = QComboBox()
        target_layout.addWidget(self.target_format_combo, 1, 1)

        self.custom_target_label = QLabel("Chaîne PROJ cible:")
        self.custom_target_edit = QLineEdit()
        self.custom_target_edit.setPlaceholderText("ex: +proj=utm +zone=30 +ellps=GRS80 +units=m")
        self.custom_target_label.setVisible(False)
        self.custom_target_edit.setVisible(False)
        target_layout.addWidget(self.custom_target_label, 2, 0)
        target_layout.addWidget(self.custom_target_edit, 2, 1)

        target_group.setLayout(target_layout)
        layout.addWidget(target_group)

        # Coordonnées
        coord_group = QGroupBox("Coordonnées à convertir")
        coord_layout = QGridLayout()

        coord_layout.addWidget(QLabel("X / Longitude / Est:"), 0, 0)
        self.source_x = QLineEdit()
        coord_layout.addWidget(self.source_x, 0, 1)

        coord_layout.addWidget(QLabel("Y / Latitude / Nord:"), 1, 0)
        self.source_y = QLineEdit()
        coord_layout.addWidget(self.source_y, 1, 1)

        coord_group.setLayout(coord_layout)
        layout.addWidget(coord_group)

        # Boutons
        self.convert_btn = QPushButton("Convertir →")
        self.convert_btn.clicked.connect(self.convert_coordinates)
        self.convert_btn.setMinimumHeight(40)
        self.convert_btn.setStyleSheet("font-weight: bold; background-color: #4CAF50; color: white;")
        layout.addWidget(self.convert_btn)

        self.swap_btn = QPushButton("⟷ Échanger source/cible")
        self.swap_btn.clicked.connect(self.swap_crs)
        layout.addWidget(self.swap_btn)

        # Résultat
        result_group = QGroupBox("Résultat de la conversion")
        result_layout = QGridLayout()

        result_layout.addWidget(QLabel("X / Est:"), 0, 0)
        self.result_x = QLineEdit()
        self.result_x.setReadOnly(True)
        result_layout.addWidget(self.result_x, 0, 1)

        result_layout.addWidget(QLabel("Y / Nord:"), 1, 0)
        self.result_y = QLineEdit()
        self.result_y.setReadOnly(True)
        result_layout.addWidget(self.result_y, 1, 1)

        result_layout.addWidget(QLabel("Statut:"), 2, 0)
        self.conversion_status = QLabel("En attente")
        result_layout.addWidget(self.conversion_status, 2, 1)

        self.copy_btn = QPushButton("📋 Copier les résultats")
        self.copy_btn.clicked.connect(self.copy_results)
        result_layout.addWidget(self.copy_btn, 3, 0, 1, 2)

        result_group.setLayout(result_layout)
        layout.addWidget(result_group)

        self.simple_tab.setLayout(layout)

        # Initialiser les formats
        self.update_source_formats()
        self.update_target_formats()
        self.update_source_placeholder()

    def update_source_formats(self):
        """Met à jour les formats disponibles selon le CRS source"""
        source_name = self.source_crs_combo.currentText()

        geographic_keywords = [
            "WGS 84 (degrés)", "WGS 84 (Web Mercator)",
            "ETRS89 (degrés)", "NAD83 (degrés)",
            "SIRGAS 2000 (degrés)", "GDA2020 (degrés)", "GDA94 (degrés)",
            "CGCS2000 (degrés)", "NZGD2000 (degrés)", "JGD2011 (degrés)",
            "degrés", "4326"
        ]

        projected_keywords = [
            "UTM zone", "WGS 84 / UTM", "BFTM", "Lambert 93", "Lambert-93",
            "Belgian Lambert", "Dutch RD New", "Spanish UTM", "Web Mercator",
            "CH1903+ / LV95", "CH1903 / LV03", "Gauss-Kruger",
            "British National Grid", "NAD83 / UTM", "GDA2020 / UTM", "GDA94 / UTM",
            "NZGD2000 / UTM", "NZTM", "Adindan (UTM", "Clarke 1880 (UTM",
            "Arc 1950 (UTM", "Arc 1960 (UTM"
        ]

        is_geographic = any(kw in source_name for kw in geographic_keywords)
        is_projected = any(kw in source_name for kw in projected_keywords)

        current = self.source_format_combo.currentText()
        self.source_format_combo.clear()

        if is_geographic:
            self.source_format_combo.addItems(["Degrés décimaux (DD)", "Degrés/Minutes/Secondes (DMS)"])
        elif is_projected:
            self.source_format_combo.addItems(["Mètres (m)"])
        else:
            self.source_format_combo.addItems(["Degrés décimaux (DD)", "Degrés/Minutes/Secondes (DMS)", "Mètres (m)"])

        idx = self.source_format_combo.findText(current)
        if idx >= 0:
            self.source_format_combo.setCurrentIndex(idx)

    def update_target_formats(self):
        """Met à jour les formats disponibles selon le CRS cible"""
        target_name = self.target_crs_combo.currentText()

        geographic_keywords = [
            "WGS 84 (degrés)", "WGS 84 (Web Mercator)",
            "ETRS89 (degrés)", "NAD83 (degrés)",
            "SIRGAS 2000 (degrés)", "GDA2020 (degrés)", "GDA94 (degrés)",
            "CGCS2000 (degrés)", "NZGD2000 (degrés)", "JGD2011 (degrés)",
            "degrés", "4326"
        ]

        projected_keywords = [
            "UTM zone", "WGS 84 / UTM", "BFTM", "Lambert 93", "Lambert-93",
            "Belgian Lambert", "Dutch RD New", "Spanish UTM", "Web Mercator",
            "CH1903+ / LV95", "CH1903 / LV03", "Gauss-Kruger",
            "British National Grid", "NAD83 / UTM", "GDA2020 / UTM", "GDA94 / UTM",
            "NZGD2000 / UTM", "NZTM", "Adindan (UTM", "Clarke 1880 (UTM",
            "Arc 1950 (UTM", "Arc 1960 (UTM"
        ]

        is_geographic = any(kw in target_name for kw in geographic_keywords)
        is_projected = any(kw in target_name for kw in projected_keywords)

        current = self.target_format_combo.currentText()
        self.target_format_combo.clear()

        if is_geographic:
            self.target_format_combo.addItems(["Degrés décimaux (DD)", "Degrés/Minutes/Secondes (DMS)"])
        elif is_projected:
            self.target_format_combo.addItems(["Mètres (m)"])
        else:
            self.target_format_combo.addItems(["Degrés décimaux (DD)", "Degrés/Minutes/Secondes (DMS)", "Mètres (m)"])

        idx = self.target_format_combo.findText(current)
        if idx >= 0:
            self.target_format_combo.setCurrentIndex(idx)

    def update_source_placeholder(self):
        """Met à jour les placeholders selon le format source choisi"""
        source_format = self.source_format_combo.currentText()
        source_name = self.source_crs_combo.currentText()

        is_geographic = "degrés" in source_name or "4326" in source_name or "WGS 84" in source_name

        if source_format == "Degrés décimaux (DD)":
            if is_geographic:
                self.source_x.setPlaceholderText("ex: -1.5042 (longitude)")
                self.source_y.setPlaceholderText("ex: 12.5042 (latitude)")
            else:
                self.source_x.setPlaceholderText("ex: 679246.00 (mètres)")
                self.source_y.setPlaceholderText("ex: 1360000.00 (mètres)")
        elif source_format == "Degrés/Minutes/Secondes (DMS)":
            self.source_x.setPlaceholderText("ex: 1°30'0\" W")
            self.source_y.setPlaceholderText("ex: 12°30'15\" N")
        else:  # Mètres (m)
            self.source_x.setPlaceholderText("ex: 679246.00 (mètres)")
            self.source_y.setPlaceholderText("ex: 1360000.00 (mètres)")

    def on_source_crs_changed(self):
        """Gère le changement de CRS source."""
        is_custom = self.source_crs_combo.currentText() == "--- Personnalisé (PROJ) ---"
        self.custom_source_label.setVisible(is_custom)
        self.custom_source_edit.setVisible(is_custom)
        self.update_source_formats()
        self.update_source_placeholder()

    def on_source_format_changed(self):
        """Gère le changement de format source."""
        self.update_source_placeholder()

    def on_target_crs_changed(self):
        """Gère le changement de CRS cible."""
        is_custom = self.target_crs_combo.currentText() == "--- Personnalisé (PROJ) ---"
        self.custom_target_label.setVisible(is_custom)
        self.custom_target_edit.setVisible(is_custom)
        self.update_target_formats()

    def convert_coordinates(self):
        try:
            if not self.source_x.text() or not self.source_y.text():
                self.iface.messageBar().pushMessage("Erreur", "Veuillez entrer des coordonnées", level=2)
                return

            # Parse source
            src_fmt = self.source_format_combo.currentText()
            if src_fmt == "Degrés décimaux (DD)":
                x = float(self.source_x.text())
                y = float(self.source_y.text())
            elif src_fmt == "Degrés/Minutes/Secondes (DMS)":
                x = self.dms_to_decimal(self.source_x.text())
                y = self.dms_to_decimal(self.source_y.text())
                if x is None or y is None:
                    self.conversion_status.setText("✗ Format DMS invalide")
                    self.conversion_status.setStyleSheet("color: red;")
                    return
            else:  # Mètres
                x = float(self.source_x.text())
                y = float(self.source_y.text())

            # CRS
            source_crs = self.get_source_crs()
            target_crs = self.get_target_crs()
            if source_crs is None or target_crs is None:
                self.conversion_status.setText("✗ CRS invalide")
                return

            # Transformation
            transform = QgsCoordinateTransform(source_crs, target_crs, QgsProject.instance().transformContext())
            point = QgsPointXY(x, y)
            transformed = transform.transform(point)

            # Formatage résultat
            tgt_fmt = self.target_format_combo.currentText()
            tgt_name = self.target_crs_combo.currentText()
            is_geo = "degrés" in tgt_name or "4326" in str(target_crs.authid())

            if tgt_fmt == "Mètres (m)":
                self.result_x.setText(f"{transformed.x():.3f}")
                self.result_y.setText(f"{transformed.y():.3f}")
            elif tgt_fmt == "Degrés/Minutes/Secondes (DMS)":
                if is_geo:
                    self.result_x.setText(self.decimal_to_dms(transformed.x(), False))
                    self.result_y.setText(self.decimal_to_dms(transformed.y(), True))
                else:
                    self.result_x.setText(f"{transformed.x():.3f}")
                    self.result_y.setText(f"{transformed.y():.3f}")
                    self.conversion_status.setText("⚠️ DMS: système projeté → mètres")
                    self.conversion_status.setStyleSheet("color: orange;")
            else:  # DD
                if is_geo:
                    self.result_x.setText(f"{transformed.x():.6f}")
                    self.result_y.setText(f"{transformed.y():.6f}")
                else:
                    self.result_x.setText(f"{transformed.x():.3f}")
                    self.result_y.setText(f"{transformed.y():.3f}")
                    self.conversion_status.setText("⚠️ DD: système projeté → mètres")
                    self.conversion_status.setStyleSheet("color: orange;")

            self.conversion_status.setText("✓ Conversion réussie")
            self.conversion_status.setStyleSheet("color: green;")

        except Exception as e:
            self.conversion_status.setText(f"✗ Erreur: {str(e)[:50]}")
            self.conversion_status.setStyleSheet("color: red;")

    # ==================== TRAITEMENT BATCH ====================

    def setup_batch_tab(self):
        layout = QVBoxLayout()

        # Fichier source
        file_group = QGroupBox("1. Fichier source")
        file_layout = QHBoxLayout()
        self.source_file_path = QLineEdit()
        self.source_file_path.setPlaceholderText("Chemin vers le fichier CSV...")
        file_layout.addWidget(self.source_file_path)
        self.browse_btn = QPushButton("Parcourir")
        self.browse_btn.clicked.connect(self.browse_source_file)
        file_layout.addWidget(self.browse_btn)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        # Configuration colonnes
        cols_group = QGroupBox("2. Configuration des colonnes")
        cols_layout = QGridLayout()
        cols_layout.addWidget(QLabel("Colonne X / Longitude:"), 0, 0)
        self.x_column_combo = QComboBox()
        cols_layout.addWidget(self.x_column_combo, 0, 1)
        cols_layout.addWidget(QLabel("Colonne Y / Latitude:"), 1, 0)
        self.y_column_combo = QComboBox()
        cols_layout.addWidget(self.y_column_combo, 1, 1)
        cols_layout.addWidget(QLabel("Séparateur CSV:"), 2, 0)
        self.separator_combo = QComboBox()
        self.separator_combo.addItems([";", ",", "|", "\\t"])
        cols_layout.addWidget(self.separator_combo, 2, 1)
        cols_group.setLayout(cols_layout)
        layout.addWidget(cols_group)

        # CRS
        crs_group = QGroupBox("3. Systèmes de coordonnées")
        crs_layout = QGridLayout()
        crs_layout.addWidget(QLabel("Système source:"), 0, 0)
        self.batch_source_crs_combo = QComboBox()
        self.populate_crs_combo(self.batch_source_crs_combo)
        self.set_combo_by_name(self.batch_source_crs_combo, "🌍 WGS 84 (degrés)")
        self.batch_source_crs_combo.currentIndexChanged.connect(self.update_batch_formats)
        crs_layout.addWidget(self.batch_source_crs_combo, 0, 1)

        crs_layout.addWidget(QLabel("Format source:"), 1, 0)
        self.batch_format_combo = QComboBox()
        crs_layout.addWidget(self.batch_format_combo, 1, 1)

        crs_layout.addWidget(QLabel("Système cible:"), 2, 0)
        self.batch_target_crs_combo = QComboBox()
        self.populate_crs_combo(self.batch_target_crs_combo)
        self.set_combo_by_name(self.batch_target_crs_combo, "🇧🇫 BFTM (Burkina Faso) - OFFICIEL")
        self.batch_target_crs_combo.currentIndexChanged.connect(self.on_batch_target_crs_changed)
        crs_layout.addWidget(self.batch_target_crs_combo, 2, 1)

        # Champs personnalisés
        self.batch_custom_source_label = QLabel("Chaîne PROJ source:")
        self.batch_custom_source_edit = QLineEdit()
        self.batch_custom_source_edit.setPlaceholderText("ex: +proj=longlat +ellps=clrk80 +towgs84=-118,-14,218")
        self.batch_custom_source_label.setVisible(False)
        self.batch_custom_source_edit.setVisible(False)
        crs_layout.addWidget(self.batch_custom_source_label, 3, 0)
        crs_layout.addWidget(self.batch_custom_source_edit, 3, 1)

        self.batch_custom_target_label = QLabel("Chaîne PROJ cible:")
        self.batch_custom_target_edit = QLineEdit()
        self.batch_custom_target_edit.setPlaceholderText("ex: +proj=utm +zone=30 +ellps=GRS80 +units=m")
        self.batch_custom_target_label.setVisible(False)
        self.batch_custom_target_edit.setVisible(False)
        crs_layout.addWidget(self.batch_custom_target_label, 4, 0)
        crs_layout.addWidget(self.batch_custom_target_edit, 4, 1)

        crs_group.setLayout(crs_layout)
        layout.addWidget(crs_group)

        # Options
        options_group = QGroupBox("4. Options")
        options_layout = QVBoxLayout()
        self.batch_add_original = QCheckBox("Conserver les colonnes originales")
        self.batch_add_original.setChecked(True)
        options_layout.addWidget(self.batch_add_original)
        self.batch_skip_invalid = QCheckBox("Ignorer les lignes invalides")
        self.batch_skip_invalid.setChecked(True)
        options_layout.addWidget(self.batch_skip_invalid)
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        # Bouton
        self.process_btn = QPushButton("5. Lancer la conversion")
        self.process_btn.setMinimumHeight(40)
        self.process_btn.setStyleSheet("font-weight: bold; background-color: #4CAF50; color: white;")
        self.process_btn.clicked.connect(self.process_batch)
        self.process_btn.setEnabled(False)
        layout.addWidget(self.process_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        log_group = QGroupBox("Journal")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        self.batch_tab.setLayout(layout)
        self.update_batch_formats()

    def update_batch_formats(self):
        """Met à jour les formats batch selon le CRS source"""
        source_name = self.batch_source_crs_combo.currentText()

        geographic_keywords = [
            "WGS 84 (degrés)", "ETRS89 (degrés)", "NAD83 (degrés)",
            "SIRGAS 2000 (degrés)", "GDA2020 (degrés)", "GDA94 (degrés)",
            "CGCS2000 (degrés)", "NZGD2000 (degrés)", "JGD2011 (degrés)",
            "degrés", "4326"
        ]

        projected_keywords = [
            "UTM zone", "WGS 84 / UTM", "BFTM", "Lambert",
            "Mercator", "CH1903", "Gauss-Kruger", "British National Grid",
            "NAD83 / UTM", "GDA2020 / UTM", "GDA94 / UTM",
            "NZGD2000 / UTM", "NZTM", "Adindan (UTM", "Clarke 1880 (UTM",
            "Arc 1950 (UTM", "Arc 1960 (UTM)"
        ]

        is_geographic = any(kw in source_name for kw in geographic_keywords)
        is_projected = any(kw in source_name for kw in projected_keywords)

        current = self.batch_format_combo.currentText()
        self.batch_format_combo.clear()

        if is_geographic:
            self.batch_format_combo.addItems(["Degrés décimaux (DD)", "Degrés/Minutes/Secondes (DMS)"])
        elif is_projected:
            self.batch_format_combo.addItems(["Mètres (m)"])
        else:
            self.batch_format_combo.addItems(["Degrés décimaux (DD)", "Degrés/Minutes/Secondes (DMS)", "Mètres (m)"])

        idx = self.batch_format_combo.findText(current)
        if idx >= 0:
            self.batch_format_combo.setCurrentIndex(idx)

    def on_batch_target_crs_changed(self):
        """Gère le changement de CRS cible dans l'onglet batch"""
        is_custom = self.batch_target_crs_combo.currentText() == "--- Personnalisé (PROJ) ---"
        self.batch_custom_target_label.setVisible(is_custom)
        self.batch_custom_target_edit.setVisible(is_custom)

    def process_batch(self):
        file_path = self.source_file_path.text()
        if not file_path:
            QMessageBox.warning(self, "Attention", "Veuillez sélectionner un fichier CSV")
            return

        x_col = self.x_column_combo.currentText()
        y_col = self.y_column_combo.currentText()
        if not x_col or not y_col:
            QMessageBox.warning(self, "Attention", "Sélectionnez les colonnes X et Y")
            return

        source_crs = self.available_crs.get(self.batch_source_crs_combo.currentText())
        target_crs = self.available_crs.get(self.batch_target_crs_combo.currentText())

        sep = self.separator_combo.currentText().replace("\\t", "\t")

        config = {
            'x_column': x_col,
            'y_column': y_col,
            'separator': sep,
            'source_crs': source_crs,
            'target_crs': target_crs,
            'input_format': self.batch_format_combo.currentText(),
            'skip_invalid': self.batch_skip_invalid.isChecked(),
            'keep_original': self.batch_add_original.isChecked()
        }

        self.log_text.clear()
        self.log_text.append("🚀 CONVERSION BATCH")
        self.log_text.append(f"📁 Fichier: {os.path.basename(file_path)}")
        self.log_text.append(f"📌 Format: {self.batch_format_combo.currentText()}")
        self.log_text.append("")

        self.processor = BatchProcessor(file_path, config, self)
        self.processor.progress.connect(self.update_progress)
        self.processor.log.connect(self.append_log)
        self.processor.finished.connect(self.batch_finished)

        self.process_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.processor.start()

    # ==================== SÉLECTION INTERACTIVE ====================

    def setup_interactive_tab(self):
        layout = QVBoxLayout()

        info_label = QLabel("Cliquez sur la carte pour obtenir les coordonnées converties")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("font-weight: bold; color: blue;")
        layout.addWidget(info_label)

        # CRS cible
        crs_group = QGroupBox("Système cible")
        crs_layout = QHBoxLayout()
        self.interactive_crs_combo = QComboBox()
        self.populate_crs_combo(self.interactive_crs_combo)
        self.set_combo_by_name(self.interactive_crs_combo, "🇧🇫 BFTM (Burkina Faso) - OFFICIEL")
        self.interactive_crs_combo.currentIndexChanged.connect(self.update_interactive_formats)
        crs_layout.addWidget(self.interactive_crs_combo)
        crs_group.setLayout(crs_layout)
        layout.addWidget(crs_group)

        # Format d'affichage
        format_group = QGroupBox("Format d'affichage")
        format_layout = QHBoxLayout()
        self.interactive_format_combo = QComboBox()
        self.interactive_format_combo.currentIndexChanged.connect(self.update_interactive_placeholder)
        format_layout.addWidget(self.interactive_format_combo)
        format_group.setLayout(format_layout)
        layout.addWidget(format_group)

        # Boutons
        btn_layout = QHBoxLayout()
        self.activate_btn = QPushButton("🎯 Activer le sélecteur")
        self.activate_btn.clicked.connect(self.activate_point_picker)
        btn_layout.addWidget(self.activate_btn)

        self.deactivate_btn = QPushButton("❌ Désactiver")
        self.deactivate_btn.clicked.connect(self.deactivate_point_picker)
        self.deactivate_btn.setEnabled(False)
        btn_layout.addWidget(self.deactivate_btn)
        layout.addLayout(btn_layout)

        # Résultat
        result_group = QGroupBox("Coordonnées")
        result_layout = QGridLayout()

        result_layout.addWidget(QLabel("Source (carte):"), 0, 0)
        self.interactive_source = QLineEdit()
        self.interactive_source.setReadOnly(True)
        result_layout.addWidget(self.interactive_source, 0, 1)

        result_layout.addWidget(QLabel("CRS source:"), 1, 0)
        self.interactive_crs_source = QLabel("CRS du projet")
        result_layout.addWidget(self.interactive_crs_source, 1, 1)

        result_layout.addWidget(QLabel("Format cible:"), 2, 0)
        self.interactive_format_label = QLabel("")
        result_layout.addWidget(self.interactive_format_label, 2, 1)

        result_layout.addWidget(QLabel("Converti:"), 3, 0)
        self.interactive_result = QLineEdit()
        self.interactive_result.setReadOnly(True)
        result_layout.addWidget(self.interactive_result, 3, 1)

        result_layout.addWidget(QLabel("Statut:"), 4, 0)
        self.interactive_status = QLabel("")
        result_layout.addWidget(self.interactive_status, 4, 1)

        self.copy_interactive_btn = QPushButton("📋 Copier le résultat")
        self.copy_interactive_btn.clicked.connect(self.copy_interactive_results)
        result_layout.addWidget(self.copy_interactive_btn, 5, 0, 1, 2)

        result_group.setLayout(result_layout)
        layout.addWidget(result_group)

        self.interactive_tab.setLayout(layout)
        self.update_interactive_formats()

    def update_interactive_formats(self):
        """Met à jour les formats disponibles selon le CRS cible"""
        target_name = self.interactive_crs_combo.currentText()

        geographic_keywords = [
            "WGS 84 (degrés)", "ETRS89 (degrés)", "NAD83 (degrés)",
            "SIRGAS 2000 (degrés)", "GDA2020 (degrés)", "GDA94 (degrés)",
            "CGCS2000 (degrés)", "NZGD2000 (degrés)", "JGD2011 (degrés)",
            "degrés", "4326"
        ]

        projected_keywords = [
            "UTM zone", "WGS 84 / UTM", "BFTM", "Lambert",
            "Mercator", "CH1903", "Gauss-Kruger", "British National Grid",
            "NAD83 / UTM", "GDA2020 / UTM", "GDA94 / UTM",
            "NZGD2000 / UTM", "NZTM", "Adindan (UTM", "Clarke 1880 (UTM",
            "Arc 1950 (UTM", "Arc 1960 (UTM)"
        ]

        is_geographic = any(kw in target_name for kw in geographic_keywords)
        is_projected = any(kw in target_name for kw in projected_keywords)

        current = self.interactive_format_combo.currentText()
        self.interactive_format_combo.clear()

        if is_geographic:
            self.interactive_format_combo.addItems(["Degrés décimaux (DD)", "Degrés/Minutes/Secondes (DMS)"])
            self.interactive_format_label.setText("DD ou DMS")
        elif is_projected:
            self.interactive_format_combo.addItems(["Mètres (m)"])
            self.interactive_format_label.setText("Mètres (m)")
        else:
            self.interactive_format_combo.addItems(["Degrés décimaux (DD)", "Degrés/Minutes/Secondes (DMS)", "Mètres (m)"])
            self.interactive_format_label.setText("DD / DMS / mètres")

        idx = self.interactive_format_combo.findText(current)
        if idx >= 0:
            self.interactive_format_combo.setCurrentIndex(idx)

        self.update_interactive_placeholder()

    def update_interactive_placeholder(self):
        """Met à jour le placeholder pour l'affichage interactif"""
        fmt = self.interactive_format_combo.currentText()
        if fmt == "Degrés décimaux (DD)":
            self.interactive_format_label.setText("Format: degrés décimaux (ex: 12.5042)")
        elif fmt == "Degrés/Minutes/Secondes (DMS)":
            self.interactive_format_label.setText("Format: DMS (ex: 12°30'15\" N)")
        else:
            self.interactive_format_label.setText("Format: mètres (ex: 679246.00)")

    def activate_point_picker(self):
        """Active l'outil de sélection de points."""
        self.map_tool = QgsMapToolEmitPoint(self.iface.mapCanvas())
        self.map_tool.canvasClicked.connect(self.on_map_click)
        self.iface.mapCanvas().setMapTool(self.map_tool)

        self.rubber_band = QgsRubberBand(self.iface.mapCanvas(), QgsWkbTypes.PointGeometry)
        self.rubber_band.setColor(Qt.red)
        self.rubber_band.setWidth(5)

        self.activate_btn.setEnabled(False)
        self.deactivate_btn.setEnabled(True)
        self.iface.messageBar().pushMessage("Info", "Cliquez sur la carte", level=1)

    def deactivate_point_picker(self):
        """Désactive l'outil de sélection de points."""
        if self.map_tool:
            self.iface.mapCanvas().unsetMapTool(self.map_tool)
            self.map_tool = None
        if self.rubber_band:
            self.rubber_band.reset()
            self.rubber_band = None
        self.activate_btn.setEnabled(True)
        self.deactivate_btn.setEnabled(False)

    def on_map_click(self, point, button):
        """Gère le clic sur la carte avec gestion du format"""
        try:
            project_crs = QgsProject.instance().crs()
            target_text = self.interactive_crs_combo.currentText()
            target_crs = self.available_crs.get(target_text, self.bftm_crs)

            transform = QgsCoordinateTransform(project_crs, target_crs, QgsProject.instance().transformContext())
            transformed = transform.transform(point)

            self.interactive_source.setText(f"{point.x():.6f}, {point.y():.6f}")
            self.interactive_crs_source.setText(project_crs.description())

            fmt = self.interactive_format_combo.currentText()
            target_name = self.interactive_crs_combo.currentText()

            is_geographic = any(kw in target_name for kw in [
                "degrés", "4326", "WGS 84", "ETRS89", "NAD83",
                "GDA2020", "CGCS2000", "NZGD2000", "JGD2011"
            ])

            if fmt == "Mètres (m)":
                self.interactive_result.setText(f"{transformed.x():.3f}, {transformed.y():.3f}")
                self.interactive_status.setText("✓ Conversion réussie (mètres)")
                self.interactive_status.setStyleSheet("color: green;")

            elif fmt == "Degrés/Minutes/Secondes (DMS)":
                if is_geographic:
                    lon_dms = self.decimal_to_dms(transformed.x(), is_latitude=False)
                    lat_dms = self.decimal_to_dms(transformed.y(), is_latitude=True)
                    self.interactive_result.setText(f"{lon_dms}, {lat_dms}")
                    self.interactive_status.setText("✓ Conversion réussie (DMS)")
                    self.interactive_status.setStyleSheet("color: green;")
                else:
                    self.interactive_result.setText(f"{transformed.x():.3f}, {transformed.y():.3f}")
                    self.interactive_status.setText("⚠️ DMS: système projeté → mètres")
                    self.interactive_status.setStyleSheet("color: orange;")

            else:  # Degrés décimaux
                if is_geographic:
                    self.interactive_result.setText(f"{transformed.x():.6f}, {transformed.y():.6f}")
                    self.interactive_status.setText("✓ Conversion réussie (degrés)")
                    self.interactive_status.setStyleSheet("color: green;")
                else:
                    self.interactive_result.setText(f"{transformed.x():.3f}, {transformed.y():.3f}")
                    self.interactive_status.setText("⚠️ Degrés: système projeté → mètres")
                    self.interactive_status.setStyleSheet("color: orange;")

        except Exception as e:
            self.interactive_status.setText(f"Erreur: {str(e)[:50]}")
            self.interactive_status.setStyleSheet("color: red;")

    def copy_interactive_results(self):
        """Copie le résultat interactif dans le presse-papier"""
        if self.interactive_result.text():
            clipboard = QApplication.clipboard()
            clipboard.setText(self.interactive_result.text())
            self.iface.messageBar().pushMessage("Succès", "Résultat copié", level=1)

    # ==================== MÉTHODES UTILITAIRES ====================

    def populate_crs_combo(self, combo):
        combo.clear()
        for name in self.available_crs.keys():
            combo.addItem(name)

    def set_combo_by_name(self, combo, name):
        for i in range(combo.count()):
            if combo.itemText(i) == name:
                combo.setCurrentIndex(i)
                return

    def get_crs_from_combo(self, combo, custom_edit, is_source=True):
        selected = combo.currentText()
        if selected == "--- Personnalisé (PROJ) ---":
            custom_crs = QgsCoordinateReferenceSystem()
            proj_string = custom_edit.text()
            if not proj_string:
                return None
            custom_crs.createFromProj(proj_string)
            return custom_crs if custom_crs.isValid() else None
        return self.available_crs.get(selected)

    def get_source_crs(self):
        return self.get_crs_from_combo(self.source_crs_combo, self.custom_source_edit, True)

    def get_target_crs(self):
        return self.get_crs_from_combo(self.target_crs_combo, self.custom_target_edit, False)

    def swap_crs(self):
        src_text = self.source_crs_combo.currentText()
        tgt_text = self.target_crs_combo.currentText()
        self.source_crs_combo.setCurrentText(tgt_text)
        self.target_crs_combo.setCurrentText(src_text)
        self.update_source_formats()
        self.update_target_formats()
        self.iface.messageBar().pushMessage("Info", "CRS échangés", level=1)

    def copy_results(self):
        QApplication.clipboard().setText(f"{self.result_x.text()}\t{self.result_y.text()}")
        self.iface.messageBar().pushMessage("Succès", "Coordonnées copiées", level=1)

    def browse_source_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Sélectionner un CSV", "", "CSV (*.csv)")
        if path:
            self.source_file_path.setText(path)
            self.process_btn.setEnabled(True)
            sep = self.separator_combo.currentText().replace("\\t", "\t")
            try:
                with open(path, 'r', encoding='utf-8-sig') as f:
                    headers = next(csv.reader(f, delimiter=sep))
                self.x_column_combo.clear()
                self.y_column_combo.clear()
                self.x_column_combo.addItems(headers)
                self.y_column_combo.addItems(headers)
            except Exception as e:
                self.log_text.append(f"Erreur: {e}")

    def update_progress(self, val):
        self.progress_bar.setValue(val)

    def append_log(self, msg):
        self.log_text.append(msg)
        self.log_text.moveCursor(QTextCursor.End)

    def batch_finished(self, path):
        self.process_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        if path:
            self.log_text.append(f"\n✅ Terminé: {path}")

    def setup_about_tab(self):
        layout = QVBoxLayout()
        title = QLabel("📖 Aide - Universal XY Converter")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setHtml("""
        <h3>📌 Formats de coordonnées supportés</h3>
        <ul>
            <li><b>Degrés décimaux (DD)</b> : 12.5042, -1.5</li>
            <li><b>Degrés/Minutes/Secondes (DMS)</b> : 12°30'15" N ou 12°30'15"</li>
            <li><b>Mètres (m)</b> : 679246.00, 1360000.00</li>
        </ul>

        <h3>📁 Format CSV pour batch</h3>
        <pre>
id,longitude,latitude,ville
1,12°30'15" N ou S,1°30'0" W ou E
2,11°12'0" N ou S,4°18'0" W ou O </pre>

        <h3>🖱️ Sélection interactive</h3>
        <ul><li>Activez le sélecteur, cliquez sur la carte</li></ul>

        <h3>🇧🇫 BFTM</h3>
        <ul><li>bftm_proj = (
            "+proj=tmerc "
            "+lat_0=0 "
            "+lon_0=-1.5 "
            "+k=0.9996 "
            "+x_0=600000 "
            "+y_0=0 "
            "+ellps=GRS80 "
            "+towgs84=0,0,0,0,0,0,0 "
            "+units=m "
            "+no_defs"</li></ul>
        <h3>📞 Support</h3>
        <p>Email: jeanbaptiste.kibora@tic.gov.bf</p>
        <p>Téléphone: +22664412514 ou +22668690411</p>
        """)
        layout.addWidget(help_text)
        self.about_tab.setLayout(layout)
