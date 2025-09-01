# 🚀 News Balance Analyzer - Backend Service

מערכת הבקנד של האתר שלך שרצה באופן רציף ומעבד חדשות אוטומטית.

## 📋 מה המערכת עושה

המערכת רצה בלולאה אינסופית ומבצעת שני תהליכים עיקריים:

### 1. 📰 News Scraper (`filter_recent.py`)
- **תדירות**: כל 5 דקות
- **תפקיד**: אוסף חדשות חדשות מ-Rotter.net
- **פלט**: שומר חדשות חדשות במסד הנתונים SQLite

### 2. 📝 Article Processor (`process_articles.py`)
- **תדירות**: כל 10 דקות  
- **תפקיד**: מעבד כתבות חדשות באמצעות AI (Claude)
- **פלט**: מנתח כתבות ומסמן אותן כמעבדות

## 🚀 איך להריץ

### אפשרות 1: Windows Batch File (הכי פשוט)
```bash
# פשוט לחץ פעמיים על הקובץ
start_backend.bat
```

### אפשרות 2: PowerShell
```powershell
# הרץ את הסקריפט
.\start_backend.ps1
```

### אפשרות 3: ישירות מ-Python
```bash
python backend_runner.py
```

## ⚙️ דרישות מקדימות

### 1. Python 3.8+
```bash
python --version
```

### 2. חבילות נדרשות
```bash
pip install -r requirements.txt
```

### 3. קובץ API Key
צור קובץ `.env.local` עם המפתח שלך:
```env
ANTHROPIC_API_KEY=your_api_key_here
```

## 📊 מעקב אחר המערכת

### 1. לוגים בזמן אמת
המערכת מציגה סטטוס בזמן אמת בטרמינל:
```
🔄 Cycle 15 - 2024-01-15 14:30:00
============================================================
📰 Time to run scraper...
🚀 Running News Scraper...
✅ News Scraper completed successfully in 45.2 seconds
📝 Time to run processor...
🚀 Running Article Processor...
✅ Article Processor completed successfully in 120.8 seconds
📊 Status Update:
   📰 Total articles: 1250
   ⏳ Unprocessed: 15
   ✅ Processed (relevant): 980
   🚫 Processed (non-relevant): 255
   🕐 Last hour activity: 8
⏰ Next runs:
   📰 Scraper: in 240 seconds
   📝 Processor: in 480 seconds
😴 Sleeping for 60 seconds before next cycle...
```

### 2. קובץ לוג מפורט
כל הפעילות נשמרת ב-`backend_runner.log`:
```bash
# צפייה בלוג בזמן אמת
tail -f backend_runner.log
```

### 3. סטטיסטיקות מסד הנתונים
המערכת מציגה סטטיסטיקות מעודכנות כל דקה:
- סה"כ כתבות במסד הנתונים
- כתבות שעדיין לא עובדו
- כתבות שעובדו (רלוונטיות/לא רלוונטיות)
- פעילות בשעה האחרונה

## 🛑 איך לעצור

### עצירה רגילה
```bash
# בטרמינל, לחץ
Ctrl+C
```

### עצירה כפויה
```bash
# אם המערכת לא מגיבה
taskkill /f /im python.exe
```

## 🔧 הגדרות מתקדמות

### שינוי זמני הרצה
ערוך את `backend_runner.py`:
```python
class BackendRunner:
    def __init__(self):
        self.scraper_interval = 300    # 5 דקות
        self.processor_interval = 600  # 10 דקות
```

### הוספת התראות
המערכת יכולה לשלוח התראות על:
- שגיאות בסקרייפינג
- בעיות בעיבוד כתבות
- סטטוס כללי

## 📁 מבנה הקבצים

```
news-balance-analyzer/
├── backend_runner.py          # הסקריפט הראשי
├── filter_recent.py           # אוסף חדשות
├── process_articles.py        # מעבד כתבות
├── start_backend.bat          # הפעלה ב-Windows
├── start_backend.ps1          # הפעלה ב-PowerShell
├── backend_runner.log         # לוג מפורט
├── rotter_news.db            # מסד הנתונים
└── .env.local                # מפתחות API
```

## 🚨 פתרון בעיות

### בעיה: Python לא נמצא
```bash
# התקן Python מ:
# https://www.python.org/downloads/
```

### בעיה: חבילות חסרות
```bash
pip install -r requirements.txt
```

### בעיה: API Key לא עובד
```bash
# בדוק שקובץ .env.local קיים ומכיל:
ANTHROPIC_API_KEY=your_actual_key_here
```

### בעיה: מסד נתונים לא נטען
```bash
# המערכת תיצור אותו אוטומטית בריצה הראשונה
```

## 📈 ביצועים

- **זמן ריצה ממוצע לסקרייפינג**: 30-60 שניות
- **זמן ריצה ממוצע לעיבוד כתבה**: 2-5 דקות
- **זיכרון נדרש**: ~100-200 MB
- **שימוש ב-CPU**: נמוך (רוב הזמן מחכה)

## 🔄 תחזוקה

### ניקוי לוגים ישנים
```bash
# מחק לוגים ישנים מ-30 יום
del backend_runner.log.old
```

### גיבוי מסד הנתונים
```bash
# גבה את מסד הנתונים
copy rotter_news.db rotter_news_backup.db
```

## 📞 תמיכה

אם יש בעיות:
1. בדוק את הלוגים ב-`backend_runner.log`
2. ודא שכל הקבצים הנדרשים קיימים
3. בדוק שהמפתחות API תקינים
4. ודא שיש חיבור לאינטרנט

---

**🎯 המטרה**: מערכת אוטומטית שתאסוף ותעבד חדשות 24/7 כבקנד של האתר שלך!
