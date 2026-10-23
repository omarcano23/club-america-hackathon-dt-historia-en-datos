# Framework Analítico: "La Historia de André Jardine"

## 1. Definición de Objetos Analíticos Principales
- **Posesión:** Cadena continua de eventos realizados por un mismo equipo. Inicia cuando el equipo recupera el balón con control o pone el balón en juego (saque de meta, tiro libre) y termina con pérdida de balón, falta cometida, disparo o interrupción arbitral.
- **Secuencia Ofensiva:** Cadena de 3 o más pases dentro de una misma posesión que logra avanzar al menos 15 metros en dirección vertical hacia la meta rival o ingresar al último tercio.
- **Transición Defensiva:** Intervalo de 8 segundos posterior a la pérdida inmediata de la posesión en campo propio o medio campo.
- **Acción de Presión Alta:** Toda acción defensiva (presión, duelo, intercepción, falta) ejecutada a más de 60 metros de la portería propia.

## 2. Supuestos Explicitados
- Se normalizan las coordenadas de todas las acciones defensivas y ofensivas a un terreno estándar de 105 x 68 metros.
- Las posesiones de menos de 2 pases que no terminen en remate no se consideran "construcción de juego" sino "balones divididos o despejes".
- Para el cálculo de la altura de la línea defensiva, se utiliza el promedio de la posición Y de los eventos 360 del bloque posterior durante la posesión rival.

## 3. Coherencia e Integridad
- Ninguna gráfica de $xG$ o $OBV$ utilizará eventos que hayan sido excluidos por el filtro de posesión activa.