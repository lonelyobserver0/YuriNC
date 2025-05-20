import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib
import subprocess
import threading

class Notification(Gtk.Window):
    def __init__(self, summary, body):
        super().__init__(type=Gtk.WindowType.POPUP)
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_border_width(10)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_default_size(300, -1)

        # Carica lo stile CSS
        self.apply_css()

        # Contenuto della notifica
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.add(box)

        title = Gtk.Label(label=summary)
        title.get_style_context().add_class("title")
        box.pack_start(title, False, False, 0)

        message = Gtk.Label(label=body)
        message.get_style_context().add_class("message")
        box.pack_start(message, False, False, 0)

        self.show_all()
        GLib.timeout_add_seconds(5, self.destroy)  # Chiude la notifica dopo 5 secondi

    def apply_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_path("style.css")
        screen = Gdk.Screen.get_default()
        Gtk.StyleContext.add_provider_for_screen(
            screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

def listen_for_notifications():
    import dbus
    from dbus.mainloop.glib import DBusGMainLoop

    DBusGMainLoop(set_as_default=True)
    bus = dbus.SessionBus()

    def notify_callback(app_name, replaces_id, app_icon, summary, body, actions, hints, expire_timeout):
        GLib.idle_add(Notification, summary, body)

    bus.add_signal_receiver(
        notify_callback,
        dbus_interface="org.freedesktop.Notifications",
        signal_name="Notify"
    )

    loop = GLib.MainLoop()
    loop.run()

if __name__ == "__main__":
    threading.Thread(target=listen_for_notifications, daemon=True).start()
    Gtk.main()
