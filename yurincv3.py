import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, Gdk, GLib
import dbus
from dbus.mainloop.glib import DBusGMainLoop
import threading
import time

class NotificationWindow(Gtk.Window):
    def __init__(self, app_name, summary, body):
        super().__init__(type=Gtk.WindowType.POPUP)
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_skip_taskbar_hint(True)
        self.set_keep_above(True)
        self.set_app_paintable(True)
        self.set_default_size(360, -1)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_border_width(20)

        self.apply_css()

        outer_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        outer_box.set_margin_top(15)
        outer_box.set_margin_bottom(15)
        outer_box.set_margin_start(20)
        outer_box.set_margin_end(20)

        title = Gtk.Label(label=summary)
        title.get_style_context().add_class("notif-title")
        title.set_xalign(0)

        message = Gtk.Label(label=body)
        message.get_style_context().add_class("notif-body")
        message.set_xalign(0)
        message.set_line_wrap(True)

        outer_box.pack_start(title, False, False, 0)
        outer_box.pack_start(message, False, False, 0)

        self.add(outer_box)
        self.show_all()

        # Autodistruzione dopo 5 secondi
        GLib.timeout_add_seconds(5, self.destroy)

    def apply_css(self):
        css_provider = Gtk.CssProvider()
        css_provider.load_from_path("style.css")
        screen = Gdk.Screen.get_default()
        Gtk.StyleContext.add_provider_for_screen(
            screen, css_provider, Gtk.STYLE_PROVIDER_PRIORITY_USER
        )

class NotificationServer:
    def __init__(self):
        DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SessionBus()
        self.bus.request_name('org.freedesktop.Notifications')
        self.bus.add_message_filter(self.filter_func)

    def filter_func(self, bus, message):
        if message.get_member() != "Notify":
            return
        args = message.get_args_list()
        app_name, replaces_id, app_icon, summary, body = args[:5]
        GLib.idle_add(self.show_notification, app_name, summary, body)

    def show_notification(self, app_name, summary, body):
        win = NotificationWindow(app_name, summary, body)
        win.show_all()

def start_dbus_server():
    NotificationServer()
    loop = GLib.MainLoop()
    loop.run()

if __name__ == "__main__":
    threading.Thread(target=start_dbus_server, daemon=True).start()
    Gtk.main()
