import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")

from gi.repository import Gtk, Gdk, GLib, GObject, Gtk4LayerShell
import os
from pathlib import Path
import dbus
import dbus.service
import dbus.mainloop.glib

# Scommenta questa riga se riscontri errori relativi a 'libgtk4-layer-shell' non trovata
# from ctypes import CDLL
# CDLL('libgtk4-layer-shell.so')

# Definisce il percorso per la directory di configurazione e il file CSS
CONFIG_DIR = Path.home() / ".config" / "yurind"
CSS_PATH = CONFIG_DIR / "style.css"

class NotificationWindow(Gtk.Window):
    """
    Rappresenta una singola finestra di notifica sullo schermo.
    Gestisce la visualizzazione, le animazioni e le interazioni dell'utente.
    """
    def __init__(self, nid, summary, body, icon, stack, service):
        super().__init__()
        self.nid = nid  # ID univoco della notifica
        self.stack = stack  # Riferimento allo stack di notifiche del servizio (per il posizionamento)
        self.service = service  # Riferimento al servizio D-Bus per la comunicazione
        self.auto_close_timeout_id = None # ID per il timer di auto-chiusura

        self.set_decorated(False) # Rimuove la decorazione della finestra (bordi, barra del titolo)
        self.set_resizable(False) # Impedisce il ridimensionamento
        self.set_name("notification") # Imposta un nome per il targeting CSS
        self.set_opacity(0.0) # Inizia completamente trasparente per l'animazione di fade-in
        self.set_default_size(300, -1) # Larghezza fissa di 300px, altezza automatica

        # Inizializza gtk4-layer-shell per la finestra
        Gtk4LayerShell.init_for_window(self)
        # Imposta il livello su OVERLAY per essere sempre sopra altre finestre
        Gtk4LayerShell.set_layer(self, Gtk4LayerShell.Layer.OVERLAY)
        # Ancoraggio in alto a destra dello schermo
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.TOP, True)
        Gtk4LayerShell.set_anchor(self, Gtk4LayerShell.Edge.RIGHT, True)
        # Imposta i margini iniziali. Il margine superiore dipende dal numero di notifiche già presenti.
        Gtk4LayerShell.set_margin(self, Gtk4LayerShell.Edge.TOP, 20 + len(stack) * 100)
        Gtk4LayerShell.set_margin(self, Gtk4LayerShell.Edge.RIGHT, 20)

        # Crea un box orizzontale per il contenuto principale della notifica
        box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12,
                      margin_top=12, margin_bottom=12, margin_start=12, margin_end=12)
        box.get_style_context().add_class("notification-box") # Aggiunge una classe per il CSS

        # Aggiunge l'icona se fornita
        if icon:
            try:
                # Tenta di creare l'immagine da un nome di icona (es. "dialog-information")
                image = Gtk.Image.new_from_icon_name(icon)
                box.append(image)
            except GLib.Error as e:
                # Gestisce l'errore se l'icona non viene trovata o è invalida
                print(f"Errore nel caricamento dell'icona '{icon}': {e}")
                # Puoi scegliere di aggiungere un'icona di fallback qui se necessario
                pass # Continua senza icona se c'è un errore

        # Box verticale per titolo e corpo della notifica
        content_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)

        # Titolo della notifica (supporta markup per il grassetto e allineamento a sinistra)
        title = Gtk.Label(label=f"<b>{summary}</b>", use_markup=True, xalign=0)
        content_box.append(title)

        # Corpo della notifica (testo che si adatta a più righe e allineamento a sinistra)
        body_label = Gtk.Label(label=body, wrap=True, xalign=0)
        content_box.append(body_label)

        # Aggiunge i pulsanti delle azioni se presenti
        if actions:
            actions_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
            for i in range(0, len(actions), 2): # Le azioni sono coppie (action_key, label)
                action_key = actions[i]
                label = actions[i+1]
                button = Gtk.Button(label=label)
                button.connect("clicked", self.on_action_clicked, action_key)
                actions_box.append(button)
            content_box.append(actions_box)

        box.append(content_box)

        # Crea un frame attorno al contenuto della notifica per lo stile e l'ombra
        frame = Gtk.Frame()
        frame.set_child(box)
        frame.set_shadow_type(Gtk.ShadowType.IN) # Tipo di ombra (puoi cambiarlo o rimuoverlo)
        frame.get_style_context().add_class("notification-frame") # Aggiunge una classe per il CSS

        self.set_child(frame)

        # Connessioni ai segnali GTK
        self.connect("close-request", self.on_close_request)

        # Utilizza Gtk.GestureClick per gestire i click sulla finestra (moderno approccio GTK4)
        gesture = Gtk.GestureClick.new()
        gesture.connect("released", self.on_click_released) # Connessione all'evento di rilascio del click
        self.add_controller(gesture) # Aggiunge il controller dei gesti alla finestra

        self.show() # Mostra la finestra GTK
        self.load_css() # Carica il CSS per applicare lo stile
        self.fade_in() # Avvia l'animazione di fade-in

        # L'auto-chiusura verrà impostata dal NotificationService in base a expire_timeout

    def load_css(self):
        """Carica il foglio di stile CSS dal percorso specificato."""
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
        """Avvia l'animazione di fade-in per la finestra della notifica."""
        def step(opacity):
            if not self.is_visible(): # Interrompi l'animazione se la finestra non è più visibile
                return False
            if opacity >= 1.0:
                self.set_opacity(1.0) # Assicura che l'opacità sia piena alla fine
                return False
            self.set_opacity(opacity)
            # Continua l'animazione dopo 15ms con un incremento di opacità
            GLib.timeout_add(15, step, opacity + 0.05)
            return False
        step(0.05) # Inizia l'animazione da un'opacità quasi trasparente

    def fade_out(self, reason=3):
        """
        Avvia l'animazione di fade-out per la finestra della notifica
        e gestisce la sua chiusura e pulizia.
        """
        # Rimuovi il timer di auto-chiusura se è attivo, per evitare chiamate multiple
        if self.auto_close_timeout_id:
            GLib.source_remove(self.auto_close_timeout_id)
            self.auto_close_timeout_id = None

        def step(opacity):
            if not self.is_visible(): # Interrompi se la finestra è già stata chiusa
                return False
            if opacity <= 0:
                self.set_opacity(0.0) # Assicura che l'opacità sia zero alla fine
                self.close() # Chiude la finestra GTK (distrugge il widget)
                # Notifica al servizio di pulire lo stato relativo a questa notifica
                self.service.notification_closed_cleanup(self.nid, reason)
                return False
            self.set_opacity(opacity)
            # Continua l'animazione dopo 15ms con un decremento di opacità
            GLib.timeout_add(15, step, opacity - 0.05)
            return False
        step(1.0) # Inizia l'animazione da opacità piena
        return False # Importante per i timer di GLib.timeout_add_seconds

    def on_close_request(self, *_):
        """
        Gestisce la richiesta di chiusura della notifica (es. da gestore finestre).
        Avvia il fade-out con motivo 'dismissed by user'.
        """
        print(f"Richiesta di chiusura per notifica {self.nid} (da gestore finestre).")
        self.fade_out(2) # Motivo 2 = dismissed by user (chiuso dall'utente)
        return True # Indica che abbiamo gestito l'evento, impedendo la chiusura predefinita di GTK

    def on_click_released(self, gesture, n_press, x, y):
        """
        Gestisce il click dell'utente sulla notifica.
        Avvia il fade-out con motivo 'dismissed by user'.
        """
        print(f"Notifica {self.nid} cliccata! Coordinate: ({x:.2f}, {y:.2f})")
        self.fade_out(2) # Motivo 2 = dismissed by user (chiuso dall'utente)

    def on_action_clicked(self, button, action_key):
        """
        Gestisce il click su un pulsante di azione della notifica.
        Invocare l'azione D-Bus e poi chiude la notifica.
        """
        print(f"Azione invocata: '{action_key}' su notifica {self.nid}")
        try:
            # Crea una connessione al bus di sessione D-Bus
            bus = dbus.SessionBus()
            # Ottiene l'oggetto D-Bus per il servizio di notifica
            obj = bus.get_object("org.freedesktop.Notifications", "/org/freedesktop/Notifications")
            # Ottiene l'interfaccia D-Bus per le notifiche
            iface = dbus.Interface(obj, "org.freedesktop.Notifications")
            # Invocare il metodo ActionInvoked sul servizio D-Bus
            iface.ActionInvoked(dbus.UInt32(self.nid), action_key)
        except dbus.DBusException as e:
            print(f"Errore nell'invocazione dell'azione D-Bus per {self.nid}, azione '{action_key}': {e}")
        self.fade_out(2) # Motivo 2 = dismissed by user (chiuso dall'utente)


class NotificationService(dbus.service.Object):
    """
    Implementa il servizio D-Bus 'org.freedesktop.Notifications'.
    Gestisce le notifiche in arrivo, il loro impilamento e la loro chiusura.
    """
    def __init__(self, bus):
        self.stack = [] # Stack di NotificationWindow per gestire l'impilamento visivo delle notifiche
        self.notifications = {}  # Dizionario nid -> NotificationWindow per accedere rapidamente alle notifiche attive
        self.next_id = 1 # ID per la prossima notifica da assegnare

        # Registra il nome del servizio D-Bus sul bus di sessione
        name = dbus.service.BusName("org.freedesktop.Notifications", bus)
        super().__init__(name, "/org/freedesktop/Notifications")
        print("Servizio D-Bus 'org.freedesktop.Notifications' avviato.")

    @dbus.service.method("org.freedesktop.Notifications", in_signature="susssasa{sv}i", out_signature="u")
    def Notify(self, app_name, replaces_id, app_icon, summary, body, actions, hints, expire_timeout):
        """
        Implementa il metodo D-Bus Notify per ricevere nuove notifiche.
        Crea o aggiorna una finestra di notifica.
        """
        nid = self.next_id
        self.next_id += 1 # Pre-incrementa per il prossimo ID

        print(f"Ricevuta notifica: '{summary}' (App: {app_name}, Rimpiazza ID: {replaces_id}, Timeout: {expire_timeout}ms)")

        # Gestisce la sostituzione di una notifica esistente
        if replaces_id != 0 and replaces_id in self.notifications:
            old_win = self.notifications[replaces_id]
            print(f"Sostituzione notifica esistente ID {replaces_id}. Nuova notifica avrà ID {replaces_id}.")
            # Chiudi la vecchia finestra UI in modo asincrono nel thread GTK
            # La pulizia dallo stack e dal dizionario avverrà tramite notification_closed_cleanup
            GLib.idle_add(old_win.close)
            nid = replaces_id # Riutilizza l'ID della notifica sostituita

        # Programma la creazione e visualizzazione della nuova notifica nel thread GTK
        GLib.idle_add(self.show_notification, nid, summary, body, app_icon, actions, expire_timeout)
        return dbus.UInt32(nid)

    def show_notification(self, nid, summary, body, icon, actions, expire_timeout):
        """
        Crea e mostra una nuova finestra di notifica GTK.
        Questa funzione viene chiamata nel thread principale di GTK.
        """
        win = NotificationWindow(nid, summary, body, icon, self.stack, self)
        self.notifications[nid] = win # Aggiunge la notifica al dizionario delle notifiche attive
        self.stack.append(win) # Aggiunge la notifica allo stack visivo

        # Imposta il timer di auto-chiusura in base a expire_timeout
        if expire_timeout == -1: # -1 significa che la notifica non deve scadere automaticamente
            print(f"Notifica {nid} non scadrà automaticamente.")
            if win.auto_close_timeout_id: # Se per qualche ragione c'era un timer, rimuovilo
                GLib.source_remove(win.auto_close_timeout_id)
                win.auto_close_timeout_id = None
        else:
            # Se expire_timeout è 0, usa un default di 4 secondi
            actual_timeout_seconds = (expire_timeout / 1000) if expire_timeout > 0 else 4
            print(f"Notifica {nid} scadrà in {actual_timeout_seconds} secondi.")
            if win.auto_close_timeout_id: # Rimuovi il vecchio timer se esiste già
                GLib.source_remove(win.auto_close_timeout_id)
            # Aggiungi il nuovo timer di auto-chiusura, motivo 1 = expired
            win.auto_close_timeout_id = GLib.timeout_add_seconds(actual_timeout_seconds, win.fade_out, 1)

        # Ricalcola i margini per tutte le notifiche impilate dopo l'aggiunta di una nuova
        self._recalculate_margins()
        return False # Importante per GLib.idle_add

    def notification_closed_cleanup(self, nid, reason):
        """
        Metodo chiamato dalla NotificationWindow quando si chiude (dopo l'animazione di fade-out).
        Esegue la pulizia dello stato nel servizio e emette il segnale D-Bus.
        """
        print(f"Pulizia per notifica {nid} iniziata. Motivo: {reason}")
        if nid in self.notifications:
            win = self.notifications.pop(nid) # Rimuove la notifica dal dizionario attivo

            if win in self.stack:
                self.stack.remove(win) # Rimuove la notifica dallo stack visivo
                self._recalculate_margins() # Ricalcola i margini delle notifiche rimanenti
            else:
                print(f"Avviso: Notifica {nid} trovata in .notifications ma non nello stack.")

            # Emette il segnale D-Bus NotificationClosed
            self.NotificationClosed(dbus.UInt32(nid), dbus.UInt32(reason))
        else:
            print(f"Avviso: Tentativo di pulire una notifica (ID: {nid}) non trovata nel dizionario.")

    def _recalculate_margins(self):
        """
        Ricalcola e imposta i margini superiori per tutte le notifiche attualmente nello stack.
        Questo assicura che le notifiche siano impilate correttamente.
        """
        for i, win in enumerate(self.stack):
            current_margin = Gtk4LayerShell.get_margin(win, Gtk4LayerShell.Edge.TOP)
            # Assumiamo un'altezza media di 100px per notifica per il calcolo del margine di impilamento
            new_margin = 20 + i * 100
            if current_margin != new_margin:
                Gtk4LayerShell.set_margin(win, Gtk4LayerShell.Edge.TOP, new_margin)
                # print(f"Aggiornato margine per notifica {win.nid} a {new_margin}")

    @dbus.service.method("org.freedesktop.Notifications", out_signature="as")
    def GetCapabilities(self):
        """
        Restituisce le capacità supportate dal servizio di notifica.
        """
        # Il servizio supporta testo nel corpo, azioni e icone per nome.
        return ["body", "actions", "icon-names"]

    @dbus.service.method("org.freedesktop.Notifications", out_signature="a{sv}")
    def GetServerInformation(self):
        """
        Restituisce le informazioni sul server di notifica.
        """
        return {
            "name": "YuriNotify",
            "vendor": "LonelyObserver0",
            "version": "1.0",
            "spec_version": "1.2"
        }

    @dbus.service.signal("org.freedesktop.Notifications", signature="uu")
    def NotificationClosed(self, nid, reason):
        """
        Segnale D-Bus emesso quando una notifica viene chiusa.
        nid: ID della notifica.
        reason: Motivo della chiusura (1=expired, 2=dismissed by user, 3=closed by call, 4=undefined).
        """
        pass # Il segnale viene emesso automaticamente dal decoratore

def main():
    """
    Funzione principale per avviare il servizio di notifica.
    """
    # Inizializza il loop principale GLib per l'integrazione D-Bus e GTK.
    # Questo è fondamentale per gestire eventi da entrambi i sistemi.
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    session_bus = dbus.SessionBus() # Ottiene un riferimento al bus di sessione D-Bus
    NotificationService(session_bus) # Istanzia e avvia il servizio di notifica

    # Avvia il loop principale di GLib. Questo blocco l'esecuzione dello script
    # e attende gli eventi D-Bus o GTK.
    print("Avvio del loop principale di GLib. Il servizio è in ascolto...")
    GLib.MainLoop().run()

if __name__ == "__main__":
    main()
