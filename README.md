# instagram-reel-bot

بوت يستقبل أي ريل تشاركه له في إنستغرام، ويرد عليك في نفس المحادثة: شنو الأداة، وهل تفيد مشاريعك.

A bot that takes any Instagram reel you share with it and replies in the same chat: what the tool is, and whether it fits your projects.

## التركيب | Install

1. نزّل المشروع (Code ← Download ZIP) وفكّه.
2. افتح المجلد في Claude Code، واكتب: `اقرا ملف SKILL.md وساعدني أركب البوت خطوة خطوة`
3. التفاصيل الكاملة: `INSTALL-AR.txt` و `STEPS-AR.txt`.

## تنبيهات | Safety

- ملف `.env` وملف `cookies.txt` مثل الباسورد: لا ترفعهم ولا ترسلهم لأحد (هم محميين في `.gitignore`).
- لا تعطي Claude أي مفتاح أو كوكي في المحادثة.
- البوت يتجاهل كل الرسائل لين تحط `ALLOWED_SENDER_ID` في `.env`.
- ملفات التشغيل التلقائي `.ps1` لـ Windows فقط؛ على الماك شغّله يدوياً أو بـ Docker.
