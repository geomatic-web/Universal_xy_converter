import os
import csv
from qgis.PyQt.QtCore import Qt, QThread, pyqtSignal
from qgis.PyQt.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                                 QLineEdit, QPushButton, QComboBox, QGroupBox, 
                                 QGridLayout, QTabWidget, QFileDialog, 
                                 QTextEdit, QProgressBar, QMessageBox, 
                                 QCheckBox, QWidget, QApplication, QRadioButton,
                                 QButtonGroup)
from qgis.PyQt.QtGui import QTextCursor
from qgis.core import (QgsCoordinateReferenceSystem, QgsCoordinateTransform, 
                      QgsProject, QgsPointXY, QgsVectorLayer, QgsField,
                      QgsFeature, QgsWkbTypes, QgsCoordinateTransformContext)
from qgis.gui import QgsMapToolEmitPoint, QgsRubberBand
from qgis.PyQt.QtCore import QVariant

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
        self.setMinimumWidth(500)
        self.setMinimumHeight(650)
        
        # Définition des systèmes de coordonnées
        self.setup_crs_definitions()
        
        self.setup_ui()
    
    def setup_crs_definitions(self):
        """Définit tous les systèmes de coordonnées disponibles."""
        
        # BFTM (Burkina Faso) - Système officiel
        self.bftm_crs = QgsCoordinateReferenceSystem()
        bftm_proj = "+proj=tmerc +lat_0=0 +lon_0=-1.5 +x_0=600000 +y_0=0 +ellps=GRS80 +units=m +no_defs +k_0=0.9996"
        self.bftm_crs.createFromProj(bftm_proj)
        
        # Dictionnaire des CRS disponibles
        self.available_crs = {}
        
        # 1. BFTM en premier
        self.available_crs["🇧🇫 BFTM (Burkina Faso) - OFFICIEL"] = self.bftm_crs
        
        # 2. WGS84 et systèmes globaux
        self.add_crs_if_valid("🌍 WGS 84 (degrés)", "EPSG:4326")
        self.add_crs_if_valid("🌍 WGS 84 (Web Mercator)", "EPSG:3857")
        
        # 3. UTM Nord (zones 1 à 60)
        for zone in range(1, 61):
            self.add_crs_if_valid(f"📐 WGS 84 / UTM zone {zone}N", f"EPSG:326{zone:02d}")
        
        # 4. UTM Sud (zones 1 à 60)
        for zone in range(1, 61):
            self.add_crs_if_valid(f"📐 WGS 84 / UTM zone {zone}S", f"EPSG:327{zone:02d}")
        
        # 5. Systèmes africains
        african_crs = [
            ("🌍 Adindan (UTM 29N) - Afrique", "EPSG:20137"),
            ("🌍 Adindan (UTM 30N) - Afrique/Burkina", "EPSG:20138"),
            ("🌍 Adindan (UTM 31N) - Afrique", "EPSG:20139"),
            ("🌍 Clarke 1880 (UTM 30N) - Afrique Sud", "EPSG:2234"),
            ("🌍 Arc 1950 (UTM 35S) - Afrique Sud", "EPSG:21035"),
            ("🌍 Arc 1950 (UTM 36S) - Afrique Sud", "EPSG:21036"),
            ("🌍 Arc 1950 (UTM 37S) - Afrique Sud", "EPSG:21037"),
            ("🌍 Arc 1960 (UTM 36N) - Afrique Est", "EPSG:21096"),
            ("🌍 Arc 1960 (UTM 37N) - Afrique Est", "EPSG:21097"),
        ]
        for name, epsg in african_crs:
            self.add_crs_if_valid(name, epsg)
        
        # 6. Systèmes européens
        european_crs = [
            ("🇪🇺 ETRS89 (degrés) - Europe", "EPSG:4258"),
            ("🇪🇺 ETRS89 / UTM zone 31N - Europe", "EPSG:25831"),
            ("🇪🇺 ETRS89 / UTM zone 32N - Europe", "EPSG:25832"),
            ("🇪🇺 ETRS89 / UTM zone 33N - Europe", "EPSG:25833"),
            ("🇪🇺 ETRS89 / UTM zone 34N - Europe", "EPSG:25834"),
            ("🇪🇺 ETRS89 / UTM zone 35N - Europe", "EPSG:25835"),
            ("🇪🇺 ETRS89 / UTM zone 36N - Europe", "EPSG:25836"),
            ("🇪🇺 ETRS89 / UTM zone 37N - Europe", "EPSG:25837"),
            ("🇫🇷 RGF93 / Lambert-93 - France", "EPSG:2154"),
            ("🇫🇷 RGF93 / UTM zone 31N - France", "EPSG:2159"),
            ("🇫🇷 RGF93 / UTM zone 32N - France", "EPSG:2160"),
            ("🇩🇪 DHDN / Gauss-Kruger 3 - Allemagne", "EPSG:31467"),
            ("🇩🇪 ETRS89 / UTM zone 32N - Allemagne", "EPSG:25832"),
            ("🇬🇧 OSGB 1936 / British National Grid - UK", "EPSG:27700"),
            ("🇪🇸 ED50 / UTM zone 30N - Espagne", "EPSG:23030"),
            ("🇪🇸 ED50 / UTM zone 31N - Espagne", "EPSG:23031"),
            ("🇮🇹 ETRS89 / UTM zone 32N - Italie", "EPSG:25832"),
            ("🇮🇹 ETRS89 / UTM zone 33N - Italie", "EPSG:25833"),
        ]
        for name, epsg in european_crs:
            self.add_crs_if_valid(name, epsg)
        
        # 7. Systèmes américains
        american_crs = [
            ("🇺🇸 NAD83 (degrés) - Amérique Nord", "EPSG:4269"),
            ("🇺🇸 NAD83 / UTM zone 10N - USA", "EPSG:26910"),
            ("🇺🇸 NAD83 / UTM zone 11N - USA", "EPSG:26911"),
            ("🇺🇸 NAD83 / UTM zone 12N - USA", "EPSG:26912"),
            ("🇺🇸 NAD83 / UTM zone 13N - USA", "EPSG:26913"),
            ("🇺🇸 NAD83 / UTM zone 14N - USA", "EPSG:26914"),
            ("🇺🇸 NAD83 / UTM zone 15N - USA", "EPSG:26915"),
            ("🇺🇸 NAD83 / UTM zone 16N - USA", "EPSG:26916"),
            ("🇺🇸 NAD83 / UTM zone 17N - USA", "EPSG:26917"),
            ("🇺🇸 NAD83 / UTM zone 18N - USA", "EPSG:26918"),
            ("🇺🇸 NAD83 / UTM zone 19N - USA", "EPSG:26919"),
            ("🇺🇸 NAD83 / UTM zone 20N - USA", "EPSG:26920"),
            ("🇺🇸 NAD83 / UTM zone 21N - USA", "EPSG:26921"),
            ("🇺🇸 NAD83 / UTM zone 22N - USA", "EPSG:26922"),
            ("🇺🇸 NAD83 / UTM zone 23N - USA", "EPSG:26923"),
            ("🇨🇦 NAD83 / UTM zone 10N - Canada", "EPSG:26910"),
            ("🇨🇦 NAD83 / UTM zone 11N - Canada", "EPSG:26911"),
            ("🇨🇦 NAD83 / UTM zone 12N - Canada", "EPSG:26912"),
            ("🇨🇦 NAD83 / UTM zone 13N - Canada", "EPSG:26913"),
            ("🇨🇦 NAD83 / UTM zone 14N - Canada", "EPSG:26914"),
            ("🇨🇦 NAD83 / UTM zone 15N - Canada", "EPSG:26915"),
            ("🇨🇦 NAD83 / UTM zone 16N - Canada", "EPSG:26916"),
            ("🇨🇦 NAD83 / UTM zone 17N - Canada", "EPSG:26917"),
            ("🇧🇷 SIRGAS 2000 (degrés) - Brésil", "EPSG:4674"),
            ("🇧🇷 SIRGAS 2000 / UTM zone 22S - Brésil", "EPSG:31982"),
            ("🇧🇷 SIRGAS 2000 / UTM zone 23S - Brésil", "EPSG:31983"),
            ("🇧🇷 SIRGAS 2000 / UTM zone 24S - Brésil", "EPSG:31984"),
            ("🇲🇽 NAD83 / UTM zone 13N - Mexique", "EPSG:26913"),
            ("🇲🇽 NAD83 / UTM zone 14N - Mexique", "EPSG:26914"),
        ]
        for name, epsg in american_crs:
            self.add_crs_if_valid(name, epsg)
        
        # 8. Systèmes asiatiques
        asian_crs = [
            ("🇨🇳 CGCS2000 (degrés) - Chine", "EPSG:4490"),
            ("🇨🇳 CGCS2000 / UTM zone 50N - Chine", "EPSG:4547"),
            ("🇨🇳 CGCS2000 / UTM zone 51N - Chine", "EPSG:4548"),
            ("🇮🇳 WGS 84 / UTM zone 43N - Inde", "EPSG:32643"),
            ("🇮🇳 WGS 84 / UTM zone 44N - Inde", "EPSG:32644"),
            ("🇮🇳 WGS 84 / UTM zone 45N - Inde", "EPSG:32645"),
            ("🇮🇳 WGS 84 / UTM zone 46N - Inde", "EPSG:32646"),
            ("🇯🇵 JGD2011 (degrés) - Japon", "EPSG:6668"),
            ("🇯🇵 JGD2011 / UTM zone 54N - Japon", "EPSG:6669"),
            ("🇯🇵 JGD2011 / UTM zone 55N - Japon", "EPSG:6670"),
            ("🇮🇩 WGS 84 / UTM zone 48S - Indonésie", "EPSG:32748"),
            ("🇮🇩 WGS 84 / UTM zone 49S - Indonésie", "EPSG:32749"),
            ("🇮🇩 WGS 84 / UTM zone 50S - Indonésie", "EPSG:32750"),
            ("🇻🇳 WGS 84 / UTM zone 48N - Vietnam", "EPSG:32648"),
            ("🇻🇳 WGS 84 / UTM zone 49N - Vietnam", "EPSG:32649"),
        ]
        for name, epsg in asian_crs:
            self.add_crs_if_valid(name, epsg)
        
        # 9. Systèmes océaniens
        oceanian_crs = [
            ("🇦🇺 GDA2020 (degrés) - Australie", "EPSG:7844"),
            ("🇦🇺 GDA2020 / UTM zone 50S - Australie", "EPSG:7850"),
            ("🇦🇺 GDA2020 / UTM zone 51S - Australie", "EPSG:7851"),
            ("🇦🇺 GDA2020 / UTM zone 52S - Australie", "EPSG:7852"),
            ("🇦🇺 GDA2020 / UTM zone 53S - Australie", "EPSG:7853"),
            ("🇦🇺 GDA2020 / UTM zone 54S - Australie", "EPSG:7854"),
            ("🇦🇺 GDA2020 / UTM zone 55S - Australie", "EPSG:7855"),
            ("🇦🇺 GDA94 (degrés) - Australie", "EPSG:4283"),
            ("🇦🇺 GDA94 / UTM zone 50S - Australie", "EPSG:28350"),
            ("🇦🇺 GDA94 / UTM zone 51S - Australie", "EPSG:28351"),
            ("🇦🇺 GDA94 / UTM zone 52S - Australie", "EPSG:28352"),
            ("🇦🇺 GDA94 / UTM zone 53S - Australie", "EPSG:28353"),
            ("🇦🇺 GDA94 / UTM zone 54S - Australie", "EPSG:28354"),
            ("🇦🇺 GDA94 / UTM zone 55S - Australie", "EPSG:28355"),
            ("🇳🇿 NZGD2000 (degrés) - Nouvelle Zélande", "EPSG:4167"),
            ("🇳🇿 NZGD2000 / UTM zone 59S - NZ", "EPSG:32759"),
            ("🇳🇿 NZGD2000 / UTM zone 60S - NZ", "EPSG:32760"),
            ("🇳🇿 NZGD2000 / NZTM - Nouvelle Zélande", "EPSG:2193"),
        ]
        for name, epsg in oceanian_crs:
            self.add_crs_if_valid(name, epsg)
        
        # 10. Projections spécifiques
        specific_crs = [
            ("🗺️ Lambert 93 - France", "EPSG:2154"),
            ("🗺️ Swiss CH1903+ / LV95 - Suisse", "EPSG:2056"),
            ("🗺️ Swiss CH1903 / LV03 - Suisse", "EPSG:21781"),
            ("🗺️ Belgian Lambert 2008 - Belgique", "EPSG:3812"),
            ("🗺️ Belgian Lambert 1972 - Belgique", "EPSG:31370"),
            ("🗺️ Dutch RD New - Pays-Bas", "EPSG:28992"),
            ("🗺️ Spanish UTM 30N - Espagne", "EPSG:25830"),
            ("🗺️ Spanish UTM 31N - Espagne", "EPSG:25831"),
        ]
        for name, epsg in specific_crs:
            self.add_crs_if_valid(name, epsg)
        
        # 11. CRS personnalisé
        self.available_crs["--- Personnalisé (PROJ) ---"] = None
    
    def add_crs_if_valid(self, name, epsg_code):
        """Ajoute un CRS au dictionnaire s'il est valide."""
        try:
            crs = QgsCoordinateReferenceSystem(epsg_code)
            if crs.isValid():
                self.available_crs[name] = crs
        except:
            pass
    
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Création des onglets
        self.tabs = QTabWidget()
        
        # Onglet 1: Conversion simple
        self.simple_tab = QWidget()
        self.setup_simple_tab()
        self.tabs.addTab(self.simple_tab, "Conversion simple")
        
        # Onglet 2: Traitement batch
        self.batch_tab = QWidget()
        self.setup_batch_tab()
        self.tabs.addTab(self.batch_tab, "Traitement batch")
        
        # Onglet 3: Sélection interactive
        self.interactive_tab = QWidget()
        self.setup_interactive_tab()
        self.tabs.addTab(self.interactive_tab, "Sélection interactive")
        
        # Onglet 4: Aide rapide
        self.about_tab = QWidget()
        self.setup_about_tab()
        self.tabs.addTab(self.about_tab, "📖 Aide")
        
        layout.addWidget(self.tabs)
        self.setLayout(layout)
    
    def setup_simple_tab(self):
        """Configure l'onglet de conversion simple avec direction."""
        layout = QVBoxLayout()
        
        # Direction de conversion
        direction_group = QGroupBox("Direction de conversion")
        direction_layout = QHBoxLayout()
        
        self.direction_group = QButtonGroup()
        self.from_bftm_radio = QRadioButton("Depuis BFTM vers autre système")
        self.to_bftm_radio = QRadioButton("Vers BFTM depuis autre système")
        self.between_radio = QRadioButton("Entre deux systèmes")
        
        self.from_bftm_radio.setChecked(False)
        self.to_bftm_radio.setChecked(True)
        self.between_radio.setChecked(False)
        
        self.from_bftm_radio.toggled.connect(self.on_direction_changed)
        self.to_bftm_radio.toggled.connect(self.on_direction_changed)
        self.between_radio.toggled.connect(self.on_direction_changed)
        
        direction_layout.addWidget(self.to_bftm_radio)
        direction_layout.addWidget(self.from_bftm_radio)
        direction_layout.addWidget(self.between_radio)
        
        direction_group.setLayout(direction_layout)
        layout.addWidget(direction_group)
        
        # --- Sélection du CRS source ---
        source_group = QGroupBox("Système source")
        source_layout = QGridLayout()
        
        source_layout.addWidget(QLabel("CRS source:"), 0, 0)
        self.source_crs_combo = QComboBox()
        self.populate_crs_combo(self.source_crs_combo)
        self.source_crs_combo.currentIndexChanged.connect(self.on_source_crs_changed)
        source_layout.addWidget(self.source_crs_combo, 0, 1)
        
        # Champ pour PROJ personnalisé (source)
        self.custom_source_label = QLabel("Chaîne PROJ source:")
        self.custom_source_edit = QLineEdit()
        self.custom_source_edit.setPlaceholderText("ex: +proj=longlat +ellps=clrk80 +towgs84=-118,-14,218")
        self.custom_source_label.setVisible(False)
        self.custom_source_edit.setVisible(False)
        source_layout.addWidget(self.custom_source_label, 1, 0)
        source_layout.addWidget(self.custom_source_edit, 1, 1)
        
        source_group.setLayout(source_layout)
        layout.addWidget(source_group)
        
        # --- Sélection du CRS cible ---
        target_group = QGroupBox("Système cible")
        target_layout = QGridLayout()
        
        target_layout.addWidget(QLabel("CRS cible:"), 0, 0)
        self.target_crs_combo = QComboBox()
        self.populate_crs_combo(self.target_crs_combo)
        self.target_crs_combo.currentIndexChanged.connect(self.on_target_crs_changed)
        target_layout.addWidget(self.target_crs_combo, 0, 1)
        
        # Champ pour PROJ personnalisé (cible)
        self.custom_target_label = QLabel("Chaîne PROJ cible:")
        self.custom_target_edit = QLineEdit()
        self.custom_target_edit.setPlaceholderText("ex: +proj=utm +zone=30 +ellps=GRS80 +units=m")
        self.custom_target_label.setVisible(False)
        self.custom_target_edit.setVisible(False)
        target_layout.addWidget(self.custom_target_label, 1, 0)
        target_layout.addWidget(self.custom_target_edit, 1, 1)
        
        target_group.setLayout(target_layout)
        layout.addWidget(target_group)
        
        # Champs de coordonnées
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
        
        # Bouton de conversion
        self.convert_btn = QPushButton("Convertir →")
        self.convert_btn.clicked.connect(self.convert_coordinates)
        self.convert_btn.setMinimumHeight(40)
        layout.addWidget(self.convert_btn)
        
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
        
        # Bouton copier
        self.copy_btn = QPushButton("Copier les résultats")
        self.copy_btn.clicked.connect(self.copy_results)
        result_layout.addWidget(self.copy_btn, 3, 0, 1, 2)
        
        # Bouton échanger
        self.swap_btn = QPushButton("⟷ Échanger source/cible")
        self.swap_btn.clicked.connect(self.swap_crs)
        result_layout.addWidget(self.swap_btn, 4, 0, 1, 2)
        
        result_group.setLayout(result_layout)
        layout.addWidget(result_group)
        
        self.simple_tab.setLayout(layout)
        
        # Initialiser l'affichage
        self.on_direction_changed()
    
    def populate_crs_combo(self, combo):
        """Remplit un combobox avec tous les CRS disponibles."""
        combo.clear()
        for name in self.available_crs.keys():
            combo.addItem(name)
    
    def on_direction_changed(self):
        """Gère le changement de direction de conversion."""
        if self.to_bftm_radio.isChecked():
            self.set_combo_by_name(self.source_crs_combo, "🌍 WGS 84 (degrés)")
            self.set_combo_by_name(self.target_crs_combo, "🇧🇫 BFTM (Burkina Faso) - OFFICIEL")
        elif self.from_bftm_radio.isChecked():
            self.set_combo_by_name(self.source_crs_combo, "🇧🇫 BFTM (Burkina Faso) - OFFICIEL")
            self.set_combo_by_name(self.target_crs_combo, "🌍 WGS 84 (degrés)")
        else:
            if self.source_crs_combo.currentText().startswith("🇧🇫 BFTM"):
                self.set_combo_by_name(self.source_crs_combo, "🌍 WGS 84 (degrés)")
            if self.target_crs_combo.currentText().startswith("🇧🇫 BFTM"):
                self.set_combo_by_name(self.target_crs_combo, "📐 WGS 84 / UTM zone 30N")
    
    def set_combo_by_name(self, combo, name):
        """Sélectionne un item dans le combobox par son nom."""
        for i in range(combo.count()):
            if combo.itemText(i) == name:
                combo.setCurrentIndex(i)
                return
        for i in range(combo.count()):
            if name in combo.itemText(i):
                combo.setCurrentIndex(i)
                return
    
    def on_source_crs_changed(self):
        """Gère le changement de CRS source."""
        is_custom = self.source_crs_combo.currentText() == "--- Personnalisé (PROJ) ---"
        self.custom_source_label.setVisible(is_custom)
        self.custom_source_edit.setVisible(is_custom)
    
    def on_target_crs_changed(self):
        """Gère le changement de CRS cible."""
        is_custom = self.target_crs_combo.currentText() == "--- Personnalisé (PROJ) ---"
        self.custom_target_label.setVisible(is_custom)
        self.custom_target_edit.setVisible(is_custom)
    
    def get_crs_from_combo(self, combo, custom_edit, is_source=True):
        """Récupère le CRS à partir du combobox."""
        selected = combo.currentText()
        
        if selected == "--- Personnalisé (PROJ) ---":
            custom_crs = QgsCoordinateReferenceSystem()
            proj_string = custom_edit.text()
            if not proj_string:
                return None
            custom_crs.createFromProj(proj_string)
            if custom_crs.isValid():
                return custom_crs
            else:
                msg = "CRS personnalisé invalide"
                if is_source:
                    self.iface.messageBar().pushMessage("Erreur", msg, level=2)
                return None
        else:
            crs = self.available_crs.get(selected)
            if crs is None:
                msg = f"CRS {selected} non disponible"
                if is_source:
                    self.iface.messageBar().pushMessage("Erreur", msg, level=2)
                return None
            return crs
    
    def get_source_crs(self):
        """Récupère le CRS source."""
        return self.get_crs_from_combo(self.source_crs_combo, self.custom_source_edit, is_source=True)
    
    def get_target_crs(self):
        """Récupère le CRS cible."""
        return self.get_crs_from_combo(self.target_crs_combo, self.custom_target_edit, is_source=False)
    
    def swap_crs(self):
        """Échange les CRS source et cible."""
        source_text = self.source_crs_combo.currentText()
        target_text = self.target_crs_combo.currentText()
        
        self.source_crs_combo.setCurrentText(target_text)
        self.target_crs_combo.setCurrentText(source_text)
        
        source_custom = self.custom_source_edit.text()
        target_custom = self.custom_target_edit.text()
        self.custom_source_edit.setText(target_custom)
        self.custom_target_edit.setText(source_custom)
        
        self.iface.messageBar().pushMessage("Info", "CRS échangés", level=1)
    
    def convert_coordinates(self):
        """Effectue la conversion entre les deux CRS."""
        try:
            if not self.source_x.text() or not self.source_y.text():
                self.iface.messageBar().pushMessage("Erreur", "Veuillez entrer des coordonnées", level=2)
                return
            
            x = float(self.source_x.text())
            y = float(self.source_y.text())
            
            source_crs = self.get_source_crs()
            target_crs = self.get_target_crs()
            
            if source_crs is None or not source_crs.isValid():
                self.conversion_status.setText("✗ CRS source invalide")
                self.conversion_status.setStyleSheet("color: red;")
                return
            
            if target_crs is None or not target_crs.isValid():
                self.conversion_status.setText("✗ CRS cible invalide")
                self.conversion_status.setStyleSheet("color: red;")
                return
            
            transform_context = QgsProject.instance().transformContext()
            transform = QgsCoordinateTransform(source_crs, target_crs, transform_context)
            source_point = QgsPointXY(x, y)
            transformed_point = transform.transform(source_point)
            
            self.result_x.setText(f"{transformed_point.x():.6f}")
            self.result_y.setText(f"{transformed_point.y():.6f}")
            
            self.conversion_status.setText("✓ Conversion réussie")
            self.conversion_status.setStyleSheet("color: green;")
            
            source_name = self.source_crs_combo.currentText()
            target_name = self.target_crs_combo.currentText()
            self.iface.messageBar().pushMessage("Succès", f"Conversion de {source_name} vers {target_name} réussie", level=1)
            
        except ValueError as e:
            self.conversion_status.setText(f"✗ Coordonnées invalides: {str(e)}")
            self.conversion_status.setStyleSheet("color: red;")
        except Exception as e:
            self.conversion_status.setText(f"✗ Conversion échouée: {str(e)}")
            self.conversion_status.setStyleSheet("color: red;")
            self.iface.messageBar().pushMessage("Erreur", str(e), level=2)
    
    def copy_results(self):
        """Copie les résultats dans le presse-papier."""
        clipboard = QApplication.clipboard()
        clipboard.setText(f"{self.result_x.text()}\t{self.result_y.text()}")
        self.iface.messageBar().pushMessage("Succès", "Coordonnées copiées", level=1)
    
    def setup_batch_tab(self):
        """Configure l'onglet de traitement batch avec sélection libre des CRS."""
        layout = QVBoxLayout()
        
        # Sélection du fichier source
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
        
        # Configuration des colonnes
        cols_group = QGroupBox("2. Configuration des colonnes du fichier CSV")
        cols_layout = QGridLayout()
        
        cols_layout.addWidget(QLabel("Colonne X / Longitude / Est:"), 0, 0)
        self.x_column_combo = QComboBox()
        cols_layout.addWidget(self.x_column_combo, 0, 1)
        
        cols_layout.addWidget(QLabel("Colonne Y / Latitude / Nord:"), 1, 0)
        self.y_column_combo = QComboBox()
        cols_layout.addWidget(self.y_column_combo, 1, 1)
        
        cols_layout.addWidget(QLabel("Séparateur CSV:"), 2, 0)
        self.separator_combo = QComboBox()
        self.separator_combo.addItems([";", ",", "|", "\\t"])
        cols_layout.addWidget(self.separator_combo, 2, 1)
        
        cols_group.setLayout(cols_layout)
        layout.addWidget(cols_group)
        
        # Sélection des CRS
        crs_group = QGroupBox("3. Systèmes de coordonnées")
        crs_layout = QGridLayout()
        
        crs_layout.addWidget(QLabel("Système source (celui des coordonnées dans le fichier):"), 0, 0, 1, 2)
        self.batch_source_crs_combo = QComboBox()
        self.populate_crs_combo(self.batch_source_crs_combo)
        self.set_combo_by_name(self.batch_source_crs_combo, "🌍 WGS 84 (degrés)")
        crs_layout.addWidget(self.batch_source_crs_combo, 1, 0, 1, 2)
        
        self.batch_custom_source_label = QLabel("Chaîne PROJ personnalisée (source):")
        self.batch_custom_source_edit = QLineEdit()
        self.batch_custom_source_edit.setPlaceholderText("ex: +proj=longlat +ellps=clrk80 +towgs84=-118,-14,218")
        self.batch_custom_source_label.setVisible(False)
        self.batch_custom_source_edit.setVisible(False)
        crs_layout.addWidget(self.batch_custom_source_label, 2, 0)
        crs_layout.addWidget(self.batch_custom_source_edit, 2, 1)
        
        crs_layout.addWidget(QLabel("Système cible (celui souhaité en sortie):"), 3, 0, 1, 2)
        self.batch_target_crs_combo = QComboBox()
        self.populate_crs_combo(self.batch_target_crs_combo)
        self.set_combo_by_name(self.batch_target_crs_combo, "🇧🇫 BFTM (Burkina Faso) - OFFICIEL")
        crs_layout.addWidget(self.batch_target_crs_combo, 4, 0, 1, 2)
        
        self.batch_custom_target_label = QLabel("Chaîne PROJ personnalisée (cible):")
        self.batch_custom_target_edit = QLineEdit()
        self.batch_custom_target_edit.setPlaceholderText("ex: +proj=utm +zone=30 +ellps=GRS80 +units=m")
        self.batch_custom_target_label.setVisible(False)
        self.batch_custom_target_edit.setVisible(False)
        crs_layout.addWidget(self.batch_custom_target_label, 5, 0)
        crs_layout.addWidget(self.batch_custom_target_edit, 5, 1)
        
        self.batch_source_crs_combo.currentIndexChanged.connect(self.on_batch_source_crs_changed)
        self.batch_target_crs_combo.currentIndexChanged.connect(self.on_batch_target_crs_changed)
        
        crs_group.setLayout(crs_layout)
        layout.addWidget(crs_group)
        
        # Options
        options_group = QGroupBox("4. Options")
        options_layout = QVBoxLayout()
        
        self.batch_add_original = QCheckBox("Conserver les colonnes originales dans le fichier de sortie")
        self.batch_add_original.setChecked(True)
        options_layout.addWidget(self.batch_add_original)
        
        self.batch_add_validation = QCheckBox("Ajouter une colonne de validation")
        self.batch_add_validation.setChecked(False)
        options_layout.addWidget(self.batch_add_validation)
        
        self.batch_skip_invalid = QCheckBox("Ignorer les lignes avec des coordonnées invalides")
        self.batch_skip_invalid.setChecked(True)
        options_layout.addWidget(self.batch_skip_invalid)
        
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)
        
        # Bouton de traitement
        self.process_btn = QPushButton("5. Lancer la conversion du fichier")
        self.process_btn.setMinimumHeight(40)
        self.process_btn.setStyleSheet("font-weight: bold; background-color: #4CAF50; color: white;")
        self.process_btn.clicked.connect(self.process_batch)
        self.process_btn.setEnabled(False)
        layout.addWidget(self.process_btn)
        
        # Barre de progression
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Journal
        log_group = QGroupBox("Journal de conversion")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFontFamily("Courier New")
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)
        
        self.batch_tab.setLayout(layout)

    def on_batch_source_crs_changed(self):
        """Affiche/masque le champ PROJ personnalisé pour la source."""
        is_custom = self.batch_source_crs_combo.currentText() == "--- Personnalisé (PROJ) ---"
        self.batch_custom_source_label.setVisible(is_custom)
        self.batch_custom_source_edit.setVisible(is_custom)

    def on_batch_target_crs_changed(self):
        """Affiche/masque le champ PROJ personnalisé pour la cible."""
        is_custom = self.batch_target_crs_combo.currentText() == "--- Personnalisé (PROJ) ---"
        self.batch_custom_target_label.setVisible(is_custom)
        self.batch_custom_target_edit.setVisible(is_custom)

    def get_batch_source_crs(self):
        """Récupère le CRS source pour le batch."""
        selected = self.batch_source_crs_combo.currentText()
        
        if selected == "--- Personnalisé (PROJ) ---":
            custom_crs = QgsCoordinateReferenceSystem()
            proj_string = self.batch_custom_source_edit.text()
            if not proj_string:
                return None
            custom_crs.createFromProj(proj_string)
            if custom_crs.isValid():
                return custom_crs
            else:
                self.iface.messageBar().pushMessage("Erreur", "CRS source personnalisé invalide", level=2)
                return None
        else:
            return self.available_crs.get(selected)

    def get_batch_target_crs(self):
        """Récupère le CRS cible pour le batch."""
        selected = self.batch_target_crs_combo.currentText()
        
        if selected == "--- Personnalisé (PROJ) ---":
            custom_crs = QgsCoordinateReferenceSystem()
            proj_string = self.batch_custom_target_edit.text()
            if not proj_string:
                return None
            custom_crs.createFromProj(proj_string)
            if custom_crs.isValid():
                return custom_crs
            else:
                self.iface.messageBar().pushMessage("Erreur", "CRS cible personnalisé invalide", level=2)
                return None
        else:
            return self.available_crs.get(selected)

    def browse_source_file(self):
        """Ouvre un dialogue pour sélectionner le fichier source."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Sélectionner un fichier CSV", "", 
            "Fichiers CSV (*.csv);;Tous les fichiers (*.*)"
        )
        if file_path:
            self.source_file_path.setText(file_path)
            self.process_btn.setEnabled(True)
            self.load_csv_columns(file_path)

    def load_csv_columns(self, file_path):
        """Charge les colonnes d'un fichier CSV."""
        try:
            sep = self.separator_combo.currentText()
            if sep == "\\t":
                sep = "\t"
            
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f, delimiter=sep)
                headers = next(reader)
                
            self.x_column_combo.clear()
            self.y_column_combo.clear()
            self.x_column_combo.addItems(headers)
            self.y_column_combo.addItems(headers)
            
            self.log_text.append(f"✅ Fichier chargé: {os.path.basename(file_path)}")
            self.log_text.append(f"📊 Colonnes trouvées: {', '.join(headers)}")
            
        except Exception as e:
            self.log_text.append(f"❌ Erreur: {str(e)}")

    def process_batch(self):
        """Traite le fichier batch avec les CRS sélectionnés librement."""
        file_path = self.source_file_path.text()
        if not file_path:
            QMessageBox.warning(self, "Attention", "Veuillez sélectionner un fichier CSV")
            return
        
        x_col = self.x_column_combo.currentText()
        y_col = self.y_column_combo.currentText()
        if not x_col or not y_col:
            QMessageBox.warning(self, "Attention", "Veuillez sélectionner les colonnes X et Y")
            return
        
        source_crs = self.get_batch_source_crs()
        target_crs = self.get_batch_target_crs()
        
        if source_crs is None:
            QMessageBox.warning(self, "Attention", "CRS source invalide")
            return
        
        if target_crs is None:
            QMessageBox.warning(self, "Attention", "CRS cible invalide")
            return
        
        sep = self.separator_combo.currentText()
        if sep == "\\t":
            sep = "\t"
        
        is_target_bftm = self.batch_target_crs_combo.currentText().startswith("🇧🇫 BFTM")
        
        config = {
            'x_column': x_col,
            'y_column': y_col,
            'separator': sep,
            'source_crs': source_crs,
            'target_crs': target_crs,
            'add_validation': self.batch_add_validation.isChecked() and is_target_bftm,
            'skip_invalid': self.batch_skip_invalid.isChecked(),
            'keep_original': self.batch_add_original.isChecked()
        }
        
        self.log_text.clear()
        self.log_text.append("🚀 DÉBUT DE LA CONVERSION BATCH")
        self.log_text.append(f"📁 Fichier: {os.path.basename(file_path)}")
        self.log_text.append(f"📌 Colonne X: {x_col}")
        self.log_text.append(f"📌 Colonne Y: {y_col}")
        self.log_text.append(f"🔄 Conversion: {self.batch_source_crs_combo.currentText()} → {self.batch_target_crs_combo.currentText()}")
        self.log_text.append("")
        
        self.processor = BatchProcessor(file_path, config)
        self.processor.progress.connect(self.update_progress)
        self.processor.log.connect(self.append_log)
        self.processor.finished.connect(self.batch_finished)
        
        self.process_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.processor.start()

    def update_progress(self, value):
        """Met à jour la barre de progression."""
        self.progress_bar.setValue(value)

    def append_log(self, message):
        """Ajoute un message au journal."""
        self.log_text.append(message)
        self.log_text.moveCursor(QTextCursor.End)

    def batch_finished(self, output_path):
        """Gère la fin du traitement batch."""
        self.process_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if output_path:
            self.log_text.append("")
            self.log_text.append("✅ TRAITEMENT TERMINÉ AVEC SUCCÈS")
            self.log_text.append(f"💾 Fichier sauvegardé: {output_path}")
            QMessageBox.information(
                self, "Succès", 
                f"Conversion terminée avec succès!\n\n"
                f"Fichier converti: {os.path.basename(output_path)}\n"
                f"Emplacement: {output_path}"
            )
        else:
            self.log_text.append("")
            self.log_text.append("❌ TRAITEMENT ÉCHOUÉ")
            QMessageBox.critical(self, "Erreur", "Le traitement a échoué. Vérifiez le journal pour plus de détails.")
    
    def setup_interactive_tab(self):
        """Configure l'onglet de sélection interactive avec choix du CRS cible."""
        layout = QVBoxLayout()
        
        info_label = QLabel("Cliquez sur un point de la carte pour obtenir ses coordonnées dans le système choisi")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("font-weight: bold; color: blue;")
        layout.addWidget(info_label)
        
        crs_group = QGroupBox("Système cible pour l'affichage")
        crs_layout = QHBoxLayout()
        
        self.interactive_crs_combo = QComboBox()
        self.populate_crs_combo(self.interactive_crs_combo)
        self.set_combo_by_name(self.interactive_crs_combo, "🇧🇫 BFTM (Burkina Faso) - OFFICIEL")
        crs_layout.addWidget(self.interactive_crs_combo)
        
        crs_group.setLayout(crs_layout)
        layout.addWidget(crs_group)
        
        btn_layout = QHBoxLayout()
        self.activate_picker_btn = QPushButton("Activer le sélecteur")
        self.activate_picker_btn.clicked.connect(self.activate_point_picker)
        btn_layout.addWidget(self.activate_picker_btn)
        
        self.deactivate_picker_btn = QPushButton("Désactiver")
        self.deactivate_picker_btn.clicked.connect(self.deactivate_point_picker)
        self.deactivate_picker_btn.setEnabled(False)
        btn_layout.addWidget(self.deactivate_picker_btn)
        layout.addLayout(btn_layout)
        
        result_group = QGroupBox("Coordonnées")
        result_layout = QGridLayout()
        
        result_layout.addWidget(QLabel("Source (carte):"), 0, 0)
        self.interactive_source = QLineEdit()
        self.interactive_source.setReadOnly(True)
        result_layout.addWidget(self.interactive_source, 0, 1)
        
        result_layout.addWidget(QLabel("CRS source:"), 1, 0)
        self.interactive_crs_source = QLabel("CRS du projet")
        result_layout.addWidget(self.interactive_crs_source, 1, 1)
        
        result_layout.addWidget(QLabel("Converti:"), 2, 0)
        self.interactive_result = QLineEdit()
        self.interactive_result.setReadOnly(True)
        result_layout.addWidget(self.interactive_result, 2, 1)
        
        result_layout.addWidget(QLabel("Statut:"), 3, 0)
        self.interactive_validation = QLabel("")
        result_layout.addWidget(self.interactive_validation, 3, 1)
        
        self.copy_interactive_btn = QPushButton("Copier le résultat")
        self.copy_interactive_btn.clicked.connect(self.copy_interactive_results)
        result_layout.addWidget(self.copy_interactive_btn, 4, 0, 1, 2)
        
        result_group.setLayout(result_layout)
        layout.addWidget(result_group)
        
        self.interactive_tab.setLayout(layout)
    
    def setup_about_tab(self):
        """Configure l'onglet Aide rapide."""
        layout = QVBoxLayout()
        
        # Titre
        title = QLabel("📖 Aide rapide - Universal XY Converter")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        layout.addSpacing(10)
        
        # Guide
        help_text = QTextEdit()
        help_text.setReadOnly(True)
        help_text.setHtml("""
        <h3>📌 Conversion simple</h3>
        <ul>
            <li>Choisissez la direction de conversion</li>
            <li>Sélectionnez le CRS source et cible</li>
            <li>Entrez les coordonnées X et Y</li>
            <li>Cliquez sur "Convertir"</li>
        </ul>
        
        <h3>📁 Traitement batch CSV</h3>
        <ul>
            <li>Chargez votre fichier CSV</li>
            <li>Sélectionnez les colonnes X et Y</li>
            <li>Choisissez les CRS source et cible</li>
            <li>Lancez la conversion</li>
        </ul>
        
        <h3>🖱️ Sélection interactive</h3>
        <ul>
            <li>Activez le sélecteur</li>
            <li>Cliquez sur la carte</li>
            <li>Obtenez les coordonnées converties</li>
        </ul>
        
        <h3>🇧🇫 BFTM (Burkina Faso)</h3>
        <ul>
            <li>Ellipsoïde: GRS80</li>
            <li>Méridien central: 1.5° Ouest</li>
            <li>Fausse est: 600 000 m</li>
            <li>Fausse nord: 0 m</li>
            <li>Facteur d'échelle: 0.9996</li>
        </ul>
        
        <h3>🔧 CRS personnalisé</h3>
        <p>Sélectionnez "--- Personnalisé (PROJ) ---" et entrez votre chaîne PROJ</p>
        <p>Exemple: <code>+proj=longlat +ellps=clrk80 +towgs84=-118,-14,218</code></p>
        
        <h3>📞 Support</h3>
        <p>Email: jeanbaptiste.kibora@tic.gov.bf</p>
        <p>GitHub: https://github.com/geomatic-web/universal_xy_converter</p>
        """)
        layout.addWidget(help_text)
        
        self.about_tab.setLayout(layout)
    
    def activate_point_picker(self):
        """Active l'outil de sélection de points."""
        self.map_tool = QgsMapToolEmitPoint(self.iface.mapCanvas())
        self.map_tool.canvasClicked.connect(self.on_map_click)
        self.iface.mapCanvas().setMapTool(self.map_tool)
        
        self.rubber_band = QgsRubberBand(self.iface.mapCanvas(), QgsWkbTypes.PointGeometry)
        self.rubber_band.setColor(Qt.red)
        self.rubber_band.setWidth(5)
        
        self.activate_picker_btn.setEnabled(False)
        self.deactivate_picker_btn.setEnabled(True)
        self.iface.messageBar().pushMessage("Info", "Cliquez sur la carte pour sélectionner un point", level=1)
    
    def deactivate_point_picker(self):
        """Désactive l'outil de sélection de points."""
        if self.map_tool:
            self.iface.mapCanvas().unsetMapTool(self.map_tool)
            self.map_tool = None
        if self.rubber_band:
            self.rubber_band.reset()
            self.rubber_band = None
        self.activate_picker_btn.setEnabled(True)
        self.deactivate_picker_btn.setEnabled(False)
    
    def on_map_click(self, point, button):
        """Gère le clic sur la carte."""
        try:
            project_crs = QgsProject.instance().crs()
            
            target_crs_text = self.interactive_crs_combo.currentText()
            if target_crs_text == "--- Personnalisé (PROJ) ---":
                target_crs = self.bftm_crs
            else:
                target_crs = self.available_crs.get(target_crs_text, self.bftm_crs)
            
            self.interactive_source.setText(f"{point.x():.6f}, {point.y():.6f}")
            self.interactive_crs_source.setText(project_crs.description())
            
            transform = QgsCoordinateTransform(project_crs, target_crs, QgsProject.instance().transformContext())
            transformed = transform.transform(point)
            
            self.interactive_result.setText(f"{transformed.x():.6f}, {transformed.y():.6f}")
            
            self.interactive_validation.setText("✓ Conversion réussie")
            self.interactive_validation.setStyleSheet("color: green;")
            
            if self.rubber_band:
                self.rubber_band.reset()
                self.rubber_band.addPoint(point)
                
        except Exception as e:
            self.interactive_validation.setText(f"Erreur: {str(e)}")
            self.interactive_validation.setStyleSheet("color: red;")
    
    def copy_interactive_results(self):
        """Copie le résultat interactif."""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.interactive_result.text())
        self.iface.messageBar().pushMessage("Succès", "Résultat copié", level=1)