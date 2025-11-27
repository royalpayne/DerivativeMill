import sys
from PyQt5.QtWidgets import QApplication, QFileDialog, QWidget

app = QApplication(sys.argv)
window = QWidget()
window.setWindowTitle('Test File Dialog')
window.show()

options = QFileDialog.Options()
options |= QFileDialog.DontUseNativeDialog
file_path, _ = QFileDialog.getOpenFileName(window, "Select CSV", "./", "CSV (*.csv)", options=options)
print(f"Selected file: {file_path}")

sys.exit()