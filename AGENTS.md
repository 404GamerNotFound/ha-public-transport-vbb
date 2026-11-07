# AGENTS.md – HA-Public-Transport-VBB

Leitfaden für KI-Agenten und Mitwirkende. Vor Änderungen zuerst diese Datei lesen.

## Projekt

Custom Integration für Home Assistant (`custom_components/vbb`, Domain `vbb`), die
Abfahrten im Verkehrsverbund Berlin-Brandenburg über die öffentliche API
`https://v6.vbb.transport.rest` (Fallback `v5`) anzeigt. Vertrieb über HACS
(Default-Repository). Autor/Codeowner: `404GamerNotFound` (Tony Brüser).

- Mindestversion Home Assistant: **2024.12** (`hacs.json`, README)
- Python: wie Home Assistant (3.12+; `type`-Aliase werden genutzt)
- Keine externen Requirements (`manifest.json` → `requirements: []`)
- Version steht in `custom_components/vbb/manifest.json`, Änderungen in `CHANGELOG.md`

## Architektur

| Datei | Aufgabe |
|---|---|
| `__init__.py` | Setup/Unload des Config Entries, erzeugt **einen** `VbbCoordinator` pro Haltestelle (`entry.runtime_data`), Update-Listener lädt bei Optionsänderung neu |
| `coordinator.py` | `VbbCoordinator` (DataUpdateCoordinator): ein API-Abruf pro Intervall, parst Abfahrten zu `Departure`-Objekten (gefiltert nach Verkehrsmittel, sortiert, ohne Ausfälle und Vergangenes) |
| `api.py` | `async_request_json`: probiert alle `API_BASES`, wirft `VbbApiError` |
| `sensor.py` | `VbbStationSensor`, `VbbDepartureSensor` (Linie + Ziel), `VbbDirectionSensor` (Linie + Richtung, Slots 1–3); alle `CoordinatorEntity`; Discovery neuer Linien über Coordinator-Listener; Rollover zur nächsten Abfahrt per `async_track_point_in_utc_time` |
| `switch.py` | Ein Schalter pro Verkehrsmittel (`EntityCategory.CONFIG`), schreibt `options[products]` |
| `config_flow.py` | Haltestellensuche (Name/Koordinaten) → Auswahl → Einstellungen; `VbbOptionsFlow` für Intervall, Zeitraum, Ergebnisse, Verkehrsmittel |
| `const.py` | Konstanten, Defaults (`DEFAULT_UPDATE_INTERVAL = 5` Minuten) |
| `translations/` | `de.json`, `en.json` (config + options) |

## Wichtige Regeln

1. **Nie pro Entity die API abfragen.** Alle Daten kommen aus dem Coordinator.
   `_attr_scan_interval` wird von Home Assistant ignoriert – Polling nur über den Coordinator.
2. **`unique_id`-Formate nicht ändern**, sonst entstehen bei Nutzern neue Entities:
   - Station: `vbb_{station_id}_station`
   - Linie/Ziel: `vbb_{station_id}_{slugify(line)}_{slugify(destination)}`
   - Linie/Richtung: `vbb_{station_id}_{slugify(line)}_{slugify(direction)}_dir_{n}`
   - Schalter: `{entry_id}_{product}_enabled`
3. Häufig wechselnde Attribute gehören in `_unrecorded_attributes` (Recorder-Größe).
   `departures`-Listen bleiben auf `MAX_ATTRIBUTE_DEPARTURES` begrenzt.
4. `delay` der API ist in **Sekunden**; `0` bedeutet pünktlich (nicht „fehlend“).
   Ausgegeben wird immer in Minuten (`get_delay_minutes`).
5. Sensorzustand = Echtzeit-Abfahrt (`when`), Fallback Fahrplan (`plannedWhen`);
   `cancelled`-Fahrten werden übersprungen.
6. Neue UI-Texte immer in `translations/de.json` **und** `en.json` pflegen.
7. YAML-Plattform (`async_setup_platform`) bleibt aus Kompatibilitätsgründen erhalten.

## Tests

```bash
pip install pytest-homeassistant-custom-component
pytest -q
```

Tests liegen in `tests/` und mocken `custom_components.vbb.coordinator.async_request_json`.
Sie prüfen u. a.: genau ein API-Aufruf für alle Sensoren, unveränderte `unique_id`s,
Rollover ohne API-Aufruf, Setup-Retry bei API-Ausfall, Options-Flow.
CI (`.github/workflows/validation.yml`): hassfest, HACS-Validierung, pytest.

## Release

1. Version in `manifest.json` erhöhen, `CHANGELOG.md` ergänzen.
2. Tests lokal ausführen.
3. Commit, Push, GitHub-Release mit Tag `vX.Y.Z` erstellen (HACS nutzt Releases).
