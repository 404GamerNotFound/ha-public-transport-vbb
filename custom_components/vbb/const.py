"""Constants for the VBB departures integration."""

DOMAIN = "vbb"
API_BASES = (
    "https://v6.vbb.transport.rest",
    "https://v5.vbb.transport.rest",
)
API_PATH = "/stops/{station}/departures"
SEARCH_PATH = "/locations"
NEARBY_PATH = "/locations/nearby"
REQUEST_TIMEOUT = 10
HEADERS = {
    "Accept": "application/json",
    "User-Agent": "HomeAssistant-VBB",
}
CONF_STATION_ID = "station_id"
CONF_DURATION = "duration"
CONF_RESULTS = "results"
CONF_PRODUCTS = "products"
DEFAULT_NAME = "VBB Departures"
DEFAULT_DURATION = 120
DEFAULT_RESULTS = 100
PRODUCT_OPTIONS = [
    "suburban",
    "subway",
    "tram",
    "bus",
    "ferry",
    "regional",
    "express",
]
DEFAULT_PRODUCTS = PRODUCT_OPTIONS
