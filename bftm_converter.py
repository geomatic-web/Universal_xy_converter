import os
from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
from .bftm_converter_dialog import UniversalXYConverterDialog


class UniversalXYConverter:
    def __init__(self, iface):
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.actions = []
        self.menu = 'Universal XY Converter'
        self.toolbar = self.iface.addToolBar('Universal XY Converter')
        self.toolbar.setObjectName('UniversalXYConverter')

    def initGui(self):
        """Crée l'entrée dans le menu et la barre d'outils."""
        # Chemin vers l'icône
        icon_path = os.path.join(self.plugin_dir, 'icon.png')

        # Si l'icône n'existe pas, utiliser l'icône par défaut
        if os.path.exists(icon_path):
            icon = QIcon(icon_path)
        else:
            # Icône par défaut (optionnel)
            icon = QIcon()

        action = QAction(icon, 'Universal XY Converter', self.iface.mainWindow())
        action.triggered.connect(self.run)
        self.iface.addPluginToMenu(self.menu, action)
        self.toolbar.addAction(action)
        self.actions.append(action)

    def unload(self):
        """Nettoie l'interface."""
        for action in self.actions:
            self.iface.removePluginMenu(self.menu, action)
            self.iface.removeToolBarIcon(action)
        del self.toolbar

    def run(self):
        """Affiche la boîte de dialogue de conversion."""
        dialog = UniversalXYConverterDialog(self.iface, self.plugin_dir)
        dialog.show()
        dialog.exec_()
