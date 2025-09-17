# HA Public Transport VBB

Este repositorio ofrece una integración para Home Assistant que obtiene los horarios de salida de la red de transporte público de Berlín-Brandeburgo (VBB) y los expone como sensores. Cada parada configurada aparece en Home Assistant como un dispositivo propio.

## Ejemplo

![Imagen de ejemplo Berlin Hauptbahnhof](images/Hauptbahnhof.png)

## Instalación

La integración está disponible como [repositorio predeterminado en HACS](https://hacs.xyz/):

1. Abre **HACS → Integrations** y busca **VBB Public Transport**.
2. Instala la integración y reinicia Home Assistant a continuación.

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

La integración utiliza la API pública `https://v5.vbb.transport.rest/`. Se requiere una conexión a Internet activa. La cobertura del servicio se limita a paradas ubicadas en Alemania (zona del VBB). Se necesita Home Assistant 2023.12 o posterior.

Por defecto se consultan las salidas para los próximos 120 minutos y hasta 100 resultados. Estos valores pueden ajustarse en la configuración.

## Autor

Este repositorio fue creado por [404GamerNotFound](https://github.com/404GamerNotFound) (Tony Brüser).
