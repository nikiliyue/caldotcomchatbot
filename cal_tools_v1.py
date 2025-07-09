# cal_tools.py

import os
import requests
from langchain_core.tools import tool
from datetime import datetime
from dateutil.parser import parse

# --- Configuration ---
CAL_API_KEY = os.getenv("CAL_API_KEY")
CAL_USER_ID = os.getenv("CAL_USER_ID")
CAL_API_BASE_URL = "https://api.cal.com/v2"

# --- Helper Functions ---
def _get_headers():
    """Returns the authorization headers for Cal.com API."""
    return {
        "Authorization": f"Bearer {CAL_API_KEY}",
        "Content-Type": "application/json"
    }

def _get_event_type_id(event_type_slug: str) -> int | None:
    """Fetches the event type ID for a given slug."""
    url = f"{CAL_API_BASE_URL}/event-types"
    try:
        response = requests.get(url, headers=_get_headers(), params={"userId": CAL_USER_ID})
        response.raise_for_status()
        event_types = response.json().get("event_types", [])
        print(event_types)
        for et in event_types:
            if et.get("slug") == event_type_slug:
                return et.get("id")
        return None
    except requests.RequestException as e:
        print(f"Error fetching event types: {e}")
        return None

# --- LangChain Tools ---

@tool
def list_scheduled_events(user_email: str) -> str:
    """
    Lists all active, scheduled events for a given user's email.
    Returns the event details including the booking ID, which is needed for cancellations.
    """
    if not CAL_API_KEY:
        return "Error: Cal.com API key is not configured."
    url = f"{CAL_API_BASE_URL}/bookings"
    params = {
        "attendeeEmail": user_email,
        "status": "ACCEPTED" # Only show active, confirmed events
    }
    try:
        response = requests.get(url, headers=_get_headers(), params=params)
        response.raise_for_status()
        bookings = response.json().get("bookings", [])

        if not bookings:
            return f"No scheduled events found for {user_email}."

        formatted_events = []
        for booking in bookings:
            start_time_utc = parse(booking['startTime'])
            start_time_local = start_time_utc.astimezone().strftime('%Y-%m-%d %I:%M %p %Z')
            formatted_events.append(
                f"- Title: {booking['title']}, "
                f"Start Time: {start_time_local}, "
                f"Booking ID: {booking['id']}"
            )
        return "Here are your scheduled events:\n" + "\n".join(formatted_events)
    except requests.HTTPError as e:
        return f"API Error: Failed to retrieve events. Status code: {e.response.status_code}, Response: {e.response.text}"
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"

@tool
def book_event(start_time: str, name: str, email: str, time_zone: str, event_type_slug: str = "30min", notes: str = "") -> str:
    """
    Books a new event/meeting. The start_time must be in ISO 8601 format (e.g., '2024-08-15T14:00:00.000Z').
    The LLM should first check for availability before calling this tool.
    The default event type is a '30min'.
    """
    if not all([CAL_API_KEY, CAL_USER_ID]):
        return "Error: Cal.com API key or User ID is not configured."

    event_type_id = _get_event_type_id(event_type_slug)
    if not event_type_id:
        return f"Error: Could not find an event type with slug '{event_type_slug}' for user '{CAL_USER_ID}'."

    url = f"{CAL_API_BASE_URL}/bookings"
    payload = {
        "start": start_time,
        "eventTypeId": event_type_id,
        "timeZone": time_zone,
        "language": "en",
        "responses": {
            "name": name,
            "email": email,
            "notes": notes,
        },
        "status": "ACCEPTED",
    }
    try:
        response = requests.post(url, headers=_get_headers(), json=payload)
        response.raise_for_status()
        booking = response.json().get("booking", {})
        return f"Success! Event '{booking['title']}' has been booked for {name} ({email}) at {booking['startTime']}. Booking ID is {booking['id']}."
    except requests.HTTPError as e:
        error_details = e.response.json().get("message", e.response.text)
        return f"API Error: Failed to book event. The time slot might be unavailable. Please check availability first. Details: {error_details}"
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"

@tool
def cancel_event(booking_id: int) -> str:
    """
    Cancels a specific event using its booking ID. The booking ID must be an integer.
    The user should be informed of the event details before confirming cancellation.
    To get the booking ID, first list the scheduled events.
    """
    if not CAL_API_KEY:
        return "Error: Cal.com API key is not configured."

    url = f"{CAL_API_BASE_URL}/bookings/{booking_id}"
    params = {"cancellationReason": "Cancelled by user via chatbot."}
    
    try:
        response = requests.delete(url, headers=_get_headers(), params=params)
        response.raise_for_status()
        return f"Success! Booking with ID {booking_id} has been cancelled."
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            return f"Error: No booking found with ID {booking_id}."
        error_details = e.response.json().get("message", e.response.text)
        return f"API Error: Failed to cancel event. Details: {error_details}"
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"

# Note: A check_availability tool could also be added, but for this challenge,
# we can let the LLM attempt to book and handle the failure if the slot is taken.
# This simplifies the user interaction flow.
