#!/usr/bin/env python3
import gi
gi.require_version("Gtk", "3.0")
gi.require_version("GtkLayerShell", "0.1")
from gi.repository import Gtk, Gdk, GLib, GObject, GtkLayerShell

import dbus
import dbus.service
import dbus.mainloop.glib
import os
from pathlib import Path

CONFIG_DIR = Path.home() / ".config" / "yurind"
CSS_PATH = CONFIG_DIR / "style.css"

class NotificationWindow(Gtk.Window):
    def __init__(self, summary, body, icon, stack):
        super().__init__()
        self.stack = stack
        self.set_decorated(False)
        self.set_resizable(False)
        self.set_app_paintable(True)
        self.set_visual(self.get_screen().get_rgba_visual())
        self.set_name("notification")
        self.set_opacity(0.0)

        # LayerShell: top-right stacking
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, True)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.TOP, 20 + len(stack) * 100)
        GtkLayerShell.set_margin(self, GtkLayerShell.Edge.RIGHT, 20)

        # Layout
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        box.set_border_width(12)
        box.get_style_context().add_class("notification-box")

        # Icon
        if icon:
            image = Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.DIALOG)
            box.pack_start(image, False, False, 0)

        # Text
        text_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)

        title = Gtk.Label(label=f"<b>{summary}</b>")
        title.set_use_markup(True)
        title.set_xalign(0)
        text_box.pack_start(title, False, False, 0)

        body_label = Gtk.Label(label=body)
        body_label.set_line_wrap(True)
        body_label.set_xalign(0)
        text_box.pack_start(body_label, False, False, 0)

        box.pack_start(text_box, True, True, 0)

        # Wrap it in a frame
        frame = Gtk.Frame()
        frame.add(box)
        frame.set_shadow_type(Gtk.ShadowType.IN)
        frame.get_style_context().add_class("notification-frame")

        self.add(frame)
        self.connect("destroy", self.on_destroy)
        self.connect("button-press-event", self.on_click)
        self.show_all()

        # CSS
        self.load_css()

        # Fade-in
        self.fade_in()

        # Auto close after 4s with fade-out
        GLib.timeout_add_seconds(4, self.fade_out)

    def load_css(self):
        if not CSS_PATH.exists():
            return
        provider = Gtk.CssProvider()
        provider.load_from_path(str(CSS_PATH))
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(),
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

    def fade_out(self):
        def step(opacity):
            if opacity <= 0:
                self.destroy()
                return False
            self.set_opacity(opacity)
            GLib.timeout_add(15, step, opacity - 0.05)
            return False
        step(1.0)
        return False

    def on_destroy(self, *_):
        if self in self.stack:
            self.stack.remove(self)
            for i, win in enumerate(self.stack):
                GtkLayerShell.set_margin(win, GtkLayerShell.Edge.TOP, 20 + i * 100)

    def on_click(self, *_):
        print("Notifica cliccata!")
        self.fade_out()

class NotificationService(dbus.service.Object):
    def __init__(self, bus):
        self.stack = []
        name = dbus.service.BusName("org.freedesktop.Notifications", bus)
        super().__init__(name, "/org/freedesktop/Notifications")

    @dbus.service.method("org.freedesktop.Notifications",
                         in_signature="susssasa{sv}i", out_signature="u")
    def Notify(self, app_name, replaces_id, app_icon, summary, body, actions, hints, expire_timeout):
        GLib.idle_add(self.show_notification, summary, body, app_icon)
        return 0

    def show_notification(self, summary, body, icon):
        win = NotificationWindow(summary, body, icon, self.stack)
        self.stack.append(win)
        return False

    @dbus.service.method("org.freedesktop.Notifications", out_signature="as")
    def GetCapabilities(self):
        return ["body", "actions"]

    @dbus.service.method("org.freedesktop.Notifications", out_signature="a{sv}")
    def GetServerInformation(self):
        return {
            "name": "YuriNotify",
            "vendor": "OpenAI",
            "version": "1.0",
            "spec_version": "1.2"
        }

def main():
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    session_bus = dbus.SessionBus()
    NotificationService(session_bus)
    GLib.MainLoop().run()

if __name__ == "__main__":
    main()
