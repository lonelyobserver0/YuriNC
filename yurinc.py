#!/usr/bin/env python3
import asyncio
from dbus_next.aio import MessageBus
from dbus_next.service import ServiceInterface, method
import subprocess

class NotificationInterceptor(ServiceInterface):
    def __init__(self):
        super().__init__('org.freedesktop.Notifications')

    @method()
    async def Notify(self, app_name: 's', replaces_id: 'u', app_icon: 's', summary: 's',
                     body: 's', actions: 'as', hints: 'a{sv}', expire_timeout: 'i') -> 'u':

        # Messaggio finale
        message = f"{summary}: {body}" if body else summary

        # Imposta l'icona in base ad app_name o hints (puoi migliorare qui)
        icon_map = {
            "error": 3,
            "warning": 0,
            "info": 1,
            "ok": 5,
        }
        icon = 1  # default: Info
        for key in icon_map:
            if key in app_name.lower():
                icon = icon_map[key]
                break

        # Imposta durata (fall back a 3000ms)
        duration = max(1000, expire_timeout) if expire_timeout > 0 else 3000

        # Colore (usa 0 per predefinito, puoi cambiarlo)
        color = "0"

        # Mostra notifica
        subprocess.run(["hyprctl", "notify", str(icon), str(duration), color, message])

        return 0  # ID notifica

async def main():
    bus = await MessageBus().connect()
    interface = NotificationInterceptor()

    # Prendi possesso del nome DBus
    await bus.request_name("org.freedesktop.Notifications")

    # Esporta l'interfaccia al path corretto
    bus.export('/org/freedesktop/Notifications', interface)

    print("✅ hyprctl-notify bridge attivo.")
    await asyncio.get_event_loop().create_future()


if __name__ == '__main__':
    asyncio.run(main())
