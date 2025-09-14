# server.py
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel, Field
from typing import Optional, List
import datetime as dt
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/calendar']
TIMEZONE = 'America/Toronto'
DEFAULT_CAL_NAME = 'Family Caledar'   # <- your default

API_TOKEN = os.getenv("GPT_CAL_API_TOKEN", "change-me")  # simple auth

app = FastAPI(title="Calendar Assistant API", version="1.0.0")

# ---------- helpers reused ----------
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

def find_calendar_id_by_name(service, name):
    target = (name or '').strip().lower()
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

def resolve_calendar_id(service, calendar_name_or_id: Optional[str]):
    if not calendar_name_or_id:
        cal_id = find_calendar_id_by_name(service, DEFAULT_CAL_NAME)
        return cal_id or 'primary'
    if '@' in calendar_name_or_id:
        return calendar_name_or_id
    return find_calendar_id_by_name(service, calendar_name_or_id) or 'primary'

# ---------- request models ----------
class CreateEventReq(BaseModel):
    title: str = Field(..., description="Event title, e.g., 'Go to supermarket'")
    description: Optional[str] = Field("", description="Event details/shopping list")
    start_iso: str = Field(..., description="Start time in ISO8601, e.g., 2025-09-14T18:00:00-04:00")
    end_iso: str = Field(..., description="End time in ISO8601, e.g., 2025-09-14T19:00:00-04:00")
    location: Optional[str] = None
    calendar: Optional[str] = Field(None, description="Calendar name or ID (defaults to Family Caledar)")

class UpdateEventReq(BaseModel):
    event_id: str
    calendar: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    start_iso: Optional[str] = None
    end_iso: Optional[str] = None

class DeleteEventReq(BaseModel):
    event_id: str
    calendar: Optional[str] = None

class FindEventReq(BaseModel):
    title: str
    start_date: str  # YYYY-MM-DD
    end_date: str    # YYYY-MM-DD
    calendar: Optional[str] = None

# ---------- endpoints ----------
def check_auth(authorization: Optional[str]):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    if token != API_TOKEN:
        raise HTTPException(status_code=403, detail="Invalid token")

@app.post("/add_event")
def add_event(payload: CreateEventReq, authorization: Optional[str] = Header(None)):
    check_auth(authorization)
    service = get_service()
    cal_id = resolve_calendar_id(service, payload.calendar)
    event = {
        'summary': payload.title,
        'description': payload.description or '',
        'start': {'dateTime': payload.start_iso, 'timeZone': TIMEZONE},
        'end':   {'dateTime': payload.end_iso,   'timeZone': TIMEZONE},
    }
    if payload.location:
        event['location'] = payload.location
    created = service.events().insert(calendarId=cal_id, body=event).execute()
    return {"htmlLink": created.get('htmlLink'), "eventId": created.get('id'), "calendarId": cal_id}

@app.post("/update_event")
def update_event(payload: UpdateEventReq, authorization: Optional[str] = Header(None)):
    check_auth(authorization)
    service = get_service()
    cal_id = resolve_calendar_id(service, payload.calendar)
    ev = service.events().get(calendarId=cal_id, eventId=payload.event_id).execute()
    if payload.title is not None: ev['summary'] = payload.title
    if payload.description is not None: ev['description'] = payload.description
    if payload.location is not None: ev['location'] = payload.location
    if payload.start_iso is not None: ev['start'] = {'dateTime': payload.start_iso, 'timeZone': TIMEZONE}
    if payload.end_iso is not None:   ev['end']   = {'dateTime': payload.end_iso,   'timeZone': TIMEZONE}
    updated = service.events().update(calendarId=cal_id, eventId=payload.event_id, body=ev).execute()
    return {"htmlLink": updated.get('htmlLink'), "eventId": updated.get('id')}

@app.post("/delete_event")
def delete_event(payload: DeleteEventReq, authorization: Optional[str] = Header(None)):
    check_auth(authorization)
    service = get_service()
    cal_id = resolve_calendar_id(service, payload.calendar)
    service.events().delete(calendarId=cal_id, eventId=payload.event_id).execute()
    return {"status": "deleted", "eventId": payload.event_id}

@app.post("/find_event")
def find_event(payload: FindEventReq, authorization: Optional[str] = Header(None)):
    check_auth(authorization)
    service = get_service()
    cal_id = resolve_calendar_id(service, payload.calendar)
    # Build time window
    start = dt.datetime.strptime(payload.start_date, "%Y-%m-%d")
    end = dt.datetime.strptime(payload.end_date, "%Y-%m-%d") + dt.timedelta(days=1)
    resp = service.events().list(
        calendarId=cal_id,
        timeMin=start.isoformat() + "Z",
        timeMax=end.isoformat() + "Z",
        singleEvents=True,
        orderBy='startTime',
        q=payload.title
    ).execute()
    events = resp.get('items', [])
    if not events:
        return {"events": []}
    # Return minimal list
    out = []
    for ev in events:
        out.append({
            "eventId": ev.get('id'),
            "summary": ev.get('summary'),
            "start": ev.get('start'),
            "end": ev.get('end'),
            "htmlLink": ev.get('htmlLink')
        })
    return {"events": out}
