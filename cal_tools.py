# cal_tools.py

import os
import requests
import logging
from langchain_core.tools import tool
from datetime import datetime, timedelta
from dateutil.parser import parse

# Get a logger instance for this module
logger = logging.getLogger(__name__)

# --- Configuration ---
CAL_API_BASE_URL_V2 = "https://api.cal.com/v2" # For /me, /bookings (read/delete)
CAL_API_BASE_URL_V1 = "https://api.cal.com/v1" # For /bookings (create), /event-types

# --- Helper Functions ---

# Module-level cache for user details
_cached_user_details = None

def _get_v2_headers():
    """Returns the authorization headers for the v2 API."""
    return {
        "Authorization": os.getenv('CAL_API_KEY'),
        "cal-api-version": "2024-08-13",
        "Content-Type": "application/json"
    }

def _get_user_details() -> dict | None:
    """
    Fetches the user's full details (ID, name, etc.) from the /v2/me endpoint.
    This is still needed to get the organizer's name for the v1 booking title.
    Caches the result to avoid repeated API calls.
    """
    global _cached_user_details
    if _cached_user_details:
        return _cached_user_details

    url = f"{CAL_API_BASE_URL_V2}/me"
    try:
        response = requests.get(url, headers=_get_v2_headers())
        response.raise_for_status()
        user_data = response.json().get("data", {})
        if user_data.get("id"):
            logger.info(f"Successfully fetched and cached user details for user: {user_data.get('username')}")
            _cached_user_details = user_data
            return _cached_user_details
        else:
            logger.error(f"Could not find user details in /me response: {response.json()}")
            return None
    except requests.RequestException as e:
        logger.error(f"Error fetching user data from /me endpoint: {e}")
        return None

def _get_event_type_details(event_type_slug: str) -> dict | None:
    """
    Fetches event type details (ID, length) for a given slug using the v1 API.
    """
    api_key = os.getenv("CAL_API_KEY")
    if not api_key:
        logger.error("Cannot fetch event types: Cal.com API key is not configured.")
        return None

    url = f"{CAL_API_BASE_URL_V1}/event-types"
    querystring = {"apiKey": api_key}
    
    logger.info(f"Fetching event types from v1 endpoint for slug: {event_type_slug}")
    
    try:
        response = requests.get(url, params=querystring)
        response.raise_for_status()
        
        # The v1 endpoint nests the list under the "event_types" key.
        event_types = response.json().get("event_types", [])
        
        if not event_types:
            logger.warning("API returned no event types from the v1 endpoint.")
            return None

        for et in event_types:
            if et.get("slug") == event_type_slug:
                details = {"id": et.get("id"), "length": et.get("length"), "title": et.get("title")}
                logger.info(f"Found matching event type details: {details} for slug: {event_type_slug}")
                return details
        
        logger.warning(f"Could not find event type with slug '{event_type_slug}' in the v1 list.")
        return None
    except requests.RequestException as e:
        logger.error(f"Error fetching event types from v1 API: {e}")
        return None


# --- LangChain Tools ---

@tool
def book_event(start_time: str, name: str, email: str, time_zone: str, event_type_slug: str = "30min", notes: str = "") -> str:
    """
    Books a new event/meeting using the Cal.com v1 API.
    The start_time must be in ISO 8601 format (e.g., '2024-08-15T14:00:00.000Z').
    """
    api_key = os.getenv("CAL_API_KEY")
    if not api_key:
        logger.error("Booking failed: Cal.com API key is not configured.")
        return "Error: Cal.com API key is not configured."

    logger.info(f"Starting v1 booking process for slug '{event_type_slug}'")
    organizer_details = _get_user_details()
    event_type_info = _get_event_type_details(event_type_slug)

    if not organizer_details or not event_type_info:
        error_msg = f"Error: Could not retrieve required information for booking. Please check event type slug ('{event_type_slug}') and API key."
        logger.error(error_msg)
        return error_msg

    try:
        start_dt = parse(start_time)
        duration_minutes = event_type_info['length']
        end_dt = start_dt + timedelta(minutes=duration_minutes)
        end_time_iso = end_dt.isoformat().replace('+00:00', 'Z')
    except (ValueError, TypeError) as e:
        error_msg = f"Error: Invalid start_time format or event duration. Details: {e}"
        logger.error(error_msg)
        return error_msg

    url = f"{CAL_API_BASE_URL_V1}/bookings"
    querystring = {"apiKey": api_key}
    
    organizer_name = organizer_details.get("name") or organizer_details.get("username") or "Organizer"
    title = f"{event_type_info['title']} between {organizer_name} and {name}"

    payload = {
        "eventTypeId": event_type_info['id'], "start": start_time, "end": end_time_iso,
        "responses": {"name": name, "email": email}, "timeZone": time_zone,
        "language": "en", "title": title, "description": notes, "status": "ACCEPTED", "metadata": {}
    }
    
    headers = {"Content-Type": "application/json"}
    logger.info(f"Sending v1 booking request to {url} with payload: {payload}")

    try:
        response = requests.post(url, json=payload, headers=headers, params=querystring)
        response.raise_for_status()
        booking = response.json()
        
        if booking.get('id'):
            success_msg = f"Success! Event '{booking.get('title')}' has been booked. Booking ID is {booking.get('id')}."
            logger.info(success_msg)
            return success_msg
        else:
            logger.error(f"Booking response did not contain an ID. Response: {booking}")
            return "Booking may have succeeded, but the response was unexpected."

    except requests.HTTPError as e:
        error_details = e.response.text
        logger.error(f"API Error during v1 booking: {error_details} | Status: {e.response.status_code}")
        return f"API Error: Failed to book event. The time slot might be unavailable. Details: {error_details}"
    except Exception as e:
        logger.error(f"An unexpected error occurred during v1 booking: {str(e)}")
        return f"An unexpected error occurred: {str(e)}"

@tool
def list_scheduled_events(user_email: str) -> str:
    """Lists all active, scheduled events for a given user's email."""
    if not os.getenv("CAL_API_KEY"):
        return "Error: Cal.com API key is not configured."
    url = f"{CAL_API_BASE_URL_V2}/bookings"
    params = {"take":"100", "status":["upcoming","recurring", "unconfirmed"]}
    try:
        response = requests.get(url, headers=_get_v2_headers(), params=params)
        response.raise_for_status()
        bookings = response.json().get("data", [])

        if not bookings:
            return f"No scheduled events found for {user_email}."
            
        formatted_events = []
        for b in bookings:
            start_time_str = b.get('start')
            if start_time_str:
                start_time_local = parse(start_time_str).astimezone().strftime('%Y-%m-%d %I:%M %p %Z')
                formatted_events.append(
                    f"- Title: {b.get('title', 'No Title')}, "
                    f"Start Time: {start_time_local}, "
                    f"Booking UID: {b.get('uid')}"
                )
        
        if not formatted_events:
            return f"Found bookings for {user_email}, but could not parse their details."

        return "Here are your scheduled events:\n" + "\n".join(formatted_events)
    except requests.HTTPError as e:
        return f"API Error: Failed to retrieve events. Status: {e.response.status_code}, Response: {e.response.text}"
    except Exception as e:
        logger.error(f"An unexpected error occurred while listing events: {str(e)}")
        return f"An unexpected error occurred: {str(e)}"

@tool
def cancel_event(booking_uid: str) -> str:
    """Cancels an event using its booking ID. To get the ID, first list the scheduled events."""
    if not os.getenv("CAL_API_KEY"):
        return "Error: Cal.com API key is not configured."
    url = f"{CAL_API_BASE_URL_V2}/bookings/{booking_uid}/cancel"
    params = {"cancellationReason": "Cancelled by user via chatbot."}
    try:
        response = requests.post(url, headers=_get_v2_headers(), json=params)
        response.raise_for_status()
        return f"Success! Booking with ID {booking_uid} has been cancelled."
    except requests.HTTPError as e:
        if e.response.status_code == 404:
            return f"Error: No booking found with ID {booking_uid}."
        error_details = e.response.json().get("message", e.response.text)
        return f"API Error: Failed to cancel event. Details: {error_details}"
    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"