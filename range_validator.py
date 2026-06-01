class CoordinateValidator:
    """
    Valide si les coordonnées BFTM se trouvent dans les limites du Burkina Faso.
    """
    
    def __init__(self):
        # Limites approximatives du Burkina Faso en BFTM (mètres)
        self.limits = {
            'x_min': 100000,   # Est minimum
            'x_max': 900000,   # Est maximum
            'y_min': 800000,   # Nord minimum
            'y_max': 1600000   # Nord maximum
        }
        
        # Limites géographiques en WGS84 (degrés)
        self.geo_limits = {
            'lon_min': -5.5,   # Longitude ouest
            'lon_max': 2.5,    # Longitude est
            'lat_min': 9.5,    # Latitude sud
            'lat_max': 15.5    # Latitude nord
        }
    
    def validate_point(self, x, y):
        """
        Valide si un point (x,y) en BFTM est dans les limites du Burkina Faso.
        """
        return (self.limits['x_min'] <= x <= self.limits['x_max'] and
                self.limits['y_min'] <= y <= self.limits['y_max'])
    
    def validate_point_geo(self, lon, lat):
        """
        Valide si un point (lon,lat) en WGS84 est dans les limites du Burkina Faso.
        """
        return (self.geo_limits['lon_min'] <= lon <= self.geo_limits['lon_max'] and
                self.geo_limits['lat_min'] <= lat <= self.geo_limits['lat_max'])
    
    def get_bounding_box(self):
        """Retourne la boîte englobante du Burkina Faso en BFTM."""
        return self.limits.copy()