import csv
import os
import re
from qgis.PyQt.QtCore import QThread, pyqtSignal
from qgis.core import QgsCoordinateTransform, QgsProject, QgsPointXY


class BatchProcessor(QThread):
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    finished = pyqtSignal(str)

    def __init__(self, file_path, config, dialog=None):
        super().__init__()
        self.file_path = file_path
        self.config = config
        self.dialog = dialog

    def dms_to_decimal(self, dms_string):
        """Convertit une chaîne DMS en degrés décimaux (supporte O pour Ouest et E pour Est)"""
        try:
            if not dms_string or str(dms_string).strip() == "":
                return None

            dms_string = str(dms_string).strip().upper()

            # Si c'est déjà un nombre décimal
            try:
                val = float(dms_string)
                return val
            except ValueError:
                pass

            # Direction : N/S/E/W/O (O pour Ouest en français)
            # O = Ouest (français), W = West (anglais)
            # E = Est (français/anglais) - positif par défaut
            # N = Nord (français/anglais) - positif par défaut
            direction = 1.0
            if 'S' in dms_string or 'W' in dms_string or 'O' in dms_string:
                direction = -1.0
            # Note: 'N' et 'E' sont positifs par défaut (direction = 1.0)

            # Nettoyer la chaîne (supprimer les symboles et lettres de direction)
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

    def run(self):
        try:
            output_path = self.process_csv()
            self.finished.emit(output_path)
        except Exception as e:
            self.log.emit(f"Erreur fatale: {str(e)}")
            self.finished.emit("")

    def process_csv(self):
        """Traite un fichier CSV avec conversion DMS ou Mètres si nécessaire"""
        input_path = self.file_path
        output_path = input_path.replace('.csv', '_converti.csv')

        # Lecture du fichier
        rows = []
        with open(input_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f, delimiter=self.config['separator'])
            headers = next(reader)
            rows = list(reader)

        # Vérification des colonnes
        if self.config['x_column'] not in headers:
            self.log.emit(f"Erreur: Colonne '{self.config['x_column']}' non trouvée")
            return ""

        if self.config['y_column'] not in headers:
            self.log.emit(f"Erreur: Colonne '{self.config['y_column']}' non trouvée")
            return ""

        x_idx = headers.index(self.config['x_column'])
        y_idx = headers.index(self.config['y_column'])

        # Nouveaux en-têtes
        new_headers = headers.copy() if self.config.get('keep_original', True) else []
        new_headers.append("X_CONVERTI")
        new_headers.append("Y_CONVERTI")

        # Transformation
        transform = QgsCoordinateTransform(
            self.config['source_crs'],
            self.config['target_crs'],
            QgsProject.instance().transformContext()
        )

        # Format d'entrée
        input_format = self.config.get('input_format', 'Degrés décimaux (DD)')

        total_rows = len(rows)
        processed = 0
        errors = 0

        output_rows = []

        for i, row in enumerate(rows):
            try:
                # Lire les coordonnées
                x_str = row[x_idx].strip()
                y_str = row[y_idx].strip()

                # Convertir selon le format
                if input_format == "Degrés/Minutes/Secondes (DMS)":
                    x = self.dms_to_decimal(x_str)
                    y = self.dms_to_decimal(y_str)
                    if x is None or y is None:
                        self.log.emit(f"⚠️ Ligne {i + 2}: format DMS invalide ('{x_str}', '{y_str}')")
                        errors += 1
                        continue
                elif input_format == "Mètres (m)":
                    # Déjà en mètres, conversion directe
                    x = float(x_str)
                    y = float(y_str)
                else:  # Degrés décimaux (DD)
                    x = float(x_str)
                    y = float(y_str)

                # Conversion CRS
                point = QgsPointXY(x, y)
                transformed = transform.transform(point)

                # Construction nouvelle ligne
                new_row = row.copy() if self.config.get('keep_original', True) else []
                new_row.append(f"{transformed.x():.6f}")
                new_row.append(f"{transformed.y():.6f}")

                output_rows.append(new_row)
                processed += 1

            except ValueError as e:
                if not self.config.get('skip_invalid', True):
                    self.log.emit(f"Erreur ligne {i + 2}: {str(e)}")
                    return ""
                else:
                    errors += 1
                    self.log.emit(f"⚠️ Ligne {i + 2} ignorée: valeur non numérique")

            except Exception as e:
                if not self.config.get('skip_invalid', True):
                    self.log.emit(f"Erreur ligne {i + 2}: {str(e)}")
                    return ""
                else:
                    errors += 1
                    self.log.emit(f"⚠️ Ligne {i + 2} ignorée: {str(e)}")

            # Progression
            if total_rows > 0:
                self.progress.emit(int((i + 1) / total_rows * 100))

        # Écriture du fichier
        with open(output_path, 'w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f, delimiter=self.config['separator'])
            writer.writerow(new_headers)
            writer.writerows(output_rows)

        # Rapport
        self.log.emit("")
        self.log.emit("=" * 50)
        self.log.emit("📊 RAPPORT DE CONVERSION")
        self.log.emit("=" * 50)
        self.log.emit(f"✅ Lignes converties: {processed}")
        if errors > 0:
            self.log.emit(f"⚠️ Lignes ignorées: {errors}")
        self.log.emit(f"📁 Fichier: {os.path.basename(output_path)}")
        self.log.emit("=" * 50)

        return output_path
