# Yuri Notifications

## Yuri Notification Daemon
File `yurind.py`  
A real notification daemon that use style from .config/yurind/style.css

## Yuri Notification Adapter
File `yuriadapter.py`  
A software that read notifications on DBus and sent them via hyprctl notify

## Installation

### Dependencies

- *python* (version 3 or newer)  
- *pydbus* (python module) installed globally, on Arch Linux use `pacman -S python-pydbus`  
- <u>(ONLY FOR Yuri Notification Daemon)</u> *gobject* (python module) installed globally, on Arch Linux use `pacman -S python-gobject`

### Installation

- Download file `yurind.py` or `yuriadapter.py`
- Make it execute on start
  - Via Hyprland
    - add `exec-once = python3 path/to/yurind` or `exec-once =python3 path/to/yuriadapter` in Hyprland configuration file
  - Via System
    - Create a systemd service or use your system workaround
