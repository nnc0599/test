FROM mcr.microsoft.com/devcontainers/python:3.12-bookworm

# System packages for virtual display, VNC, noVNC, and Qt/X11 runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Virtual framebuffer and VNC
    xvfb \
    x11vnc \
    novnc \
    websockify \
    # Qt / X11 runtime libraries required by PySide6
    libxcb-xinerama0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-shape0 \
    libxcb-xkb1 \
    libxkbcommon-x11-0 \
    libxkbcommon0 \
    libgl1-mesa-dri \
    libegl1 \
    libdbus-1-3 \
    libfontconfig1 \
    libfreetype6 \
    # Fonts (Liberation Serif substitutes Times New Roman; Noto covers Vietnamese glyphs)
    fonts-liberation \
    fonts-noto \
    && rm -rf /var/lib/apt/lists/*
