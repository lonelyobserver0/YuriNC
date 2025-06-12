// main.cpp
#include <QApplication>
#include "notificationdaemon.h"

int main(int argc, char *argv[]) {
    QApplication app(argc, argv);

    // Imposta il nome dell'applicazione per D-Bus e stili
    app.setApplicationName("yurinotifyd");
    app.setOrganizationName("yurinotify");

    NotificationDaemon daemon;
    if (!daemon.init()) {
        qCritical("Failed to initialize notification daemon.");
        return 1;
    }

    return app.exec();
}