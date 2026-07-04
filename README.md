# ha-public-transport-vbb

Home Assistant integration for public transport departures in Berlin-Brandenburg (VBB).

## Availability

The integration provides data for stops served by the Verkehrsverbund Berlin-Brandenburg and is therefore only relevant for installations located in Germany.

## Installation via HACS

This repository is available as a [default repository in HACS](https://hacs.xyz/). Install it by navigating to **HACS → Integrations**, searching for **VBB Public Transport** and completing the installation flow. Afterwards restart Home Assistant so the integration becomes available under **Settings → Devices & Services → Add Integration**.

The integration requires Home Assistant 2023.12 or newer.

## Languages

- [Deutsch](README.de.md)
- [English](README.en.md)
- [Français](README.fr.md)
- [Español](README.es.md)
- [Polski](README.pl.md)

## Konfiguration

Nach der Installation kann die Integration über die Benutzeroberfläche
konfiguriert werden. Gehe zu **Einstellungen → Geräte & Dienste → Integration
hinzufügen** und wähle **VBB Public Transport** aus. Gib die gewünschte
Haltestellen-ID (z. B. `900000003201` für Berlin Hauptbahnhof) sowie einen
Namen an. Zusätzlich können die Abfragezeitspanne (`duration` in Minuten) und
die maximale Anzahl an Ergebnissen (`results`) eingestellt werden.

Für jede Linie und Zielrichtung an der Haltestelle wird ein eigener Sensor
angelegt (z. B. `S7 S Strausberg`). Der Sensor zeigt die Zeit der nächsten
Abfahrt als Zustand an. Weitere Abfahrten werden als Attribut `departures`
bereitgestellt. Zusätzlich werden Informationen zur Haltestelle wie
`latitude` und `longitude` als Attribute bereitgestellt.

## Hinweise

Die Integration verwendet die öffentliche API unter
`https://v5.vbb.transport.rest/`. Für die Verwendung ist eine funktionierende
Internetverbindung erforderlich.

Standardmäßig werden die Abfahrten für 120 Minuten im Voraus und maximal 100
Ergebnisse abgefragt. Diese Werte lassen sich in der Konfiguration anpassen.

## Autor

Dieses Repository wurde von [404GamerNotFound](https://github.com/404GamerNotFound) (Tony Brüser) erstellt.

## Support

If you find this project helpful, you can support it via PayPal: [paypal.me/TonyBrueser](https://www.paypal.com/paypalme/TonyBrueser)

