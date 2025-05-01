# optimizer/optimization.py
import numpy as np
from .indices import calculate_user_indices
from .simulations import simulate_lluvia, simulate_tmax_daily, simulate_precio_org, simulate_error_R
from .factors import calculate_factor_lluvia, calculate_factor_calor, get_modifiers_for_level
from .core_logic import calculate_yield_k, calculate_expected_profit_for_level

# --- NUEVO: Importar SHARED_PARAMS ---
from .parameters import SHARED_PARAMS # Necesario para get_level_params

# --- calculate_A_user (Sin cambios) ---
def calculate_A_user(S_user, I_user, T_user, R_avg_user, params):
    alpha = params['alpha']
    beta = params['beta']
    gamma = params['gamma']
    denominator = (S_user**alpha) * (I_user**beta) * (T_user**gamma)
    if denominator == 0:
        print("ADVERTENCIA: Denominador cero al calcular A_user.")
        return 1.0
    A_user = R_avg_user / denominator
    return A_user

# --- precalculate_expected_yields (Sin cambios respecto a la última versión) ---
def precalculate_expected_yields(A_usuario_calculado, params, location_key):
    # ... (código igual que antes, devuelve E_R_Niveles, Stats_Detalladas_Yield) ...
    N_sim_yield = params.get('N_simulaciones_yield', params.get('N_simulaciones', 5000))
    niveles = list(params['S_Niveles'].keys())
    resultados_R_por_nivel = {nm: np.zeros(N_sim_yield) for nm in niveles}
    stats_detalladas_por_nivel = {nm: {} for nm in niveles}
    loc_params = params['location_specific']
    if loc_params.get('Tmax_prom_suave_doy') is None: #... error
        raise ValueError(f"Datos Tmax no cargados para {location_key} en precalculate_expected_yields.")
    print(f"--- Iniciando pre-cálculo de E[R] para {loc_params.get('location_name', location_key)} ...")
    for nm in niveles:
        print(f"Simulando rendimiento para Nivel: {nm}")
        # ... (obtener S, I, T, modifiers, FactorPlagas, MitigR, ModIrrig) ...
        S_actual, I_actual, T_actual = params['S_Niveles'][nm], params['I_Niveles'][nm], params['T_Niveles'][nm]
        modifiers = get_modifiers_for_level(nm, params)
        FactorPlagas_actual = modifiers['FactorPlagas']
        MitigR_actual = modifiers['MitigRiego']
        ModIrrig_actual = modifiers['ModIrrig']

        # ... (inicializar listas lluvias_k, etc.) ...
        lluvias_k, factores_lluvia_k, factores_calor_k, errores_R_k = [np.zeros(N_sim_yield) for _ in range(4)]

        for k in range(N_sim_yield):
            # ... (simular Lluvia, Tmax, ErrorR) ...
            Lluvia_sim_k = simulate_lluvia(loc_params)
            FactorLluvia_k = calculate_factor_lluvia(Lluvia_sim_k, nm, params)
            Tmax_sim_criticos_k = simulate_tmax_daily(len(params['dias_periodo_critico']), min(params['dias_periodo_critico']), loc_params)
            FactorCalor_k = calculate_factor_calor(Tmax_sim_criticos_k, nm, params)
            epsilon_R_k = simulate_error_R(params)

            # ... (calcular R_k) ...
            R_k = calculate_yield_k(nm, FactorLluvia_k, FactorCalor_k, epsilon_R_k, FactorPlagas_actual, params, A_usuario_calculado)

            # ... (guardar valores k) ...
            lluvias_k[k], factores_lluvia_k[k], factores_calor_k[k], errores_R_k[k] = Lluvia_sim_k, FactorLluvia_k, FactorCalor_k, epsilon_R_k
            resultados_R_por_nivel[nm][k] = R_k

        # ... (Calcular y guardar/imprimir stats detalladas CONVIRTIENDO a tipos JSON) ...
        stats_detalladas_por_nivel[nm]['FactorPlagas_Fijo'] = float(FactorPlagas_actual)
        stats_detalladas_por_nivel[nm]['Lluvia_sim_Resumen'] = np.percentile(lluvias_k, [0, 25, 50, 75, 100]).tolist()
        stats_detalladas_por_nivel[nm]['Lluvia_sim_Media'] = float(np.mean(lluvias_k))
        # ... (resto de stats para FactorLluvia, FactorCalor, Epsilon_R, R) ...
        stats_detalladas_por_nivel[nm]['FactorLluvia_Resumen'] = np.percentile(factores_lluvia_k, [0, 25, 50, 75, 100]).tolist()
        stats_detalladas_por_nivel[nm]['FactorLluvia_Media'] = float(np.mean(factores_lluvia_k))
        stats_detalladas_por_nivel[nm]['FactorCalor_Resumen'] = np.percentile(factores_calor_k, [0, 25, 50, 75, 100]).tolist()
        stats_detalladas_por_nivel[nm]['FactorCalor_Media'] = float(np.mean(factores_calor_k))
        stats_detalladas_por_nivel[nm]['Epsilon_R_Resumen'] = np.percentile(errores_R_k, [0, 25, 50, 75, 100]).tolist()
        stats_detalladas_por_nivel[nm]['Epsilon_R_Media'] = float(np.mean(errores_R_k))
        stats_detalladas_por_nivel[nm]['R_Resumen'] = np.percentile(resultados_R_por_nivel[nm], [0, 25, 50, 75, 100]).tolist()
        stats_detalladas_por_nivel[nm]['R_Media'] = float(np.mean(resultados_R_por_nivel[nm]))
        stats_detalladas_por_nivel[nm]['R_StdDev'] = float(np.std(resultados_R_por_nivel[nm]))

        # ... (imprimir resumen por nivel) ...
        print(f"--- Resumen para Nivel {nm} en {loc_params.get('location_name', location_key)} ---")
        print(f"  Rendimiento R (Media E[R]): {stats_detalladas_por_nivel[nm]['R_Media']:.2f} ton/ha")
        # ...

    E_R_Niveles = {nm: np.mean(resultados_R_por_nivel[nm]) for nm in niveles}
    print(f"--- E[R] Pre-calculados para {loc_params.get('location_name', location_key)} ... ---")
    print(E_R_Niveles)
    return E_R_Niveles, stats_detalladas_por_nivel


# --- NUEVA Función Helper para obtener parámetros de nivel ---
def get_level_params_detailed(level_name, params):
    """
    Extrae los valores de los componentes S, I, T para un nivel específico
    usando los defaults para Intermedio y valores específicos para Avanzado donde estén definidos.
    Devuelve un diccionario con nombres amigables.
    """
    level_params = {}
    defaults = params.get('defaults_usuario', {})
    norm_params = params.get('norm_params', {})
    # Usamos SHARED_PARAMS directamente ya que params debería contenerlo o serlo
    # (Asegúrate que SHARED_PARAMS sea accesible si params no lo contiene)
    shared = params # O params['shared_params'] si estructuraste así

    # --- Nombres Amigables (Puedes mover esto fuera si prefieres) ---
    param_map_friendly_to_internal = {
      'Rendimiento Promedio (ton/ha)': 'R_avg_usuario',
      'Materia Orgánica (%)': 'MO',
      'pH del Suelo': 'pH',
      'POXC (mg/kg)': 'POXC',
      'Densidad Aparente (g/cm³)': 'DA',
      'Aporte MO Insumo (t/ha/año)': 'AporteMO',
      'Carbono Insumo (%)': 'CalidadComp_C',
      'Nitrógeno Insumo (%)': 'CalidadComp_N',
      'Diversidad Fuentes Insumo (1-4)': 'DiversidadNumCat',
      'Nivel Uso Bio-Insumos (0-3)': 'NivelBioIns',
      'Sistema de Riego': 'TipoSistemaRiego', # Clave de defaults
      'Nivel Práctica MRP (1-4)': 'PracticaMRP',
      'Nivel Práctica MIP (1-4)': 'PracticaMIP',
      'Nivel Práctica Ges. Info (1-4)': 'PracticaGesInf',
      'Índice Suelo (S)': 'S_Index',
      'Índice Insumos (I)': 'I_Index',
      'Índice Tecnología (T)': 'T_Index',
    }
    # Invertir mapa para búsqueda fácil por clave interna
    param_map_internal_to_friendly = {v: k for k, v in param_map_friendly_to_internal.items()}

    # --- Lógica por Nivel ---
    if level_name == 'Intermedio':
        # Usar los defaults directamente
        for friendly_name, internal_key in param_map_friendly_to_internal.items():
             if internal_key in defaults: # Solo añadir si existe en defaults
                level_params[friendly_name] = defaults.get(internal_key)

    elif level_name == 'Avanzado':
        # Usar valores ÓPTIMOS de norm_params donde aplique,
        # y valores específicos de nivel definidos en shared_params
        level_params[param_map_internal_to_friendly.get('MO')] = norm_params.get('MO', {}).get('opt')
        level_params[param_map_internal_to_friendly.get('pH')] = norm_params.get('pH', {}).get('opt')
        level_params[param_map_internal_to_friendly.get('POXC')] = norm_params.get('POXC', {}).get('opt')
        # Para DA, el óptimo es < 1.45, podemos mostrar ese objetivo
        level_params[param_map_internal_to_friendly.get('DA')] = f"< {norm_params.get('DA', {}).get('opt')}"
        # Para AporteMO, el óptimo es el máximo recomendable
        level_params[param_map_internal_to_friendly.get('AporteMO')] = norm_params.get('AporteMO', {}).get('maxr')
        # Para Calidad C/N, el óptimo es C/N 15-25 y N > 1.5% (no un valor numérico simple)
        level_params[param_map_internal_to_friendly.get('CalidadComp_C')] = "Óptimo" # Indicar objetivo cualitativo
        level_params[param_map_internal_to_friendly.get('CalidadComp_N')] = "Óptimo (>1.5%)"
        # Para categóricos, usar el nivel más alto definido
        level_params[param_map_internal_to_friendly.get('DiversidadNumCat')] = 4 # Máximo nivel
        level_params[param_map_internal_to_friendly.get('NivelBioIns')] = 3 # Máximo nivel
        # Usar los valores específicos de shared_params
        esire_avanzado = shared.get('ESiRe_Niveles', {}).get('Avanzado')
        if esire_avanzado == 0.90: level_params[param_map_internal_to_friendly.get('TipoSistemaRiego')] = 'Goteo'
        elif esire_avanzado == 1.0: level_params[param_map_internal_to_friendly.get('TipoSistemaRiego')] = 'Goteo+Sensores'
        else: level_params[param_map_internal_to_friendly.get('TipoSistemaRiego')] = 'Desconocido'

        mip_avanzado = shared.get('MIPOrg_Niveles', {}).get('Avanzado')
        if mip_avanzado == 1.0: level_params[param_map_internal_to_friendly.get('PracticaMIP')] = 4
        else: level_params[param_map_internal_to_friendly.get('PracticaMIP')] = 'N/A'
        # Para MRP y GesInfo, si no están definidos para Avanzado, podemos poner el máx o N/A
        level_params[param_map_internal_to_friendly.get('PracticaMRP')] = 4 # Asumiendo óptimo es 4
        level_params[param_map_internal_to_friendly.get('PracticaGesInf')] = 4 # Asumiendo óptimo es 4
        # Incluir los índices objetivo
        level_params['Índice Suelo (S)'] = shared['S_Niveles'].get('Avanzado')
        level_params['Índice Insumos (I)'] = shared['I_Niveles'].get('Avanzado')
        level_params['Índice Tecnología (T)'] = shared['T_Niveles'].get('Avanzado')

    elif level_name == 'Basico':
        # Similar a Avanzado, pero con valores mínimos o específicos para Básico
        level_params[param_map_internal_to_friendly.get('MO')] = norm_params.get('MO', {}).get('min')
        # etc... para otros componentes S/I (usar valores mínimos o bajos representativos)
        level_params[param_map_internal_to_friendly.get('pH')] = "~5.5" # Límite inferior tolerable aprox
        level_params[param_map_internal_to_friendly.get('POXC')] = norm_params.get('POXC', {}).get('min')
        level_params[param_map_internal_to_friendly.get('DA')] = f"~ {norm_params.get('DA', {}).get('crit')}" # Cercano al crítico
        level_params[param_map_internal_to_friendly.get('AporteMO')] = norm_params.get('AporteMO', {}).get('min')
        level_params[param_map_internal_to_friendly.get('CalidadComp_C')] = "Bajo"
        level_params[param_map_internal_to_friendly.get('CalidadComp_N')] = "Bajo (<1.0%)"
        level_params[param_map_internal_to_friendly.get('DiversidadNumCat')] = 1 # Mínimo
        level_params[param_map_internal_to_friendly.get('NivelBioIns')] = 0 # Mínimo
        # Componentes T específicos para Básico
        esire_basico = shared.get('ESiRe_Niveles', {}).get('Basico')
        if esire_basico == 0.55: level_params[param_map_internal_to_friendly.get('TipoSistemaRiego')] = 'Gravedad'
        elif esire_basico == 0: level_params[param_map_internal_to_friendly.get('TipoSistemaRiego')] = 'Temporal'
        else: level_params[param_map_internal_to_friendly.get('TipoSistemaRiego')] = 'N/A'

        mip_basico = shared.get('MIPOrg_Niveles', {}).get('Basico')
        if mip_basico == 0.5: level_params[param_map_internal_to_friendly.get('PracticaMIP')] = 2
        elif mip_basico == 0.2: level_params[param_map_internal_to_friendly.get('PracticaMIP')] = 1
        else: level_params[param_map_internal_to_friendly.get('PracticaMIP')] = 'N/A'

        level_params[param_map_internal_to_friendly.get('PracticaMRP')] = 1 # Asumiendo mínimo
        level_params[param_map_internal_to_friendly.get('PracticaGesInf')] = 1 # Asumiendo mínimo
        # Incluir los índices objetivo
        level_params['Índice Suelo (S)'] = shared['S_Niveles'].get('Basico')
        level_params['Índice Insumos (I)'] = shared['I_Niveles'].get('Basico')
        level_params['Índice Tecnología (T)'] = shared['T_Niveles'].get('Basico')


    # Filtrar claves None que pudieron quedar si el mapeo falló
    return {k: v for k, v in level_params.items() if k is not None and v is not None}


# --- run_epsilon_constraint_optimization (MODIFICADO) ---
def run_epsilon_constraint_optimization(user_inputs_raw, params, location_key):
    """Orquesta el análisis MOO completo."""

    # 1. Obtener inputs y defaults
    defaults = params['defaults_usuario']
    # *** CORRECCIÓN/VERIFICACIÓN: Asegurar que user_inputs_cleaned se define aquí ***
    # (Si Pylance sigue dando error pero el código funciona, puede ser un falso positivo del linter)
    user_inputs_cleaned = {k: user_inputs_raw.get(k, defaults[k]) for k in defaults.keys()}
    ST_user = float(user_inputs_raw.get('st'))
    PT_user = float(user_inputs_raw.get('pt'))
    R_avg_user = float(user_inputs_cleaned.get('R_avg_usuario')) # Usa el valor limpio/default
    C_fijo = params['C_fijo_default']
    C_cert = params['C_cert_default']

    # 2. Calcular S, I, T del usuario
    # *** CORRECCIÓN: Pasa user_inputs_cleaned ***
    indices_usuario = calculate_user_indices(user_inputs_cleaned, defaults, params)
    S_user, I_user, T_user = indices_usuario['S'], indices_usuario['I'], indices_usuario['T']
    print(f"Índices calculados del usuario: S={S_user:.3f}, I={I_user:.3f}, T={T_user:.3f}")

    # 3. Calcular A_usuario
    A_usuario = calculate_A_user(S_user, I_user, T_user, R_avg_user, params)
    print(f"A_base calculado para el usuario: {A_usuario:.4f}")

    # 4. Pre-calcular E[R] y obtener stats de simulación de yield
    E_R_Calculados, Stats_Detalladas_Yield = precalculate_expected_yields(A_usuario, params, location_key)
    params['E_R_Niveles'] = E_R_Calculados # Actualiza params para la siguiente función

    # 5. Calcular E[pi], E[sc] y obtener stats de simulación de precio por nivel
    niveles = list(params['S_Niveles'].keys())
    # *** CORRECCIÓN: Calcular primero, luego procesar ***
    resultados_por_nivel_calc = {
         nm: calculate_expected_profit_for_level(nm, params, ST_user, PT_user, C_fijo, C_cert)
         for nm in niveles
    }

    # Extraer resumen simple y stats de precio
    resultados_level_summary = {}
    price_simulation_stats = {}

    print("\n--- Procesando resultados por nivel ---") # Debug
    # *** CORRECCIÓN: Iterar sobre el diccionario calculado ***
    for nm, result_data in resultados_por_nivel_calc.items():
         # *** AÑADIR ESTE PRINT para depurar ***
         print(f"  Nivel: {nm}, Claves recibidas: {list(result_data.keys())}")
         # ************************************
         resultados_level_summary[nm] = {
              'Nivel': result_data['Nivel'],
              'E_pi': float(result_data['E_pi']),
              'E_sc': float(result_data['E_sc']),
              'S_logrado': float(result_data['S_logrado'])
         }
         # Poblar stats de precio
         if 'price_stats' in result_data: # La condición que podría estar fallando
              print(f"    -> Encontrada clave 'price_stats' para nivel {nm}") # Debug
              price_simulation_stats[nm] = result_data['price_stats']
         else:
              print(f"    -> ADVERTENCIA: No se encontró 'price_stats' para nivel {nm}") # Debug

    print("--- Fin procesamiento por nivel ---\n") # Debug

    # 6. Calcular Frontera Pareto
    # ... (código como antes, usando resultados_level_summary) ...
    # ... encontrar E_pi_max_global, Nivel_max_pi, S_en_max_pi ...
    # ... encontrar S_max_global, Nivel_max_S, E_pi_en_max_S ...
    # ... bucle epsilon para llenar pareto_results_list ...
    E_pi_max_global = -np.inf
    Nivel_max_pi = None
    S_en_max_pi = -np.inf
    for nm in niveles:
        if resultados_level_summary[nm]['E_pi'] > E_pi_max_global:
           E_pi_max_global = resultados_level_summary[nm]['E_pi']
           Nivel_max_pi = nm
           S_en_max_pi = resultados_level_summary[nm]['S_logrado']

    S_max_global = max(params['S_Niveles'].values())
    Nivel_max_S = [nm for nm, s_val in params['S_Niveles'].items() if abs(s_val - S_max_global) < 1e-9][0]
    E_pi_en_max_S = resultados_level_summary[Nivel_max_S]['E_pi']
    print(f"Max E[pi] Global: {E_pi_max_global:.2f} en Nivel: {Nivel_max_pi} con S={S_en_max_pi:.3f}")
    print(f"Max S Global: {S_max_global:.3f} en Nivel: {Nivel_max_S} con E[pi]={E_pi_en_max_S:.2f}")

    pareto_results_list = []
    S_targets = np.linspace(min(params['S_Niveles'].values()), S_max_global, num=6)
    if S_en_max_pi > min(S_targets) and abs(S_max_global - S_en_max_pi) > 1e-6: # Evitar linspace con min=max
         S_targets = np.linspace(S_en_max_pi, S_max_global, num=5)
    elif abs(S_max_global - min(params['S_Niveles'].values())) < 1e-6: # Si todos S son iguales
         S_targets = [S_max_global] # Solo un target

    for s_target in S_targets:
        max_pi_for_s_target = -np.inf
        best_sc_for_s_target = 0.0
        best_nivel_for_s_target = None
        for nm in niveles:
            # Usar S_logrado del nivel para comparar con s_target
            if resultados_level_summary[nm]['S_logrado'] >= s_target - 1e-6: # Tolerancia pequeña
                current_result = resultados_level_summary[nm]
                if current_result['E_pi'] > max_pi_for_s_target:
                    max_pi_for_s_target = current_result['E_pi']
                    best_nivel_for_s_target = nm
                    best_sc_for_s_target = current_result['E_sc']

        if best_nivel_for_s_target is not None:
             # Evitar añadir puntos duplicados si múltiples S_targets llevan al mismo nivel óptimo
             is_duplicate = False
             if pareto_results_list:
                  last_point = pareto_results_list[-1]
                  if (last_point['Nivel_Optimo'] == best_nivel_for_s_target and
                      abs(last_point['E_pi_Maximo'] - max_pi_for_s_target) < 0.01 and
                      abs(last_point['SC_Optimo'] - best_sc_for_s_target) < 0.01):
                      is_duplicate = True
             if not is_duplicate:
                  pareto_results_list.append({
                       'S_Objetivo': round(s_target, 3), # Guardar el S objetivo
                       'E_pi_Maximo': float(round(max_pi_for_s_target, 2)),
                       'Nivel_Optimo': best_nivel_for_s_target,
                       'SC_Optimo': float(round(best_sc_for_s_target, 2)),
                       # Añadir S logrado por este nivel para referencia
                       'S_Logrado_Optimo': float(round(params['S_Niveles'][best_nivel_for_s_target], 3))
                  })
        # ... (manejo infactible como antes, si es necesario) ...


    # 7. Preparar datos para comparación (AHORA USA la función actualizada)
    comparison_data = {
        'user_inputs': user_inputs_cleaned,
        'user_indices': {'S': S_user, 'I': I_user, 'T': T_user},
        'max_profit_params': get_level_params_detailed(Nivel_max_pi, params),
        'max_soil_params': get_level_params_detailed(Nivel_max_S, params)
    }
    # Añadir también los parámetros del nivel Básico si se quisiera comparar con ese
    # comparison_data['base_params'] = get_level_params_detailed('Basico', params)


    # 8. Devolver todos los resultados
    return {
         'pareto_points': pareto_results_list,
         'level_summary': resultados_level_summary,
         'yield_simulation_stats': Stats_Detalladas_Yield,
         'price_simulation_stats': price_simulation_stats,
         'comparison_data': comparison_data
    }