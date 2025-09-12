"""Constants for the VBB departures integration."""

DOMAIN = "vbb"
API_URL = (
    "https://v5.vbb.transport.rest/stops/{station}/departures"
    "?duration={duration}&results={results}"
)
SEARCH_URL = "https://v5.vbb.transport.rest/locations"
NEARBY_URL = "https://v5.vbb.transport.rest/locations/nearby"
HEADERS = {
    "Accept": "application/json",
    "User-Agent": "HomeAssistant-VBB",
}
CONF_STATION_ID = "station_id"
CONF_DURATION = "duration"
CONF_RESULTS = "results"
DEFAULT_NAME = "VBB Departures"
DEFAULT_DURATION = 120
DEFAULT_RESULTS = 100
