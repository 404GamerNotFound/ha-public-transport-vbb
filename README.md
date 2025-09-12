# HA Public Transport VBB

Dieses Repository stellt ein einfaches Home-Assistant Plugin bereit, um
Abfahrtszeiten des Verkehrsverbunds Berlin-Brandenburg (VBB) abzurufen und
als Sensor anzuzeigen. Jede konfigurierte Haltestelle wird in Home Assistant
als eigenes Gerät dargestellt.

## Beispiel

![Beispielbild Berlin Hauptbahnhof](images/Hauptbahnhof.png)

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
Namen an. Zusätzlich können die Abfragezeitspanne (`duration` in Minuten) und
die maximale Anzahl an Ergebnissen (`results`) eingestellt werden.

### Haltestellen-ID finden

Die ID einer Haltestelle lässt sich über die öffentliche API ermitteln. Rufe
im Browser `https://v6.vbb.transport.rest/locations?query=<Haltestellenname>`
auf (z. B. `https://v6.vbb.transport.rest/locations?query=Berlin%20Hauptbahnhof`).
In der JSON-Antwort steht im Feld `id` die benötigte Haltestellen-ID.

Für jede Linie und Zielrichtung an der Haltestelle wird ein eigener Sensor
angelegt (z. B. `S7 S Strausberg`). Der Sensor zeigt die Zeit der nächsten
Abfahrt als Zustand an. Die aktuelle Verspätung in Minuten wird als Attribut
`delay` angezeigt. Weitere Abfahrten werden als Attribut `departures`
bereitgestellt. Zusätzlich werden Informationen zur Haltestelle wie
`latitude`, `longitude`, `station_dhid`, `line_id`, `operator` und `trip_id`
als Attribute bereitgestellt.

## Hinweise

Die Integration verwendet die öffentliche API unter
`https://v6.vbb.transport.rest/`. Für die Verwendung ist eine funktionierende
Internetverbindung erforderlich.

Standardmäßig werden die Abfahrten für 120 Minuten im Voraus und maximal 100
Ergebnisse abgefragt. Diese Werte lassen sich in der Konfiguration anpassen.

## Autor

Dieses Repository wurde von [404GamerNotFound](https://github.com/404GamerNotFound) (Tony Brüser) erstellt.
