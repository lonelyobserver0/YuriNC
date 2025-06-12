import dbus

try:
    bus = dbus.SessionBus()
    notification_service = bus.get_object("org.freedesktop.Notifications", "/org/freedesktop/Notifications")
    notification_interface = dbus.Interface(notification_service, "org.freedesktop.Notifications")

    app_name = "TestApp"
    replaces_id = dbus.UInt32(0)
    app_icon = "dialog-information"
    summary = "Test from Python"
    body = "This is a direct D-Bus notification."
    actions = dbus.Array([], signature='s') # No actions for simplicity
    hints = dbus.Dictionary({}, signature='sv')
    expire_timeout = dbus.Int32(5000) # 5 seconds

    nid = notification_interface.Notify(
        app_name, replaces_id, app_icon, summary, body, actions, hints, expire_timeout
    )
    print(f"Notification sent. ID: {nid}")

except dbus.DBusException as e:
    print(f"D-Bus error: {e}")
    print("Ensure your notification daemon is running.")
