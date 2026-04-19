// Notifications System
let notificationsOpen = false;

function toggleNotifications() {
    const dropdown = document.getElementById('notificationsDropdown');
    notificationsOpen = !notificationsOpen;
    dropdown.classList.toggle('active', notificationsOpen);
    if (notificationsOpen) {
        loadNotifications();
    }
}

function loadNotifications() {
    fetch('/api/notifications/')
        .then(r => r.json())
        .then(data => {
            const list = document.getElementById('notifList');
            const badge = document.getElementById('notifBadge');
            const markBtn = document.getElementById('markAllReadBtn');

            // Update badge
            if (data.unread_count > 0) {
                badge.textContent = data.unread_count;
                badge.style.display = 'flex';
                markBtn.style.display = 'inline';
            } else {
                badge.style.display = 'none';
                markBtn.style.display = 'none';
            }

            // Update list
            if (data.notifications.length === 0) {
                list.innerHTML = '<div class="notif-empty">لا توجد إشعارات</div>';
                return;
            }

            list.innerHTML = data.notifications.map(n => `
                <div class="notif-item ${n.read ? '' : 'unread'}" onclick="markRead(${n.id})">
                    <div>${n.message}</div>
                    <div style="font-size:11px;color:var(--text-muted);white-space:nowrap">${n.created_at}</div>
                </div>
            `).join('');
        });
}

function markRead(id) {
    fetch(`/api/notifications/${id}/read/`)
        .then(() => loadNotifications());
}

function markAllRead() {
    fetch('/api/notifications/read-all/')
        .then(() => loadNotifications());
}

// Auto-refresh notifications every 30 seconds
if (document.getElementById('notificationsBtn')) {
    setInterval(() => {
        if (!notificationsOpen) {
            fetch('/api/notifications/')
                .then(r => r.json())
                .then(data => {
                    const badge = document.getElementById('notifBadge');
                    if (data.unread_count > 0) {
                        badge.textContent = data.unread_count;
                        badge.style.display = 'flex';
                    } else {
                        badge.style.display = 'none';
                    }
                });
        }
    }, 30000);
}

// Close notifications on outside click
document.addEventListener('click', function(e) {
    const wrapper = document.querySelector('.notifications-wrapper');
    if (wrapper && notificationsOpen && !wrapper.contains(e.target)) {
        notificationsOpen = false;
        document.getElementById('notificationsDropdown').classList.remove('active');
    }
});
