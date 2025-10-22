# ha-public-transport-vbb

Dieses Repository stellt eine Home-Assistant Integration bereit, um Abfahrtszeiten des Verkehrsverbunds Berlin-Brandenburg (VBB) als Sensoren anzuzeigen. Jede konfigurierte Haltestelle erscheint in Home Assistant als eigenes Gerät.

## Beispiel

![Beispielbild Berlin Hauptbahnhof](images/Hauptbahnhof.png)

## Installation

Die Integration steht als [Standard-Repository in HACS](https://hacs.xyz/) zur Verfügung und kann direkt installiert werden:

1. Öffne **HACS → Integrationen** und suche nach **VBB Public Transport**.
2. Installiere die Integration und starte anschließend Home Assistant neu.

Alternativ kann der Ordner `custom_components/vbb` manuell in das `custom_components`-Verzeichnis kopiert werden.

## Konfiguration

Nach der Installation kann die Integration über die Benutzeroberfläche konfiguriert werden:

1. Gehe zu **Einstellungen → Geräte & Dienste → Integration hinzufügen**.
2. Wähle **VBB Public Transport** aus.
3. Suche nach einer Haltestelle, indem du den Namen oder Koordinaten eingibst, und wähle den gewünschten Treffer aus.
4. Lege Name, Abfragezeitspanne (`duration` in Minuten) und die maximale Anzahl an Ergebnissen (`results`) fest.

### Haltestellen-ID (optional)

Die Integration enthält eine Suchfunktion, sodass keine manuelle Haltestellen-ID benötigt wird. Die ID lässt sich weiterhin über die öffentliche API ermitteln: `https://v6.vbb.transport.rest/locations?query=<Haltestellenname>` (z. B. `https://v6.vbb.transport.rest/locations?query=Berlin%20Hauptbahnhof`). In der JSON-Antwort steht im Feld `id` die Haltestellen-ID.

Für jede Linie und Zielrichtung an der Haltestelle wird ein eigener Sensor angelegt (z. B. `S7 S Strausberg`). Der Sensor zeigt die Zeit der nächsten Abfahrt als Zustand an. Die aktuelle Verspätung in Minuten wird als Attribut `delay` angezeigt. Weitere Abfahrten stehen als Attribut `departures` zur Verfügung. Zusätzlich werden Informationen wie `latitude`, `longitude`, `station_dhid`, `line_id`, `operator` und `trip_id` bereitgestellt.

## Hinweise

Die Integration verwendet die öffentliche API unter `https://v6.vbb.transport.rest/`. Eine funktionierende Internetverbindung ist erforderlich. Der Dienst deckt ausschließlich Haltestellen in Deutschland (VBB-Gebiet) ab. Home Assistant 2023.12 oder neuer wird benötigt.

Standardmäßig werden Abfahrten für 120 Minuten im Voraus und maximal 100 Ergebnisse abgefragt. Diese Werte lassen sich in der Konfiguration anpassen.

## Autor

Dieses Repository wurde von [404GamerNotFound](https://github.com/404GamerNotFound) (Tony Brüser) erstellt.
