# optimizer/parameters.py
import numpy as np
import pandas as pd
import os

# --- Definición de Rutas ---
APP_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(APP_DIR, 'data')

# --- Parámetros Compartidos ---
# (Costos, Pesos, Normalización, Niveles S/I/T, etc. que son iguales para ambas ubicaciones)
SHARED_PARAMS = {
    'alpha': 0.3, 'beta': 0.4, 'gamma': 0.2,
    'sigma_epsilon_R': 0.1,
    'weights_S': {'MO': 0.40, 'pH': 0.15, 'POXC': 0.25, 'DA': 0.20},
    'weights_I': {'AporteMO': 0.40, 'CIns': 0.20, 'Diver': 0.25, 'BioIns': 0.15},
    'weights_T': {'ESiRe': 0.40, 'MRP': 0.20, 'MIPOrg': 0.25, 'GesInf': 0.15},
    'norm_params': {
        'MO': {'min': 1.5, 'opt': 4.0}, 'pH': {'opt': 6.5, 'sigma': 1.0},
        'POXC': {'min': 400, 'opt': 900}, 'DA': {'opt': 1.45, 'crit': 1.6},
        'AporteMO': {'min': 5, 'maxr': 32},
    },
    'S_Niveles': {'Basico': 0.620, 'Intermedio': 0.830, 'Avanzado': 0.991},
    'I_Niveles': {'Basico': 0.626, 'Intermedio': 0.845, 'Avanzado': 1.000},
    'T_Niveles': {'Basico': 0.520, 'Intermedio': 0.800, 'Avanzado': 0.960},
    'ESiRe_Niveles': {'Basico': 0.55, 'Intermedio': 0.75, 'Avanzado': 0.90},
    'MIPOrg_Niveles': {'Basico': 0.5, 'Intermedio': 0.8, 'Avanzado': 1.0},
    # Lluvia - SOLO parámetros compartidos aquí
    'Lluvia_max_exceso': 0.6,
    # Plagas (asumimos iguales)
    'PerdPoten': {'STK': 0.70, 'PIC': 0.40, 'NMT': 0.40, 'MF': 0.30},
    # Calor - Umbrales (asumimos iguales)
    'T_umbral_estres': 35,
    'T_umbral_critico': 40,
    'dias_periodo_critico': list(range(244, 366)), # Ajustar si el ciclo cambia por ubicación
    # Precio (asumimos igual)
    'Pconv_esperado_ton': 4182.04,
    'premio_factor': 1.6697,
    'mu_epsilon_P': 1.0,
    'sigma_epsilon_P': 0.303,
    # Costos DEFAULT (pueden ser sobrescritos por input del usuario)
    'C_fijo_default': 43500,
    'C_cert_default': 20000,
    'C_var_por_ha_Niveles': {'Basico': 120915, 'Intermedio': 177728, 'Avanzado': 280105},
    # Simulación
    'N_simulaciones': 5000,
    # Defaults Usuario (para inputs opcionales)
    'defaults_usuario': {
        'MO': 3.25, 'pH': 6.5, 'POXC': 800, 'DA': 1.3,
        'AporteMO': 30, 'CalidadComp_C': 25.0, 'CalidadComp_N': 1.85,
        'DiversidadNumCat': 3, 'NivelBioIns': 2,
        'TipoSistemaRiego': 'Aspersion', 'PracticaMRP': 3, 'PracticaMIP': 3, 'PracticaGesInf': 3,
        'R_avg_usuario': 30.0
        # Los costos fijos/cert/var no van aquí, se pasan o usan default
    },
}

# --- Parámetros Específicos por Ubicación ---
LOCATION_PARAMS = {
    'Tecoman': {
        'location_name': 'Tecomán',
        # Lluvia - Distribución
        'shape_lluvia': 9.59,
        'scale_lluvia': 85.37,
        # Lluvia - Umbrales
        'Lluvia_crit_min': 405.69,
        'Lluvia_opt_min': 946.62,
        'Lluvia_opt_max': 1893.23,
        'Lluvia_crit_max': 3245.54,
        # Tmax - Simulación
        'phi_Tmax': 0.7021,
        'sigma_ruido_Tmax': 0.71468,
        # Tmax - Archivos y Columnas
        'tmax_prom_csv': 'tmax_prom_suave_tecoman.csv',
        'tmax_std_csv': 'tmax_std_suave_tecoman.csv',
        'columna_datos_prom': 'PROM_S', # Nombre de columna en tu CSV Tecomán prom
        'columna_datos_std': 'DESVEST_S'   # Nombre de columna en tu CSV Tecomán std
        # Añadir aquí otros parámetros si varían, ej: ETc, umbrales lluvia...
    },
    'Manzanillo': {
        'location_name': 'Manzanillo',
        # Lluvia - Distribución
        'shape_lluvia': 5.76,  
        'scale_lluvia': 150.28,
        # Lluvia - Umbrales
        'Lluvia_crit_min': 306.54,
        'Lluvia_opt_min': 715.26,
        'Lluvia_opt_max': 1430.52,
        'Lluvia_crit_max': 2452.31,
        # Tmax - Simulación
        'phi_Tmax': 0.5783,  
        'sigma_ruido_Tmax': 0.834175,
        # Tmax - Archivos y Columnas
        'tmax_prom_csv': 'tmax_prom_suave_manzanillo.csv', # Debes crear este archivo CSV
        'tmax_std_csv': 'tmax_prom_suave_manzanillo.csv',   # Debes crear este archivo CSV
        'columna_datos_prom': 'PROM_S', # Ajusta si la columna se llama diferente
        'columna_datos_std': 'DESVEST_S'    # Ajusta si la columna se llama diferente
    }
    # Añadir más ubicaciones aquí si es necesario
}

# --- Función para Cargar Datos Tmax de una Ubicación Específica ---
def load_tmax_data(location_id, params):
    """Carga los datos Tmax promedio y std dev para la ubicación dada."""
    if location_id not in LOCATION_PARAMS:
        print(f"ERROR CRÍTICO: Ubicación '{location_id}' no encontrada en LOCATION_PARAMS.")
        return None, None

    loc_params = LOCATION_PARAMS[location_id]
    archivo_csv_prom = loc_params.get('tmax_prom_csv')
    archivo_csv_std = loc_params.get('tmax_std_csv')
    col_prom = loc_params.get('columna_datos_prom', 'PROM_S') # Default si no está definido
    col_std = loc_params.get('columna_datos_std', 'DESVEST_S')   # Default si no está definido

    if not archivo_csv_prom or not archivo_csv_std:
         print(f"ERROR CRÍTICO: Nombres de archivo CSV Tmax no definidos para '{location_id}'.")
         return None, None

    ruta_completa_prom = os.path.join(DATA_DIR, archivo_csv_prom)
    ruta_completa_std = os.path.join(DATA_DIR, archivo_csv_std)
    tmax_prom_data = None
    tmax_std_data = None

    print(f"--- Cargando datos Tmax para: {loc_params.get('location_name', location_id)} ---")
    try:
        print(f"Leyendo promedio desde: {ruta_completa_prom}")
        df_prom = pd.read_csv(ruta_completa_prom)
        if col_prom not in df_prom.columns:
            raise KeyError(f"Columna '{col_prom}' no encontrada en {archivo_csv_prom}")
        tmax_prom_data = df_prom[col_prom].to_numpy()
        if len(tmax_prom_data) != 366:
            print(f"ERROR: Se esperaban 366 valores Tmax prom, encontrados {len(tmax_prom_data)}.")
            tmax_prom_data = None
        else:
             print("OK: Datos Tmax promedio cargados.")

    except FileNotFoundError:
        print(f"ERROR: Archivo no encontrado: {ruta_completa_prom}")
    except Exception as e:
        print(f"Error al leer CSV de promedios ({archivo_csv_prom}): {e}")

    try:
        print(f"Leyendo std dev desde: {ruta_completa_std}")
        df_std = pd.read_csv(ruta_completa_std)
        if col_std not in df_std.columns:
            raise KeyError(f"Columna '{col_std}' no encontrada en {archivo_csv_std}")
        tmax_std_data = df_std[col_std].to_numpy()
        if len(tmax_std_data) != 366:
             print(f"ERROR: Se esperaban 366 valores Tmax std dev, encontrados {len(tmax_std_data)}.")
             tmax_std_data = None
        else:
             print("OK: Datos Tmax std dev cargados.")
    except FileNotFoundError:
        print(f"ERROR: Archivo no encontrado: {ruta_completa_std}")
    except Exception as e:
        print(f"Error al leer CSV de std dev ({archivo_csv_std}): {e}")

    if tmax_prom_data is None or tmax_std_data is None:
         print("\n*** ADVERTENCIA SEVERA: No se pudieron cargar datos Tmax estacionales para esta ubicación. ***")

    return tmax_prom_data, tmax_std_data


# --- Combinar Parámetros ---
# Puedes tener una función que combine shared y location-specific si lo necesitas
# o acceder a ellos por separado. Por ahora, los mantenemos separados.

# Nota: La carga de datos Tmax ahora debería llamarse desde donde se necesite,
# pasando la ubicación seleccionada, en lugar de cargar todo al inicio.
# O podrías precargarlos todos si prefieres. Vamos a cargarlos bajo demanda.

print("Módulo de parámetros cargado. Estructura lista para ubicaciones.")
# No cargamos Tmax aquí, se hará bajo demanda.