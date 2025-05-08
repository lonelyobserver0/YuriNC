# YuriNC

A software that read notifications on DBus and sent them via hyprctl notify

## Installation

### Dependencies

python (version 3 or newer)
pydbus (python module) installed globally, on Arch Linux use `pacman -S python-pydbus`

### Installation

- Download file `yurinc.py`
- Make it executable with `chmod +x yurinc.py`
- Make it execute on start adding `exec-once = ./yurinc` in the Hyprland configuration file
