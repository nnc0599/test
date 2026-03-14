from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget


def disable_minimize_button(window: QWidget) -> None:
    flags = window.windowFlags()
    has_maximize = bool(flags & Qt.WindowMaximizeButtonHint)
    has_context_help = bool(flags & Qt.WindowContextHelpButtonHint)

    window.setWindowFlag(Qt.CustomizeWindowHint, True)
    window.setWindowFlag(Qt.WindowTitleHint, True)
    window.setWindowFlag(Qt.WindowSystemMenuHint, True)
    window.setWindowFlag(Qt.WindowCloseButtonHint, True)
    window.setWindowFlag(Qt.WindowMaximizeButtonHint, has_maximize)
    window.setWindowFlag(Qt.WindowContextHelpButtonHint, has_context_help)
    window.setWindowFlag(Qt.WindowMinimizeButtonHint, False)
