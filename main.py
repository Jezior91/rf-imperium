"""RF Imperium v5.0 MAX — Entry Point"""
import sys
import os

# Ensure local packages are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtCore import Qt
except ImportError:
    print("ERROR: PyQt6 nie jest zainstalowany.")
    print("Uruchom: pip install PyQt6 pyqtgraph numpy scipy")
    sys.exit(1)

from src.ui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("RF Imperium v5.0 MAX")
    app.setOrganizationName("RF Imperium")
    
    # High DPI
    try:
        app.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    except AttributeError:
        pass

    window = MainWindow(config_path="config.json")
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
