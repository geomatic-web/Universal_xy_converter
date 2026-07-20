import csv
import os
import re
from qgis.PyQt.QtCore import QThread, pyqtSignal
from qgis.core import QgsCoordinateTransform, QgsProject, QgsPointXY

from .i18n import tr


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

    def run(self):
        try:
            output_path = self.process_csv()
            self.finished.emit(output_path)
        except Exception as e:
            self.log.emit(f"Erreur fatale: {str(e)}")
            self.finished.emit("")

    def process_csv(self):
        input_path = self.file_path
        output_path = input_path.replace(".csv", "_converti.csv")

        rows = []
        with open(input_path, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f, delimiter=self.config["separator"])
            headers = next(reader)
            rows = list(reader)

        # Messages de début
        self.log.emit(tr("batch_start"))
        self.log.emit(f"{tr('batch_file')} {os.path.basename(input_path)}")
        self.log.emit(
            f"{tr('batch_format')} {self.config.get('input_format', 'Degrés décimaux (DD)')}"
        )
        self.log.emit("")

        if self.config["x_column"] not in headers:
            self.log.emit(f"Erreur: Colonne '{self.config['x_column']}' non trouvée")
            return ""

        if self.config["y_column"] not in headers:
            self.log.emit(f"Erreur: Colonne '{self.config['y_column']}' non trouvée")
            return ""

        x_idx = headers.index(self.config["x_column"])
        y_idx = headers.index(self.config["y_column"])

        new_headers = headers.copy() if self.config.get("keep_original", True) else []
        new_headers.append("X_CONVERTI")
        new_headers.append("Y_CONVERTI")

        transform = QgsCoordinateTransform(
            self.config["source_crs"],
            self.config["target_crs"],
            QgsProject.instance().transformContext(),
        )

        input_format = self.config.get("input_format", "Degrés décimaux (DD)")

        total_rows = len(rows)
        processed = 0
        errors = 0
        output_rows = []

        for i, row in enumerate(rows):
            try:
                x_str = row[x_idx].strip()
                y_str = row[y_idx].strip()

                if input_format == tr("source_format_dms"):
                    x = self.dms_to_decimal(x_str)
                    y = self.dms_to_decimal(y_str)
                    if x is None or y is None:
                        self.log.emit(
                            f"⚠️ Ligne {i + 2}: format DMS invalide ('{x_str}', '{y_str}')"
                        )
                        errors += 1
                        continue
                elif input_format == tr("source_format_m"):
                    x = float(x_str)
                    y = float(y_str)
                else:
                    x = float(x_str)
                    y = float(y_str)

                point = QgsPointXY(x, y)
                transformed = transform.transform(point)

                new_row = row.copy() if self.config.get("keep_original", True) else []
                new_row.append(f"{transformed.x():.6f}")
                new_row.append(f"{transformed.y():.6f}")

                output_rows.append(new_row)
                processed += 1

            except ValueError as e:
                if not self.config.get("skip_invalid", True):
                    self.log.emit(f"Erreur ligne {i + 2}: {str(e)}")
                    return ""
                else:
                    errors += 1
                    self.log.emit(f"⚠️ Ligne {i + 2} ignorée: valeur non numérique")

            except Exception as e:
                if not self.config.get("skip_invalid", True):
                    self.log.emit(f"Erreur ligne {i + 2}: {str(e)}")
                    return ""
                else:
                    errors += 1
                    self.log.emit(f"⚠️ Ligne {i + 2} ignorée: {str(e)}")

            if total_rows > 0:
                self.progress.emit(int((i + 1) / total_rows * 100))

        with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f, delimiter=self.config["separator"])
            writer.writerow(new_headers)
            writer.writerows(output_rows)

        self.log.emit("")
        self.log.emit("=" * 50)
        self.log.emit(tr("batch_report"))
        self.log.emit("=" * 50)
        self.log.emit(f"{tr('batch_converted')} {processed}")
        if errors > 0:
            self.log.emit(f"{tr('batch_skipped')} {errors}")
        self.log.emit(f"{tr('batch_file_output')} {os.path.basename(output_path)}")
        self.log.emit("=" * 50)

        return output_path
