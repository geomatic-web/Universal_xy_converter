import csv
import os
from qgis.PyQt.QtCore import QThread, pyqtSignal
from qgis.core import QgsCoordinateTransform, QgsProject, QgsPointXY

try:
    from .range_validator import CoordinateValidator
except ImportError:
    from range_validator import CoordinateValidator

class BatchProcessor(QThread):
    progress = pyqtSignal(int)
    log = pyqtSignal(str)
    finished = pyqtSignal(str)
    
    def __init__(self, file_path, config):
        super().__init__()
        self.file_path = file_path
        self.config = config
        self.validator = CoordinateValidator()
        
    def run(self):
        try:
            output_path = self.process_csv()
            self.finished.emit(output_path)
        except Exception as e:
            self.log.emit(f"Erreur fatale: {str(e)}")
            self.finished.emit("")
    
    def process_csv(self):
        """Traite un fichier CSV avec conversion libre entre CRS."""
        input_path = self.file_path
        output_path = input_path.replace('.csv', '_converti.csv')
        
        # Lecture du fichier
        rows = []
        with open(input_path, 'r', encoding='utf-8') as f:
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
        
        # Préparation des nouveaux en-têtes
        new_headers = headers.copy() if self.config.get('keep_original', True) else []
        
        target_crs_desc = self.config['target_crs'].description()
        new_headers.append(f"X_CONVERTI")
        new_headers.append(f"Y_CONVERTI")
        
        if self.config.get('add_validation', False):
            new_headers.append("DANS_BURKINA_FASO")
        
        # Transformation
        transform_context = QgsProject.instance().transformContext()
        transform = QgsCoordinateTransform(
            self.config['source_crs'], 
            self.config['target_crs'], 
            transform_context
        )
        
        total_rows = len(rows)
        processed = 0
        valid_count = 0
        invalid_count = 0
        skipped_count = 0
        
        output_rows = []
        
        for i, row in enumerate(rows):
            try:
                x = float(row[x_idx])
                y = float(row[y_idx])
                
                point = QgsPointXY(x, y)
                transformed = transform.transform(point)
                
                # Construction de la nouvelle ligne
                new_row = row.copy() if self.config.get('keep_original', True) else []
                new_row.append(f"{transformed.x():.6f}")
                new_row.append(f"{transformed.y():.6f}")
                
                # Validation si demandé
                if self.config.get('add_validation', False):
                    is_valid = self.validator.validate_point(transformed.x(), transformed.y())
                    new_row.append("OUI" if is_valid else "NON")
                    if is_valid:
                        valid_count += 1
                    else:
                        invalid_count += 1
                
                output_rows.append(new_row)
                processed += 1
                
            except ValueError as e:
                if not self.config.get('skip_invalid', True):
                    self.log.emit(f"Erreur ligne {i+2}: Valeur non numérique - {str(e)}")
                    return ""
                else:
                    skipped_count += 1
                    self.log.emit(f"⚠️ Ligne {i+2} ignorée (coordonnées invalides)")
                    
            except Exception as e:
                if not self.config.get('skip_invalid', True):
                    self.log.emit(f"Erreur ligne {i+2}: {str(e)}")
                    return ""
                else:
                    skipped_count += 1
                    self.log.emit(f"⚠️ Ligne {i+2} ignorée (erreur): {str(e)}")
            
            # Mise à jour progression
            progress_val = int((i + 1) / total_rows * 100)
            self.progress.emit(progress_val)
        
        # Écriture du fichier de sortie
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f, delimiter=self.config['separator'])
            writer.writerow(new_headers)
            writer.writerows(output_rows)
        
        # Rapport final
        self.log.emit("")
        self.log.emit("=" * 50)
        self.log.emit("📊 RAPPORT DE CONVERSION")
        self.log.emit("=" * 50)
        self.log.emit(f"✅ Lignes converties avec succès: {processed}")
        
        if self.config.get('add_validation', False):
            self.log.emit(f"   • Points dans Burkina Faso: {valid_count}")
            self.log.emit(f"   • Points hors Burkina Faso: {invalid_count}")
        
        if skipped_count > 0:
            self.log.emit(f"⚠️ Lignes ignorées (erreurs): {skipped_count}")
        
        self.log.emit(f"📁 Fichier de sortie: {os.path.basename(output_path)}")
        self.log.emit("=" * 50)
        
        return output_path