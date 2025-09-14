from __future__ import print_function
import os
import datetime as dt
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# ===== SETTINGS =====
SCOPES = ['https://www.googleapis.com/auth/calendar']   # full read/write
TIMEZONE = 'America/Toronto'
DEFAULT_CAL_NAME = 'Family Caledar'  # <- keep exactly as your calendar's display name

# ===== AUTH / SERVICE =====
def get_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('calendar', 'v3', credentials=creds)

# ===== CALENDAR HELPERS =====
def list_calendars(service):
    print("\nYour calendars:")
    page = None
    while True:
        resp = service.calendarList().list(pageToken=page).execute()
        for cal in resp.get('items', []):
            print(f" - {cal.get('summary')}  (id: {cal.get('id')})")
        page = resp.get('nextPageToken')
        if not page:
            break

def find_calendar_id_by_name(service, name):
    target = (name or '').strip().lower()
    if not target:
        return None
    page = None
    while True:
        resp = service.calendarList().list(pageToken=page).execute()
        for cal in resp.get('items', []):
            if (cal.get('summary') or '').strip().lower() == target:
                return cal.get('id')
        page = resp.get('nextPageToken')
        if not page:
            break
    return None

def get_default_calendar_id(service):
    cal_id = find_calendar_id_by_name(service, DEFAULT_CAL_NAME)
    if cal_id:
        print(f"\n✅ Default calendar: {DEFAULT_CAL_NAME} (id: {cal_id})")
        return cal_id
    print(f"\n⚠️ Couldn’t find a calendar named '{DEFAULT_CAL_NAME}'. Falling back to primary.")
    return 'primary'

# ===== EVENT HELPERS =====
def create_event(service, calendar_id, title, description, start_dt, end_dt, location=None):
    event = {
        'summary': title,
        'description': description or '',
        'start': {'dateTime': start_dt.strftime("%Y-%m-%dT%H:%M:00"), 'timeZone': TIMEZONE},
        'end':   {'dateTime': end_dt.strftime("%Y-%m-%dT%H:%M:00"),   'timeZone': TIMEZONE},
    }
    if location:
        event['location'] = location
    created = service.events().insert(calendarId=calendar_id, body=event).execute()
    print("\n🎉 Event created:", created.get('htmlLink'))
    print("eventId:", created.get('id'))
    return created

def find_event_by_title_in_range(service, calendar_id, title, start_date, end_date):
    """
    Return the first event whose summary matches title (case-insensitive) within [start_date, end_date].
    Dates are strings 'YYYY-MM-DD' in local time; we query a UTC window that covers those days.
    """
    # Build an inclusive window (start 00:00, end next day 00:00) in UTC 'Z'
    try:
        start = dt.datetime.strptime(start_date, "%Y-%m-%d")
        end = dt.datetime.strptime(end_date, "%Y-%m-%d") + dt.timedelta(days=1)
    except ValueError:
        print("Invalid date format. Use YYYY-MM-DD.")
        return None

    time_min = start.isoformat() + "Z"
    time_max = end.isoformat() + "Z"

    resp = service.events().list(
        calendarId=calendar_id,
        timeMin=time_min,
        timeMax=time_max,
        singleEvents=True,
        orderBy='startTime',
        q=title  # free-text search
    ).execute()
    events = resp.get('items', [])
    # Prefer exact title match (case-insensitive), else first result
    for ev in events:
        if (ev.get('summary') or '').strip().lower() == title.strip().lower():
            return ev
    return events[0] if events else None

def update_event(service, calendar_id, event_id, **fields):
    """
    Update specific fields on an event.
    Supported keys: summary, description, location, start_dt (datetime), end_dt (datetime),
                    reminders (dict), attendees (list), recurrence (list)
    """
    ev = service.events().get(calendarId=calendar_id, eventId=event_id).execute()

    if 'summary' in fields and fields['summary'] is not None:
        ev['summary'] = fields['summary']
    if 'description' in fields and fields['description'] is not None:
        ev['description'] = fields['description']
    if 'location' in fields and fields['location'] is not None:
        ev['location'] = fields['location']

    if 'start_dt' in fields and fields['start_dt'] is not None:
        ev['start'] = {'dateTime': fields['start_dt'].strftime("%Y-%m-%dT%H:%M:00"), 'timeZone': TIMEZONE}
    if 'end_dt' in fields and fields['end_dt'] is not None:
        ev['end']   = {'dateTime': fields['end_dt'].strftime("%Y-%m-%dT%H:%M:00"),   'timeZone': TIMEZONE}

    if 'reminders' in fields and fields['reminders'] is not None:
        ev['reminders'] = fields['reminders']
    if 'attendees' in fields and fields['attendees'] is not None:
        ev['attendees'] = fields['attendees']
    if 'recurrence' in fields and fields['recurrence'] is not None:
        ev['recurrence'] = fields['recurrence']

    updated = service.events().update(calendarId=calendar_id, eventId=event_id, body=ev).execute()
    print("\n✅ Event updated:", updated.get('htmlLink'))
    return updated

def delete_event(service, calendar_id, event_id):
    service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
    print("🗑️ Deleted.")

# ===== INPUT HELPERS =====
def prompt_datetime():
    date_str = input("Date (YYYY-MM-DD): ").strip()
    time_str = input("Start time 24h (HH:MM): ").strip()
    duration = int(input("Duration minutes (default 60): ").strip() or "60")
    try:
        start_dt = dt.datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    except ValueError:
        print("Invalid date/time. Use YYYY-MM-DD and HH:MM (24h).")
        return None, None
    end_dt = start_dt + dt.timedelta(minutes=duration)
    return start_dt, end_dt

# ===== MAIN =====
def main():
    service = get_service()

    # Choose default calendar automatically (Family Caledar -> primary fallback)
    cal_id = get_default_calendar_id(service)

    print("\nChoose an action:")
    print("1) Create event")
    print("2) Edit event")
    print("3) Delete event")
    print("4) List my calendars")
    choice = input("Enter 1/2/3/4: ").strip()

    if choice == "4":
        list_calendars(service)
        return

    # Allow overriding the calendar (optional)
    override = input("\n(Press Enter to use the default above)\nOr paste a different calendar NAME or ID: ").strip()
    if override:
        cal_id = override if '@' in override else (find_calendar_id_by_name(service, override) or cal_id)
    print(f"\nUsing calendar id: {cal_id}")

    if choice == "1":
        title = input("\nTitle (e.g., Go to supermarket): ").strip()
        details = input("Details/description (e.g., Milk, eggs, apples): ").strip()
        location = input("Location (optional): ").strip() or None
        start_dt, end_dt = prompt_datetime()
        if not start_dt:
            return
        create_event(service, cal_id, title, details, start_dt, end_dt, location)

    elif choice == "2":
        print("\nEdit by searching for the event:")
        title = input("Exact title to find: ").strip()
        start_date = input("Search start date (YYYY-MM-DD): ").strip()
        end_date   = input("Search end date   (YYYY-MM-DD): ").strip()
        found = find_event_by_title_in_range(service, cal_id, title, start_date, end_date)
        if not found:
            print("No matching event found.")
            return
        print(f"Found: {found.get('summary')}  (eventId: {found.get('id')})")

        new_title = input("New title (Enter to keep): ").strip() or None
        new_desc  = input("New details/description (Enter to keep): ").strip() or None
        new_loc   = input("New location (Enter to keep): ").strip() or None

        change_time = input("Change time? (y/N): ").strip().lower() == 'y'
        start_dt = end_dt = None
        if change_time:
            start_dt, end_dt = prompt_datetime()
            if not start_dt:
                return

        update_event(
            service, cal_id, found['id'],
            summary=new_title, description=new_desc, location=new_loc,
            start_dt=start_dt, end_dt=end_dt
        )

    elif choice == "3":
        print("\nDelete by searching for the event:")
        title = input("Exact title to find: ").strip()
        start_date = input("Search start date (YYYY-MM-DD): ").strip()
        end_date   = input("Search end date   (YYYY-MM-DD): ").strip()
        found = find_event_by_title_in_range(service, cal_id, title, start_date, end_date)
        if not found:
            print("No matching event found.")
            return
        print(f"About to delete: {found.get('summary')}  (eventId: {found.get('id')})")
        really = input("Type DELETE to confirm: ").strip()
        if really == "DELETE":
            delete_event(service, cal_id, found['id'])
        else:
            print("Cancelled.")

    else:
        print("No action selected.")

if __name__ == '__main__':
    main()
