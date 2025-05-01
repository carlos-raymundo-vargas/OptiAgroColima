# optimizer/views.py
from django.http import JsonResponse, HttpRequest
from django.views.decorators.csrf import csrf_exempt
import json
import traceback
import numpy as np
import pprint
import os


# Importa los parámetros COMPARTIDOS y por UBICACIÓN
from .parameters import SHARED_PARAMS, LOCATION_PARAMS, load_tmax_data
from .optimization import run_epsilon_constraint_optimization
from pyairtable import Api as AirtableApi # Importar pyairtable

# --- ¡¡¡ CONFIGURA ESTAS VARIABLES (MEJOR CON VARIABLES DE ENTORNO) !!! ---
AIRTABLE_PAT = os.environ.get('AIRTABLE_PAT') # Sin default hardcodeado
AIRTABLE_BASE_ID = os.environ.get('AIRTABLE_BASE_ID') # Sin default hardcodeado
AIRTABLE_TABLE_NAME = os.environ.get('AIRTABLE_TABLE_NAME', 'AIRTABLE_TABLE_NAME') # ¡CAMBIA ESTO!

# --- NUEVA/ACTUALIZADA VISTA para Compartir Datos con Airtable ---

# --- VISTA OPTIMIZE CORREGIDA ---
@csrf_exempt
def optimize_view(request: HttpRequest):
    """
    Vista de API que recibe los parámetros del usuario y devuelve la optimización.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido, usar POST.'}, status=405)

    # --- INICIO Bloque TRY principal ---
    try:
        # --- Log cuerpo crudo (opcional, puedes quitarlo si ya no lo necesitas) ---
        # print(f"--- Raw Request Body ({request.content_type}) ---")
        # print(request.body)
        # print("----------------------------------------")
        # --- Fin Log ---

        # --- Parseo JSON ---
        try:
            user_inputs_raw = json.loads(request.body)
            if not isinstance(user_inputs_raw, dict):
                raise ValueError("El cuerpo debe ser un objeto JSON.")
        except json.JSONDecodeError:
             print("!!! ERROR: JSONDecodeError al parsear request.body !!!")
             return JsonResponse({'error': 'Cuerpo de la solicitud no es JSON válido.'}, status=400)

        # --- Validación de Parámetros Obligatorios ---
        st_val = user_inputs_raw.get('st')
        pt_val = user_inputs_raw.get('pt')
        config_id = user_inputs_raw.get('configId')
        if st_val is None or pt_val is None or config_id is None:
            return JsonResponse({'error': 'Parámetros obligatorios "st", "pt" y/o "configId" faltantes.'}, status=400)
        try:
            st_user = float(st_val)
            pt_user = float(pt_val)
            if st_user <= 0 or pt_user < 0:
                raise ValueError("ST debe ser positivo y PT debe ser no negativo.")
        except (ValueError, TypeError):
            return JsonResponse({'error': 'Valores inválidos para "st" o "pt".'}, status=400)

        # --- Determinar Ubicación ---
        location_key = config_id.split('_')[0]
        if location_key not in LOCATION_PARAMS:
             return JsonResponse({'error': f'Configuración regional inválida: {location_key}'}, status=400)

        # --- Cargar Datos Tmax ---
        tmax_prom_data, tmax_std_data = load_tmax_data(location_key, LOCATION_PARAMS)
        if tmax_prom_data is None or tmax_std_data is None:
             return JsonResponse({'error': f'Error de configuración del servidor: No se pudieron cargar los datos climáticos para {location_key}.'}, status=500)

        # --- Preparar Parámetros Combinados ---
        current_run_params = {}
        current_run_params.update(SHARED_PARAMS)
        current_run_params['location_specific'] = LOCATION_PARAMS[location_key].copy()
        current_run_params['location_specific']['Tmax_prom_suave_doy'] = tmax_prom_data
        current_run_params['location_specific']['Tmax_std_suave_doy'] = tmax_std_data

        # --- Sobrescribir costos si vienen del usuario ---
        c_fijo_user = user_inputs_raw.get('c_fijo_user')
        c_cert_user = user_inputs_raw.get('c_cert_user')
        c_var_user_val = user_inputs_raw.get('c_var_user_ha')
        if c_fijo_user is not None:
            try: current_run_params['C_fijo_default'] = float(c_fijo_user)
            except (ValueError, TypeError): print("Advertencia: c_fijo_user inválido")
        if c_cert_user is not None:
            try: current_run_params['C_cert_default'] = float(c_cert_user)
            except (ValueError, TypeError): print("Advertencia: c_cert_user inválido")
        c_var_user_ha = None
        if c_var_user_val is not None:
             try:
                 c_var_user_ha = float(c_var_user_val)
                 if c_var_user_ha < 0: c_var_user_ha = None
             except (ValueError, TypeError): print(f"Advertencia: c_var_user_ha inválido")
        current_run_params['c_var_override_ha'] = c_var_user_ha

        # --- Llamar a la Optimización ---
        print(f"Iniciando run_epsilon_constraint_optimization para ubicación: {location_key}...")
        resultados = run_epsilon_constraint_optimization(user_inputs_raw, current_run_params, location_key)
        print("Finalizado run_epsilon_constraint_optimization.")

        # --- Log de Resultados Finales (opcional, puedes quitarlo) ---
        # print("\n--- Final Results Dict to Serialize ---")
        # pprint.pprint(resultados)
        # print("------------------------------------\n")
        # --- Fin Log ---

        # Devolver éxito
        return JsonResponse(resultados, status=200)

    # --- INICIO BLOQUES EXCEPT RESTAURADOS ---
    except ValueError as e: # Captura errores de validación específicos (ej. float(), config invalida)
         print(f"Error de Validación en optimize_view: {e}")
         return JsonResponse({'error': f'Error en los datos de entrada o configuración: {e}'}, status=400)
    except KeyError as e: # Por si alguna clave se accede mal internamente en la lógica
         print(f"Error de Clave en optimize_view: {e}")
         print(traceback.format_exc()) # Imprime traceback completo en consola del servidor
         return JsonResponse({'error': f'Error interno del servidor: Falta clave de configuración {e}'}, status=500)
    except Exception as e: # Captura cualquier otro error inesperado
         print(f"!!! ERROR INESPERADO EN LA VISTA optimize_view !!! - {type(e).__name__}: {e}")
         print("--- Traceback ---")
         print(traceback.format_exc())
         print("-----------------")
         return JsonResponse({'error': 'Ocurrió un error interno inesperado en el servidor al procesar la optimización.'}, status=500)
    # --- FIN BLOQUES EXCEPT ---

# --- Fin optimize_view ---

# ------------------------------------------------------------------------

@csrf_exempt
def share_data_view(request: HttpRequest):
    """
    Recibe datos compartidos por el usuario y los guarda en Airtable.
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'Método no permitido, usar POST.'}, status=405)
    
    # --- Añadir prints de depuración ANTES del 'if' ---
    # print(f"\nDEBUG: Verificando credenciales...")
    # print(f"DEBUG: Valor de AIRTABLE_PAT antes del check: '{AIRTABLE_PAT}'")
    # print(f"DEBUG: Valor de AIRTABLE_BASE_ID antes del check: '{AIRTABLE_BASE_ID}'")
    # --- Fin prints de depuración ---

    # Verificar que las credenciales estén configuradas
    # --- ESTA CONDICIÓN ESTÁ DANDO TRUE ---
    # if 'patuPX3vza0Rj5vr4.6415b63a9b1739d807571fbb24f45183eb64147e70f277a5482b2d2258528ca3' in AIRTABLE_PAT or 'appEw6svGJ8y55Jrc' in AIRTABLE_BASE_ID:
         # print("ERROR CRÍTICO: Credenciales de Airtable (PAT o Base ID) no configuradas.")
         # --- Y POR ESO DEVUELVE ESTE ERROR ---
        # return JsonResponse({'error': 'Error de configuración del servidor [Airtable Credentials].'}, status=500)
    # -------------------------------------------

    try:
        # Verificar si las variables de configuración esenciales están vacías (mejor check)
        if not AIRTABLE_PAT or not AIRTABLE_BASE_ID or not AIRTABLE_TABLE_NAME:
         print("ERROR CRÍTICO: Falta configuración de Airtable (PAT, Base ID o Table Name) en el entorno.")
         return JsonResponse({'error': 'Error de configuración del servidor [Airtable Config Missing].'}, status=500)
        
        data = json.loads(request.body)

        # Validar datos mínimos recibidos
        name = data.get('name', '')
        email = data.get('email', '')
        inputs = data.get('inputs')
        results = data.get('results')
        timestamp = data.get('timestamp')
        # --- LEER costos personalizados del nivel superior de 'data' ---
        c_fijo_user_val = data.get('c_fijo_user')
        c_cert_user_val = data.get('c_cert_user')
        c_var_user_ha_val = data.get('c_var_user_ha')
        # -----------------------------------------------------------

        if not inputs or not results or not timestamp:
            return JsonResponse({'error': 'Faltan datos esenciales (inputs, results, timestamp).'}, status=400)
        if not isinstance(inputs, dict) or not isinstance(results, dict):
             return JsonResponse({'error': 'Formato inválido para inputs o results.'}, status=400)

        print(f"Recibidos datos para compartir en Airtable de: {name} ({email})")

        # --- Conectar con Airtable ---
        try:
            # *** CAMBIO: Inicializar Api con el PAT ***
            airtable_api = AirtableApi(AIRTABLE_PAT)
            # ***************************************
            airtable_table = airtable_api.table(AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME)
            print(f"Conectado a Airtable: Base ID='{AIRTABLE_BASE_ID}', Tabla='{AIRTABLE_TABLE_NAME}'")
        except Exception as e:
             print(f"ERROR conectando a Airtable: {e}")
             raise ConnectionError("No se pudo conectar al servicio de almacenamiento de datos.")
        
        # --- Función auxiliar para conversión segura a número ---
        def safe_float(value):
            if value is None: return None
            try: return float(value)
            except (ValueError, TypeError): return None
        def safe_int(value):
             if value is None: return None
             try: return int(float(value)) # Convertir a float primero por si viene como "3.0"
             except (ValueError, TypeError): return None
        # ----------------------------------------------------

        # --- Preparar el diccionario de datos para Airtable ---
        # Las claves deben coincidir EXACTAMENTE con los nombres de las columnas en Airtable
        # Convierte tipos si es necesario (Airtable es flexible pero mejor ser explícito)
        airtable_data = {
            # Las claves deben coincidir con tus columnas Airtable
            'Timestamp': timestamp,
            'Nombre': name,
            'Correo': email,
            # --- Leer de 'inputs' ---
            'Ubicación': inputs.get('configId', 'N/A').split('_')[0], # Ahora debería funcionar
            'ST': safe_float(inputs.get('st')), # Usar safe_float
            'PT': safe_float(inputs.get('pt')), # Usar safe_float
            'R_Avg_User': safe_float(inputs.get('R_avg_usuario')),
            'MO': safe_float(inputs.get('MO')),
            'pH': safe_float(inputs.get('pH')),
            'POXC': safe_int(inputs.get('POXC')), # Entero
            'DA': safe_float(inputs.get('DA')),
            'AporteMO': safe_int(inputs.get('AporteMO')), # Entero
            'C_Insumo': safe_float(inputs.get('CalidadComp_C')),
            'N_Insumo': safe_float(inputs.get('CalidadComp_N')),
            'Diversidad': safe_int(inputs.get('DiversidadNumCat')),
            'BioIns': safe_int(inputs.get('NivelBioIns')),
            'Riego': inputs.get('TipoSistemaRiego'),
            'MRP': safe_int(inputs.get('PracticaMRP')),
            'MIP': safe_int(inputs.get('PracticaMIP')),
            'GesInfo': safe_int(inputs.get('PracticaGesInf')),
            # --- Leer costos personalizados de 'data' (nivel superior) ---
            'C_Fijo_User': safe_float(c_fijo_user_val),
            'C_Cert_User': safe_float(c_cert_user_val),
            'C_Var_User_HA': safe_float(c_var_user_ha_val),
            # --- Resultados (como antes) ---
            'LevelSummaryJSON': json.dumps(results.get('level_summary', {})),
            'ParetoPointsJSON': json.dumps(results.get('pareto_points', [])),
        }
        # Filtrar claves con valor None porque Airtable no los acepta bien a veces
        airtable_data_filtered = {k: v for k, v in airtable_data.items() if v is not None}
        print("--- Datos Filtrados para Airtable ---")
        print(airtable_data_filtered)


        # --- Crear el registro en Airtable ---
        try:
            created_record = airtable_table.create(airtable_data_filtered)
            print(f"Registro creado en Airtable exitosamente. ID: {created_record['id']}")
            return JsonResponse({'status': 'success', 'message': 'Datos compartidos exitosamente.'}, status=200)
        except Exception as e:
             print(f"ERROR al crear registro en Airtable: {e}")
             raise ConnectionError("No se pudo guardar el registro en el servicio de almacenamiento.")

    except ValueError as e:
        print(f"Error de Validación: {e}")
        return JsonResponse({'error': f'Error en los datos de entrada: {e}'}, status=400)
    except KeyError as e:
        print(f"Error de Clave: {e}")
        print(traceback.format_exc())
        return JsonResponse({'error': f'Error interno del servidor: Falta clave {e}'}, status=500)
    except ConnectionError as e: return JsonResponse({'error': str(e)}, status=503)
    except Exception as e:
        # ... (Manejo de error genérico como antes) ...
        print(f"!!! ERROR INESPERADO EN LA VISTA share_data_view !!! - {type(e).__name__}: {e}")
        # ...
        return JsonResponse({'error': 'Ocurrió un error interno al procesar los datos compartidos.'}, status=500)