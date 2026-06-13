// NutraX Service Worker
// بيخلي الموقع يشتغل كتطبيق + بيستقبل إشعارات الموبايل (Web Push)

const CACHE = "nutrax-v1";

// تثبيت
self.addEventListener("install", (event) => {
  self.skipWaiting();
});

// تفعيل
self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

// ═══════ استقبال إشعار من السيرفر (Web Push) ═══════
self.addEventListener("push", (event) => {
  let data = { title: "NutraX", body: "عندك إشعار جديد", url: "/admin/notifications" };
  try {
    if (event.data) {
      data = Object.assign(data, event.data.json());
    }
  } catch (e) {
    if (event.data) data.body = event.data.text();
  }

  const options = {
    body: data.body,
    icon: "/static/icon-192.png",
    badge: "/static/icon-192.png",
    dir: "rtl",
    lang: "ar",
    vibrate: [120, 60, 120],
    data: { url: data.url || "/admin/notifications" },
    tag: data.tag || "nutrax-notif",
    renotify: true
  };

  event.waitUntil(self.registration.showNotification(data.title, options));
});

// ═══════ لما المستخدم يدوس على الإشعار ═══════
self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const url = (event.notification.data && event.notification.data.url) || "/admin/notifications";
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clientsArr) => {
      for (const c of clientsArr) {
        if ("focus" in c) {
          c.navigate(url);
          return c.focus();
        }
      }
      if (self.clients.openWindow) return self.clients.openWindow(url);
    })
  );
});
