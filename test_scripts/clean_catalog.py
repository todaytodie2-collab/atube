import json
import re
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
JS_DATA_FILE = os.path.join(PROJECT_ROOT, "js", "bundled-data.js")

ARABIC_TRANSLATIONS = {
    "Spider-Man: Brand New Day": "سبايدرمان: يوم جديد",
    "Record of Ragnarok": "سجلات راجناروك",
    "Star Wars Visions Presents The Ninth Jedi": "حرب النجوم: الجيداي التاسع",
    "Main Vaapas Aaunga 2026": "سأعود 2026",
    "M4M Motive For Murder 2026": "دافع للقتل 2026",
    "Alpha 2026": "ألفا 2026",
    "The Dog Stars 2026": "نجوم الكلاب 2026",
    "Idiots 2026": "أغبياء 2026",
    "The Ugly Stepsister 2025": "الأخت القبيحة 2025",
    "Kiss Of The Spider Woman 2025": "قبلة المرأة العنكبوت 2025",
    "Lisabi The Uprising 2024": "ليسابي: الانتفاضة 2024",
    "Color Book 2024": "كتاب التلوين 2024",
    "Downtown Owl 2023": "بومة وسط المدينة 2023",
    "I'm Not a Robot 2023": "لست روبوتاً 2023",
    "The Beloved 2026": "الحبيب 2026",
    "Mayday 2026": "مايو يوم 2026",
    "Popeye The Slayer Man 2025": "باباي الرجل القاتل 2025",
    "DJ Ahmet 2025": "دي جي أحمد 2025",
    "Junction 2024": "تقاطع طرق 2024",
    "Golden Kamuy 2024": "جولدن كاموي 2024",
    "Wrongful Death 2023": "الموت الخطأ 2023",
    "Night of the Hunted 2023": "ليلة المطاردة 2023",
    "Star Wars Maul Shadow Lord": "حرب النجوم: لورد الظل مول",
    "Kaiju No 8": "كايجو رقم 8",
    "Pyaar Prema Kalyanam 2026": "حب وزواج 2026",
    "Lenin 2026": "لينين 2026",
    "Cocktail 2 2026": "كوكتيل الجزء 2",
    "Cocktail 2012": "كوكتيل 2012",
    "Ghabadkund 2026": "جابادكوند 2026",
    "Penny Lane Is Dead 2025": "بيني لين ماتت 2025",
    "Off Rip 2025": "خارج الريب 2025",
    "Blood Shine 2025": "بريق الدم 2025",
    "Motor City 2025": "موتور سيتي 2025",
    "Whistle 2025": "صافرة 2025",
    "Lola Dust 2024": "لولا داست 2024",
    "Waltzing with Brando 2024": "الرقص مع براندو 2024",
    "Camera 2024": "كاميرا 2024",
    "Bull Shark 3 2024": "قرش الثور 3",
    "Moana 2026": "موانا 2026",
    "Shark Frenzy 2026": "جنون القرش 2026",
    "Top Gun: Maverick 2022": "توب جان: مافريك",
    "Don't Breathe 2 2021": "لا تتنفس 2",
    "Turning Point: Generation 9/11 2026": "نقطة التحول: جيل 9/11",
    "Lanterns": "لانترنز",
    "Reacher": "ريتشر",
    "Star Trek Strange New Worlds": "ستار تريك: عوالم جديدة غريبة",
    "Fall 2 Deadpoint 2026": "سقوط 2: ديدبوينت",
    "Runner 2026": "العداء 2026",
    "Zip Wire 2026": "حبل انزلاقي 2026",
    "Splash City 2026": "مدينة سبلاش 2026",
    "Dark Hollow 2026": "دارك هولو 2026",
    "Come With Me 2026": "تعال معي 2026",
    "Clash of the Thundermans 2026": "صراع عائلة ثاندرمان",
    "The Girl In The River 2026": "الفتاة في النهر 2026"
}

def clean_catalog():
    with open(JS_DATA_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    match = re.search(r'(window\.ATUBE_STATIC_CATALOG\s*=\s*)(\[\{.*?\}\]);(\s*window\.ATUBE_STATIC_CHANNELS.*)', content, re.DOTALL)
    if not match:
        print("Failed to match JS catalog structure.")
        return

    prefix = match.group(1)
    catalog_json = json.loads(match.group(2))
    suffix = match.group(3)

    seen_ids = set()
    seen_titles = set()
    cleaned_catalog = []

    for item in catalog_json:
        item_id = item.get("id")
        title = item.get("title", "")
        year = item.get("year", "")
        sig = f"{title}_{year}"

        # 1. Deduplication by ID or Title+Year
        if item_id in seen_ids or sig in seen_titles:
            print(f"Removing duplicate item: {title} ({item_id})")
            continue

        # 2. Filter empty series
        if item.get("content_type") == "series":
            seasons = item.get("seasons", [])
            if not seasons:
                print(f"Removing empty series with no seasons/episodes: {title}")
                continue

        # 3. Add Arabic title translations
        if title in ARABIC_TRANSLATIONS:
            item["arabic_title"] = ARABIC_TRANSLATIONS[title]

        seen_ids.add(item_id)
        seen_titles.add(sig)
        cleaned_catalog.append(item)

    # Write back
    new_content = prefix + json.dumps(cleaned_catalog, ensure_ascii=False) + ";" + suffix
    with open(JS_DATA_FILE, 'w', encoding='utf-8') as f:
        f.write(new_content)

    print(f"Cleaned catalog saved successfully! Original items: {len(catalog_json)}, Cleaned items: {len(cleaned_catalog)}")

if __name__ == "__main__":
    clean_catalog()
