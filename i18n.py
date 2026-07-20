# i18n.py
# Fichier de traduction pour Universal XY Converter

from qgis.PyQt.QtCore import QLocale
from qgis.core import QgsApplication

# Dictionnaire des traductions
TRANSLATIONS = {
    "fr": {
        # Titres et onglets
        "window_title": "Convertisseur XY Universel",
        "simple_tab": "Conversion simple",
        "batch_tab": "Traitement batch",
        "interactive_tab": "Sélection interactive",
        "help_tab": "Aide",
        # Groupes
        "source_system": "Système source",
        "target_system": "Système cible",
        "coordinates": "Coordonnées à convertir",
        "result": "Résultat de la conversion",
        "source_file": "1. Fichier source",
        "column_config": "2. Configuration des colonnes",
        "crs_config": "3. Systèmes de coordonnées",
        "options": "4. Options",
        "log": "Journal",
        "display_format": "Format d'affichage",
        "interactive_result": "Coordonnées",
        # Labels
        "source_crs": "CRS source:",
        "target_crs": "CRS cible:",
        "source_format": "Format source:",
        "target_format": "Format cible:",
        "x_longitude": "X / Longitude / Est:",
        "y_latitude": "Y / Latitude / Nord:",
        "x_east": "X / Est:",
        "y_north": "Y / Nord:",
        "status": "Statut:",
        "x_column": "Colonne X / Longitude:",
        "y_column": "Colonne Y / Latitude:",
        "separator": "Séparateur CSV:",
        "source_system_label": "Système source:",
        "target_system_label": "Système cible:",
        "source_format_label": "Format source:",
        "target_crs_interactive": "Système cible:",
        "display_format_label": "Format d'affichage:",
        "source_map": "Source (carte):",
        "crs_source": "CRS source:",
        "target_format_label": "Format cible:",
        "converted": "Converti:",
        "status_label": "Statut:",
        # Placeholders
        "x_placeholder_geo": "ex: -1.5042 (longitude)",
        "y_placeholder_geo": "ex: 12.5042 (latitude)",
        "x_placeholder_proj": "ex: 679246.00 (mètres)",
        "y_placeholder_proj": "ex: 1360000.00 (mètres)",
        "x_placeholder_dms": "ex: 1°30'0\" W ou O",
        "y_placeholder_dms": "ex: 12°30'15\" N",
        "file_placeholder": "Chemin vers le fichier CSV...",
        "custom_proj_source": "ex: +proj=longlat +ellps=clrk80 +towgs84=-118,-14,218",
        "custom_proj_target": "ex: +proj=utm +zone=30 +ellps=GRS80 +units=m",
        "source_format_dd": "Degrés décimaux (DD)",
        "source_format_dms": "Degrés/Minutes/Secondes (DMS)",
        "source_format_m": "Mètres (m)",
        "target_format_dd": "Degrés décimaux (DD)",
        "target_format_dms": "Degrés/Minutes/Secondes (DMS)",
        "target_format_m": "Mètres (m)",
        # Boutons
        "convert_btn": "Convertir →",
        "swap_btn": "⟷ Échanger source/cible",
        "copy_btn": "Copier les résultats",
        "browse_btn": "Parcourir",
        "process_btn": "5. Lancer la conversion",
        "activate_btn": "Activer le sélecteur",
        "deactivate_btn": "Désactiver",
        "copy_interactive_btn": "Copier le résultat",
        # Checkboxes
        "keep_original": "Conserver les colonnes originales",
        "skip_invalid": "Ignorer les lignes invalides",
        # Messages
        "error_enter_coords": "Veuillez entrer des coordonnées",
        "error_dms_format": "✗ Format DMS invalide",
        "error_invalid_crs": "✗ CRS invalide",
        "conversion_success": "✓ Conversion réussie",
        "conversion_pending": "En attente",
        "interactive_click": "Cliquez sur la carte pour obtenir les coordonnées converties",
        "interactive_info": "Cliquez sur la carte",
        "copy_success": "Coordonnées copiées",
        "copy_result": "Résultat copié",
        "crs_swapped": "CRS échangés",
        "batch_start": "CONVERSION BATCH",
        "batch_file": "Fichier:",
        "batch_format": "Format:",
        "batch_no_file": "Veuillez sélectionner un fichier CSV",
        "batch_select_columns": "Sélectionnez les colonnes X et Y",
        "batch_completed": "Terminé:",
        "batch_report": "RAPPORT DE CONVERSION",
        "batch_converted": "Lignes converties:",
        "batch_skipped": "Lignes ignorées:",
        "batch_file_output": "Fichier:",
        "warning_dms_projected": "DMS: système projeté → mètres",
        "warning_dd_projected": "Degrés: système projeté → mètres",
        "custom_source": "Chaîne PROJ source:",
        "custom_target": "Chaîne PROJ cible:",
        # CRS names (French translations)
        "crs_bftm": "🇧🇫 BFTM (Burkina Faso) - OFFICIEL",
        "crs_wgs84": "🌍 WGS 84 (degrés)",
        "crs_wgs84_mercator": "🌍 WGS 84 (Web Mercator)",
        "crs_clarke_west": "🗺️ Clarke 1880 (degrés) - Afrique Ouest",
        "crs_clarke_cameroon": "🗺️ Clarke 1880 (degrés) - Cameroun",
        "crs_adindan_west": "🌍 Adindan (degrés) - Afrique Ouest",
        "crs_adindan_cameroon": "🌍 Adindan (degrés) - Cameroun",
        "crs_custom": "--- Personnalisé (PROJ) ---",
        "crs_load_all": "--- 🔄 Charger tous les CRS UTM (1-60) ---",
        "crs_loaded_all": "--- Tous les CRS sont chargés ---",
        "crs_clarke_utm_west": "🗺️ Clarke 1880 Ouest / UTM",
        "crs_clarke_utm_cameroon": "🗺️ Clarke 1880 Cameroun / UTM",
        "crs_adindan_utm_west": "🌍 Adindan Ouest / UTM",
        "crs_adindan_utm_cameroon": "🌍 Adindan Cameroun / UTM",
        "crs_wgs84_utm": "📐 WGS 84 / UTM zone",
        "crs_itrf2008": "🌐 ITRF2008 (degrés)",
        "crs_itrf2008_utm": "🌐 ITRF2008 / UTM zone",
        "crs_itrf2000": "🌐 ITRF2000 (degrés)",
        # Help tab
        "help_title": "Aide - Universal XY Converter",
        "help_supported_formats": "📌 Formats de coordonnées supportés",
        "help_csv_format": "Format CSV pour batch",
        "help_interactive": "Sélection interactive",
        "help_bftm": "🇧🇫 BFTM - Burkina Faso",
        "help_clarke": "Clarke 1880",
        "help_adindan": "Adindan",
        "help_support": "📞 Support",
        "help_dd": "Degrés décimaux (DD)",
        "help_dms": "Degrés/Minutes/Secondes (DMS)",
        "help_meters": "Mètres (m)",
        "help_interactive_desc": "Activez le sélecteur, cliquez sur la carte",
        "help_clarke_desc": "Ellipsoïde historique utilisé en Afrique",
        "help_adindan_desc": "Datum utilisé au Burkina Faso et Afrique de l'Ouest",
    },
    "en": {
        # Titres et onglets
        "window_title": "Universal XY Converter",
        "simple_tab": "Simple Conversion",
        "batch_tab": "Batch Processing",
        "interactive_tab": "Interactive Selection",
        "help_tab": "Help",
        # Groupes
        "source_system": "Source System",
        "target_system": "Target System",
        "coordinates": "Coordinates to Convert",
        "result": "Conversion Result",
        "source_file": "1. Source File",
        "column_config": "2. Column Configuration",
        "crs_config": "3. Coordinate Systems",
        "options": "4. Options",
        "log": "Log",
        "display_format": "Display Format",
        "interactive_result": "Coordinates",
        # Labels
        "source_crs": "Source CRS:",
        "target_crs": "Target CRS:",
        "source_format": "Source Format:",
        "target_format": "Target Format:",
        "x_longitude": "X / Longitude / East:",
        "y_latitude": "Y / Latitude / North:",
        "x_east": "X / East:",
        "y_north": "Y / North:",
        "status": "Status:",
        "x_column": "X / Longitude column:",
        "y_column": "Y / Latitude column:",
        "separator": "CSV Separator:",
        "source_system_label": "Source system:",
        "target_system_label": "Target system:",
        "source_format_label": "Source format:",
        "target_crs_interactive": "Target CRS:",
        "display_format_label": "Display format:",
        "source_map": "Source (map):",
        "crs_source": "Source CRS:",
        "target_format_label": "Target format:",
        "converted": "Converted:",
        "status_label": "Status:",
        # Placeholders
        "x_placeholder_geo": "ex: -1.5042 (longitude)",
        "y_placeholder_geo": "ex: 12.5042 (latitude)",
        "x_placeholder_proj": "ex: 679246.00 (meters)",
        "y_placeholder_proj": "ex: 1360000.00 (meters)",
        "x_placeholder_dms": "ex: 1°30'0\" W",
        "y_placeholder_dms": "ex: 12°30'15\" N",
        "file_placeholder": "Path to CSV file...",
        "custom_proj_source": "ex: +proj=longlat +ellps=clrk80 +towgs84=-118,-14,218",
        "custom_proj_target": "ex: +proj=utm +zone=30 +ellps=GRS80 +units=m",
        "source_format_dd": "Decimal Degrees (DD)",
        "source_format_dms": "Degrees/Minutes/Seconds (DMS)",
        "source_format_m": "Meters (m)",
        "target_format_dd": "Decimal Degrees (DD)",
        "target_format_dms": "Degrees/Minutes/Seconds (DMS)",
        "target_format_m": "Meters (m)",
        # Boutons
        "convert_btn": "Convert →",
        "swap_btn": "⟷ Swap source/target",
        "copy_btn": "Copy results",
        "browse_btn": "Browse",
        "process_btn": "5. Start Conversion",
        "activate_btn": "Activate picker",
        "deactivate_btn": "Deactivate",
        "copy_interactive_btn": "Copy result",
        # Checkboxes
        "keep_original": "Keep original columns",
        "skip_invalid": "Skip invalid rows",
        # Messages
        "error_enter_coords": "Please enter coordinates",
        "error_dms_format": "✗ Invalid DMS format",
        "error_invalid_crs": "✗ Invalid CRS",
        "conversion_success": "✓ Conversion successful",
        "conversion_pending": "Pending",
        "interactive_click": "Click on the map to get converted coordinates",
        "interactive_info": "Click on the map",
        "copy_success": "Coordinates copied",
        "copy_result": "Result copied",
        "crs_swapped": "CRS swapped",
        "batch_start": "BATCH CONVERSION",
        "batch_file": "File:",
        "batch_format": "Format:",
        "batch_no_file": "Please select a CSV file",
        "batch_select_columns": "Select X and Y columns",
        "batch_completed": "Completed:",
        "batch_report": "CONVERSION REPORT",
        "batch_converted": "Converted rows:",
        "batch_skipped": "Skipped rows:",
        "batch_file_output": "File:",
        "warning_dms_projected": "DMS: projected system → meters",
        "warning_dd_projected": "Degrees: projected system → meters",
        "custom_source": "Source PROJ string:",
        "custom_target": "Target PROJ string:",
        # CRS names (English)
        "crs_bftm": "🇧🇫 BFTM (Burkina Faso) - OFFICIAL",
        "crs_wgs84": "🌍 WGS 84 (degrees)",
        "crs_wgs84_mercator": "🌍 WGS 84 (Web Mercator)",
        "crs_clarke_west": "🗺️ Clarke 1880 (degrees) - West Africa",
        "crs_clarke_cameroon": "🗺️ Clarke 1880 (degrees) - Cameroon",
        "crs_adindan_west": "🌍 Adindan (degrees) - West Africa",
        "crs_adindan_cameroon": "🌍 Adindan (degrees) - Cameroon",
        "crs_custom": "--- Custom (PROJ) ---",
        "crs_load_all": "--- 🔄 Load all UTM CRS (1-60) ---",
        "crs_loaded_all": "--- All CRS loaded ---",
        "crs_clarke_utm_west": "🗺️ Clarke 1880 West / UTM",
        "crs_clarke_utm_cameroon": "🗺️ Clarke 1880 Cameroon / UTM",
        "crs_adindan_utm_west": "🌍 Adindan West / UTM",
        "crs_adindan_utm_cameroon": "🌍 Adindan Cameroon / UTM",
        "crs_wgs84_utm": "📐 WGS 84 / UTM zone",
        "crs_itrf2008": "🌐 ITRF2008 (degrees)",
        "crs_itrf2008_utm": "🌐 ITRF2008 / UTM zone",
        "crs_itrf2000": "🌐 ITRF2000 (degrees)",
        # Help tab
        "help_title": "Help - Universal XY Converter",
        "help_supported_formats": "Supported coordinate formats",
        "help_csv_format": "CSV format for batch",
        "help_interactive": "Interactive selection",
        "help_bftm": "🇧🇫 BFTM - Burkina Faso",
        "help_clarke": "Clarke 1880",
        "help_adindan": "Adindan",
        "help_support": "📞 Support",
        "help_dd": "Decimal Degrees (DD)",
        "help_dms": "Degrees/Minutes/Seconds (DMS)",
        "help_meters": "Meters (m)",
        "help_interactive_desc": "Activate the picker, click on the map",
        "help_clarke_desc": "Historical ellipsoid used in Africa",
        "help_adindan_desc": "Datum used in Burkina Faso and West Africa",
    },
}


class Translator:
    """Gestionnaire de traduction pour le plugin"""

    _instance = None
    _current_lang = None
    _translations = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Translator, cls).__new__(cls)
            cls._instance._init_translator()
        return cls._instance

    def _init_translator(self):
        """Initialise le traducteur avec la langue QGIS"""
        self._translations = TRANSLATIONS
        self._current_lang = self.get_qgis_language()

    def get_qgis_language(self):
        """Récupère la langue de QGIS"""
        try:
            # Essayer via QgsApplication
            lang = QgsApplication.locale()
            if lang:
                lang = lang[:2]  # Prendre les 2 premières lettres (fr, en, es, etc.)
                if lang in self._translations:
                    return lang
        except BaseException:
            pass

        # Essayer via QLocale
        try:
            locale = QLocale.system().name()
            lang = locale[:2]
            if lang in self._translations:
                return lang
        except BaseException:
            pass

        # Par défaut: français
        return "fr"

    def get_language(self):
        """Retourne la langue actuelle"""
        return self._current_lang

    def set_language(self, lang):
        """Change la langue"""
        if lang in self._translations:
            self._current_lang = lang
            return True
        return False

    def tr(self, key):
        """Traduit une clé dans la langue actuelle"""
        lang_dict = self._translations.get(self._current_lang, self._translations["fr"])
        return lang_dict.get(key, key)

    def tr_fallback(self, key, fallback_key=None):
        """Traduit avec fallback vers une autre clé"""
        value = self.tr(key)
        if value == key and fallback_key:
            return self.tr(fallback_key)
        return value


# Fonction globale pour faciliter l'utilisation
def tr(key):
    """Fonction de traduction globale"""
    return Translator().tr(key)


def get_language():
    """Retourne la langue actuelle"""
    return Translator().get_language()


def set_language(lang):
    """Change la langue"""
    return Translator().set_language(lang)
