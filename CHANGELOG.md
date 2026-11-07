# Changelog

## 0.8.0

### Performance
- One API request per station and update interval (`DataUpdateCoordinator`).
  Previously every sensor polled the API itself every 30 seconds, because the
  configured interval was never applied (`_attr_scan_interval` is not read by
  Home Assistant). A station with 9 sensors made ~18 requests per minute; now
  it makes one every 5 minutes.
- Sensors switch to the next departure exactly when the current one leaves,
  without an extra request.
- Frequently changing attributes (`departures`, `delay`, `trip_id`,
  `current_trip_position`, …) are excluded from the recorder; the `departures`
  list is capped at 10 entries.

### Fixes
- Discovery timer was never cancelled, so every reload added another polling
  loop.
- HTTP responses are now always released (`async with`), timeouts use
  `asyncio.timeout`.
- Delay of `0` (on time) was reported as missing; delays are now always minutes.
- State now uses the realtime departure (`when`); the planned time is available
  as `planned_when`. Cancelled trips are skipped.
- Toggling a product switch reloaded the entry twice.
- Station search shows a proper error when the API is unreachable.
- Setup retries automatically while the API is down.

### New
- Options flow: change update interval, time span, results and transport types
  without removing the station.
- Product switches belong to the station device.
- Test suite (`pytest`) and CI job.

### Requirements
- Home Assistant 2024.12 or newer.
