// notificationdaemon.h
#ifndef NOTIFICATIONDAEMON_H
#define NOTIFICATIONDAEMON_H

#include <QObject>
#include <QDBusConnection>
#include <QDBusMessage>
#include <QDBusAbstractAdaptor>
#include <QQueue>
#include <QTimer>

// Generated from org.freedesktop.Notifications.xml
#include "org_freedesktop_Notifications_adaptor.h"
#include "notificationwidget.h" // La tua classe per la notifica visibile

// Struttura per contenere i dati della notifica
struct NotificationData {
    QString app_name;
    quint32 replaces_id;
    QString app_icon;
    QString summary;
    QString body;
    QStringList actions;
    QVariantMap hints;
    qint32 expire_timeout; // -1 per default, 0 per persistente
};

class NotificationDaemon : public QObject
{
    Q_OBJECT
    Q_CLASSINFO("D-Bus Interface", "org.freedesktop.Notifications")

public:
    explicit NotificationDaemon(QObject *parent = nullptr);
    bool init();

private slots:
    // Metodi D-Bus (implementati dall'adaptor)
    Q_NOREPLY void CloseNotification(quint32 id);
    QStringList GetCapabilities();
    quint32 Notify(const QString &app_name, quint32 replaces_id, const QString &app_icon,
                   const QString &summary, const QString &body, const QStringList &actions,
                   const QVariantMap &hints, qint32 expire_timeout);

    // Metodi interni per gestire la coda e la visualizzazione
    void showNextNotification();
    void hideCurrentNotification();
    void loadStyleSheet(); // Carica e applica lo stile SCSS/CSS

private:
    QDBusConnection m_dbusConnection;
    quint32 m_nextNotificationId;
    QQueue<NotificationData> m_notificationQueue;
    NotificationWidget* m_currentNotificationWidget;
    QTimer m_hideTimer;

    // Metodo per processare le azioni (es. click sul pulsante)
    void notificationActionInvoked(quint32 id, const QString &action_key);
    void notificationClosed(quint32 id, quint32 reason); // Ragioni: 1=expired, 2=dismissed, 3=closed by api, 4=undefined
};

#endif // NOTIFICATIONDAEMON_H