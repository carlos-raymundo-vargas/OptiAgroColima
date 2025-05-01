# optimizer/factors.py
import numpy as np
# from .parameters import SHARED_PARAMS, LOCATION_PARAMS # No se importan directamente aquí

# --- get_modifiers_for_level (Sin cambios, usa params compartidos) ---
def get_modifiers_for_level(nivel_manejo, params):
    """Obtiene ModIrrig, MitigRiego, FactorPlagas para un nivel dado."""
    # Accede a parámetros compartidos
    ESiRe_actual = params['ESiRe_Niveles'][nivel_manejo]
    MIPOrg_actual = params['MIPOrg_Niveles'][nivel_manejo]
    PerdPoten = params['PerdPoten']

    # Calcular ModIrrig
    ModIrrig = 0.0
    if ESiRe_actual > 0.8: ModIrrig = 0.95
    elif ESiRe_actual > 0.6: ModIrrig = 0.8
    elif ESiRe_actual > 0: ModIrrig = 0.5

    # Calcular MitigRiego
    MitigR = 0.0
    if ESiRe_actual > 0.8: MitigR = 0.15
    elif ESiRe_actual > 0.6: MitigR = 0.25
    elif ESiRe_actual > 0: MitigR = 0.10

    # Calcular FactorPlagas
    EficaciaC = 0.0
    if MIPOrg_actual >= 1.0: EficaciaC = 0.95
    elif MIPOrg_actual >= 0.8: EficaciaC = 0.85
    elif MIPOrg_actual >= 0.5: EficaciaC = 0.55
    elif MIPOrg_actual >= 0.2: EficaciaC = 0.15

    PerdReal = {k: v * (1 - EficaciaC) for k, v in PerdPoten.items()}
    FactorPlagas = np.prod([(1 - v) for v in PerdReal.values()])

    return {'ModIrrig': ModIrrig, 'MitigRiego': MitigR, 'FactorPlagas': FactorPlagas}


# --- calculate_factor_lluvia (MODIFICADO para usar umbrales de ubicación) ---
def calculate_factor_lluvia(Lluvia_sim, nivel_manejo, params):
    """Calcula el factor lluvia usando umbrales específicos de la ubicación."""

    # Obtener modificador de riego (depende del nivel, usa params compartidos)
    modifiers = get_modifiers_for_level(nivel_manejo, params)
    ModIrrig_actual = modifiers['ModIrrig']
    minsequia_actual = 0.1 + (ModIrrig_actual * 0.6)

    # Obtener umbrales y max_exceso específicos de la ubicación
    # params aquí es el diccionario combinado que incluye ['location_specific']
    loc_params = params['location_specific']
    critmin = loc_params['Lluvia_crit_min']
    optmin = loc_params['Lluvia_opt_min']
    optmax = loc_params['Lluvia_opt_max']
    critmax = loc_params['Lluvia_crit_max']
    # max_exceso se quedó en shared_params, lo leemos de ahí
    max_exceso = params['Lluvia_max_exceso']


    # --- Lógica de cálculo del factor phi (simplificada, revisar/implementar interpolación si es necesaria) ---
    phi = 1.0 # Valor por defecto en rango óptimo

    if Lluvia_sim <= critmin:
        phi = minsequia_actual
    elif Lluvia_sim >= critmax:
        phi = max_exceso

    return max(0.0, min(1.0, phi)) # Asegura que phi esté entre 0 y 1


# --- calculate_factor_calor (Sin cambios, usa umbrales compartidos y MitigR del nivel) ---
def calculate_factor_calor(Tmax_vector_critico, nivel_manejo, params):
    """Calcula el factor calor para un nivel de manejo."""
    modifiers = get_modifiers_for_level(nivel_manejo, params)
    MitigR_actual = modifiers['MitigRiego']
    # Usa umbrales compartidos
    T_estres = params['T_umbral_estres']
    T_critico = params['T_umbral_critico']

    estres_diario = np.zeros(len(Tmax_vector_critico))
    mask_mid = (Tmax_vector_critico > T_estres) & (Tmax_vector_critico < T_critico)
    mask_high = Tmax_vector_critico >= T_critico

    # Evitar división por cero si T_critico == T_estres
    divisor = T_critico - T_estres
    if divisor > 0:
        estres_diario[mask_mid] = (Tmax_vector_critico[mask_mid] - T_estres) / divisor
    else: # Si umbrales son iguales, el estrés es 0 o 1
        estres_diario[mask_mid] = 0.0

    estres_diario[mask_high] = 1.0

    estres_promedio = np.mean(estres_diario) if len(estres_diario) > 0 else 0.0
    factor_calor = max(0.0, 1.0 - (estres_promedio * (1.0 - MitigR_actual)))
    return factor_calor