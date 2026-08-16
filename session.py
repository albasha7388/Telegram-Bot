import asyncio
from pyrogram import Client

# ضع معلوماتك هنا
API_ID = 31992504 # استبدله بالـ API_ID الخاص بك (يجب أن يكون رقماً)
API_HASH = "65eda65624bbbd83bc31079bb2d0095f"  # استبدله بالـ API_HASH الخاص بك

async def main():
    print("🚀 جاري الاتصال بتلجرام لإنشاء الجلسة النصية...")
    
    # in_memory=True تعني أنه لن ينشئ ملفاً، بل سيحفظها في الذاكرة المؤقتة
    app = Client("memory_session", api_id=API_ID, api_hash=API_HASH, in_memory=True)
    
    await app.start()
    session_string = await app.export_session_string()
    
    print("\n" + "="*50)
    print("✅ تم استخراج الجلسة بنجاح! انسخ هذا النص الطويل بالأسفل:\n")
    print(session_string)
    print("\n" + "="*50)
    print("⚠️ تحذير: هذا النص بمثابة كلمة مرور لحسابك، ضعه في Render ولا تشاركه مع أحد.")
    
    await app.stop()

if __name__ == "__main__":
    asyncio.run(main())