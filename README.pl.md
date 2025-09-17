# HA Public Transport VBB

To repozytorium udostępnia integrację Home Assistant, która pobiera czasy odjazdów z sieci transportu publicznego Berlina i Brandenburgii (VBB) i prezentuje je jako sensory. Każdy skonfigurowany przystanek pojawia się w Home Assistant jako osobne urządzenie.

## Przykład

![Przykładowy obraz Berlin Hauptbahnhof](images/Hauptbahnhof.png)

## Instalacja

Integrację można zainstalować jako [repozytorium domyślne w HACS](https://hacs.xyz/):

1. Otwórz **HACS → Integrations** i wyszukaj **VBB Public Transport**.
2. Zainstaluj integrację i uruchom ponownie Home Assistant.

Alternatywnie skopiuj folder `custom_components/vbb` do swojego katalogu `custom_components`.

## Konfiguracja

Po instalacji integrację można skonfigurować za pomocą interfejsu użytkownika:

1. Przejdź do **Ustawienia → Urządzenia i usługi → Dodaj integrację**.
2. Wybierz **VBB Public Transport**.
3. Wyszukaj przystanek, wpisując jego nazwę lub współrzędne, i wybierz odpowiedni wynik.
4. Ustaw nazwę, okno zapytania (`duration` w minutach) oraz maksymalną liczbę wyników (`results`).

### ID przystanku (opcjonalnie)

Integracja zawiera funkcję wyszukiwania, więc ręczne podawanie ID przystanku nie jest już wymagane. Nadal można je uzyskać z publicznego API: `https://v5.vbb.transport.rest/locations?query=<nazwa przystanku>` (np. `https://v5.vbb.transport.rest/locations?query=Berlin%20Hauptbahnhof`). ID przystanku znajduje się w polu `id` odpowiedzi JSON.

Dla każdej linii i kierunku na przystanku tworzony jest osobny sensor (np. `S7 S Strausberg`). Stan sensora pokazuje czas następnego odjazdu. Aktualne opóźnienie w minutach udostępniane jest w atrybucie `delay`. Kolejne odjazdy są dostępne w atrybucie `departures`. Udostępniane są również dodatkowe informacje jak `latitude`, `longitude`, `station_dhid`, `line_id`, `operator` i `trip_id`.

## Uwagi

Integracja korzysta z publicznego API `https://v5.vbb.transport.rest/`. Wymagane jest aktywne połączenie z Internetem. Usługa obejmuje wyłącznie przystanki w Niemczech (obszar VBB). Wymagany jest Home Assistant 2023.12 lub nowszy.

Domyślnie pobierane są odjazdy na 120 minut do przodu i maksymalnie 100 wyników. Wartości te można dostosować w konfiguracji.

## Autor

Repozytorium zostało stworzone przez [404GamerNotFound](https://github.com/404GamerNotFound) (Tony Brüser).
