from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget


def disable_minimize_button(window: QWidget) -> None:
    flags = window.windowFlags()
    flags &= ~Qt.WindowMinimizeButtonHint
    window.setWindowFlags(flags)
