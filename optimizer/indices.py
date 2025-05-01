# optimizer/indices.py
import numpy as np

# --- Funciones de Normalización (Basadas en tu DOCX) ---

def normalize_min_max(value, min_val, max_val):
    if max_val == min_val: return 0.5 # Evitar división por cero
    score = (value - min_val) / (max_val - min_val)
    return max(0.0, min(1.0, score))

def normalize_gauss(value, opt_val, sigma=1.0):
    return np.exp(-((value - opt_val)**2) / (2 * sigma**2))

def normalize_min_max_inv(value, opt_val, crit_val):
     if crit_val == opt_val: return 0.5 # Evitar división por cero
     score = 1.0 - (value - opt_val) / (crit_val - opt_val)
     return max(0.0, min(1.0, score))

def normalize_cins(c_percent, n_percent):
    # Lógica de Puntos C/N
    puntos_cn = 0.2 # Default Inaceptable
    if n_percent > 0:
        cn_ratio = c_percent / n_percent
        if 15 <= cn_ratio <= 25: puntos_cn = 1.0
        elif (12 <= cn_ratio < 15) or (25 < cn_ratio <= 30): puntos_cn = 0.7
    # Lógica de Puntos %N
    puntos_n = 0.2 # Default Bajo
    if n_percent >= 1.5: puntos_n = 1.0
    elif n_percent >= 1.0: puntos_n = 0.7
    
    return (puntos_cn + puntos_n) / 2.0

def normalize_categ(value, scale_map):
    # scale_map es un diccionario, ej: {1: 0.3, 2: 0.6, 3: 0.8, 4: 1.0}
    # O podría ser directo si el valor es la categoría: {0:0, 1:0.3, 2:0.7, 3:1.0}
    return scale_map.get(value, 0) # Devuelve 0 si no encuentra la categoría

def normalize_riego(tipo_riego_str):
    mapa = {"Temporal": 0, "Gravedad": 0.55, "Aspersion": 0.80, "Goteo": 0.90, "Goteo+Sensores": 1.0}
    return mapa.get(tipo_riego_str, 0) # Default 0 si no coincide

# --- Función Principal para Calcular Índices del Usuario ---

def calculate_user_indices(user_inputs, defaults, params):
    """Calcula S, I, T del usuario usando inputs y defaults."""
    
    # Usar input del usuario o default si falta
    def get_val(key):
        return user_inputs.get(key, defaults[key])

    # Calcular componentes normalizados S
    mo_val = get_val('MO')
    ph_val = get_val('pH')
    poxc_val = get_val('POXC')
    da_val = get_val('DA')
    
    mo_norm = normalize_min_max(mo_val, params['norm_params']['MO']['min'], params['norm_params']['MO']['opt'])
    ph_norm = normalize_gauss(ph_val, params['norm_params']['pH']['opt'], params['norm_params']['pH']['sigma'])
    poxc_norm = normalize_min_max(poxc_val, params['norm_params']['POXC']['min'], params['norm_params']['POXC']['opt'])
    struct_norm = normalize_min_max_inv(da_val, params['norm_params']['DA']['opt'], params['norm_params']['DA']['crit'])

    # Calcular componentes normalizados I
    aporte_mo_val = get_val('AporteMO')
    calidad_c = get_val('CalidadComp_C') # Asume se pide %C
    calidad_n = get_val('CalidadComp_N') # Asume se pide %N
    diver_num = get_val('DiversidadNumCat')
    bioins_nivel = get_val('NivelBioIns')

    aporte_mo_norm = normalize_min_max(aporte_mo_val, params['norm_params']['AporteMO']['min'], params['norm_params']['AporteMO']['maxr'])
    cins_norm = normalize_cins(calidad_c, calidad_n)
    diver_norm = normalize_categ(diver_num, {1: 0.3, 2: 0.6, 3: 0.8, 4: 1.0}) # Escala DOCX [source: 708]
    bioins_norm = normalize_categ(bioins_nivel, {0: 0, 1: 0.4, 2: 0.7, 3: 1.0}) # Escala DOCX [source: 715]

    # Calcular componentes normalizados T
    riego_tipo = get_val('TipoSistemaRiego') # String: 'Gravedad', 'Aspersion', 'Goteo'
    mrp_nivel = get_val('PracticaMRP')       # Nivel 1-4
    mip_nivel = get_val('PracticaMIP')       # Nivel 1-4
    gesinf_nivel = get_val('PracticaGesInf') # Nivel 1-4
    
    esire_norm = normalize_riego(riego_tipo) # Mapea string a valor 0-1
    mrp_norm = normalize_categ(mrp_nivel, {1: 0.2, 2: 0.5, 3: 0.8, 4: 1.0}) # Escala DOCX [source: 723]
    miporg_norm = normalize_categ(mip_nivel, {1: 0.2, 2: 0.5, 3: 0.8, 4: 1.0}) # Escala DOCX [source: 731]
    gesinf_norm = normalize_categ(gesinf_nivel, {1: 0.2, 2: 0.5, 3: 0.8, 4: 1.0}) # Escala DOCX [source: 734]

    # Calcular Índices Finales S, I, T
    w = params['weights_S']
    v = params['weights_I']
    u = params['weights_T']

    S_user = (w['MO'] * mo_norm + w['pH'] * ph_norm + w['POXC'] * poxc_norm + w['DA'] * struct_norm)
    I_user = (v['AporteMO'] * aporte_mo_norm + v['CIns'] * cins_norm + v['Diver'] * diver_norm + v['BioIns'] * bioins_norm)
    T_user = (u['ESiRe'] * esire_norm + u['MRP'] * mrp_norm + u['MIPOrg'] * miporg_norm + u['GesInf'] * gesinf_norm)

    return {'S': S_user, 'I': I_user, 'T': T_user}