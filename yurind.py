#!/usr/bin/env python3

# From gtk4-layer-shell docs:
#from ctypes import CDLL
#CDLL('libgtk4-layer-shell.so')

import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")

from gi.repository import Gtk, Gdk, GLib, GObject, Gtk4LayerShell
import os
from pathlib import Path
import dbus
import dbus.service
import dbus.mainloop.glib


CONFIG_DIR = Path.home() / ".config" / "yurind"
CSS_PATH = CONFIG_DIR / "style.css"

class NotificationWindow(Gtk.Window):
    def __init__(self, nid, summary, body, icon, stack, actions, service):
        super().__init__()
        self.nid = nid
        self.stack = stack
        self.service = service
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_name("notification")
        self.set_opacity(0.0)
        self.set_default_size(300, -1)

        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, True)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, 20 + len(stack) * 100)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.RIGHT, 20)

        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12,
                      margin_top=12, margin_bottom=12, margin_start=12, margin_end=12)
        box.get_style_context().add_class("notification-box")

        if icon:
            image = Gtk.Image.new_from_icon_name(icon)
            box.append(image)

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)

        title = Gtk.Label(label=f"<b>{summary}</b>", use_markup=True, xalign=0)
        content_box.append(title)

        body_label = Gtk.Label(label=body, wrap=True, xalign=0)
        content_box.append(body_label)

        if actions:
            actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            for i in range(0, len(actions), 2):
                action_key = actions[i]
                label = actions[i+1]
                button = Gtk.Button(label=label)
                button.connect("clicked", self.on_action_clicked, action_key)
                actions_box.append(button)
            content_box.append(actions_box)

        box.append(content_box)

        frame = Gtk.Frame()
        frame.set_child(box)
        frame.set_shadow_type(Gtk.ShadowType.IN)
        frame.get_style_context().add_class("notification-frame")

        self.set_child(frame)

        self.connect("close-request", self.on_close_request)
        self.connect("button-press-event", self.on_click)

        self.show()
        self.load_css()
        self.fade_in()
        # Auto chiusura dopo 4 secondi, motivo = 1 (expired)
        GLib.timeout_add_seconds(4, self.fade_out, 1)

    def load_css(self):
        if not CSS_PATH.exists():
            return
        provider = Gtk.CssProvider()
        provider.load_from_path(str(CSS_PATH))
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(),
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def fade_in(self):
        def step(opacity):
            if opacity >= 1.0:
                return False
            self.set_opacity(opacity)
            GLib.timeout_add(15, step, opacity + 0.05)
            return False
        step(0.05)

    def fade_out(self, reason=3):
        def step(opacity):
            if opacity <= 0:
                self.close()
                # Notifica chiusa con motivo 'reason'
                self.service.NotificationClosed(self.nid, reason)
                return False
            self.set_opacity(opacity)
            GLib.timeout_add(15, step, opacity - 0.05)
            return False
        step(1.0)
        return False

    def on_close_request(self, *_):
        if self in self.stack:
            self.stack.remove(self)
            for i, win in enumerate(self.stack):
                GtkLayerShell.set_margin(win, GtkLayerShell.Edge.TOP, 20 + i * 100)
        # Emissione segnale con motivo 2 = dismissed by user
        self.service.NotificationClosed(self.nid, 2)
        return False

    def on_click(self, *_):
        print(f"Notifica {self.nid} cliccata!")
        self.fade_out(2)  # dismissed by user

    def on_action_clicked(self, button, action_key):
        print(f"Azione invocata: {action_key} su notifica {self.nid}")
        bus = dbus.SessionBus()
        obj = bus.get_object("org.freedesktop.Notifications", "/org/freedesktop/Notifications")
        iface = dbus.Interface(obj, "org.freedesktop.Notifications")
        iface.ActionInvoked(self.nid, action_key)
        self.fade_out(2)  # dismissed by user


class NotificationService(dbus.service.Object):
    def __init__(self, bus):
        self.stack = []
        self.notifications = {}  # nid -> NotificationWindow
        self.next_id = 1
        name = dbus.service.BusName("org.freedesktop.Notifications", bus)
        super().__init__(name, "/org/freedesktop/Notifications")

    @dbus.service.method("org.freedesktop.Notifications", in_signature="susssasa{sv}i", out_signature="u")
    def Notify(self, app_name, replaces_id, app_icon, summary, body, actions, hints, expire_timeout):
        nid = self.next_id
        self.next_id += 1

        if replaces_id != 0 and replaces_id in self.notifications:
            old_win = self.notifications[replaces_id]
            GLib.idle_add(old_win.close)
            del self.notifications[replaces_id]
            nid = replaces_id

        GLib.idle_add(self.show_notification, nid, summary, body, app_icon, actions)
        return dbus.UInt32(nid)


    def show_notification(self, nid, summary, body, icon, actions):
        win = NotificationWindow(nid, summary, body, icon, self.stack, actions, self)
        self.notifications[nid] = win
        self.stack.append(win)
        return False

    @dbus.service.method("org.freedesktop.Notifications", out_signature="as")
    def GetCapabilities(self):
        return ["body", "actions"]

    @dbus.service.method("org.freedesktop.Notifications", out_signature="a{sv}")
    def GetServerInformation(self):
        return {
            "name": "YuriNotify",
            "vendor": "LonelyObserver0",
            "version": "1.0",
            "spec_version": "1.2"
        }

    @dbus.service.signal("org.freedesktop.Notifications", signature="uu")
    def NotificationClosed(self, nid, reason):
        pass


def main():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    session_bus = dbus.SessionBus()
    NotificationService(session_bus)
    GLib.MainLoop().run()

def main1():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SessionBus()
    service = NotificationService(bus)

    loop = GLib.MainLoop()
    loop.run()

if __name__ == "__main__":
    main1()
