# HA Public Transport VBB

Dieses Repository stellt ein einfaches Home-Assistant Plugin bereit, um
Abfahrtszeiten des Verkehrsverbunds Berlin-Brandenburg (VBB) abzurufen und
als Sensor anzuzeigen. Jede konfigurierte Haltestelle wird in Home Assistant
als eigenes Gerät dargestellt.

## Installation

Die Integration kann bequem über [HACS](https://hacs.xyz/) installiert
werden:

1. Füge dieses Repository in HACS als benutzerdefiniertes Repository hinzu.
2. Suche nach "VBB Public Transport" und installiere die Integration.
3. Starte Home Assistant neu.

Alternativ kann der Ordner `custom_components/vbb` manuell in das
`custom_components` Verzeichnis kopiert werden.

## Konfiguration

Nach der Installation kann die Integration über die Benutzeroberfläche
konfiguriert werden. Gehe zu **Einstellungen → Geräte & Dienste → Integration
hinzufügen** und wähle **VBB Public Transport** aus. Gib die gewünschte
Haltestellen-ID (z. B. `900000003201` für Berlin Hauptbahnhof) sowie einen
Namen an.

Für jede Linie und Richtung an der Haltestelle wird ein eigener Sensor
angelegt (z. B. `S7_1` und `S7_2`). Der Sensor zeigt die Zeit der nächsten
Abfahrt als Zustand an. Weitere Abfahrten werden als Attribut `departures`
bereitgestellt.

## Hinweise

Die Integration verwendet die öffentliche API unter
`https://v5.vbb.transport.rest/`. Für die Verwendung ist eine funktionierende
Internetverbindung erforderlich.
