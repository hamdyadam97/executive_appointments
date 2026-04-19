# دليل النشر على Hostinger VPS

## المتطلبات
- VPS Ubuntu 22.04/24.04
- Domain name (اختياري)

---

## 1. رفع الملفات على السيرفر

أولاً اضغط المشروع في ملف ZIP:
```bash
# على جهازك المحلي (Windows)
# اضغط مجلد المشروع كامل
```

ارفع الملفات للسيرفر عبر SFTP أو SCP إلى:
```
/var/www/executive_appointments/
```

---

## 2. تشغيل سكربت التنصيب

بعد رفع الملفات، SSH للسيرفر وشغّل:

```bash
cd /var/www/executive_appointments
chmod +x deploy/setup.sh
sudo ./deploy/setup.sh
```

السكربت هيعمل كل حاجة:
- يثبت Python, Nginx
- يعمل venv ويثبت المتطلبات
- يشغّل migrations
- يجمع static files
- يعدّل Nginx + systemd service

---

## 3. عدل ملف `.env`

```bash
cd /var/www/executive_appointments
sudo nano .env
```

أهم القيم اللي لازم تغيّرها:
```env
SECRET_KEY=ghyr-dah-bta3-dev-w-7ot-haga-2wiya-2wiya
DEBUG=False
ALLOWED_HOSTS=your-domain.com
CSRF_TRUSTED_ORIGINS=https://your-domain.com

# لو عندك إيميل SMTP:
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.hostinger.com
EMAIL_PORT=587
EMAIL_HOST_USER=noreply@your-domain.com
EMAIL_HOST_PASSWORD=your-password
```

---

## 4. أول Secret Key

لو ما عندك secret key، شغّل على السيرفر:
```bash
cd /var/www/executive_appointments
source venv/bin/activate
python -c "import secrets; print(secrets.token_urlsafe(50))"
```

انسخ الناتج وحطّه في `.env`.

---

## 5. أوامر مهمة

| الأمر | الوصف |
|-------|-------|
| `sudo systemctl status executive_appointments` | حالة التطبيق |
| `sudo systemctl restart executive_appointments` | إعادة تشغيل التطبيق |
| `sudo systemctl restart nginx` | إعادة تشغيل Nginx |
| `sudo tail -f /var/log/gunicorn/error.log` | متابعة الأخطاء |
| `sudo tail -f /var/log/nginx/error.log` | أخطاء Nginx |

---

## 6. SSL Certificate (HTTPS) - مجاني

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

Certbot هيضيف HTTPS تلقائياً.

---

## 7. تحديث المشروع بعد التعديلات

```bash
cd /var/www/executive_appointments
source venv/bin/activate

# جلب التحديثات
git pull  # لو بتستخدم git
# أو ارفع الملفات يدوياً

# التحديثات
pip install -r requirements.txt
python manage.py migrate --noinput
python manage.py collectstatic --noinput
sudo systemctl restart executive_appointments
```

---

## ملاحظات

- SQLite شغّالة ومفيش مشكلة للاستخدام المتوسط. لو عايز PostgreSQL افتح issue.
- المشروع بيشتغل على port 8000 داخلياً، وNginx بيوجّه الطلبات له.
- static files متجمعة في `staticfiles/` وNginx بيخدمها مباشرة.
