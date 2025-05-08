#!/usr/bin/env python3
import asyncio
import subprocess
from dbus_next.aio import MessageBus
from dbus_next.service import ServiceInterface, method
from dbus_next import Variant

class NotificationInterceptor(ServiceInterface):
    def __init__(self):
        super().__init__('org.freedesktop.Notifications')

    @method()
    async def Notify(self, app_name: 's', replaces_id: 'u', app_icon: 's', summary: 's',
                     body: 's', actions: 'as', hints: 'a{sv}', expire_timeout: 'i') -> 'u':

        # Costruisci il messaggio
        message = f"{summary}: {body}" if body else summary

        # Determina l'icona da usare
        icon_map = {
            "error": 3,
            "warning": 0,
            "info": 1,
            "ok": 5,
        }
        icon = 1  # default: info
        for key in icon_map:
            if key in app_name.lower():
                icon = icon_map[key]
                break

        # Imposta durata
        duration = max(1000, expire_timeout) if expire_timeout > 0 else 3000

        # Colore della notifica (0 = predefinito)
        color = "0"

        # Mostra la notifica usando hyprctl
        subprocess.run(["hyprctl", "notify", str(icon), str(duration), color, message])

        return 0  # ID della notifica (fittizio)

    @method()
    async def GetServerInformation(self) -> 'ssss':
        return ("hyprctl-bridge", "custom", "1.0", "1.2")

    @method()
    async def GetCapabilities(self) -> 'as':
        return ["body"]

    @method()
    async def CloseNotification(self, id: 'u'):
        # Ignorato, Hyprland non gestisce chiusura diretta da qui
        pass

async def main():
    bus = await MessageBus().connect()
    interface = NotificationInterceptor()

    # Richiede il nome sul bus DBus
    await bus.request_name("org.freedesktop.Notifications")

    # Esporta l'interfaccia al path corretto
    bus.export('/org/freedesktop/Notifications', interface)

    print("✅ hyprctl-notify bridge attivo.")
    await asyncio.get_event_loop().create_future()

if __name__ == '__main__':
    asyncio.run(main())
