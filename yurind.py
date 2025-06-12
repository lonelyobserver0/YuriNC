import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")

# È fondamentale caricare esplicitamente la libreria gtk4-layer-shell
# prima di qualsiasi inizializzazione di GTK o Gtk4LayerShell.
# Questo garantisce che le funzionalità del layer shell siano disponibili.
from ctypes import CDLL
CDLL('libgtk4-layer-shell.so')

from gi.repository import Gtk, Gdk, GLib, GObject, Gtk4LayerShell
import os
from pathlib import Path
import dbus
import dbus.service
import dbus.mainloop.glib

# Percorsi per la configurazione e il CSS
CONFIG_DIR = Path.home() / ".config" / "yurind"
CSS_PATH = CONFIG_DIR / "style.css"

class NotificationWindow(Gtk.Window):
    """
    Rappresenta una singola finestra di notifica GTK4.
    Gestisce la visualizzazione, le animazioni, le interazioni e il posizionamento.
    """
    def __init__(self, nid, summary, body, icon, stack, actions, service):
        super().__init__()
        self.set_app_id("yurinotify-notification")
        self.nid = nid  # ID univoco della notifica
        self.stack = stack  # Riferimento allo stack globale delle notifiche attive
        self.service = service  # Riferimento al servizio D-Bus per la comunicazione
        self.auto_close_timeout_id = None # ID per il timer di auto-chiusura

        # Configurazione base della finestra GTK
        self.set_decorated(False) # Rimuove bordi e barra del titolo
        self.set_resizable(False) # Impedisce il ridimensionamento
        self.set_name("notification") # Nome per il targeting CSS
        self.set_opacity(0.0) # Inizialmente trasparente per l'animazione
        self.set_default_size(300, -1) # Larghezza fissa, altezza automatica

        # Inizializzazione e configurazione con gtk4-layer-shell
        Gtk4LayerShell.init_for_window(self)
        Gtk4LayerShell.set_layer(self, Gtk4LayerShell.Layer.OVERLAY) # Sempre sopra altre finestre
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.TOP, True) # Ancoraggio in alto
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.RIGHT, True) # Ancoraggio a destra
        # Margine iniziale basato sulla posizione nello stack
        Gtk4LayerShell.set_margin(self, Gtk4LayerShell.Edge.TOP, 20 + len(stack) * 100)
        Gtk4LayerShell.set_margin(self, Gtk4LayerShell.Edge.RIGHT, 20)

        # Costruzione dell'interfaccia utente della notifica
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12,
                      margin_top=12, margin_bottom=12, margin_start=12, margin_end=12)
        box.get_style_context().add_class("notification-box")

        if icon:
            try:
                # Tenta di caricare l'icona dal nome
                image = Gtk.Image.new_from_icon_name(icon)
                box.append(image)
            except GLib.Error as e:
                print(f"Avviso: Errore nel caricamento dell'icona '{icon}': {e}")
                # Continua senza icona in caso di errore

        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)

        # Titolo in grassetto
        title = Gtk.Label(label=f"<b>{summary}</b>", use_markup=True, xalign=0)
        content_box.append(title)

        # Corpo della notifica con wrapping del testo
        body_label = Gtk.Label(label=body, wrap=True, xalign=0)
        content_box.append(body_label)

        # Pulsanti delle azioni
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

        # Frame per lo stile visivo
        frame = Gtk.Frame()
        frame.set_child(box)
        frame.set_shadow_type(Gtk.ShadowType.IN)
        frame.get_style_context().add_class("notification-frame")

        self.set_child(frame)

        # Connessioni agli eventi
        self.connect("close-request", self.on_close_request)
        # Gtk.GestureClick è il modo moderno per gestire i click in GTK4
        gesture = Gtk.GestureClick.new()
        gesture.connect("released", self.on_click_released)
        self.add_controller(gesture)

        self.show() # Mostra la finestra
        self.load_css() # Carica lo stile CSS
        self.fade_in() # Avvia l'animazione di apparizione
        # Il timer di auto-chiusura è ora gestito dal NotificationService
        # in base al parametro expire_timeout ricevuto da D-Bus.

    def load_css(self):
        """Carica il file CSS per applicare lo stile alla notifica."""
        if not CSS_PATH.exists():
            print(f"Avviso: File CSS non trovato in {CSS_PATH}")
            return
        provider = Gtk.CssProvider()
        try:
            provider.load_from_path(str(CSS_PATH))
            Gtk.StyleContext.add_provider_for_display(
                Gdk.Display.get_default(),
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
            )
        except GLib.Error as e:
            print(f"Errore nel caricamento del CSS da {CSS_PATH}: {e}")

    def fade_in(self):
        """Animazione di apparizione (fade-in) della notifica."""
        def step(opacity):
            if not self.is_visible(): return False # Interrompi se già chiusa
            if opacity >= 1.0:
                self.set_opacity(1.0)
                return False
            self.set_opacity(opacity)
            GLib.timeout_add(15, step, opacity + 0.05)
            return False
        step(0.05)

    def fade_out(self, reason=3):
        """
        Animazione di scomparsa (fade-out) della notifica e sua successiva chiusura.
        reason: Motivo della chiusura (1=expired, 2=dismissed by user, 3=closed by call, 4=undefined).
        """
        # Rimuovi il timer di auto-chiusura se attivo, per prevenire chiamate multiple
        if self.auto_close_timeout_id:
            GLib.source_remove(self.auto_close_timeout_id)
            self.auto_close_timeout_id = None

        def step(opacity):
            if not self.is_visible(): return False # Interrompi se già chiusa
            if opacity <= 0:
                self.set_opacity(0.0)
                self.close() # Chiude la finestra GTK (la distrugge)
                # Notifica al servizio di pulire lo stato relativo a questa notifica
                self.service.notification_closed_cleanup(self.nid, reason)
                return False
            self.set_opacity(opacity)
            GLib.timeout_add(15, step, opacity - 0.05)
            return False
        step(1.0)
        return False

    def on_close_request(self, *_):
        """Gestisce la richiesta di chiusura della finestra (es. da gestore finestre)."""
        print(f"Richiesta di chiusura (sistema) per notifica {self.nid}")
        self.fade_out(2) # Motivo 2 = dismissed by user
        return True # Indica che abbiamo gestito l'evento

    def on_click_released(self, gesture, n_press, x, y):
        """Gestisce il click dell'utente sulla notifica."""
        print(f"Notifica {self.nid} cliccata!")
        self.fade_out(2) # Motivo 2 = dismissed by user

    def on_action_clicked(self, button, action_key):
        """Gestisce il click su un pulsante di azione."""
        print(f"Azione invocata: '{action_key}' su notifica {self.nid}")
        try:
            # Invoca l'azione D-Bus sul bus di sessione
            bus = dbus.SessionBus()
            obj = bus.get_object("org.freedesktop.Notifications", "/org/freedesktop/Notifications")
            iface = dbus.Interface(obj, "org.freedesktop.Notifications")
            iface.ActionInvoked(dbus.UInt32(self.nid), action_key)
        except dbus.DBusException as e:
            print(f"Errore D-Bus nell'invocazione dell'azione: {e}")
        self.fade_out(2) # Motivo 2 = dismissed by user


class NotificationService(dbus.service.Object):
    """
    Implementa il servizio D-Bus 'org.freedesktop.Notifications'.
    È il cuore del demone, gestisce le notifiche in arrivo, la loro gestione interna
    e l'emissione di segnali D-Bus.
    """
    def __init__(self, bus):
        self.stack = [] # Lista di NotificationWindow per l'ordinamento visivo
        self.notifications = {}  # Mappa ID notifica -> oggetto NotificationWindow
        self.next_id = 1 # Prossimo ID disponibile per una nuova notifica

        # Registra il nome del servizio D-Bus sul bus di sessione
        name = dbus.service.BusName("org.freedesktop.Notifications", bus)
        super().__init__(name, "/org/freedesktop/Notifications")
        print("Servizio D-Bus 'org.freedesktop.Notifications' avviato.")

    @dbus.service.method("org.freedesktop.Notifications", in_signature="susssasa{sv}i", out_signature="u")
    def Notify(self, app_name, replaces_id, app_icon, summary, body, actions, hints, expire_timeout):
        """
        Metodo D-Bus chiamato per inviare una nuova notifica.
        Gestisce la creazione di una nuova finestra o la sostituzione di una esistente.
        """
        nid = self.next_id
        self.next_id += 1

        print(f"Ricevuta notifica: '{summary}' (App: {app_name}, Rimpiazza ID: {replaces_id}, Timeout: {expire_timeout}ms)")

        # Gestione della sostituzione di notifiche esistenti
        if replaces_id != 0 and replaces_id in self.notifications:
            old_win = self.notifications[replaces_id]
            print(f"Sostituzione notifica ID {replaces_id}.")
            # Chiude la vecchia finestra in modo asincrono, la pulizia avverrà tramite cleanup
            GLib.idle_add(old_win.close)
            nid = replaces_id # Riutilizza l'ID della notifica sostituita

        # Programma la visualizzazione della nuova notifica nel thread principale GTK
        GLib.idle_add(self.show_notification, nid, summary, body, app_icon, actions, expire_timeout)
        return dbus.UInt32(nid) # Restituisce l'ID della notifica

    def show_notification(self, nid, summary, body, icon, actions, expire_timeout):
        """
        Crea e aggiunge una nuova NotificationWindow allo stack e al dizionario.
        Imposta anche il timer di auto-chiusura.
        """
        win = NotificationWindow(nid, summary, body, icon, self.stack, actions, self)
        self.notifications[nid] = win
        self.stack.append(win)

        # Configura il timer di auto-chiusura in base al parametro D-Bus
        if expire_timeout == -1: # Notifica persistente
            print(f"Notifica {nid} non scadrà automaticamente.")
        else:
            # Se expire_timeout è 0, usa un default di 4 secondi (secondo la spec D-Bus)
            actual_timeout_seconds = (expire_timeout / 1000) if expire_timeout > 0 else 4
            print(f"Notifica {nid} scadrà in {actual_timeout_seconds} secondi.")
            if win.auto_close_timeout_id: # Rimuovi il vecchio timer se presente
                GLib.source_remove(win.auto_close_timeout_id)
            win.auto_close_timeout_id = GLib.timeout_add_seconds(actual_timeout_seconds, win.fade_out, 1) # Motivo 1 = expired

        self._recalculate_margins() # Ricalcola i margini per tutte le notifiche impilate
        return False # Importante per GLib.idle_add

    def notification_closed_cleanup(self, nid, reason):
        """
        Esegue la pulizia dello stato del servizio quando una notifica viene chiusa.
        Rimuove la notifica dagli elenchi interni ed emette il segnale D-Bus.
        """
        print(f"Pulizia per notifica {nid} (Motivo: {reason}).")
        if nid in self.notifications:
            win = self.notifications.pop(nid) # Rimuove dal dizionario
            if win in self.stack:
                self.stack.remove(win) # Rimuove dallo stack visivo
                self._recalculate_margins() # Ricalcola i margini delle rimanenti
            else:
                print(f"Avviso: Notifica {nid} trovata in .notifications ma non nello stack.")

            # Emette il segnale D-Bus NotificationClosed
            self.NotificationClosed(dbus.UInt32(nid), dbus.UInt32(reason))
        else:
            print(f"Avviso: Tentativo di pulire una notifica (ID: {nid}) non trovata.")

    def _recalculate_margins(self):
        """Ricalcola e imposta i margini superiori per tutte le notifiche nello stack visivo."""
        for i, win in enumerate(self.stack):
            new_margin = 20 + i * 100 # Margine base + 100px per ogni notifica precedente
            if Gtk4LayerShell.get_margin(win, Gtk4LayerShell.Edge.TOP) != new_margin:
                Gtk4LayerShell.set_margin(win, Gtk4LayerShell.Edge.TOP, new_margin)
                # print(f"Aggiornato margine per notifica {win.nid} a {new_margin}")

    @dbus.service.method("org.freedesktop.Notifications", out_signature="as")
    def GetCapabilities(self):
        """Restituisce le capacità supportate dal servizio di notifica."""
        return ["body", "actions", "icon-names"]

    @dbus.service.method("org.freedesktop.Notifications", out_signature="a{sv}")
    def GetServerInformation(self):
        """Restituisce le informazioni sul server di notifica."""
        return {
            "name": "YuriNotify",
            "vendor": "LonelyObserver0",
            "version": "1.0",
            "spec_version": "1.2"
        }

    @dbus.service.signal("org.freedesktop.Notifications", signature="uu")
    def NotificationClosed(self, nid, reason):
        """Segnale D-Bus emesso quando una notifica viene chiusa."""
        pass # Il segnale viene emesso automaticamente dal decoratore

def main():
    """Funzione principale per avviare il demone di notifica."""
    # Inizializza il loop principale GLib per l'integrazione D-Bus e GTK.
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    session_bus = dbus.SessionBus() # Connette al bus di sessione D-Bus
    NotificationService(session_bus) # Avvia il servizio di notifica

    print("Avvio del loop principale di GLib. Il servizio è in ascolto...")
    GLib.MainLoop().run() # Avvia il loop di eventi (blocca l'esecuzione qui)

if __name__ == "__main__":
    main()
