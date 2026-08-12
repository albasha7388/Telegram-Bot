# استخدام نسخة بايثون خفيفة وسريعة
FROM python:3.12-slim

# تحديث النظام الأساسي وتثبيت أدوات ضرورية لقواعد بيانات SQLite
RUN apt-get update && apt-get install -y gcc sqlite3 libsqlite3-dev && rm -rf /var/lib/apt/lists/*

# تحديد مجلد العمل داخل السيرفر
WORKDIR /app

# نسخ ملف المكتبات أولاً لتسريع عملية البناء (Caching)
COPY requirements.txt .

# تثبيت المكتبات
RUN pip install --no-cache-dir -r requirements.txt

# نسخ باقي ملفات المشروع إلى السيرفر
COPY . .

# الأمر النهائي لتشغيل البوت
CMD ["python", "main.py"]