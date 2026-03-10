// This file handles notifications within the application, such as alerts and messages.

class Notification {
    constructor() {
        this.notificationsContainer = document.createElement('div');
        this.notificationsContainer.className = 'notifications';
        document.body.appendChild(this.notificationsContainer);
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerText = message;

        this.notificationsContainer.appendChild(notification);

        setTimeout(() => {
            this.notificationsContainer.removeChild(notification);
        }, 3000);
    }

    info(message) {
        this.showNotification(message, 'info');
    }

    success(message) {
        this.showNotification(message, 'success');
    }

    warning(message) {
        this.showNotification(message, 'warning');
    }

    error(message) {
        this.showNotification(message, 'error');
    }
}

const notification = new Notification();