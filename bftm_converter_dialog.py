import os
import csv
import re
import pickle
from qgis.PyQt.QtCore import Qt, QTimer, QStandardPaths
from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QGroupBox,
    QGridLayout,
    QTabWidget,
    QFileDialog,
    QTextEdit,
    QProgressBar,
    QMessageBox,
    QCheckBox,
    QWidget,
    QApplication,
)
from qgis.PyQt.QtGui import QTextCursor
from qgis.core import (
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
    QgsPointXY,
    QgsWkbTypes,
    Qgis,
)
from qgis.gui import QgsMapToolEmitPoint, QgsRubberBand

from .i18n import tr, get_language

try:
    from .batch_processor import BatchProcessor
except ImportError:
    import sys

    sys.path.append(os.path.dirname(__file__))
    from batch_processor import BatchProcessor


class UniversalXYConverterDialog(QDialog):
    #  CACHE AU NIVEAU CLASSE
    _crs_definitions_cache = None  # Cache des définitions texte
    _crs_objects_cache = {}  # Cache des objets CRS déjà créés
    _cache_file = None  # Chemin du cache disque
    _is_loading = False

    def __init__(self, iface, plugin_dir):
        super().__init__()
        self.iface = iface
        self.plugin_dir = plugin_dir
        self.map_tool = None
        self.rubber_band = None
        self.processor = None
        self.all_crs_loaded = False
        self._initializing = True

        self.setWindowTitle(tr("window_title"))
        self.setMinimumWidth(700)
        self.setMinimumHeight(750)

        # Initialiser le chemin du cache disque
        if UniversalXYConverterDialog._cache_file is None:
            cache_dir = QStandardPaths.writableLocation(
                QStandardPaths.StandardLocation.CacheLocation
            )
            if not cache_dir:
                cache_dir = os.path.expanduser("~/.qgis3/cache")
            try:
                os.makedirs(cache_dir, exist_ok=True)
            except BaseException:
                cache_dir = os.path.expanduser("~/.cache/qgis3")
                os.makedirs(cache_dir, exist_ok=True)
            UniversalXYConverterDialog._cache_file = os.path.join(
                cache_dir, "universal_xy_converter_crs_defs.pkl"
            )

        #  CONSTRUCTION UI COMPLÈTE
        self.setup_ui()

        #  CHARGEMENT DES CRS EN ARRIÈRE-PLAN
        QTimer.singleShot(50, self._load_crs_async)

    #  CHARGEMENT ASYNCHRONE DES CRS

    def _load_crs_async(self):
        """Charge les définitions CRS de manière asynchrone"""
        if UniversalXYConverterDialog._is_loading:
            return

        UniversalXYConverterDialog._is_loading = True

        try:
            # Charger les définitions CRS (avec cache)
            self.setup_crs_definitions()

            # Mettre à jour tous les combobox
            self._populate_all_combos()

            # Mettre à jour les formats
            self.update_source_formats()
            self.update_target_formats()
            self.update_batch_formats()
            self.update_interactive_formats()

            self._initializing = False

        except Exception as e:
            print(f"Erreur chargement CRS: {e}")
        finally:
            UniversalXYConverterDialog._is_loading = False

    def _populate_all_combos(self):
        """Remplit tous les combobox avec les CRS chargés"""
        if hasattr(self, "source_crs_combo"):
            self._populate_crs_combo(self.source_crs_combo)
            self.set_combo_by_name(self.source_crs_combo, "🌍 WGS 84 (degrés)")

        if hasattr(self, "target_crs_combo"):
            self._populate_crs_combo(self.target_crs_combo)
            self.set_combo_by_name(
                self.target_crs_combo, "🇧🇫 BFTM (Burkina Faso) - OFFICIEL"
            )

        if hasattr(self, "batch_source_crs_combo"):
            self._populate_crs_combo(self.batch_source_crs_combo)
            self.set_combo_by_name(self.batch_source_crs_combo, "🌍 WGS 84 (degrés)")

        if hasattr(self, "batch_target_crs_combo"):
            self._populate_crs_combo(self.batch_target_crs_combo)
            self.set_combo_by_name(
                self.batch_target_crs_combo, "🇧🇫 BFTM (Burkina Faso) - OFFICIEL"
            )

        if hasattr(self, "interactive_crs_combo"):
            self._populate_crs_combo(self.interactive_crs_combo)
            self.set_combo_by_name(
                self.interactive_crs_combo, "🇧🇫 BFTM (Burkina Faso) - OFFICIEL"
            )

    #  GESTION DU CACHE DISQUE

    def _load_crs_from_disk_cache(self):
        """Charge les définitions CRS depuis le cache disque"""
        try:
            if not os.path.exists(UniversalXYConverterDialog._cache_file):
                return None
            with open(UniversalXYConverterDialog._cache_file, "rb") as f:
                return pickle.load(f)
        except Exception:
            return None

    def _save_crs_to_disk_cache(self, crs_defs):
        """Sauvegarde les définitions CRS dans le cache disque"""
        try:
            with open(UniversalXYConverterDialog._cache_file, "wb") as f:
                pickle.dump(crs_defs, f)
            return True
        except Exception:
            return False

    #  MÉTHODES DE CONVERSION DMS

    def dms_to_decimal(self, dms_string):
        try:
            if not dms_string or dms_string.strip() == "":
                return None
            dms_string = dms_string.strip().upper()
            try:
                val = float(dms_string)
                return val
            except ValueError:
                pass
            direction = 1.0
            if "S" in dms_string or "W" in dms_string or "O" in dms_string:
                direction = -1.0
            dms_string = (
                dms_string.replace("°", " ").replace("'", " ").replace('"', " ")
            )
            dms_string = dms_string.replace("N", " ").replace("S", " ")
            dms_string = dms_string.replace("E", " ").replace("W", " ")
            dms_string = dms_string.replace("O", " ").replace(",", ".")
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

    #  CRS OPTIMISÉ (LAZY LOADING)

    def setup_crs_definitions(self):
        """
        Stocke UNIQUEMENT des DEFINITIONS textuelles (légères).
        Aucun objet QgsCoordinateReferenceSystem n'est créé ici.
        """
        # Vérifier le cache mémoire
        if UniversalXYConverterDialog._crs_definitions_cache is not None:
            return

        # Vérifier le cache disque
        disk_cache = self._load_crs_from_disk_cache()
        if disk_cache is not None:
            UniversalXYConverterDialog._crs_definitions_cache = disk_cache
            return

        # CRÉATION DES DÉFINITIONS (TEXTE UNIQUEMENT)
        defs = {}

        # 1. SYSTÈMES DE RÉFÉRENCE PRINCIPAUX
        defs["🇧🇫 BFTM (Burkina Faso) - OFFICIEL"] = (
            "+proj=tmerc +lat_0=0 +lon_0=-1.5 +k=0.9996 "
            "+x_0=600000 +y_0=0 +ellps=GRS80 +units=m +no_defs"
        )
        defs["🌍 WGS 84 (degrés)"] = "EPSG:4326"
        defs["🌍 WGS 84 (Web Mercator)"] = "EPSG:3857"
        defs["🌐 ITRF2008 (degrés) [EPSG:8999]"] = (
            "+proj=longlat +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +no_defs"
        )

        # 2. CLARKE 1880 (degrés)
        defs["🗺️ Clarke 1880 (degrés) - Afrique Ouest"] = (
            "+proj=longlat +ellps=clrk80 +towgs84=-118,-14,218 +no_defs"
        )
        defs["🗺️ Clarke 1880 (degrés) - Cameroun"] = (
            "+proj=longlat +ellps=clrk80 +towgs84=-166,-15,204 +no_defs"
        )

        # 3. ADINDAN (degrés)
        defs["🌍 Adindan (degrés) - Afrique Ouest"] = (
            "+proj=longlat +ellps=clrk80 +towgs84=-118,-14,218 +no_defs"
        )
        defs["🌍 Adindan (degrés) - Cameroun"] = (
            "+proj=longlat +ellps=clrk80 +towgs84=-166,-15,204 +no_defs"
        )

        # 4. WGS 84 UTM - ZONES 1 À 60
        for zone in range(1, 61):
            defs[f"📐 WGS 84 / UTM zone {zone}N"] = f"EPSG:326{zone:02d}"
            defs[f"📐 WGS 84 / UTM zone {zone}S"] = f"EPSG:327{zone:02d}"

        #  5. CLARKE 1880 UTM - ZONES 1 À 60
        for zone in range(1, 61):
            defs[f"🗺️ Clarke 1880 Ouest / UTM {zone}N"] = (
                f"+proj=utm +zone={zone} +ellps=clrk80 "
                f"+towgs84=-118,-14,218 +units=m +no_defs"
            )
            defs[f"🗺️ Clarke 1880 Cameroun / UTM {zone}N"] = (
                f"+proj=utm +zone={zone} +ellps=clrk80 "
                f"+towgs84=-166,-15,204 +units=m +no_defs"
            )

        #  6. ADINDAN UTM - ZONES 1 À 60
        for zone in range(1, 61):
            defs[f"🌍 Adindan Ouest / UTM {zone}N"] = (
                f"+proj=utm +zone={zone} +ellps=clrk80 "
                f"+towgs84=-118,-14,218 +units=m +no_defs"
            )
            defs[f"🌍 Adindan Cameroun / UTM {zone}N"] = (
                f"+proj=utm +zone={zone} +ellps=clrk80 "
                f"+towgs84=-166,-15,204 +units=m +no_defs"
            )

        #  7. ITRF2008 UTM - ZONES 1 À 60
        for zone in range(1, 61):
            defs[f"🌐 ITRF2008 / UTM zone {zone}N"] = (
                f"+proj=utm +zone={zone} +ellps=GRS80 "
                f"+towgs84=0,0,0,0,0,0,0 +units=m +no_defs"
            )

        #  8. CRS PERSONNALISÉ
        defs["--- Personnalisé (PROJ) ---"] = "CUSTOM"

        #  9. OPTION POUR CHARGER PLUS
        defs["--- 🔄 Charger tous les CRS supplémentaires ---"] = "LOAD_ALL"

        # Sauvegarder dans le cache mémoire
        UniversalXYConverterDialog._crs_definitions_cache = defs

        # Sauvegarder sur disque
        QTimer.singleShot(500, lambda: self._save_crs_to_disk_cache(defs))

    def _instantiate_crs(self, crs_name):
        """
        Crée l'objet QgsCoordinateReferenceSystem UNIQUEMENT quand on en a besoin.
        Utilise un cache pour éviter de recréer plusieurs fois le même CRS.
        """
        if not crs_name:
            return None

        # Vérifier si l'objet existe déjà dans le cache
        if crs_name in UniversalXYConverterDialog._crs_objects_cache:
            return UniversalXYConverterDialog._crs_objects_cache[crs_name]

        # Récupérer la définition
        definition = UniversalXYConverterDialog._crs_definitions_cache.get(crs_name)
        if not definition:
            return None

        # CRS personnalisé
        if definition == "CUSTOM":
            return None

        # Chargement "LOAD_ALL" - ne pas instancier
        if definition == "LOAD_ALL":
            return None

        # Créer l'objet CRS
        crs = QgsCoordinateReferenceSystem()

        if definition.startswith("EPSG:"):
            crs.createFromOgcWmsCrs(definition)
        else:
            crs.createFromProj(definition)

        if crs.isValid():
            # Stocker dans le cache des objets
            UniversalXYConverterDialog._crs_objects_cache[crs_name] = crs
            return crs

        return None

    def load_all_crs(self):
        """Charge TOUS les CRS supplémentaires (appelé par l'utilisateur)"""
        if self.all_crs_loaded:
            return

        self.all_crs_loaded = True
        self.iface.messageBar().pushMessage(
            "Info", "Tous les CRS sont déjà disponibles", Qgis.Success
        )

    def _populate_crs_combo(self, combo):
        """Remplit le combo en une seule opération native (Ultra rapide)"""
        if combo is None:
            return
        combo.blockSignals(True)
        combo.clear()
        combo.addItems(list(UniversalXYConverterDialog._crs_definitions_cache.keys()))
        combo.blockSignals(False)

    #  GETTERS AVEC LAZY LOADING

    def get_source_crs(self):
        """Retourne le CRS source avec Lazy Loading"""
        current_text = self.source_crs_combo.currentText()
        if current_text == "--- Personnalisé (PROJ) ---":
            crs = QgsCoordinateReferenceSystem()
            proj_string = self.custom_source_edit.text()
            if not proj_string:
                return None
            crs.createFromProj(proj_string)
            return crs if crs.isValid() else None
        return self._instantiate_crs(current_text)

    def get_target_crs(self):
        """Retourne le CRS cible avec Lazy Loading"""
        current_text = self.target_crs_combo.currentText()
        if current_text == "--- Personnalisé (PROJ) ---":
            crs = QgsCoordinateReferenceSystem()
            proj_string = self.custom_target_edit.text()
            if not proj_string:
                return None
            crs.createFromProj(proj_string)
            return crs if crs.isValid() else None
        return self._instantiate_crs(current_text)

    def get_batch_source_crs(self):
        """Retourne le CRS source du batch avec Lazy Loading"""
        current_text = self.batch_source_crs_combo.currentText()
        if current_text == "--- Personnalisé (PROJ) ---":
            crs = QgsCoordinateReferenceSystem()
            proj_string = self.batch_custom_source_edit.text()
            if not proj_string:
                return None
            crs.createFromProj(proj_string)
            return crs if crs.isValid() else None
        return self._instantiate_crs(current_text)

    def get_batch_target_crs(self):
        """Retourne le CRS cible du batch avec Lazy Loading"""
        current_text = self.batch_target_crs_combo.currentText()
        if current_text == "--- Personnalisé (PROJ) ---":
            crs = QgsCoordinateReferenceSystem()
            proj_string = self.batch_custom_target_edit.text()
            if not proj_string:
                return None
            crs.createFromProj(proj_string)
            return crs if crs.isValid() else None
        return self._instantiate_crs(current_text)

    # ==================== UI ====================

    def setup_ui(self):
        """Construction COMPLÈTE de l'UI"""
        layout = QVBoxLayout()
        self.tabs = QTabWidget()

        self.simple_tab = QWidget()
        self.setup_simple_tab()
        self.tabs.addTab(self.simple_tab, tr("simple_tab"))

        self.batch_tab = QWidget()
        self.setup_batch_tab()
        self.tabs.addTab(self.batch_tab, tr("batch_tab"))

        self.interactive_tab = QWidget()
        self.setup_interactive_tab()
        self.tabs.addTab(self.interactive_tab, tr("interactive_tab"))

        self.about_tab = QWidget()
        self.setup_about_tab()
        self.tabs.addTab(self.about_tab, tr("help_tab"))

        layout.addWidget(self.tabs)
        self.setLayout(layout)

    #  CONVERSION SIMPLE

    def setup_simple_tab(self):
        layout = QVBoxLayout()

        source_group = QGroupBox(tr("source_system"))
        source_layout = QGridLayout()

        source_layout.addWidget(QLabel(tr("source_crs")), 0, 0)
        self.source_crs_combo = QComboBox()
        self.source_crs_combo.addItem("⏳ Chargement des CRS...")
        self.source_crs_combo.currentIndexChanged.connect(self.on_source_crs_changed)
        source_layout.addWidget(self.source_crs_combo, 0, 1)

        source_layout.addWidget(QLabel(tr("source_format")), 1, 0)
        self.source_format_combo = QComboBox()
        self.source_format_combo.addItems(
            [tr("source_format_dd"), tr("source_format_dms"), tr("source_format_m")]
        )
        self.source_format_combo.currentIndexChanged.connect(
            self.on_source_format_changed
        )
        source_layout.addWidget(self.source_format_combo, 1, 1)

        self.custom_source_label = QLabel(tr("custom_source"))
        self.custom_source_edit = QLineEdit()
        self.custom_source_edit.setPlaceholderText(tr("custom_proj_source"))
        self.custom_source_label.setVisible(False)
        self.custom_source_edit.setVisible(False)
        source_layout.addWidget(self.custom_source_label, 2, 0)
        source_layout.addWidget(self.custom_source_edit, 2, 1)

        source_group.setLayout(source_layout)
        layout.addWidget(source_group)

        target_group = QGroupBox(tr("target_system"))
        target_layout = QGridLayout()

        target_layout.addWidget(QLabel(tr("target_crs")), 0, 0)
        self.target_crs_combo = QComboBox()
        self.target_crs_combo.addItem("⏳ Chargement des CRS...")
        self.target_crs_combo.currentIndexChanged.connect(self.on_target_crs_changed)
        target_layout.addWidget(self.target_crs_combo, 0, 1)

        target_layout.addWidget(QLabel(tr("target_format")), 1, 0)
        self.target_format_combo = QComboBox()
        self.target_format_combo.addItems(
            [tr("target_format_dd"), tr("target_format_dms"), tr("target_format_m")]
        )
        target_layout.addWidget(self.target_format_combo, 1, 1)

        self.custom_target_label = QLabel(tr("custom_target"))
        self.custom_target_edit = QLineEdit()
        self.custom_target_edit.setPlaceholderText(tr("custom_proj_target"))
        self.custom_target_label.setVisible(False)
        self.custom_target_edit.setVisible(False)
        target_layout.addWidget(self.custom_target_label, 2, 0)
        target_layout.addWidget(self.custom_target_edit, 2, 1)

        target_group.setLayout(target_layout)
        layout.addWidget(target_group)

        coord_group = QGroupBox(tr("coordinates"))
        coord_layout = QGridLayout()

        coord_layout.addWidget(QLabel(tr("x_longitude")), 0, 0)
        self.source_x = QLineEdit()
        coord_layout.addWidget(self.source_x, 0, 1)

        coord_layout.addWidget(QLabel(tr("y_latitude")), 1, 0)
        self.source_y = QLineEdit()
        coord_layout.addWidget(self.source_y, 1, 1)

        coord_group.setLayout(coord_layout)
        layout.addWidget(coord_group)

        self.convert_btn = QPushButton(tr("convert_btn"))
        self.convert_btn.clicked.connect(self.convert_coordinates)
        self.convert_btn.setMinimumHeight(40)
        self.convert_btn.setStyleSheet(
            "font-weight: bold; background-color: #4CAF50; color: white;"
        )
        layout.addWidget(self.convert_btn)

        self.swap_btn = QPushButton(tr("swap_btn"))
        self.swap_btn.clicked.connect(self.swap_crs)
        layout.addWidget(self.swap_btn)

        result_group = QGroupBox(tr("result"))
        result_layout = QGridLayout()

        result_layout.addWidget(QLabel(tr("x_east")), 0, 0)
        self.result_x = QLineEdit()
        self.result_x.setReadOnly(True)
        result_layout.addWidget(self.result_x, 0, 1)

        result_layout.addWidget(QLabel(tr("y_north")), 1, 0)
        self.result_y = QLineEdit()
        self.result_y.setReadOnly(True)
        result_layout.addWidget(self.result_y, 1, 1)

        result_layout.addWidget(QLabel(tr("status")), 2, 0)
        self.conversion_status = QLabel(tr("conversion_pending"))
        result_layout.addWidget(self.conversion_status, 2, 1)

        self.copy_btn = QPushButton(tr("copy_btn"))
        self.copy_btn.clicked.connect(self.copy_results)
        result_layout.addWidget(self.copy_btn, 3, 0, 1, 2)

        result_group.setLayout(result_layout)
        layout.addWidget(result_group)

        self.simple_tab.setLayout(layout)

    # ==================== MÉTHODES DE MISE À JOUR ====================

    def update_source_formats(self):
        if not hasattr(self, "source_crs_combo") or self.source_crs_combo.count() == 0:
            return
        if self.source_crs_combo.currentText().startswith("⏳"):
            return
        source_name = self.source_crs_combo.currentText()
        geographic_keywords = [
            "WGS 84 (degrés)",
            "WGS 84 (Web Mercator)",
            "degrés",
            "4326",
            "degrees",
            "ITRF2008",
        ]
        projected_keywords = [
            "UTM zone",
            "WGS 84 / UTM",
            "BFTM",
            "Lambert",
            "Adindan",
            "Clarke 1880",
            "ITRF2008 / UTM",
        ]
        is_geographic = any(kw in source_name for kw in geographic_keywords)
        is_projected = any(kw in source_name for kw in projected_keywords)
        current = self.source_format_combo.currentText()
        self.source_format_combo.clear()
        if is_geographic:
            self.source_format_combo.addItems(
                [tr("source_format_dd"), tr("source_format_dms")]
            )
        elif is_projected:
            self.source_format_combo.addItems([tr("source_format_m")])
        else:
            self.source_format_combo.addItems(
                [tr("source_format_dd"), tr("source_format_dms"), tr("source_format_m")]
            )
        idx = self.source_format_combo.findText(current)
        if idx >= 0:
            self.source_format_combo.setCurrentIndex(idx)
        elif self.source_format_combo.count() > 0:
            self.source_format_combo.setCurrentIndex(0)

    def update_target_formats(self):
        if not hasattr(self, "target_crs_combo") or self.target_crs_combo.count() == 0:
            return
        if self.target_crs_combo.currentText().startswith("⏳"):
            return
        target_name = self.target_crs_combo.currentText()
        geographic_keywords = [
            "WGS 84 (degrés)",
            "WGS 84 (Web Mercator)",
            "degrés",
            "4326",
            "degrees",
            "ITRF2008",
        ]
        projected_keywords = [
            "UTM zone",
            "WGS 84 / UTM",
            "BFTM",
            "Lambert",
            "Adindan",
            "Clarke 1880",
            "ITRF2008 / UTM",
        ]
        is_geographic = any(kw in target_name for kw in geographic_keywords)
        is_projected = any(kw in target_name for kw in projected_keywords)
        current = self.target_format_combo.currentText()
        self.target_format_combo.clear()
        if is_geographic:
            self.target_format_combo.addItems(
                [tr("target_format_dd"), tr("target_format_dms")]
            )
        elif is_projected:
            self.target_format_combo.addItems([tr("target_format_m")])
        else:
            self.target_format_combo.addItems(
                [tr("target_format_dd"), tr("target_format_dms"), tr("target_format_m")]
            )
        idx = self.target_format_combo.findText(current)
        if idx >= 0:
            self.target_format_combo.setCurrentIndex(idx)
        elif self.target_format_combo.count() > 0:
            self.target_format_combo.setCurrentIndex(0)

    def update_source_placeholder(self):
        if not hasattr(self, "source_crs_combo") or self.source_crs_combo.count() == 0:
            return
        if self.source_crs_combo.currentText().startswith("⏳"):
            return
        source_format = self.source_format_combo.currentText()
        source_name = self.source_crs_combo.currentText()
        is_geographic = (
            "degrés" in source_name
            or "4326" in source_name
            or "WGS 84" in source_name
            or "ITRF" in source_name
        )
        if source_format == tr("source_format_dd"):
            if is_geographic:
                self.source_x.setPlaceholderText(tr("x_placeholder_geo"))
                self.source_y.setPlaceholderText(tr("y_placeholder_geo"))
            else:
                self.source_x.setPlaceholderText(tr("x_placeholder_proj"))
                self.source_y.setPlaceholderText(tr("y_placeholder_proj"))
        elif source_format == tr("source_format_dms"):
            self.source_x.setPlaceholderText(tr("x_placeholder_dms"))
            self.source_y.setPlaceholderText(tr("y_placeholder_dms"))
        else:
            self.source_x.setPlaceholderText(tr("x_placeholder_proj"))
            self.source_y.setPlaceholderText(tr("y_placeholder_proj"))

    def on_source_crs_changed(self):
        if (
            self._initializing
            or not hasattr(self, "source_crs_combo")
            or self.source_crs_combo.count() == 0
        ):
            return
        if self.source_crs_combo.currentText().startswith("⏳"):
            return
        is_custom = self.source_crs_combo.currentText() == "--- Personnalisé (PROJ) ---"
        self.custom_source_label.setVisible(is_custom)
        self.custom_source_edit.setVisible(is_custom)
        self.update_source_formats()
        self.update_source_placeholder()
        if (
            self.source_crs_combo.currentText()
            == "--- 🔄 Charger tous les CRS supplémentaires ---"
        ):
            self.load_all_crs()

    def on_source_format_changed(self):
        if self._initializing:
            return
        self.update_source_placeholder()

    def on_target_crs_changed(self):
        if (
            self._initializing
            or not hasattr(self, "target_crs_combo")
            or self.target_crs_combo.count() == 0
        ):
            return
        if self.target_crs_combo.currentText().startswith("⏳"):
            return
        is_custom = self.target_crs_combo.currentText() == "--- Personnalisé (PROJ) ---"
        self.custom_target_label.setVisible(is_custom)
        self.custom_target_edit.setVisible(is_custom)
        self.update_target_formats()

    # ==================== CONVERSION ====================

    def convert_coordinates(self):
        try:
            if not self.source_x.text() or not self.source_y.text():
                self.iface.messageBar().pushMessage(
                    "Erreur", tr("error_enter_coords"), Qgis.Critical
                )
                return
            src_fmt = self.source_format_combo.currentText()
            if src_fmt == tr("source_format_dd"):
                x = float(self.source_x.text())
                y = float(self.source_y.text())
            elif src_fmt == tr("source_format_dms"):
                x = self.dms_to_decimal(self.source_x.text())
                y = self.dms_to_decimal(self.source_y.text())
                if x is None or y is None:
                    self.conversion_status.setText(tr("error_dms_format"))
                    self.conversion_status.setStyleSheet("color: red;")
                    return
            else:
                x = float(self.source_x.text())
                y = float(self.source_y.text())

            source_crs = self.get_source_crs()
            target_crs = self.get_target_crs()
            if source_crs is None or target_crs is None:
                self.conversion_status.setText(tr("error_invalid_crs"))
                return

            transform = QgsCoordinateTransform(
                source_crs, target_crs, QgsProject.instance().transformContext()
            )
            point = QgsPointXY(x, y)
            transformed = transform.transform(point)

            tgt_fmt = self.target_format_combo.currentText()
            tgt_name = self.target_crs_combo.currentText()
            is_geo = (
                "degrés" in tgt_name
                or "4326" in str(target_crs.authid())
                or "ITRF" in tgt_name
            )

            if tgt_fmt == tr("target_format_m"):
                self.result_x.setText(f"{transformed.x():.3f}")
                self.result_y.setText(f"{transformed.y():.3f}")
            elif tgt_fmt == tr("target_format_dms"):
                if is_geo:
                    self.result_x.setText(self.decimal_to_dms(transformed.x(), False))
                    self.result_y.setText(self.decimal_to_dms(transformed.y(), True))
                else:
                    self.result_x.setText(f"{transformed.x():.3f}")
                    self.result_y.setText(f"{transformed.y():.3f}")
                    self.conversion_status.setText(tr("warning_dms_projected"))
                    self.conversion_status.setStyleSheet("color: orange;")
            else:
                if is_geo:
                    self.result_x.setText(f"{transformed.x():.6f}")
                    self.result_y.setText(f"{transformed.y():.6f}")
                else:
                    self.result_x.setText(f"{transformed.x():.3f}")
                    self.result_y.setText(f"{transformed.y():.3f}")
                    self.conversion_status.setText(tr("warning_dd_projected"))
                    self.conversion_status.setStyleSheet("color: orange;")

            self.conversion_status.setText(tr("conversion_success"))
            self.conversion_status.setStyleSheet("color: green;")
        except Exception as e:
            self.conversion_status.setText(f"✗ Erreur: {str(e)[:50]}")
            self.conversion_status.setStyleSheet("color: red;")

    # ==================== TRAITEMENT BATCH ====================

    def setup_batch_tab(self):
        layout = QVBoxLayout()

        file_group = QGroupBox(tr("source_file"))
        file_layout = QHBoxLayout()
        self.source_file_path = QLineEdit()
        self.source_file_path.setPlaceholderText(tr("file_placeholder"))
        file_layout.addWidget(self.source_file_path)
        self.browse_btn = QPushButton(tr("browse_btn"))
        self.browse_btn.clicked.connect(self.browse_source_file)
        file_layout.addWidget(self.browse_btn)
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)

        cols_group = QGroupBox(tr("column_config"))
        cols_layout = QGridLayout()
        cols_layout.addWidget(QLabel(tr("x_column")), 0, 0)
        self.x_column_combo = QComboBox()
        cols_layout.addWidget(self.x_column_combo, 0, 1)
        cols_layout.addWidget(QLabel(tr("y_column")), 1, 0)
        self.y_column_combo = QComboBox()
        cols_layout.addWidget(self.y_column_combo, 1, 1)
        cols_layout.addWidget(QLabel(tr("separator")), 2, 0)
        self.separator_combo = QComboBox()
        self.separator_combo.addItems([";", ",", "|", "\\t"])
        cols_layout.addWidget(self.separator_combo, 2, 1)
        cols_group.setLayout(cols_layout)
        layout.addWidget(cols_group)

        crs_group = QGroupBox(tr("crs_config"))
        crs_layout = QGridLayout()
        crs_layout.addWidget(QLabel(tr("source_system_label")), 0, 0)
        self.batch_source_crs_combo = QComboBox()
        self.batch_source_crs_combo.addItem("⏳ Chargement des CRS...")
        self.batch_source_crs_combo.currentIndexChanged.connect(
            self.update_batch_formats
        )
        crs_layout.addWidget(self.batch_source_crs_combo, 0, 1)

        crs_layout.addWidget(QLabel(tr("source_format_label")), 1, 0)
        self.batch_format_combo = QComboBox()
        self.batch_format_combo.addItems(
            [tr("source_format_dd"), tr("source_format_dms"), tr("source_format_m")]
        )
        crs_layout.addWidget(self.batch_format_combo, 1, 1)

        crs_layout.addWidget(QLabel(tr("target_system_label")), 2, 0)
        self.batch_target_crs_combo = QComboBox()
        self.batch_target_crs_combo.addItem("⏳ Chargement des CRS...")
        self.batch_target_crs_combo.currentIndexChanged.connect(
            self.on_batch_target_crs_changed
        )
        crs_layout.addWidget(self.batch_target_crs_combo, 2, 1)

        self.batch_custom_source_label = QLabel(tr("custom_source"))
        self.batch_custom_source_edit = QLineEdit()
        self.batch_custom_source_edit.setPlaceholderText(tr("custom_proj_source"))
        self.batch_custom_source_label.setVisible(False)
        self.batch_custom_source_edit.setVisible(False)
        crs_layout.addWidget(self.batch_custom_source_label, 3, 0)
        crs_layout.addWidget(self.batch_custom_source_edit, 3, 1)

        self.batch_custom_target_label = QLabel(tr("custom_target"))
        self.batch_custom_target_edit = QLineEdit()
        self.batch_custom_target_edit.setPlaceholderText(tr("custom_proj_target"))
        self.batch_custom_target_label.setVisible(False)
        self.batch_custom_target_edit.setVisible(False)
        crs_layout.addWidget(self.batch_custom_target_label, 4, 0)
        crs_layout.addWidget(self.batch_custom_target_edit, 4, 1)

        crs_group.setLayout(crs_layout)
        layout.addWidget(crs_group)

        options_group = QGroupBox(tr("options"))
        options_layout = QVBoxLayout()
        self.batch_add_original = QCheckBox(tr("keep_original"))
        self.batch_add_original.setChecked(True)
        options_layout.addWidget(self.batch_add_original)
        self.batch_skip_invalid = QCheckBox(tr("skip_invalid"))
        self.batch_skip_invalid.setChecked(True)
        options_layout.addWidget(self.batch_skip_invalid)
        options_group.setLayout(options_layout)
        layout.addWidget(options_group)

        self.process_btn = QPushButton(tr("process_btn"))
        self.process_btn.setMinimumHeight(40)
        self.process_btn.setStyleSheet(
            "font-weight: bold; background-color: #4CAF50; color: white;"
        )
        self.process_btn.clicked.connect(self.process_batch)
        self.process_btn.setEnabled(False)
        layout.addWidget(self.process_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        log_group = QGroupBox(tr("log"))
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        layout.addWidget(log_group)

        self.batch_tab.setLayout(layout)

    def update_batch_formats(self):
        if (
            not hasattr(self, "batch_source_crs_combo")
            or self.batch_source_crs_combo.count() == 0
        ):
            return
        if self.batch_source_crs_combo.currentText().startswith("⏳"):
            return
        source_name = self.batch_source_crs_combo.currentText()
        geographic_keywords = [
            "WGS 84 (degrés)",
            "degrés",
            "4326",
            "degrees",
            "ITRF2008",
        ]
        projected_keywords = [
            "UTM zone",
            "WGS 84 / UTM",
            "BFTM",
            "Lambert",
            "Adindan",
            "Clarke 1880",
            "ITRF2008 / UTM",
        ]
        is_geographic = any(kw in source_name for kw in geographic_keywords)
        is_projected = any(kw in source_name for kw in projected_keywords)
        current = self.batch_format_combo.currentText()
        self.batch_format_combo.clear()
        if is_geographic:
            self.batch_format_combo.addItems(
                [tr("source_format_dd"), tr("source_format_dms")]
            )
        elif is_projected:
            self.batch_format_combo.addItems([tr("source_format_m")])
        else:
            self.batch_format_combo.addItems(
                [tr("source_format_dd"), tr("source_format_dms"), tr("source_format_m")]
            )
        idx = self.batch_format_combo.findText(current)
        if idx >= 0:
            self.batch_format_combo.setCurrentIndex(idx)
        elif self.batch_format_combo.count() > 0:
            self.batch_format_combo.setCurrentIndex(0)

    def on_batch_target_crs_changed(self):
        if (
            not hasattr(self, "batch_target_crs_combo")
            or self.batch_target_crs_combo.count() == 0
        ):
            return
        if self.batch_target_crs_combo.currentText().startswith("⏳"):
            return
        is_custom = (
            self.batch_target_crs_combo.currentText() == "--- Personnalisé (PROJ) ---"
        )
        self.batch_custom_target_label.setVisible(is_custom)
        self.batch_custom_target_edit.setVisible(is_custom)

    def process_batch(self):
        file_path = self.source_file_path.text()
        if not file_path:
            QMessageBox.warning(self, "Attention", tr("batch_no_file"))
            return
        x_col = self.x_column_combo.currentText()
        y_col = self.y_column_combo.currentText()
        if not x_col or not y_col:
            QMessageBox.warning(self, "Attention", tr("batch_select_columns"))
            return

        source_crs = self.get_batch_source_crs()
        target_crs = self.get_batch_target_crs()

        sep = self.separator_combo.currentText().replace("\\t", "\t")
        config = {
            "x_column": x_col,
            "y_column": y_col,
            "separator": sep,
            "source_crs": source_crs,
            "target_crs": target_crs,
            "input_format": self.batch_format_combo.currentText(),
            "skip_invalid": self.batch_skip_invalid.isChecked(),
            "keep_original": self.batch_add_original.isChecked(),
        }
        self.log_text.clear()
        self.log_text.append(tr("batch_start"))
        self.log_text.append(f"{tr('batch_file')} {os.path.basename(file_path)}")
        self.log_text.append(
            f"{tr('batch_format')} {self.batch_format_combo.currentText()}"
        )
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

        info_label = QLabel(tr("interactive_click"))
        info_label.setWordWrap(True)
        info_label.setStyleSheet("font-weight: bold; color: blue;")
        layout.addWidget(info_label)

        crs_group = QGroupBox(tr("target_crs_interactive"))
        crs_layout = QHBoxLayout()
        self.interactive_crs_combo = QComboBox()
        self.interactive_crs_combo.addItem("⏳ Chargement des CRS...")
        self.interactive_crs_combo.currentIndexChanged.connect(
            self.update_interactive_formats
        )
        crs_layout.addWidget(self.interactive_crs_combo)
        crs_group.setLayout(crs_layout)
        layout.addWidget(crs_group)

        format_group = QGroupBox(tr("display_format"))
        format_layout = QHBoxLayout()
        self.interactive_format_combo = QComboBox()
        self.interactive_format_combo.addItems(
            [tr("target_format_dd"), tr("target_format_dms"), tr("target_format_m")]
        )
        self.interactive_format_combo.currentIndexChanged.connect(
            self.update_interactive_placeholder
        )
        format_layout.addWidget(self.interactive_format_combo)
        format_group.setLayout(format_layout)
        layout.addWidget(format_group)

        btn_layout = QHBoxLayout()
        self.activate_btn = QPushButton(tr("activate_btn"))
        self.activate_btn.clicked.connect(self.activate_point_picker)
        btn_layout.addWidget(self.activate_btn)

        self.deactivate_btn = QPushButton(tr("deactivate_btn"))
        self.deactivate_btn.clicked.connect(self.deactivate_point_picker)
        self.deactivate_btn.setEnabled(False)
        btn_layout.addWidget(self.deactivate_btn)
        layout.addLayout(btn_layout)

        result_group = QGroupBox(tr("interactive_result"))
        result_layout = QGridLayout()

        result_layout.addWidget(QLabel(tr("source_map")), 0, 0)
        self.interactive_source = QLineEdit()
        self.interactive_source.setReadOnly(True)
        result_layout.addWidget(self.interactive_source, 0, 1)

        result_layout.addWidget(QLabel(tr("crs_source")), 1, 0)
        self.interactive_crs_source = QLabel("CRS du projet")
        result_layout.addWidget(self.interactive_crs_source, 1, 1)

        result_layout.addWidget(QLabel(tr("target_format_label")), 2, 0)
        self.interactive_format_label = QLabel("")
        result_layout.addWidget(self.interactive_format_label, 2, 1)

        result_layout.addWidget(QLabel(tr("converted")), 3, 0)
        self.interactive_result = QLineEdit()
        self.interactive_result.setReadOnly(True)
        result_layout.addWidget(self.interactive_result, 3, 1)

        result_layout.addWidget(QLabel(tr("status_label")), 4, 0)
        self.interactive_status = QLabel("")
        result_layout.addWidget(self.interactive_status, 4, 1)

        self.copy_interactive_btn = QPushButton(tr("copy_interactive_btn"))
        self.copy_interactive_btn.clicked.connect(self.copy_interactive_results)
        result_layout.addWidget(self.copy_interactive_btn, 5, 0, 1, 2)

        result_group.setLayout(result_layout)
        layout.addWidget(result_group)

        self.interactive_tab.setLayout(layout)

    def update_interactive_formats(self):
        if (
            not hasattr(self, "interactive_crs_combo")
            or self.interactive_crs_combo.count() == 0
        ):
            return
        if self.interactive_crs_combo.currentText().startswith("⏳"):
            return
        target_name = self.interactive_crs_combo.currentText()
        geographic_keywords = [
            "WGS 84 (degrés)",
            "degrés",
            "4326",
            "degrees",
            "ITRF2008",
        ]
        projected_keywords = [
            "UTM zone",
            "WGS 84 / UTM",
            "BFTM",
            "Lambert",
            "Adindan",
            "Clarke 1880",
            "ITRF2008 / UTM",
        ]
        is_geographic = any(kw in target_name for kw in geographic_keywords)
        is_projected = any(kw in target_name for kw in projected_keywords)
        current = self.interactive_format_combo.currentText()
        self.interactive_format_combo.clear()
        if is_geographic:
            self.interactive_format_combo.addItems(
                [tr("target_format_dd"), tr("target_format_dms")]
            )
            self.interactive_format_label.setText("DD ou DMS")
        elif is_projected:
            self.interactive_format_combo.addItems([tr("target_format_m")])
            self.interactive_format_label.setText(tr("target_format_m"))
        else:
            self.interactive_format_combo.addItems(
                [tr("target_format_dd"), tr("target_format_dms"), tr("target_format_m")]
            )
            self.interactive_format_label.setText("DD / DMS / mètres")
        idx = self.interactive_format_combo.findText(current)
        if idx >= 0:
            self.interactive_format_combo.setCurrentIndex(idx)
        elif self.interactive_format_combo.count() > 0:
            self.interactive_format_combo.setCurrentIndex(0)
        self.update_interactive_placeholder()

    def update_interactive_placeholder(self):
        fmt = self.interactive_format_combo.currentText()
        if fmt == tr("target_format_dd"):
            self.interactive_format_label.setText(
                "Format: degrés décimaux (ex: 12.5042)"
            )
        elif fmt == tr("target_format_dms"):
            self.interactive_format_label.setText("Format: DMS (ex: 12°30'15\" N)")
        else:
            self.interactive_format_label.setText("Format: mètres (ex: 679246.00)")

    def activate_point_picker(self):
        self.map_tool = QgsMapToolEmitPoint(self.iface.mapCanvas())
        self.map_tool.canvasClicked.connect(self.on_map_click)
        self.iface.mapCanvas().setMapTool(self.map_tool)
        self.rubber_band = QgsRubberBand(
            self.iface.mapCanvas(), QgsWkbTypes.PointGeometry
        )
        self.rubber_band.setColor(Qt.GlobalColor.red)
        self.rubber_band.setWidth(5)
        self.activate_btn.setEnabled(False)
        self.deactivate_btn.setEnabled(True)
        self.iface.messageBar().pushMessage("Info", tr("interactive_info"), Qgis.Info)

    def deactivate_point_picker(self):
        if self.map_tool:
            self.iface.mapCanvas().unsetMapTool(self.map_tool)
            self.map_tool = None
        if self.rubber_band:
            self.rubber_band.reset()
            self.rubber_band = None
        self.activate_btn.setEnabled(True)
        self.deactivate_btn.setEnabled(False)

    def on_map_click(self, point, button):
        try:
            project_crs = QgsProject.instance().crs()
            target_text = self.interactive_crs_combo.currentText()
            target_crs = self._instantiate_crs(target_text)
            if target_crs is None:
                target_crs = self.bftm_crs if hasattr(self, "bftm_crs") else None
            if target_crs is None:
                self.interactive_status.setText("Erreur: CRS cible non disponible")
                self.interactive_status.setStyleSheet("color: red;")
                return

            transform = QgsCoordinateTransform(
                project_crs, target_crs, QgsProject.instance().transformContext()
            )
            transformed = transform.transform(point)
            self.interactive_source.setText(f"{point.x():.6f}, {point.y():.6f}")
            self.interactive_crs_source.setText(project_crs.description())
            fmt = self.interactive_format_combo.currentText()
            target_name = self.interactive_crs_combo.currentText()
            is_geographic = any(
                kw in target_name
                for kw in [
                    "degrés",
                    "4326",
                    "WGS 84",
                    "ETRS89",
                    "NAD83",
                    "GDA2020",
                    "CGCS2000",
                    "NZGD2000",
                    "JGD2011",
                    "degrees",
                    "ITRF2008",
                ]
            )
            if fmt == tr("target_format_m"):
                self.interactive_result.setText(
                    f"{transformed.x():.3f}, {transformed.y():.3f}"
                )
                self.interactive_status.setText(tr("conversion_success") + " (mètres)")
                self.interactive_status.setStyleSheet("color: green;")
            elif fmt == tr("target_format_dms"):
                if is_geographic:
                    lon_dms = self.decimal_to_dms(transformed.x(), is_latitude=False)
                    lat_dms = self.decimal_to_dms(transformed.y(), is_latitude=True)
                    self.interactive_result.setText(f"{lon_dms}, {lat_dms}")
                    self.interactive_status.setText(tr("conversion_success") + " (DMS)")
                    self.interactive_status.setStyleSheet("color: green;")
                else:
                    self.interactive_result.setText(
                        f"{transformed.x():.3f}, {transformed.y():.3f}"
                    )
                    self.interactive_status.setText(tr("warning_dms_projected"))
                    self.interactive_status.setStyleSheet("color: orange;")
            else:
                if is_geographic:
                    self.interactive_result.setText(
                        f"{transformed.x():.6f}, {transformed.y():.6f}"
                    )
                    self.interactive_status.setText(
                        tr("conversion_success") + " (degrés)"
                    )
                    self.interactive_status.setStyleSheet("color: green;")
                else:
                    self.interactive_result.setText(
                        f"{transformed.x():.3f}, {transformed.y():.3f}"
                    )
                    self.interactive_status.setText(tr("warning_dd_projected"))
                    self.interactive_status.setStyleSheet("color: orange;")
        except Exception as e:
            self.interactive_status.setText(f"Erreur: {str(e)[:50]}")
            self.interactive_status.setStyleSheet("color: red;")

    def copy_interactive_results(self):
        if self.interactive_result.text():
            clipboard = QApplication.clipboard()
            clipboard.setText(self.interactive_result.text())
            self.iface.messageBar().pushMessage("Succès", tr("copy_result"), Qgis.Info)

    # ==================== MÉTHODES UTILITAIRES ====================

    def set_combo_by_name(self, combo, name):
        if combo is None:
            return
        for i in range(combo.count()):
            if combo.itemText(i) == name:
                combo.setCurrentIndex(i)
                return

    def swap_crs(self):
        src_text = self.source_crs_combo.currentText()
        tgt_text = self.target_crs_combo.currentText()
        self.source_crs_combo.setCurrentText(tgt_text)
        self.target_crs_combo.setCurrentText(src_text)
        self.update_source_formats()
        self.update_target_formats()
        self.iface.messageBar().pushMessage("Info", tr("crs_swapped"), Qgis.Info)

    def copy_results(self):
        QApplication.clipboard().setText(
            f"{self.result_x.text()}\t{self.result_y.text()}"
        )
        self.iface.messageBar().pushMessage("Succès", tr("copy_success"), Qgis.Info)

    def browse_source_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Sélectionner un CSV", "", "CSV (*.csv)"
        )
        if path:
            self.source_file_path.setText(path)
            self.process_btn.setEnabled(True)
            sep = self.separator_combo.currentText().replace("\\t", "\t")
            try:
                with open(path, "r", encoding="utf-8-sig") as f:
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
            self.log_text.append(f"\n{tr('batch_completed')} {path}")

    # ==================== AIDE ====================

    def setup_about_tab(self):
        layout = QVBoxLayout()
        title = QLabel(tr("help_title"))
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        help_text = QTextEdit()
        help_text.setReadOnly(True)

        lang = get_language()
        if lang == "fr":
            help_html = self.get_help_fr()
        else:
            help_html = self.get_help_en()

        help_text.setHtml(help_html)
        layout.addWidget(help_text)
        self.about_tab.setLayout(layout)

    def get_help_fr(self):
        return """
        <h3>Formats de coordonnées supportés</h3>
        <ul>
            <li><b>Degrés décimaux (DD)</b> : 12.5042, -1.5</li>
            <li><b>Degrés/Minutes/Secondes (DMS)</b> : 12°30'15" N ou 12°30'15"</li>
            <li><b>Mètres (m)</b> : 679246.00, 1360000.00</li>
        </ul>

        <h3>Format CSV pour batch</h3>
        <pre>
id,longitude,latitude,ville
1,12°30'15" N,1°30'0" O
2,11°12'0" N,4°18'0" O</pre>

        <h3>Sélection interactive</h3>
        <ul><li>Activez le sélecteur, cliquez sur la carte</li></ul>

        <h3>🇧🇫 BFTM - Burkina Faso</h3>
        <ul>
            <li>Ellipsoïde: GRS80</li>
            <li>Méridien central: 1.5° Ouest</li>
            <li>Fausse est: 600 000 m</li>
            <li>Facteur d'échelle: 0.9996</li>
        </ul>

        <h3>ITRF2008</h3>
        <ul>
            <li>International Terrestrial Reference Frame 2008</li>
            <li>Ellipsoïde: GRS80 (a=6378137.0, f=1/298.257222101)</li>
            <li>Méridien: Greenwich</li>
            <li>Unité angulaire: Degré (0.0174532925199433)</li>
            <li>EPSG: 8999</li>
        </ul>

        <h3>Clarke 1880</h3>
        <ul>
            <li>Ellipsoïde historique utilisé en Afrique</li>
            <li>Demi-grand axe: 6 378 249.145 m</li>
            <li>Aplatissement: 1/293.465</li>
            <li><b>Vers WGS84 (Ouest):</b> -118,-14,218</li>
            <li><b>Vers WGS84 (Cameroun):</b> -166,-15,204</li>
        </ul>

        <h3>Adindan</h3>
        <ul>
            <li>Datum utilisé au Burkina Faso et Afrique de l'Ouest</li>
            <li>Ellipsoïde: Clarke 1880</li>
            <li><b>Vers WGS84 (Ouest):</b> -118,-14,218</li>
            <li><b>Vers WGS84 (Cameroun):</b> -166,-15,204</li>
        </ul>

        <h3>Support</h3>
        <p>Email: jeanbaptiste.kibora@tic.gov.bf</p>
        <p>Téléphone: +22664412514 ou +22668690411</p>
        """

    def get_help_en(self):
        return """
        <h3>Supported coordinate formats</h3>
        <ul>
            <li><b>Decimal Degrees (DD)</b> : 12.5042, -1.5</li>
            <li><b>Degrees/Minutes/Seconds (DMS)</b> : 12°30'15" N or 12°30'15"</li>
            <li><b>Meters (m)</b> : 679246.00, 1360000.00</li>
        </ul>

        <h3>CSV format for batch</h3>
        <pre>
id,longitude,latitude,city
1,12°30'15" N,1°30'0" W
2,11°12'0" N,4°18'0" W</pre>

        <h3>Interactive selection</h3>
        <ul><li>Activate the picker, click on the map</li></ul>

        <h3>🇧🇫 BFTM - Burkina Faso</h3>
        <ul>
            <li>Ellipsoid: GRS80</li>
            <li>Central meridian: 1.5° West</li>
            <li>False easting: 600,000 m</li>
            <li>Scale factor: 0.9996</li>
        </ul>

        <h3>ITRF2008</h3>
        <ul>
            <li>International Terrestrial Reference Frame 2008</li>
            <li>Ellipsoid: GRS80 (a=6378137.0, f=1/298.257222101)</li>
            <li>Prime Meridian: Greenwich</li>
            <li>Angular Unit: Degree (0.0174532925199433)</li>
            <li>EPSG: 8999</li>
        </ul>

        <h3>Clarke 1880</h3>
        <ul>
            <li>Historical ellipsoid used in Africa</li>
            <li>Semi-major axis: 6,378,249.145 m</li>
            <li>Flattening: 1/293.465</li>
            <li><b>To WGS84 (West):</b> -118,-14,218</li>
            <li><b>To WGS84 (Cameroon):</b> -166,-15,204</li>
        </ul>

        <h3>Adindan</h3>
        <ul>
            <li>Datum used in Burkina Faso and West Africa</li>
            <li>Ellipsoid: Clarke 1880</li>
            <li><b>To WGS84 (West):</b> -118,-14,218</li>
            <li><b>To WGS84 (Cameroon):</b> -166,-15,204</li>
        </ul>

        <h3>Support</h3>
        <p>Email: jeanbaptiste.kibora@tic.gov.bf</p>
        <p>Phone: +22664412514 or +22668690411</p>
        """
