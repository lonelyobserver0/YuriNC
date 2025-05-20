#!/usr/bin/env python3
from pydbus import SessionBus
from gi.repository import GLib
import subprocess

# Mappa urgenze -> icona Hyprland
URGENCY_TO_ICON = {
    0: 2,  # Low    → Hint
    1: 1,  # Normal → Info
    2: 0   # Critical → Warning
}

class NotificationDaemon:
    """
    <node>
        <interface name='org.freedesktop.Notifications'>
            <method name='Notify'>
                <arg type='s' name='app_name' direction='in'/>
                <arg type='u' name='replaces_id' direction='in'/>
                <arg type='s' name='app_icon' direction='in'/>
                <arg type='s' name='summary' direction='in'/>
                <arg type='s' name='body' direction='in'/>
                <arg type='as' name='actions' direction='in'/>
                <arg type='a{sv}' name='hints' direction='in'/>
                <arg type='i' name='expire_timeout' direction='in'/>
                <arg type='u' name='id' direction='out'/>
            </method>
            <method name='CloseNotification'>
                <arg type='u' name='id' direction='in'/>
            </method>
            <method name='GetCapabilities'>
                <arg type='as' name='capabilities' direction='out'/>
            </method>
            <method name='GetServerInformation'>
                <arg type='s' name='name' direction='out'/>
                <arg type='s' name='vendor' direction='out'/>
                <arg type='s' name='version' direction='out'/>
                <arg type='s' name='spec_version' direction='out'/>
            </method>
        </interface>
    </node>
    """

    def Notify(self, app_name, replaces_id, app_icon, summary, body,
               actions, hints, expire_timeout):
        urgency = hints.get("urgency", 1)
        icon = URGENCY_TO_ICON.get(urgency, 6)
        message = f"{summary}: {body}" if body else summary
        timeout = expire_timeout if expire_timeout > 0 else 5000

        try:
            subprocess.run([
                "hyprctl", "notify",
                str(icon),
                str(timeout),
                "0",
                message
            ])
        except Exception as e:
            print(f"Errore invocando hyprctl: {e}")

        return 0  # puoi generare un ID incrementale se vuoi

    def CloseNotification(self, id):
        pass  # non gestiamo chiusura per ora

    def GetCapabilities(self):
        return ["body"]

    def GetServerInformation(self):
        return ("HyprlandNotifier", "Custom", "1.0", "1.2")

# Avvio
bus = SessionBus()
bus.publish("org.freedesktop.Notifications",
            ("/org/freedesktop/Notifications", NotificationDaemon()))

print("In ascolto per notifiche...")
GLib.MainLoop().run()
