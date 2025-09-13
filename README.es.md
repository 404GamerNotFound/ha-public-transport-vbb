# HA Public Transport VBB

Este repositorio ofrece una integración para Home Assistant que obtiene los horarios de salida de la red de transporte público de Berlín-Brandeburgo (VBB) y los expone como sensores. Cada parada configurada aparece en Home Assistant como un dispositivo propio.

## Ejemplo

![Imagen de ejemplo Berlin Hauptbahnhof](images/Hauptbahnhof.png)

## Instalación

La integración puede instalarse a través de [HACS](https://hacs.xyz/):

1. Añade este repositorio como repositorio personalizado en HACS.
2. Busca "VBB Public Transport" e instala la integración.
3. Reinicia Home Assistant.

Como alternativa, copia la carpeta `custom_components/vbb` en tu directorio `custom_components`.

## Configuración

Después de la instalación, la integración puede configurarse mediante la interfaz de usuario:

1. Ve a **Ajustes → Dispositivos y servicios → Añadir integración**.
2. Elige **VBB Public Transport**.
3. Busca una parada introduciendo su nombre o coordenadas y selecciona el resultado deseado.
4. Define el nombre, el intervalo de consulta (`duration` en minutos) y el número máximo de resultados (`results`).

### ID de parada (opcional)

La integración incluye una función de búsqueda, por lo que ya no es necesario proporcionar manualmente la ID de la parada. Aun así puede obtenerse mediante la API pública: `https://v5.vbb.transport.rest/locations?query=<nombre de la parada>` (ej. `https://v5.vbb.transport.rest/locations?query=Berlin%20Hauptbahnhof`). La ID se encuentra en el campo `id` de la respuesta JSON.

Para cada línea y dirección en la parada se crea un sensor separado (p. ej. `S7 S Strausberg`). El estado del sensor muestra la hora de la siguiente salida. El retraso actual en minutos se expone en el atributo `delay`. Otras salidas están disponibles en el atributo `departures`. Se proporciona información adicional como `latitude`, `longitude`, `station_dhid`, `line_id`, `operator` y `trip_id`.

## Notas

La integración utiliza la API pública `https://v5.vbb.transport.rest/`. Se requiere una conexión a Internet activa.

Por defecto se consultan las salidas para los próximos 120 minutos y hasta 100 resultados. Estos valores pueden ajustarse en la configuración.

## Autor

Este repositorio fue creado por [404GamerNotFound](https://github.com/404GamerNotFound) (Tony Brüser).
