# optimizer/core_logic.py
import numpy as np
# from .parameters import PARAMS # No se usa directamente aquí
from .simulations import simulate_precio_org # Usado aquí
# from .factors import get_modifiers_for_level # No se usa directamente aquí
# from .indices import calculate_user_indices # No se usa directamente aquí
import json # Importar si no estaba

# --- calculate_yield_k (Sin cambios si A_base se pasa directamente) ---
def calculate_yield_k(nivel_manejo, factor_lluvia_k, factor_calor_k, epsilon_R_k, factor_plagas_nivel, params, A_base):
    S = params['S_Niveles'][nivel_manejo]
    I = params['I_Niveles'][nivel_manejo]
    T = params['T_Niveles'][nivel_manejo]
    alpha = params['alpha']
    beta = params['beta']
    gamma = params['gamma']
    # factor_plagas_nivel ya viene calculado
    R_k = (A_base * (S**alpha) * (I**beta) * (T**gamma) *
           factor_lluvia_k * factor_plagas_nivel * factor_calor_k * epsilon_R_k)
    return max(0.0, R_k) # Asegurar rendimiento no negativo

# --- find_optimal_sc (MODIFICADO para aceptar C_fijo, C_cert) ---
def find_optimal_sc(E_R_nivel, C_var_ha_nivel, C_fijo_actual, C_cert_actual, ST, PT, P_org_k):
    sc_optimo_k = 0.0
    margen_bruto_por_ha_k = (P_org_k * E_R_nivel) - C_var_ha_nivel
    if margen_bruto_por_ha_k > 0:
        costos_no_variables = C_fijo_actual + C_cert_actual # Usa los costos actuales
        if PT > costos_no_variables and C_var_ha_nivel > 0:
             sc_max_budget = (PT - costos_no_variables) / C_var_ha_nivel
        elif PT <= costos_no_variables:
            sc_max_budget = 0.0 # No alcanza ni para fijos/cert
        else: # C_var_ha_nivel es 0 o negativo? (muy raro) - Limitar por ST
            sc_max_budget = ST

        sc_max_budget = max(0.0, sc_max_budget)
        sc_optimo_k = min(ST, sc_max_budget)
    return sc_optimo_k

# --- calculate_expected_profit_for_level (MODIFICADO para aceptar C_fijo, C_cert) ---
# Añadir C_fijo_run y C_cert_run como argumentos
def calculate_expected_profit_for_level(nivel_actual, params, ST_p, PT_p, C_fijo_run, C_cert_run):
    """Calcula E[pi] y E[sc] para un nivel, usando E[R] precalculado y costos específicos."""
    N_sim = params.get('N_simulaciones', 5000)

    # Obtener E[R] PRECALCULADO para este nivel
    E_R_actual = params['E_R_Niveles'].get(nivel_actual)
    if E_R_actual is None:
        raise ValueError(f"E[R] no encontrado para {nivel_actual} en calculate_expected_profit")

    S_actual = params['S_Niveles'][nivel_actual]
    c_var_override = params.get('c_var_override_ha')
    C_var_ha_actual = c_var_override if c_var_override is not None and c_var_override >= 0 else params['C_var_por_ha_Niveles'][nivel_actual]

    ganancias_optimas_k = np.zeros(N_sim)
    sc_optimos_k = np.zeros(N_sim)
    precios_org_k = np.zeros(N_sim) # Para el resumen de precios

    for k in range(N_sim):
        P_org_k = simulate_precio_org(params)
        precios_org_k[k] = P_org_k

        sc_optimo_k = find_optimal_sc( E_R_actual, C_var_ha_actual, C_fijo_run, C_cert_run, ST_p, PT_p, P_org_k )
        sc_optimos_k[k] = sc_optimo_k

        ingresos_k = P_org_k * E_R_actual * sc_optimo_k
        costos_variables_k = C_var_ha_actual * sc_optimo_k
        costos_totales_k = C_fijo_run + costos_variables_k + C_cert_run
        ganancias_optimas_k[k] = ingresos_k - costos_totales_k

    E_pi_nivel = float(np.mean(ganancias_optimas_k))
    E_sc_nivel = float(np.mean(sc_optimos_k))

    # Preparar resumen de precios para devolverlo
    price_stats = {
       'P_org_Mean': float(np.mean(precios_org_k)),
       'P_org_StdDev': float(np.std(precios_org_k)),
       'P_org_Min': float(np.min(precios_org_k)),
       'P_org_Q1': float(np.percentile(precios_org_k, 25)),
       'P_org_Median': float(np.median(precios_org_k)),
       'P_org_Q3': float(np.percentile(precios_org_k, 75)),
       'P_org_Max': float(np.max(precios_org_k)),
       'P_org_Resumen_List': np.percentile(precios_org_k, [0, 25, 50, 75, 100]).tolist()
    }

    # Imprimir resumen de precios simulados para esta llamada (opcional)
    print(f"--- Resumen Precio Org Simulado (para cálculo E[pi] Nivel {nivel_actual}) ---")
    print(f"  P_org (Media E[P]): {np.mean(precios_org_k):.2f} MXN/ton")
    # print(f"  P_org Resumen (Min, Q1, Med, Q3, Max): {np.round(np.percentile(precios_org_k, [0, 25, 50, 75, 100]), 1)}")
    print("-" * 20)

    # *** ASEGÚRATE DE QUE EL RETURN INCLUYA 'price_stats' ***
    return {
        'Nivel': nivel_actual,
        'E_pi': E_pi_nivel,
        'E_sc': E_sc_nivel,
        'S_logrado': float(S_actual),
        'price_stats': price_stats # <--- ¡Asegúrate que esta línea exista!
    }
# --- Fin Función ---