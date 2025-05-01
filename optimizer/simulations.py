# optimizer/simulations.py
import numpy as np
from scipy.stats import gamma, norm, lognorm
# No necesita importar PARAMS aquí

def simulate_lluvia(loc_params): # Recibe params específicos de ubicación
    """Genera un valor de lluvia total desde Gamma."""
    shape = loc_params['shape_lluvia']
    scale = loc_params['scale_lluvia']
    return gamma.rvs(a=shape, scale=scale, size=1)[0]

def simulate_tmax_daily(num_dias, start_day_of_year, loc_params): # Recibe params específicos de ubicación
    """Simula Tmax diaria usando WG AR(1)+Normal."""
    phi_T = loc_params['phi_Tmax']
    sigma_ruido_T = loc_params['sigma_ruido_Tmax']
    # Accede a los datos Tmax ya cargados dentro de loc_params
    prom_suave = loc_params['Tmax_prom_suave_doy']
    std_suave = loc_params['Tmax_std_suave_doy']

    if prom_suave is None or std_suave is None:
        raise ValueError("Datos Tmax estacionales no disponibles en loc_params.")

    tmax_sim_periodo = np.zeros(num_dias)
    residuo_z_sim_previo = 0.0 # Podría inicializarse con una muestra aleatoria

    for i in range(num_dias):
        doy = (start_day_of_year + i - 1) % 366 + 1
        # Asegurarse que doy está dentro de los límites 1-366
        doy_idx = min(max(1, doy), 366) - 1 # Índice 0 a 365

        tmax_prom_esperada = prom_suave[doy_idx]
        tmax_std_esperada = std_suave[doy_idx]

        ruido_sim_actual = norm.rvs(loc=0, scale=sigma_ruido_T, size=1)[0]
        residuo_z_sim_actual = phi_T * residuo_z_sim_previo + ruido_sim_actual
        tmax_sim_i = tmax_prom_esperada + residuo_z_sim_actual * tmax_std_esperada

        tmax_sim_periodo[i] = tmax_sim_i
        residuo_z_sim_previo = residuo_z_sim_actual

    return tmax_sim_periodo

def simulate_precio_org(params): # Recibe params generales (contiene los compartidos)
    """Simula un precio orgánico."""
    Pconv_esp = params['Pconv_esperado_ton']
    premio_f = params['premio_factor']
    mu_epsP = params['mu_epsilon_P']
    sigma_epsP = params['sigma_epsilon_P']

    epsilon_P_k = norm.rvs(loc=mu_epsP, scale=sigma_epsP, size=1)[0]
    epsilon_P_k = max(0.01, epsilon_P_k)
    P_org_k = premio_f * Pconv_esp * epsilon_P_k
    return P_org_k

def simulate_error_R(params): # Recibe params generales
    """Simula el error multiplicativo del rendimiento."""
    sigma_epsR = params['sigma_epsilon_R']
    return lognorm.rvs(s=sigma_epsR, scale=1, size=1)[0]