# YuriNC

## yuriadapter.py
A software that read notifications on DBus and sent them via hyprctl notify

## yurind.py
A real Notification Daemon (ND) that use style from .config/yurind/style.css

## Installation

### Dependencies

python (version 3 or newer)
pydbus (python module) installed globally, on Arch Linux use `pacman -S python-pydbus`
(ONLY FOR yurind) gobject (python module) installed globally, on Arch Linux use `pacman -S python-gobject`

### Installation

- Download file `yurind.py` or `yuriadapter.py`
- Make it execute on start adding `exec-once = python3 path/to/yurind` or `exec-once =python3 path/to/yuriadapter` in the Hyprland configuration file
