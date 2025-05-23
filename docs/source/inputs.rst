Input de datos
==============

Este es el esquema de datos que deben seguir los archivos suministrados como insumos a UrbanTrips.

Transacciones
-------------

Tabla con las transacciones.

.. list-table:: 
   :widths: 25 25 50
   :header-rows: 1

   * - Campo
     - Tipo de dato
     - Descripción
   * - *id_trx*
     - int
     - **Obligatorio**. Id único que identifique cada registro y permita luego vincular la transacción en Urbantrips con el dataset original.
   * - *fecha_trx*
     - strftime
     - **Obligatorio**. Timestamp de la transaccion. Puede ser solo el día o el dia, hora y minuto.
   * - *id_tarjeta_trx*
     - int/str
     - **Obligatorio**. Un id que identifique a cada tarjeta.
   * - *modo_trx*
     - str
     - Opcional. Se estandarizará con lo especificado en `modos` en el archivo de configuración. Si no hay información en la tabla, se imputará todo como `autobus`.
   * - *hora_trx*
     - int
     - Opcional a menos que `fecha_trx` no tenga información de la hora y minutos. Entero de 0 a 23 indicando la hora de la transacción.
   * - *id_linea_trx*
     - int
     - **Obligatorio**. Entero que identifique a la linea. 
   * - *id_ramal_trx*
     - int
     - Opcional. Entero que identifique al ramal.
   * - *interno_trx*
     - int
     - **Obligatorio**. Entero que identifique al interno 
   * - *orden_trx*
     - int
     - Opcional a menos que `fecha_trx` no tenga información de la hora y minutos. Entero comenzando en 0 que esatblezca el orden de transacciones para una misma tarjeta en un mismo día.
   * - *latitud_trx*
     - float
     - **Obligatorio**. Latitud de la transacción.
   * - *longitud_trx*
     - float
     - **Obligatorio**. Longitud de la transacción. 
   * - *factor_expansion*
     - float
     - Opcional. Factor de expansión en caso de tratarse de una muestra. 
    
     
Información de lineas y ramales
-------------------------------

Tabla con metadata descriptiva de las lineas y ramales. La forma de tratar a las líneas y ramales en UrbanTrips es muy específica, por lo tanto se aconseja leer el apartado  :doc:`lineas_ramales`.

.. list-table:: 
   :widths: 25 25 50
   :header-rows: 1

   * - Campo
     - Tipo de dato
     - Descripción
   * - *id_linea*
     - int
     - **Obligatorio**. Entero que identifique a la linea.
   * - *nombre_linea*
     - str
     - **Obligatorio**. Nombre de la línea.
   * - *modo*
     - str
     - **Obligatorio**. Modo de la linea.
   * - *id_ramal*
     - int
     - **Obligatorio si hay ramales**.Entero que identifique al ramal.   
   * - *nombre_ramal*
     - str
     - **Obligatorio si hay ramales**. Nombre del ramal.
   * - *empresa*
     - str
     - Opcional. Nombre de la empresa.
   * - *descripcion*
     - str
     - Opcional. Descripción adicional de la linea o ramal.
   * - *id_linea_agg*
     - int
     - Opcional. id único de una línea que contenga más de un ramal y deba tratarse de modo unificado para imputar destinos.
   * - *nombre_linea_agg*
     - str
     - Opcional. descripción de la línea que contenga más de un ramal y deba tratarse de modo unificado para imputar destinos
     
               	

     

Recorridos lineas
-----------------

Archivo ``geojson`` con la cartografía de los recorridos de la linea. Debe ser un LineString 2D, sin multilineas. Se necesita una única línea por cada linea o ramal (si existen ramales). Por ello no se considera el sentido del recorrido (ida o vuelta). Se debe tomar uno solo para construir las paradas. En caso de que existan diferencias en el recorrido, se puede desviar el mismo para que pase por un punto medio y seguir siendo un recorrido representativo del ramal.

.. list-table:: 
   :widths: 25 25 50
   :header-rows: 1

   * - Campo
     - Tipo de dato
     - Descripción
   * - *id_linea*
     - int
     - **Obligatorio**. Entero que identifique a la linea.
   * - *id_ramal*
     - int
     - **Obligatorio si hay ramales**. Entero que identifique al ramal.
   * - *stops_distance*
     - int
     - Opcional. Distancia en metros a aplicarse al interpolar paradas sobre el recorrido.
   * - *line_stops_buffer*
     - int
     - Opcional. Distancia en metros entre paradas para que se puedan agregar en una sola.
   * - *geometry*
     - 2DLineString
     - Polilinea del recorrido. No puede ser multilinea.


GPS
---

Tabla con el posicionamiento de cada interno con información de linea y ramal.  La existencia de la tabla GPS permitira calcular KPI adicionales como el Índice Pasajero- Kilómetro (IPK) o el factor de ocupación, entre otros.

.. list-table:: 
   :widths: 25 25 50
   :header-rows: 1

   * - Campo
     - Tipo de dato
     - Descripción
   * - *id_gps*
     - int
     - **Obligatorio**. Id único que identifique cada registro.
   * - *id_linea_gps*
     - int
     - **Obligatorio**. Id único que identifique la linea.
   * - *id_ramal_gps*
     - int
     - **Obligatorio si hay ramales**. Id único que identifique cada ramal.
   * - *interno_gps*
     - int
     - **Obligatorio**. Id único que identifique cada interno.
   * - *fecha_gps*
     - strftime
     - **Obligatorio**. Dia, hora y minuto de la posición GPS del interno.
   * - *latitud_gps*
     - float
     - **Obligatorio**. Latitud. 
   * - *longitud_gps*
     - float
     - **Obligatorio**. Longitud.
   * - *servicios_gps*
     - int | str
     - **Obligatorio si se quiere procesar serviciobs**. Columna que contiene la apertura y cierre de un servicio.
   * - *velocity_gps*
     - float
     - **Opcional**. Velocidad del vehíuclo en km/h.

Paradas
-------

Tabla que contenga las paradas de cada linea y ramal (si hay ramales). El campo ``node_id`` se utiliza para identificar en qué paradas puede haber transbordo entre dos ramales de la misma linea. Para esas paradas el ``node_id`` debe ser el mismo, para las demas paradas debe ser único dentro de la misma línea. De contar con recorridos puede utilizarse el notebook ``stops_creation_with_node_id_helper.ipynb`` para crearlas.

.. list-table:: 
   :widths: 25 25 50
   :header-rows: 1

   * - Campo
     - Tipo de dato
     - Descripción
   * - *id_linea*
     - int
     - **Obligatorio**. Entero que identifique a la linea.
   * - *id_ramal*
     - int
     - **Obligatorio si hay ramales**. Entero que identifique a al ramal.     
   * - *order*
     - int
     - **Obligatorio**. Entero único que siga un recorrido de la linea o ramal de manera incremental. No importa el sentido
   * - *y*
     - float
     - **Obligatorio**. Latitud.     
   * - *x*
     - float
     - **Obligatorio**. Longitud.
   * - *node_id*
     - int
     - **Obligatorio**. Identifica con el mismo id estaciones donde puede haber transbordo entre ramales de una misma linea. Único para los otros casos dentro de la misma línea.     
     
     
Zonificaciones  
--------------

Tabla que contenga las zonificaciones o zonas de análisis de tránsito para las que se quieran agregar datos. No existe una esquema de datos definido, puede tener cualquier columna o atributo y la cantidad que se desee, siempre que se especifique correctamente en el archivo de configuración.

Polígonos de interés
--------------------

.. list-table:: 
   :widths: 25 25 50
   :header-rows: 1

   * - id
     - tipo
     - geometry
   * - *id*
     - str
     - **Obligatorio**. Texto que identifique con un nombre al polígono de interés.
   * - *tipo*
     - str
     - Debe identificar si se trata de un polígono de interés o de una cuenca. Debe tomar valores `poligono` o `cuenca`.
   * - *geometry*
     - Polygon o MultiPolygon
     - Polígono de la zona de interés. 



Tiempos de viaje entre estaciones
---------------------------------

.. list-table:: 
   :widths: 25 25 50
   :header-rows: 1

   * - Campo
     - Tipo de dato
     - Descripción
   * - *id_o*
     - int
     - **Obligatorio**. id de la estación de origen.
   * - *id_linea_o*
     - int
     - **Obligatorio**. id de la línea de origen.
   * - *id_ramal_o*
     - int
     - id del ramal de origen en caso de que existan ramales.
   * - *lat_o*
     - float
     - **Obligatorio**. Latitud de la estación de origen.
   * - *lon_o*
     - float
     - **Obligatorio**. Longitud de la estación de origen. 
   * - *id_d*
     - int
     - **Obligatorio**. id de la estación de destino.
   * - *id_linea_d*
     - int
     - **Obligatorio**. id de la línea de destino.
   * - *id_ramal_d*
     - int
     - id del ramal de destino en caso de que existan ramales.
   * - *lat_d*
     - float
     - **Obligatorio**. Latitud de la estación de destino.
   * - *lon_d*
     - float
     - **Obligatorio**. Longitud de la estación de destino.
   * - *travel_time_min*
     - float
     - **Obligatorio**. Tiempo de viaje en minutos entre las dos estaciones.
