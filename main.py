import caldav
from notion_client import Client
from datetime import datetime, timedelta
import pytz
import time
from dateutil import parser
from icalendar import Event, Calendar
import os
from dotenv import load_dotenv

load_dotenv()


notion_token = os.getenv("NOTION_TOKEN")
database_id = os.getenv("DATABASE_ID")
apple_id = os.getenv("APPLE_ID")
app_password = os.getenv("APPLE_PASSWORD")

# --- ИНИЦИАЛИЗАЦИЯ КЛИЕНТОВ ---
notion = Client(auth=notion_token)
url = "https://caldav.icloud.com/"
client = caldav.DAVClient(url, username=apple_id, password=app_password)
principal = client.principal()
calendars = principal.calendars()

calendar = None
for cal in calendars:
    if cal.name == "Tasks":
        calendar = cal
        break

if not calendar:
    print("⚠️ Календарь 'Tasks' не найден.")
    exit()

# --- ПОЛУЧЕНИЕ УЖЕ СУЩЕСТВУЮЩИХ СОБЫТИЙ ---


def get_existing_events():
    events = []
    for event in calendar.events():
        try:
            events.append(event.instance.vevent.summary.value)
        except:
            continue
    return events

# --- ОБНОВЛЕНИЕ КАЛЕНДАРЯ ---


def update_calendar():
    try:
        existing_events = get_existing_events()
        response = notion.databases.query(database_id=database_id)

        for page in response["results"]:
            # Название
            name_property = page["properties"].get("Name", {}).get("title", [])
            if not name_property:
                continue
            event_title = name_property[0]["text"]["content"]

            # Дата
            date_property = page["properties"].get(
                "Date", {}).get("date", None)
            if not date_property or not date_property.get("start"):
                print(f"⚠️ У события '{event_title}' нет даты.")
                continue

            date_str = date_property["start"]
            is_all_day = 'T' not in date_str

            page_id = page['id'].replace('-', '')
            notion_url = f"https://www.notion.so/{page_id}"

            print(notion_url)

            if event_title in existing_events:
                continue  # Тихо пропускаем, не выводим в консоль

            cal = Calendar()
            vevent = Event()
            vevent.add("summary", event_title)

            if is_all_day:
                start = parser.parse(date_str).date()
                end = start + timedelta(days=1)
                vevent.add("dtstart", start)
                vevent.add("dtend", end)
                vevent.add('url', notion_url)
                print(
                    f"📅 Добавляется all-day событие '{event_title}' на {start}")
            else:
                start = parser.isoparse(date_str)
                end = start + timedelta(hours=1)
                start = start.astimezone(pytz.utc)
                end = end.astimezone(pytz.utc)
                vevent.add("dtstart", start)
                vevent.add("dtend", end)
                vevent.add('url', notion_url)

                print(
                    f"🕒 Добавляется событие '{event_title}' с {start} до {end}")

            cal.add_component(vevent)
            calendar.add_event(cal.to_ical())
            print(f"✅ Событие '{event_title}' добавлено в iCloud.")

    except Exception as e:
        print(f"❌ Ошибка при обновлении календаря: {str(e)}")


# --- БЕСКОНЕЧНЫЙ ЦИКЛ ---
while True:
    print("🔄 Обновление календаря...")
    update_calendar()
    print("⏳ Ожидание 0.3 минут...")
    time.sleep(30)
