import os.path
import datetime
import argparse
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/calendar']

JST = datetime.timezone(datetime.timedelta(hours=9))

# Fixed path logic for Skills structure (.agent/skills/hmc_pilot/scripts/)
# Need to go up 5 levels to reach root (file -> scripts -> hmc_pilot -> skills -> .agent -> root)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))
CREDENTIALS_FILE = os.path.join(BASE_DIR, 'oauth_credentials.json')
TOKEN_FILE = os.path.join(BASE_DIR, 'token.json')

def get_service():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Token expired. Refreshing...")
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Refresh failed: {e}. Falling back to manual authentication.")
                creds = None
        
        if not creds or not creds.valid:
            if not os.path.exists(CREDENTIALS_FILE):
                raise FileNotFoundError(f"Credentials file not found at {CREDENTIALS_FILE}")
            
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES)
            # Use manual flow for remote environment
            flow.redirect_uri = 'http://localhost'
            auth_url, _ = flow.authorization_url(prompt='consent')

            print(f"Please go to this URL: {auth_url}")
            code = input("Enter the authorization code (found in the URL after authorization, value of 'code='): ")
            flow.fetch_token(code=code)
            creds = flow.credentials
        # Save the credentials for the next run
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
    
    # Proactive refresh if expiring soon (within 10 minutes)
    elif creds and creds.valid and creds.expiry:
        # Check if expiration is within 10 minutes
        # Note: creds.expiry is usually UTC naive
        now_utc = datetime.datetime.utcnow()
        if creds.expiry - now_utc < datetime.timedelta(minutes=10):
            print("Token expiring soon. Forcing refresh...")
            try:
                creds.refresh(Request())
                with open(TOKEN_FILE, 'w') as token:
                    token.write(creds.to_json())
                print("Token refreshed and saved.")
            except Exception as e:
                print(f"Proactive refresh failed: {e}")

    service = build('calendar', 'v3', credentials=creds)
    return service

def get_events(target_date_str=None):
    service = get_service()
    
    # Get the start and end of the current day or target day (JST)
    if target_date_str:
        try:
            now = datetime.datetime.strptime(target_date_str, "%Y-%m-%d").replace(tzinfo=JST)
        except ValueError:
            print("Invalid date format. Use 'YYYY-MM-DD'")
            return
    else:
        now = datetime.datetime.now(JST)

    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
    end_of_day = now.replace(hour=23, minute=59, second=59, microsecond=999999).isoformat()

    print(f"Getting events for: {now.date()} (JST)")
    events_result = service.events().list(calendarId='primary', timeMin=start_of_day,
                                          timeMax=end_of_day, singleEvents=True,
                                          orderBy='startTime', timeZone='Asia/Tokyo').execute()
    events = events_result.get('items', [])

    if not events:
        print('No upcoming events found.')
        return

    for event in events:
        start = event['start'].get('dateTime', event['start'].get('date'))
        # Parse start time to be more readable if it's dateTime
        if 'T' in start:
             dt = datetime.datetime.fromisoformat(start).astimezone(JST)
             start_str = dt.strftime('%H:%M')
        else:
             start_str = "All Day"

        print(f"{start_str} {event['summary']}")

def add_event(title, start_time_str, duration_minutes=60):
    """
    Adds an event to the calendar.
    start_time_str should be in 'YYYY-MM-DD HH:MM' format or just 'HH:MM' for today.
    """
    service = get_service()
    
    now = datetime.datetime.now()
    
    if len(start_time_str) == 5: # HH:MM
        start_dt = datetime.datetime.strptime(f"{now.date()} {start_time_str}", "%Y-%m-%d %H:%M")
    else:
        try:
             start_dt = datetime.datetime.strptime(start_time_str, "%Y-%m-%d %H:%M")
        except ValueError:
            print("Invalid date format. Use 'YYYY-MM-DD HH:MM' or 'HH:MM'")
            return

    end_dt = start_dt + datetime.timedelta(minutes=int(duration_minutes))
    
    event = {
      'summary': title,
      'start': {
        'dateTime': start_dt.isoformat(),
        'timeZone': 'Asia/Tokyo', # Assuming JST based on user location
      },
      'end': {
        'dateTime': end_dt.isoformat(),
        'timeZone': 'Asia/Tokyo',
      },
    }

    event = service.events().insert(calendarId='primary', body=event).execute()
    print(f"Event created: {event.get('htmlLink')}")

def delete_event(title):
    """
    Deletes events with the matching title from today onwards.
    """
    service = get_service()
    now = datetime.datetime.utcnow().isoformat() + 'Z'
    
    events_result = service.events().list(calendarId='primary', timeMin=now,
                                          singleEvents=True, orderBy='startTime').execute()
    events = events_result.get('items', [])

    found = False
    for event in events:
        if event.get('summary') == title:
            service.events().delete(calendarId='primary', eventId=event['id']).execute()
            print(f"Event deleted: {event['summary']} ({event['start'].get('dateTime', event['start'].get('date'))})")
            found = True
    
    if not found:
        print(f"No event found with title: {title}")

def main():
    parser = argparse.ArgumentParser(description='HMC Calendar Manager')
    parser.add_argument('--action', choices=['get_events', 'add_event', 'delete_event'], required=True, help='Action to perform')
    parser.add_argument('--title', help='Title of the event')
    parser.add_argument('--start', help='Start time (HH:MM or YYYY-MM-DD HH:MM)')
    parser.add_argument('--duration', default=60, help='Duration in minutes')
    parser.add_argument('--date', help='Target date for get_events (YYYY-MM-DD)')

    args = parser.parse_args()

    try:
        if args.action == 'get_events':
            get_events(args.date)
        elif args.action == 'add_event':
            if not args.title or not args.start:
                print("Title and start time are required for adding an event.")
                return
            add_event(args.title, args.start, args.duration)
        elif args.action == 'delete_event':
            if not args.title:
                print("Title is required for deleting an event.")
                return
            delete_event(args.title)
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == '__main__':
    main()
