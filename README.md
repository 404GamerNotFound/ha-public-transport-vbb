# HA Public Transport VBB

Dieses Repository stellt ein einfaches Home-Assistant Plugin bereit, um
Abfahrtszeiten des Verkehrsverbunds Berlin-Brandenburg (VBB) abzurufen und
als Sensor anzuzeigen. Jede konfigurierte Haltestelle wird in Home Assistant
als eigenes Gerät dargestellt.

## Installation

1. Kopiere den Ordner `custom_components/vbb` in das `custom_components`
   Verzeichnis deiner Home‑Assistant Installation.
2. Starte Home Assistant neu.

## Konfiguration

Füge in deiner `configuration.yaml` einen Sensor wie folgt hinzu:

```yaml
sensor:
  - platform: vbb
    station_id: "900000003201"  # Beispiel: Berlin Hauptbahnhof
    name: "Berlin Hbf"
```

Der Sensor zeigt die Zeit der nächsten Abfahrt als Zustand an. Weitere
Abfahrten werden als Attribut `departures` bereitgestellt.

## Hinweise

Die Integration verwendet die öffentliche API unter
`https://v5.vbb.transport.rest/`. Für die Verwendung ist eine funktionierende
Internetverbindung erforderlich.
