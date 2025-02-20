from shapely.geometry import LineString
import streamlit as st
import pandas as pd
import geopandas as gpd
import numpy as np
from PIL import Image
import requests
import matplotlib.pyplot as plt
import os
import yaml
import sqlite3
from shapely import wkt
from matplotlib import colors as mcolors
from folium import Figure
from shapely.geometry import LineString, Point, Polygon, shape, mapping
import h3


def leer_configs_generales():
    """
    Esta funcion lee los configs generales
    """
    path = os.path.join("configs", "configuraciones_generales.yaml")

    try:
        with open(path, 'r', encoding="utf8") as file:
            config = yaml.safe_load(file)
    except yaml.YAMLError as error:
        print(f'Error al leer el archivo de configuracion: {error}')

    return config


def leer_alias(tipo='dash'):
    """
    Esta funcion toma un tipo de datos (data o insumos)
    y devuelve el alias seteado en el archivo de congifuracion
    """
    configs = leer_configs_generales()
    # Setear el tipo de key en base al tipo de datos
    if tipo == 'data':
        key = 'alias_db_data'
    elif tipo == 'insumos':
        key = 'alias_db_insumos'
    elif tipo == 'dash':
        key = 'alias_db_dashboard'
    else:
        raise ValueError('tipo invalido: %s' % tipo)
    # Leer el alias
    try:
        alias = configs[key] + '_'
    except KeyError:
        alias = ''
    return alias


def traigo_db_path(tipo='dash'):
    """
    Esta funcion toma un tipo de datos (data o insumos)
    y devuelve el path a una base de datos con esa informacion
    """
    if tipo not in ('data', 'insumos', 'dash'):
        raise ValueError('tipo invalido: %s' % tipo)

    alias = leer_alias(tipo)

    db_path = os.path.join("data", "db", f"{alias}{tipo}.sqlite")

    return db_path


def iniciar_conexion_db(tipo='dash'):
    """"
    Esta funcion toma un tipo de datos (data o insumos)
    y devuelve una conexion sqlite a la db
    """
    db_path = traigo_db_path(tipo)
    assert os.path.isfile(
        db_path), f'No existe la base de datos para el dashboard en {db_path}'
    conn = sqlite3.connect(db_path, timeout=10)

    return conn

# Calculate weighted mean, handling division by zero or empty inputs


def weighted_mean(series, weights):
    try:
        result = (series * weights).sum() / weights.sum()
    except ZeroDivisionError:
        result = np.nan
    return result


def calculate_weighted_means(
    df_,
    aggregate_cols,
    weighted_mean_cols,
    weight_col,
    zero_to_nan=[],
    var_fex_summed=True,
):
    df = df_.copy()
    for i in zero_to_nan:
        df.loc[df[i] == 0, i] = np.nan

    # calculate_weighted_means  # Validate inputs
    if not set(aggregate_cols + weighted_mean_cols + [weight_col]).issubset(df.columns):
        raise ValueError("One or more columns specified do not exist in the DataFrame.")
    result = pd.DataFrame([])
    # Calculate the product of the value and its weight for weighted mean calculation
    for col in weighted_mean_cols:
        df.loc[df[col].notna(), f"{col}_weighted"] = (
            df.loc[df[col].notna(), col] * df.loc[df[col].notna(), weight_col]
        )
        grouped = (
            df.loc[df[col].notna()]
            .groupby(aggregate_cols, as_index=False)[[f"{col}_weighted", weight_col]]
            .sum()
        )
        grouped[col] = grouped[f"{col}_weighted"] / grouped[weight_col]
        grouped = grouped.drop([f"{col}_weighted", weight_col], axis=1)

        if len(result) == 0:
            result = grouped.copy()
        else:
            result = result.merge(grouped, how="left", on=aggregate_cols)

    if var_fex_summed:
        fex_summed = df.groupby(aggregate_cols, as_index=False)[weight_col].sum()
        result = result.merge(fex_summed, how="left", on=aggregate_cols)
    else:
        fex_mean = df.groupby(aggregate_cols, as_index=False)[weight_col].mean()
        result = result.merge(fex_mean, how="left", on=aggregate_cols)

    return result


def normalize_vars(tabla):
    if 'dia' in tabla.columns:
        tabla.loc[tabla.dia == 'weekday', 'dia'] = 'Hábil'
        tabla.loc[tabla.dia == 'weekend', 'dia'] = 'Fin de semana'
    if 'day_type' in tabla.columns:
        tabla.loc[tabla.day_type == 'weekday', 'day_type'] = 'Hábil'
        tabla.loc[tabla.day_type == 'weekend', 'day_type'] = 'Fin de semana'
    if 'tipo_dia' in tabla.columns:
        tabla.loc[tabla.tipo_dia == 'Dia habil', 'tipo_dia'] = 'Hábil'
        # tabla.loc[tabla.tipo_dia == 'weekend', 'tipo_dia'] = 'Fin de semana'

        
    if 'nombre_linea' in tabla.columns:
        tabla['nombre_linea'] = tabla['nombre_linea'].str.replace(' -', '')
    if 'Modo' in tabla.columns:
        tabla['Modo'] = tabla['Modo'].str.capitalize()
    if 'modo' in tabla.columns:
        tabla['modo'] = tabla['modo'].str.capitalize()
    return tabla


@st.cache_data
def levanto_tabla_sql(tabla_sql, tabla_tipo="dash", query=''):

    conn = iniciar_conexion_db(tipo=tabla_tipo)

    try:
        if len(query) == 0:
            query = f"""
            SELECT *
            FROM {tabla_sql}
            """

        tabla = pd.read_sql_query( query, conn )
    except:
        print(f"{tabla_sql} no existe")
        tabla = pd.DataFrame([])

    conn.close()

    if len(tabla) > 0:
        if "wkt" in tabla.columns:
            tabla["geometry"] = tabla.wkt.apply(wkt.loads)
            tabla = gpd.GeoDataFrame(tabla, crs=4326)
            tabla = tabla.drop(["wkt"], axis=1)

    tabla = normalize_vars(tabla)

    return tabla

def levanto_tabla_sql_local(tabla_sql, tabla_tipo="dash", query=''):

    conn = iniciar_conexion_db(tipo=tabla_tipo)

    try:
        if len(query) == 0:
            query = f"""
            SELECT *
            FROM {tabla_sql}
            """

        tabla = pd.read_sql_query( query, conn )
    except:
        print(f"{tabla_sql} no existe")
        tabla = pd.DataFrame([])

    conn.close()

    if len(tabla) > 0:
        if "wkt" in tabla.columns:
            tabla["geometry"] = tabla.wkt.apply(wkt.loads)
            tabla = gpd.GeoDataFrame(tabla, crs=4326)
            tabla = tabla.drop(["wkt"], axis=1)

    tabla = normalize_vars(tabla)

    return tabla
    
@st.cache_data
def get_logo():
    file_logo = os.path.join(
        "docs", "urbantrips_logo.jpg")
    if not os.path.isfile(file_logo):
        # URL of the image file on Github
        url = 'https://raw.githubusercontent.com/EL-BID/UrbanTrips/main/docs/urbantrips_logo.jpg'

        # Send a request to get the content of the image file
        response = requests.get(url)

        # Save the content to a local file
        with open(file_logo, 'wb') as f:
            f.write(response.content)
    image = Image.open(file_logo)
    return image


@st.cache_data
def create_linestring_od(df,
                         lat_o='lat_o',
                         lon_o='lon_o',
                         lat_d='lat_d',
                         lon_d='lon_d'):

    # Create LineString objects from the coordinates
    geometry = [LineString([(row['lon_o'], row['lat_o']),
                           (row['lon_d'], row['lat_d'])])
                for _, row in df.iterrows()]

    # Create a GeoDataFrame
    gdf = gpd.GeoDataFrame(df, geometry=geometry, crs=4326)

    return gdf


def calculate_weighted_means_ods(df,
                                 aggregate_cols,
                                 weighted_mean_cols,
                                 weight_col,
                                 agg_transferencias=False,
                                 agg_modo=False,
                                 agg_hora=False,
                                 agg_distancia=False,
                                 zero_to_nan=[]
                                 ):

    if agg_transferencias:
        df['transferencia'] = 99
    if agg_modo:
        df['modo_agregado'] = 99
    if agg_hora:
        df['rango_hora'] = 99
    if agg_distancia:
        df['distancia'] = 99

    df = calculate_weighted_means(df,
                                  aggregate_cols,
                                  weighted_mean_cols,
                                  weight_col,
                                  zero_to_nan)
    return df


def agg_matriz(df,
               aggregate_cols=['id_polygon', 
                               'zona', 
                               'Origen', 
                               'Destino',
                               'transferencia', 
                               'modo_agregado', 
                               'rango_hora', 
                               'distancia'],
               weight_col=['distance_osm_drive', 
                           'travel_time_min', 
                           'travel_speed'],
               weight_var='factor_expansion_linea',               
               zero_to_nan=['distance_osm_drive', 
                           'travel_time_min', 
                           'travel_speed'],
               agg_transferencias=False,
               agg_modo=False,
               agg_hora=False,
               agg_distancia=False):

    if len(df) > 0:
        if agg_transferencias:
            df['transferencia'] = 99
        if agg_modo:
            df['modo_agregado'] = 99
        if agg_hora:
            df['rango_hora'] = 99
        if agg_distancia:
            df['distancia'] = 99
        
        df1 = df.groupby(aggregate_cols, as_index=False)[weight_var].sum()

        df2 = calculate_weighted_means(df,
                              aggregate_cols=aggregate_cols,
                              weighted_mean_cols=weight_col,
                              weight_col=weight_var,
                              zero_to_nan=zero_to_nan)
        df = df1.merge(df2)


    return df


def creo_bubble_od(df,
                   aggregate_cols,
                   weighted_mean_cols,
                   weight_col,
                   agg_transferencias=False,
                   agg_modo=False,
                   agg_hora=False,
                   agg_distancia=False,
                   od='',
                   lat='lat1',
                   lon='lon1'):

    if 'id_polygon' not in df.columns:
        df['id_polygon'] = 'NONE'

    orig = pd.DataFrame([])
    if len(df) > 0:
        if agg_transferencias:
            df['transferencia'] = 99
        if agg_modo:
            df['modo_agregado'] = 99
        if agg_hora:
            df['rango_hora'] = 99
        if agg_distancia:
            df['distancia'] = 99

        orig = calculate_weighted_means_ods(df,
                                            aggregate_cols,
                                            [lat, lon],
                                            'factor_expansion_linea',
                                            agg_transferencias=agg_transferencias,
                                            agg_modo=agg_modo,
                                            agg_hora=agg_hora,
                                            agg_distancia=agg_distancia)

        orig['tot'] = orig.groupby(['id_polygon',
                                    'zona',
                                    'transferencia',
                                    'modo_agregado',
                                    'rango_hora',
                                    'distancia']).factor_expansion_linea.transform('sum')
        geometry = [Point(xy) for xy in zip(orig[lon], orig[lat])]
        orig = gpd.GeoDataFrame(orig, geometry=geometry, crs=4326)
        orig['viajes_porc'] = (
            orig.factor_expansion_linea / orig.tot * 100).round(1)
        orig = orig.rename(columns={od: 'od', lat: 'lat', lon: 'lon'})

    return orig


def df_to_linestrings(df, lat_cols, lon_cols):
    """
    Converts DataFrame rows into LineStrings based on specified lat/lon columns,
    ignoring pairs where either lat or lon is zero.

    Parameters:
    - df: pandas DataFrame containing the data.
    - lat_cols: List of column names for latitudes.
    - lon_cols: List of column names for longitudes.

    Returns:
    - GeoDataFrame with an added 'geometry' column containing LineStrings.
    """

    def create_linestring(row):
        # Filter out coordinate pairs where lat or lon is 0
        points = [(row[lon_cols[i]], row[lat_cols[i]]) for i in range(len(lat_cols))
                  if row[lat_cols[i]] != 0 and row[lon_cols[i]] != 0]
        # Create a LineString if there are at least two points
        return LineString(points) if len(points) >= 2 else None

    # Create 'geometry' column with LineStrings
    df['geometry'] = df.apply(create_linestring, axis=1)

    # Convert DataFrame to GeoDataFrame
    gdf = gpd.GeoDataFrame(df, geometry='geometry', crs=4326)

    return gdf


def create_data_folium(etapas,
                       viajes_matrices,
                       agg_transferencias=False,
                       agg_modo=False,
                       agg_hora=False,
                       agg_distancia=False,
                       agg_cols_etapas=[],
                       agg_cols_viajes=[],
                       etapas_seleccionada = True,
                       viajes_seleccionado = True,
                       origenes_seleccionado = True,
                       destinos_seleccionado = True,
                       transferencias_seleccionado = False):
    

    if transferencias_seleccionado:

        t1 = etapas.loc[etapas.transfer1_norm!='', ['zona', 
                                                    'transfer1_norm', 
                                                    'lat2_norm', 
                                                    'lon2_norm', 
                                                    'transferencia', 
                                                    'modo_agregado', 
                                                    'rango_hora', 
                                                    'distancia',
                                                    'factor_expansion_linea',]].rename(columns={'transfer1_norm':'transfer', 'lat2_norm':'lat_norm', 'lon2_norm':'lon_norm'})
        t2 = etapas.loc[etapas.transfer2_norm!='', ['zona', 
                                                    'transfer2_norm', 
                                                    'lat3_norm', 
                                                    'lon3_norm', 
                                                    'transferencia', 
                                                    'modo_agregado', 
                                                    'rango_hora', 
                                                    'distancia', 
                                                    'factor_expansion_linea',]].rename(columns={'transfer2_norm':'transfer', 'lat3_norm':'lat_norm', 'lon3_norm':'lon_norm'})
        transferencias = pd.concat([t1,t2], ignore_index=True)     
        transferencias['id_polygon'] = 'NONE'
        
        trans_cols_o = ['id_polygon', 
                        'zona', 
                        'transfer',
                         'transferencia', 
                        'modo_agregado', 
                        'rango_hora', 
                        'distancia']

        transferencias = creo_bubble_od(transferencias,
                                aggregate_cols=trans_cols_o,
                                weighted_mean_cols=['lat_norm', 'lon_norm'],
                                weight_col='factor_expansion_linea',
                                agg_transferencias=agg_transferencias,
                                agg_modo=agg_modo,
                                agg_hora=agg_hora,
                                agg_distancia=agg_distancia,
                                od='transfer',
                                lat='lat_norm',
                                lon='lon_norm')
        transferencias['factor_expansion_linea'] = transferencias['factor_expansion_linea'].round(0)
    else:
        transferencias = pd.DataFrame([])
    
    if etapas_seleccionada | transferencias_seleccionado:
        etapas = calculate_weighted_means_ods(etapas,
                                              agg_cols_etapas,
                                              ['distance_osm_drive', 'lat1_norm', 'lon1_norm', 'lat2_norm',
                                               'lon2_norm', 'lat3_norm', 'lon3_norm', 'lat4_norm', 'lon4_norm'],    
                                              'factor_expansion_linea',
                                              agg_transferencias=agg_transferencias,
                                              agg_modo=agg_modo,
                                              agg_hora=agg_hora,
                                              agg_distancia=agg_distancia,
                                              zero_to_nan=['lat1_norm', 'lon1_norm', 'lat2_norm', 'lon2_norm', 'lat3_norm', 'lon3_norm', 'lat4_norm', 'lon4_norm'])
    
        etapas[['lat1_norm',
                'lon1_norm',
                'lat2_norm',
                'lon2_norm',
                'lat3_norm',
                'lon3_norm',
                'lat4_norm',
                'lon4_norm']] = etapas[['lat1_norm',
                                        'lon1_norm',
                                        'lat2_norm',
                                        'lon2_norm',
                                        'lat3_norm',
                                        'lon3_norm',
                                        'lat4_norm',
                                        'lon4_norm']].fillna(0)
    
        etapas = df_to_linestrings(etapas,
                               lat_cols=['lat1_norm', 'lat2_norm', 'lat3_norm', 'lat4_norm'], lon_cols=['lon1_norm', 'lon2_norm', 'lon3_norm', 'lon4_norm'])

        etapas = etapas[etapas.inicio_norm != etapas.fin_norm].copy()
        etapas['factor_expansion_linea'] = etapas['factor_expansion_linea'].round(0)

    if viajes_seleccionado:
        viajes = calculate_weighted_means_ods(etapas,
                                              agg_cols_viajes,
                                              ['distance_osm_drive',
                                               'lat1_norm',
                                               'lon1_norm',
                                               'lat4_norm',
                                               'lon4_norm'],
                                              'factor_expansion_linea',
                                              agg_transferencias=agg_transferencias,
                                              agg_modo=agg_modo,
                                              agg_hora=agg_hora,
                                              agg_distancia=agg_distancia,
                                              zero_to_nan=['lat1_norm', 'lon1_norm', 'lat4_norm', 'lon4_norm'])
        viajes[['lat1_norm',
                'lon1_norm',
                'lat4_norm',
                'lon4_norm']] = viajes[['lat1_norm',
                                       'lon1_norm',
                                        'lat4_norm',
                                        'lon4_norm']].fillna(0)
    
        if 'id_polygon' not in viajes_matrices.columns:
            viajes_matrices['id_polygon'] = 'NONE'
    
        viajes = df_to_linestrings(viajes,
                                   lat_cols=['lat1_norm', 'lat4_norm'], lon_cols=['lon1_norm', 'lon4_norm'])

        viajes = viajes[viajes.inicio_norm != viajes.fin_norm].copy()
        viajes['factor_expansion_linea'] = viajes['factor_expansion_linea'].round(0)
    else:
        viajes = pd.DataFrame([])
        
    matriz = agg_matriz(viajes_matrices,
                        aggregate_cols=['id_polygon', 
                                        'zona', 
                                        'Origen', 
                                        'Destino',
                                        'transferencia', 
                                        'modo_agregado', 
                                        'rango_hora', 
                                        'distancia'],
                        weight_col=['distance_osm_drive', 
                                    'travel_time_min', 
                                    'travel_speed'],
                        zero_to_nan=['distance_osm_drive', 
                           'travel_time_min', 
                           'travel_speed'],
                        weight_var='factor_expansion_linea',
                        agg_transferencias=agg_transferencias,
                        agg_modo=agg_modo,
                        agg_hora=agg_hora,
                        agg_distancia=agg_distancia)
    
    matriz['factor_expansion_linea'] = matriz['factor_expansion_linea'].round(0)
    
    if ('poly_inicio' in viajes_matrices.columns) | ('poly_fin' in viajes_matrices.columns):
        bubble_cols_o = ['id_polygon', 'zona', 'inicio', 'poly_inicio',
                         'transferencia', 'modo_agregado', 'rango_hora', 'distancia']
        bubble_cols_d = ['id_polygon', 'zona', 'fin', 'poly_fin',
                         'transferencia', 'modo_agregado', 'rango_hora', 'distancia']
    else:
        bubble_cols_o = ['id_polygon', 'zona', 'inicio',
                         'transferencia', 'modo_agregado', 'rango_hora', 'distancia']
        bubble_cols_d = ['id_polygon', 'zona', 'fin',
                         'transferencia', 'modo_agregado', 'rango_hora', 'distancia']

    if origenes_seleccionado:
        origen = creo_bubble_od(viajes_matrices,
                                aggregate_cols=bubble_cols_o,
                                weighted_mean_cols=['lat1', 'lon1'],
                                weight_col='factor_expansion_linea',
                                agg_transferencias=agg_transferencias,
                                agg_modo=agg_modo,
                                agg_hora=agg_hora,
                                agg_distancia=agg_distancia,
                                od='inicio',
                                lat='lat1',
                                lon='lon1')
        origen['factor_expansion_linea'] = origen['factor_expansion_linea'].round()
    else:
        origen = pd.DataFrame([])

    if destinos_seleccionado:
        destino = creo_bubble_od(viajes_matrices,
                                 aggregate_cols=bubble_cols_d,
                                 weighted_mean_cols=['lat4', 'lon4'],
                                 weight_col='factor_expansion_linea',
                                 agg_transferencias=agg_transferencias,
                                 agg_modo=agg_modo,
                                 agg_hora=agg_hora,
                                 agg_distancia=agg_distancia,
                                 od='fin',
                                 lat='lat4',
                                 lon='lon4')
        destino['factor_expansion_linea'] = destino['factor_expansion_linea'].round(0)
    else:
        destino = pd.DataFrame([])

    if not etapas_seleccionada:
        etapas = pd.DataFrame([])


    return etapas, viajes, matriz, origen, destino, transferencias


@st.cache_data
def traigo_indicadores(tipo='all'):
    if tipo == 'all':
        indicadores_all = levanto_tabla_sql('agg_indicadores')
    else:
        indicadores_all = levanto_tabla_sql('poly_indicadores')

    general = indicadores_all[indicadores_all.Tipo == 'General']
    modal = indicadores_all[indicadores_all.Tipo == 'Modal']
    distancias = indicadores_all[indicadores_all.Tipo == 'Distancias']
    return general, modal, distancias


def get_epsg_m():
    '''
    Gets the epsg id for a coordinate reference system in meters from config
    '''
    configs = leer_configs_generales()
    epsg_m = configs['epsg_m']

    return epsg_m


def create_squared_polygon(min_x, min_y, max_x, max_y, epsg):

    width = max(max_x - min_x, max_y - min_y)
    center_x = (max_x + min_x) / 2
    center_y = (max_y + min_y) / 2

    square_bbox_min_x = center_x - width / 2
    square_bbox_min_y = center_y - width / 2
    square_bbox_max_x = center_x + width / 2
    square_bbox_max_y = center_y + width / 2

    square_bbox_coords = [
        (square_bbox_min_x, square_bbox_min_y),
        (square_bbox_max_x, square_bbox_min_y),
        (square_bbox_max_x, square_bbox_max_y),
        (square_bbox_min_x, square_bbox_max_y)
    ]

    p = Polygon(square_bbox_coords)
    s = gpd.GeoSeries([p], crs=f'EPSG:{epsg}')
    return s


def extract_hex_colors_from_cmap(cmap, n=5):
    # Choose a colormap
    cmap = plt.get_cmap(cmap)

    # Extract colors from the colormap
    colors = cmap(np.linspace(0, 1, n))

    # Convert the colors to hex format
    hex_colors = [mcolors.rgb2hex(color) for color in colors]

    return hex_colors
    
@st.cache_data
def bring_latlon():
    try:
        latlon = levanto_tabla_sql('agg_etapas', 'dash', 'SELECT lat1_norm, lon1_norm FROM agg_etapas ORDER BY RANDOM() LIMIT 100;')
        lat = latlon['lat1_norm'].mean()
        lon = latlon['lon1_norm'].mean()
        latlon = [lat, lon]
    except: 
        latlon = [-34.593, -58.451]
    return latlon

@st.cache_data
def traigo_lista_zonas(tipo = 'etapas'):

    if tipo == 'etapas':
        table = 'agg_etapas'        
    else:
        table = 'poly_etapas'

    query = f"""
            SELECT DISTINCT zona, inicio_norm FROM {table}
            UNION
            SELECT DISTINCT zona, transfer1_norm FROM {table}
            UNION
            SELECT DISTINCT zona, transfer2_norm FROM {table}
            UNION
            SELECT DISTINCT zona, fin_norm FROM {table};
            """
    zonas_values = etapas=levanto_tabla_sql(table, 'dash', query)
    zonas_values = zonas_values[(zonas_values.inicio_norm!='')&
                            (zonas_values.inicio_norm.notna())&
                            (zonas_values.inicio_norm!=' (cuenca)')].sort_values(['zona', 'inicio_norm']).rename(columns={'inicio_norm':'Nombre'})

    return zonas_values
    
# Convert geometry to H3 indices
def get_h3_indices_in_geometry(geometry, resolution):
    geojson = mapping(geometry)
    h3_indices = list(h3.polyfill(geojson, resolution, geo_json_conformant=True))
    return h3_indices


def normalizar_zonas(df, inicio_col, lat1_col, lon1_col, fin_col, lat2_col, lon2_col):
    """
    Normaliza las zonas para que los pares inicio/fin siempre estén ordenados de forma consistente,
    dejando sin cambios los registros donde inicio_col o fin_col estén vacíos (="").
    """
    # Máscara para identificar registros válidos (sin valores vacíos)
    mask_valid = (df[inicio_col] != "") & (df[fin_col] != "")
    
    # Máscara para el orden correcto (solo en registros válidos)
    mask_order = mask_valid & (df[inicio_col] < df[fin_col])
    
    # Asignar valores normalizados columna por columna
    df[f'{inicio_col}_norm'] = np.where(
        mask_valid,
        np.where(mask_order, df[inicio_col], df[fin_col]),
        df[inicio_col]
    )
    df[f'{lat1_col}_norm'] = np.where(
        mask_valid,
        np.where(mask_order, df[lat1_col], df[lat2_col]),
        df[lat1_col]
    )
    df[f'{lon1_col}_norm'] = np.where(
        mask_valid,
        np.where(mask_order, df[lon1_col], df[lon2_col]),
        df[lon1_col]
    )
    df[f'{fin_col}_norm'] = np.where(
        mask_valid,
        np.where(mask_order, df[fin_col], df[inicio_col]),
        df[fin_col]
    )
    df[f'{lat2_col}_norm'] = np.where(
        mask_valid,
        np.where(mask_order, df[lat2_col], df[lat1_col]),
        df[lat2_col]
    )
    df[f'{lon2_col}_norm'] = np.where(
        mask_valid,
        np.where(mask_order, df[lon2_col], df[lon1_col]),
        df[lon2_col]
    )
    
    return df


def traigo_tablas_con_filtros(mes, tipo_dia, var_zonif, var_filtro1, det_filtro1, var_filtro2, det_filtro2, zonas, zonificaciones):    

    lst1 = zonas[zonas[var_filtro1] == det_filtro1].h3.unique().tolist()
    lst2 = zonas[zonas[var_filtro2] == det_filtro2].h3.unique().tolist()
        
    conn = iniciar_conexion_db(tipo='dash')
    
    cursor = conn.cursor()

    # Crear marcadores de posición para SQL
    placeholders1 = ", ".join(["?"] * len(lst1))  # Para lista origen
    placeholders2 = ", ".join(["?"] * len(lst2))  # Para lista destino
    
    # Parámetros de la consulta
    params = [mes, tipo_dia] + lst1 * 4 + lst2 * 4
    
    # Consulta SQL
    query = f"""
    SELECT * FROM agg_etapas 
    WHERE zona = 'res_8'
    AND mes = ? 
    AND tipo_dia = ? 
    AND (
        (inicio_norm IN ({placeholders1}) OR transfer1_norm IN ({placeholders1}) OR transfer2_norm IN ({placeholders1}) OR fin_norm IN ({placeholders1}))
        AND 
        (inicio_norm IN ({placeholders2}) OR transfer1_norm IN ({placeholders2}) OR transfer2_norm IN ({placeholders2}) OR fin_norm IN ({placeholders2}))
    );
    """
    # Ejecutar consulta
    agg_etapas = pd.read_sql_query(query, conn, params=params)
    
    
    if len(agg_etapas) > 0:
        zonas_renamed = zonas[['h3', 'latitud', 'longitud', var_zonif]]
        
        for i, z in enumerate(['inicio', 'transfer1', 'transfer2', 'fin'], start=1):
            zonas_temp = zonas_renamed.rename(
                columns={
                    'h3': f'{z}_norm',
                    'latitud': f'lat{i}',
                    'longitud': f'lon{i}',
                    var_zonif: z
                }
            )
            agg_etapas = agg_etapas.merge(zonas_temp, how='left')
            agg_etapas[z] = agg_etapas[z].fillna('')
        
        # Filtros innecesarios en un solo paso
        agg_etapas = agg_etapas[
            ~(((agg_etapas.inicio == '') & (agg_etapas.inicio_norm != '')) |
              ((agg_etapas.fin == '') & (agg_etapas.fin_norm != '')) |
              ((agg_etapas.transfer1 == '') & (agg_etapas.transfer1_norm != '')) |
              ((agg_etapas.transfer2 == '') & (agg_etapas.transfer2_norm != '')))
        ]
    
        
        aggregate_cols = ['mes', 
                          'tipo_dia', 
                          'inicio', 
                          'transfer1', 
                          'transfer2', 
                          'fin', 
                          'zona', 
                          'transferencia', 
                          'modo_agregado',
                          'rango_hora', 
                          'genero', 
                          'tarifa', 
                          'coincidencias', 
                          'distancia',] 
        weighted_mean_cols=['distance_osm_drive',                                 
                            'travel_time_min', 
                            'travel_speed', 
                            'lat1', 
                            'lon1', 
                            'lat2', 
                            'lon2', 
                            'lat3', 
                            'lon3', 
                            'lat4', 
                            'lon4',
                             ]
        zero_to_nan = ['lat1',
                       'lon1',
                       'lat2',
                       'lon2',
                       'lat3',
                       'lon3',
                       'lat4',
                       'lon4',
                       'distance_osm_drive',                                 
                       'travel_time_min', 
                       'travel_speed',]
        
        agg_etapas = calculate_weighted_means(agg_etapas,
                                    aggregate_cols=aggregate_cols,
                                    weighted_mean_cols=weighted_mean_cols,
                                    weight_col='factor_expansion_linea',
                                    zero_to_nan=zero_to_nan,
                                    var_fex_summed=False)
        
        agg_etapas = normalizar_zonas(agg_etapas, 'inicio', 'lat1', 'lon1', 'fin', 'lat4', 'lon4')
        agg_etapas = normalizar_zonas(agg_etapas, 'transfer1', 'lat2', 'lon2', 'transfer2', 'lat3', 'lon3')
    
        agg_etapas['zona'] = var_zonif
    
    # Crear una lista de valores para la cláusula IN de forma segura
    placeholders1 = ", ".join(["?"] * len(lst1))
    placeholders2 = ", ".join(["?"] * len(lst2))
    params = [mes, tipo_dia] + lst1 * 2 + lst2 * 2
    
    query = f"""
    SELECT * FROM agg_matrices 
    WHERE zona = 'res_8'
    AND mes = ? 
    AND tipo_dia = ? 
        AND (
        (inicio IN ({placeholders1}) OR fin IN ({placeholders1}))
        AND 
        (inicio IN ({placeholders2}) OR fin IN ({placeholders2}))
    );
    """
    
    agg_matrices = pd.read_sql_query(query, conn, params=params)
    
    if len(agg_matrices) > 0:
        zonas_renamed = zonas[['h3', var_zonif, 'latitud', 'longitud']]
        for i, z in enumerate(['inicio', 'fin'], start=1):
            zonas_temp = zonas_renamed.rename(
                columns={
                    'h3': f'{z}',
                    'latitud': f'lat{i}_new',
                    'longitud': f'lon{i}_new',
                    var_zonif: f'{z}_new'
                }
            )
            agg_matrices = agg_matrices.merge(zonas_temp, how='left')
            agg_matrices[z] = agg_matrices[z].fillna('')

        agg_matrices = agg_matrices.drop(['inicio', 'fin', 'lat1', 'lon1', 'lat4', 'lon4'], axis=1)
        agg_matrices = agg_matrices.rename(columns={
            'inicio_new': 'inicio',
            'fin_new': 'fin',
            'lat1_new': 'lat1',
            'lon1_new': 'lon1',
            'lat2_new': 'lat4',
            'lon2_new': 'lon4'
        })
        
        agg_matrices = agg_matrices.merge(zonificaciones[['id', 'orden']].rename(columns={'id':'inicio', 'orden': 'orden_inicio'}))
        agg_matrices = agg_matrices.merge(zonificaciones[['id', 'orden']].rename(columns={'id':'fin', 'orden': 'orden_fin'}))
        
        agg_matrices['Origen'] = agg_matrices.orden_inicio.astype(
        int).astype(str).str.zfill(3)+'_'+agg_matrices.inicio
        agg_matrices['Destino'] = agg_matrices.orden_fin.astype(
            int).astype(str).str.zfill(3)+'_'+agg_matrices.fin
        agg_matrices = agg_matrices.drop(['orden_inicio', 'orden_fin'], axis=1)
    
    return agg_etapas, agg_matrices