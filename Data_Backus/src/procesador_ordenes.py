import pandas as pd
import json
import os
from datetime import datetime
import argparse
import numpy as np

class ProcesadorOrdenes:
    """Clase para procesar el archivo de ordenes CSV y extraer información"""
    
    def __init__(self, ruta_salida=None):
        if ruta_salida is None:
            self.ruta_salida = r"D:\Github-Time\Solutions-to-Coding-Challenges\Data_Backus\data\2.processed"
        else:
            self.ruta_salida = ruta_salida
        
        os.makedirs(self.ruta_salida, exist_ok=True)
    
    # ============================================
    # MÉTODOS GENERALES
    # ============================================
    
    def extraer_info(self, ruta_archivo):
        """Extrae información básica del archivo"""
        nombre = os.path.basename(ruta_archivo)
        
        try:
            df = pd.read_csv(ruta_archivo, sep=',')
            
            resultado = {
                "archivo": nombre,
                "fecha_ejecucion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "estado": "exitoso",
                "informacion": {
                    "filas": int(df.shape[0]),  # Convertir a int nativo
                    "columnas": int(df.shape[1]),  # Convertir a int nativo
                    "lista_columnas": df.columns.tolist(),
                    "tipos_datos": df.dtypes.astype(str).to_dict(),
                    "datos_faltantes": {k: int(v) for k, v in df.isnull().sum().to_dict().items()},  # Convertir valores
                    "memoria_uso_kb": float(round(df.memory_usage(deep=True).sum() / 1024, 2))
                },
                "errores": []
            }
            
            self._guardar_resultado(resultado, nombre)
            self._mostrar_resumen(df, nombre)
            
            return resultado
            
        except Exception as e:
            return {
                "archivo": nombre,
                "fecha_ejecucion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "estado": "error_lectura",
                "informacion": {},
                "errores": [{"tipo": "lectura", "mensaje": str(e)}]
            }
    
    # ============================================
    # PROCESADOR PARA ORDENES
    # ============================================
    
    def validar_y_extraer(self, ruta_archivo, configuracion):
        """Extrae información, valida y separa datos limpios y sucios para ORDENES"""
        nombre = os.path.basename(ruta_archivo)
        
        try:
            df = pd.read_csv(ruta_archivo, sep=',')
            
            # =============================================
            # VALIDACIÓN CRÍTICA DE COLUMNAS
            # =============================================
            columnas_actuales = set(df.columns)
            columnas_esperadas = set(configuracion.get('columnas', []))
            
            faltantes = columnas_esperadas - columnas_actuales
            sobrantes = columnas_actuales - columnas_esperadas
            
            # Si hay columnas faltantes, NO CONTINUAMOS
            if faltantes:
                resultado = self._crear_resultado_error_columnas(nombre, df, faltantes, sobrantes, columnas_esperadas)
                self._guardar_resultado(resultado, nombre)
                print(f"\n❌ ERROR CRÍTICO: Faltan columnas obligatorias")
                print(f"   Columnas faltantes: {list(faltantes)}")
                print(f"   ⛔ Proceso detenido - No se generaron archivos CSV")
                return resultado
            
            # Construir resultado
            resultado = {
                "archivo": nombre,
                "fecha_ejecucion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "estado": "exitoso",
                "informacion": {
                    "filas": int(df.shape[0]),
                    "columnas": int(df.shape[1]),
                    "lista_columnas": df.columns.tolist(),
                    "tipos_datos": df.dtypes.astype(str).to_dict(),
                    "datos_faltantes": {k: int(v) for k, v in df.isnull().sum().to_dict().items()},
                    "memoria_uso_kb": float(round(df.memory_usage(deep=True).sum() / 1024, 2))
                },
                "errores": [],
                "separacion_datos": {},
                "validaciones_especificas": {}
            }
            
            if sobrantes:
                resultado["errores"].append({
                    "tipo": "estructura_columnas_advertencia",
                    "descripcion": "El archivo contiene columnas adicionales no esperadas",
                    "columnas_sobrantes": list(sobrantes)
                })
            
            # Validar y separar datos con todas las reglas específicas
            errores_validacion, df_limpio, df_sucios, validaciones = self._validar_y_separar(df, configuracion)
            
            if errores_validacion:
                resultado["estado"] = "error_validacion"
                resultado["errores"].extend(errores_validacion)
            
            # Convertir valores numpy a tipos nativos para JSON
            resultado["validaciones_especificas"] = self._convertir_a_nativos(validaciones)
            
            # Guardar datos separados
            self._guardar_datos_separados(df_limpio, df_sucios, nombre)
            
            # Actualizar información de separación
            resultado["separacion_datos"] = {
                "registros_limpios": int(len(df_limpio)),
                "registros_sucios": int(len(df_sucios)),
                "porcentaje_limpios": float(round(len(df_limpio) / len(df) * 100, 2)) if len(df) > 0 else 0,
                "porcentaje_sucios": float(round(len(df_sucios) / len(df) * 100, 2)) if len(df) > 0 else 0
            }
            
            self._guardar_resultado(resultado, nombre)
            self._mostrar_resumen(df, nombre)
            self._mostrar_separacion(resultado["separacion_datos"])
            
            # Mostrar validaciones específicas - PASAMOS LA CONFIGURACIÓN
            self._mostrar_validaciones_especificas(validaciones, configuracion)
            
            return resultado
            
        except Exception as e:
            resultado = {
                "archivo": nombre,
                "fecha_ejecucion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "estado": "error_lectura",
                "informacion": {},
                "errores": [{"tipo": "lectura", "mensaje": str(e)}],
                "separacion_datos": {},
                "validaciones_especificas": {}
            }
            self._guardar_resultado(resultado, nombre)
            return resultado
    
    def _convertir_a_nativos(self, obj):
        """Convierte objetos numpy/pandas a tipos nativos de Python para JSON"""
        if isinstance(obj, dict):
            return {k: self._convertir_a_nativos(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._convertir_a_nativos(v) for v in obj]
        elif isinstance(obj, (np.int64, np.int32, np.int16, np.int8)):
            return int(obj)
        elif isinstance(obj, (np.float64, np.float32)):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, pd.Timestamp):
            return obj.strftime('%Y-%m-%d %H:%M:%S')
        elif pd.isna(obj):
            return None
        else:
            return obj
    
    def _validar_y_separar(self, df, configuracion):
        """
        Valida los datos de ordenes y separa en limpios y sucios
        - orden_id: Debe ser único (se queda con la fecha_proceso más reciente)
        - Los duplicados van a la data sucia
        """
        errores = []
        validaciones = {}
        
        # ============================================
        # 0. DETECCIÓN Y MANEJO DE DUPLICADOS EN orden_id
        # ============================================
        duplicados_count = 0
        df_con_problemas = df.copy()
        
        if 'orden_id' in df.columns:
            # Identificar duplicados
            mascara_duplicados = df.duplicated(subset=['orden_id'], keep=False)
            duplicados_count = int(mascara_duplicados.sum())
            
            if duplicados_count > 0:
                # Obtener los IDs duplicados
                ids_duplicados = df[mascara_duplicados]['orden_id'].unique().tolist()
                
                errores.append({
                    "tipo": "orden_id_duplicado",
                    "columna": "orden_id",
                    "descripcion": f"Se encontraron {duplicados_count} registros duplicados en orden_id",
                    "cantidad_invalidos": duplicados_count,
                    "ids_duplicados": ids_duplicados[:10],
                    "total_ids_duplicados": len(ids_duplicados),
                    "accion": "Se mantiene el registro con fecha_proceso más reciente en data limpia, los duplicados van a data sucia"
                })
                
                # 1. Crear máscara para identificar duplicados que NO son la fecha más reciente
                # Ordenar por fecha_proceso descendente (más reciente primero)
                df_sorted = df.sort_values('fecha_proceso', ascending=False)
                
                # Marcar los duplicados (keep='first' mantiene el primero que es el más reciente por el sort)
                mascara_duplicados_a_eliminar = df_sorted.duplicated(subset=['orden_id'], keep='first')
                
                # Los duplicados a eliminar son los que NO son la fecha más reciente
                # Estos irán a la data sucia
                mascara_sucia = mascara_duplicados_a_eliminar
                
                # Guardar información de duplicados para validaciones
                validaciones["duplicados"] = {
                    "total_duplicados": duplicados_count,
                    "ids_duplicados": ids_duplicados[:10],
                    "total_ids_afectados": len(ids_duplicados),
                    "criterio": "Se mantiene la fecha_proceso más reciente en data limpia"
                }
                
                # Crear una columna para identificar duplicados en el DataFrame original
                df['es_duplicado'] = False
                df.loc[mascara_sucia, 'es_duplicado'] = True
                
                # Guardar el orden_id original para los duplicados
                df.loc[mascara_sucia, 'orden_id_original_duplicado'] = df.loc[mascara_sucia, 'orden_id']
                df.loc[mascara_sucia, 'fecha_proceso_original'] = df.loc[mascara_sucia, 'fecha_proceso']
                
                print(f"\n   ⚠️  Se encontraron {duplicados_count} registros duplicados en orden_id")
                print(f"   📊 Se mantiene la fecha_proceso más reciente en data limpia")
                print(f"   📋 Los duplicados van a data sucia")
        
        # ============================================
        # 1. VALIDACIÓN DE LONGITUD FIJA
        # ============================================
        longitudes_esperadas = {
            'orden_id': 10,
            'cliente_id': 6
        }
        
        for col, longitud_esperada in longitudes_esperadas.items():
            if col in df.columns:
                longitudes = df[col].astype(str).str.len()
                min_len = int(longitudes.min())
                max_len = int(longitudes.max())
                
                cumple_longitud = longitudes == longitud_esperada
                registros_erroneos = df[~cumple_longitud]
                
                if not cumple_longitud.all():
                    errores.append({
                        "tipo": "longitud_fija",
                        "columna": col,
                        "descripcion": f"Longitud esperada: {longitud_esperada}. Mín: {min_len}, Máx: {max_len}",
                        "longitud_esperada": longitud_esperada,
                        "cantidad_invalidos": int(len(registros_erroneos)),
                        "porcentaje_invalidos": float(round(len(registros_erroneos) / len(df) * 100, 2))
                    })
                    
                    mascara_sucia = mascara_sucia | ~cumple_longitud
                    
                    validaciones[f"longitud_{col}"] = {
                        "valida": False,
                        "longitud_esperada": longitud_esperada,
                        "min_len": min_len,
                        "max_len": max_len,
                        "cantidad_errores": int(len(registros_erroneos)),
                        "ejemplos_incorrectos": registros_erroneos[col].astype(str).head(5).tolist()
                    }
                else:
                    validaciones[f"longitud_{col}"] = {
                        "valida": True,
                        "longitud_esperada": longitud_esperada,
                        "todos_cumplen": True
                    }
        
        # ============================================
        # 2. PROCESAMIENTO DE FECHAS
        # ============================================
        columnas_fechas = ['fecha_pedido', 'fecha_entrega', 'fecha_proceso']
        reporte_fechas = {}
        
        for col in columnas_fechas:
            if col in df.columns:
                df[f'{col}_original'] = df[col]
                
                fechas = pd.to_datetime(df[col], errors='coerce', format='%Y-%m-%d')
                
                mask_nat = fechas.isna()
                if mask_nat.any():
                    fechas.loc[mask_nat] = pd.to_datetime(
                        df.loc[mask_nat, col], 
                        errors='coerce', 
                        format='%d/%m/%Y'
                    )
                
                errores_conversion = int(fechas.isna().sum())
                
                if errores_conversion > 0:
                    errores.append({
                        "tipo": "conversion_fecha",
                        "columna": col,
                        "cantidad_invalidos": errores_conversion,
                        "porcentaje_invalidos": float(round(errores_conversion / len(df) * 100, 2))
                    })
                    mascara_sucia = mascara_sucia | fechas.isna()
                
                df[col] = fechas
                
                reporte_fechas[col] = {
                    "errores_conversion": errores_conversion,
                    "fechas_validas": int(len(df) - errores_conversion)
                }
        
        validaciones["fechas"] = reporte_fechas
        
        # ============================================
        # 3. VALIDACIÓN Y ESTANDARIZACIÓN DE ESTADOS
        # ============================================
        if 'estado' in df.columns:
            estados_validos = configuracion.get('estados_validos', [])
            
            # Limpiar y estandarizar
            df['estado_original'] = df['estado']
            df['estado'] = df['estado'].str.strip().str.upper()
            
            # IDENTIFICAR ESTADOS INVÁLIDOS
            estados_invalidos = ~df['estado'].isin(estados_validos)
            
            if estados_invalidos.any():
                valores_invalidos = df[estados_invalidos]['estado'].unique().tolist()
                
                # CONTAR CUÁNTOS HAY DE CADA ESTADO INVÁLIDO
                conteo_estados_invalidos = df[estados_invalidos]['estado'].value_counts().to_dict()
                
                errores.append({
                    "tipo": "estado_invalido",
                    "columna": "estado",
                    "descripcion": "Estados no reconocidos en el sistema - Estos registros serán marcados como sucios",
                    "estados_validos": estados_validos,
                    "estados_invalidos_encontrados": valores_invalidos,
                    "conteo_estados_invalidos": conteo_estados_invalidos,
                    "cantidad_invalidos": int(estados_invalidos.sum()),
                    "porcentaje_invalidos": float(round(estados_invalidos.sum() / len(df) * 100, 2))
                })
                
                # MARCAR COMO SUCIOS TODOS LOS REGISTROS CON ESTADOS INVÁLIDOS
                mascara_sucia = mascara_sucia | estados_invalidos
                
                # Guardar el estado original para auditoría
                df.loc[estados_invalidos, 'estado_original_invalido'] = df.loc[estados_invalidos, 'estado']
                
                # Estandarizar a "OTROS" los inválidos
                df.loc[estados_invalidos, 'estado'] = "OTROS"
                
                validaciones["estados"] = {
                    "todos_validos": False,
                    "estados_originales": df['estado_original'].value_counts().to_dict(),
                    "estados_estandarizados": df['estado'].value_counts().to_dict(),
                    "estados_invalidos_encontrados": valores_invalidos,
                    "conteo_estados_invalidos": conteo_estados_invalidos,
                    "total_estados_invalidos": int(estados_invalidos.sum())
                }
            else:
                validaciones["estados"] = {
                    "todos_validos": True,
                    "distribucion": df['estado'].value_counts().to_dict()
                }
        
        # ============================================
        # 4. VALIDACIÓN DE MONTOS
        # ============================================
        if 'monto_total' in df.columns:
            df['monto_total_original'] = df['monto_total']
            df['monto_total'] = pd.to_numeric(df['monto_total'], errors='coerce')
            
            montos_invalidos = df['monto_total'] <= 0
            
            if montos_invalidos.any():
                df_montos_invalidos = df[montos_invalidos]
                errores.append({
                    "tipo": "monto_invalido",
                    "columna": "monto_total",
                    "descripcion": "Montos deben ser mayores a 0",
                    "cantidad_invalidos": int(montos_invalidos.sum()),
                    "promedio_monto_invalido": float(df_montos_invalidos['monto_total'].mean()) if not df_montos_invalidos.empty else 0,
                    "min_monto": float(df_montos_invalidos['monto_total'].min()) if not df_montos_invalidos.empty else 0,
                    "max_monto": float(df_montos_invalidos['monto_total'].max()) if not df_montos_invalidos.empty else 0
                })
                mascara_sucia = mascara_sucia | montos_invalidos
            
            validaciones["montos"] = {
                "total_registros": int(len(df)),
                "montos_validos": int((~montos_invalidos).sum()),
                "montos_invalidos": int(montos_invalidos.sum()),
                "monto_promedio": float(df[df['monto_total'] > 0]['monto_total'].mean()) if (df['monto_total'] > 0).any() else 0,
                "monto_min": float(df[df['monto_total'] > 0]['monto_total'].min()) if (df['monto_total'] > 0).any() else 0,
                "monto_max": float(df[df['monto_total'] > 0]['monto_total'].max()) if (df['monto_total'] > 0).any() else 0
            }
        
        # ============================================
        # 5. VALIDACIÓN DE TIPOS BÁSICOS
        # ============================================
        tipos_esperados = configuracion.get('tipos', {})
        for col, tipos in tipos_esperados.items():
            if col in df.columns:
                if not isinstance(tipos, list):
                    tipos = [tipos]
                
                tipo_actual = str(df[col].dtype)
                
                if 'object' in tipos and tipo_actual == 'str':
                    continue
                if 'str' in tipos and tipo_actual == 'object':
                    continue
                
                if tipo_actual not in tipos:
                    errores.append({
                        "tipo": "tipo_dato",
                        "columna": col,
                        "esperado": tipos,
                        "actual": tipo_actual,
                        "cantidad_invalidos": int(len(df))
                    })
                    mascara_sucia = mascara_sucia | pd.Series([True] * len(df), index=df.index)
        
        # ============================================
        # SEPARAR DATOS
        # ============================================
        df_limpio = df[~mascara_sucia].copy()
        df_sucios = df[mascara_sucia].copy()
        
        # Agregar motivos de rechazo
        if not df_sucios.empty:
            df_sucios = self._agregar_motivos_rechazo(df_sucios, df, configuracion, longitudes_esperadas)
        
        return errores, df_limpio, df_sucios, validaciones
    
    # ============================================
    # MÉTODOS AUXILIARES
    # ============================================
    
    def _agregar_motivos_rechazo(self, df_sucios, df_original, configuracion, longitudes_esperadas):
        """Agrega columna de motivos de rechazo para ordenes"""
        df_sucios['motivo_rechazo'] = ''
        
        for idx in df_sucios.index:
            razones = []
            
            # Verificar duplicado de orden_id
            if 'es_duplicado' in df_sucios.columns and df_sucios.loc[idx, 'es_duplicado'] == True:
                if 'orden_id_original_duplicado' in df_sucios.columns:
                    orden_id = df_sucios.loc[idx, 'orden_id_original_duplicado']
                    razones.append(f"❌ orden_id: duplicado (CRÍTICO - {orden_id} ya existe con fecha_proceso más reciente) - Este registro va a data sucia")
            
            # Validar longitud
            for col, longitud_esperada in longitudes_esperadas.items():
                if col in df_original.columns:
                    valor_actual = str(df_sucios.loc[idx, col])
                    if len(valor_actual) != longitud_esperada:
                        razones.append(f"{col}: longitud incorrecta (esperado: {longitud_esperada}, actual: {len(valor_actual)}, valor: '{valor_actual}')")
            
            # Validar fechas
            for col in ['fecha_pedido', 'fecha_entrega', 'fecha_proceso']:
                if col in df_original.columns:
                    if pd.isna(df_sucios.loc[idx, col]):
                        razones.append(f"{col}: fecha inválida o formato incorrecto")
            
            # Validar estado
            if 'estado' in df_original.columns:
                estados_validos = configuracion.get('estados_validos', [])
                if 'estado_original_invalido' in df_sucios.columns and pd.notna(df_sucios.loc[idx, 'estado_original_invalido']):
                    estado_invalido = df_sucios.loc[idx, 'estado_original_invalido']
                    razones.append(f"estado: valor inválido ('{estado_invalido}') - Estados permitidos: {estados_validos}")
                elif df_sucios.loc[idx, 'estado'] == "OTROS" and df_sucios.loc[idx, 'estado_original'] not in estados_validos:
                    razones.append(f"estado: valor inválido ('{df_sucios.loc[idx, 'estado_original']}') - Estados permitidos: {estados_validos}")
            
            # Validar monto
            if 'monto_total' in df_original.columns:
                try:
                    monto = df_sucios.loc[idx, 'monto_total']
                    if pd.isna(monto) or monto <= 0:
                        razones.append(f"monto_total: debe ser > 0 (valor: {monto})")
                except:
                    razones.append(f"monto_total: valor no numérico o inválido")
            
            if not razones:
                razones.append("Error de tipo de dato o formato incorrecto")
            
            df_sucios.loc[idx, 'motivo_rechazo'] = ' | '.join(razones)
        
        return df_sucios
    
    def _crear_resultado_error_columnas(self, nombre, df, faltantes, sobrantes, columnas_esperadas):
        """Crea un resultado de error por columnas faltantes"""
        return {
            "archivo": nombre,
            "fecha_ejecucion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "estado": "error_estructura_critico",
            "mensaje": "FALTAN COLUMNAS OBLIGATORIAS - No se puede procesar el archivo",
            "informacion": {
                "filas": int(df.shape[0]),
                "columnas": int(df.shape[1]),
                "lista_columnas": df.columns.tolist(),
                "tipos_datos": df.dtypes.astype(str).to_dict(),
            },
            "errores": [{
                "tipo": "estructura_columnas_critico",
                "descripcion": "El archivo no contiene todas las columnas requeridas",
                "columnas_faltantes": list(faltantes),
                "columnas_sobrantes": list(sobrantes) if sobrantes else [],
                "columnas_esperadas": list(columnas_esperadas),
                "columnas_actuales": list(df.columns),
                "accion": "PROCESO DETENIDO - Se requiere corregir la estructura del archivo"
            }],
            "separacion_datos": {}
        }
    
    def _guardar_datos_separados(self, df_limpio, df_sucios, nombre_archivo):
        """Guarda los datos limpios y sucios en archivos CSV"""
        nombre_base = nombre_archivo.replace('.csv', '')
        
        # Guardar datos limpios
        if not df_limpio.empty:
            path_clean = os.path.join(self.ruta_salida, f'{nombre_base}_cleaned.csv')
            df_limpio.to_csv(path_clean, index=False, encoding='utf-8')
            print(f"✅ Datos limpios guardados: {path_clean} ({len(df_limpio)} registros)")
        else:
            print("⚠️  No hay datos limpios para guardar")
        
        # Guardar datos sucios
        if not df_sucios.empty:
            path_dirty = os.path.join(self.ruta_salida, f'{nombre_base}_dirty.csv')
            df_sucios.to_csv(path_dirty, index=False, encoding='utf-8')
            print(f"⚠️  Datos sucios guardados: {path_dirty} ({len(df_sucios)} registros)")
        else:
            print("✅ No se encontraron datos sucios")
    
    def _guardar_resultado(self, resultado, nombre_archivo):
        """Guarda UN SOLO resultado en un archivo JSON"""
        fecha = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_base = nombre_archivo.replace('.csv', '')
        nombre_json = f"{nombre_base}_{fecha}.json"
        ruta_json = os.path.join(self.ruta_salida, nombre_json)
        
        with open(ruta_json, "w", encoding="utf-8") as f:
            json.dump(resultado, f, indent=4, ensure_ascii=False, default=str)
        
        print(f"📄 Reporte JSON guardado en: {ruta_json}")
    
    def _mostrar_resumen(self, df, nombre):
        """Muestra un resumen en consola"""
        print(f"\n✅ Archivo '{nombre}' procesado exitosamente")
        print(f"   📊 Filas: {df.shape[0]}, Columnas: {df.shape[1]}")
        print(f"   📋 Columnas: {', '.join(df.columns)}")
        print(f"   💾 Memoria: {round(df.memory_usage(deep=True).sum() / 1024, 2)} KB")
    
    def _mostrar_separacion(self, separacion):
        """Muestra información de la separación de datos"""
        print(f"\n📊 Separación de datos:")
        print(f"   ✅ Registros limpios: {separacion.get('registros_limpios', 0)} ({separacion.get('porcentaje_limpios', 0)}%)")
        print(f"   ❌ Registros sucios: {separacion.get('registros_sucios', 0)} ({separacion.get('porcentaje_sucios', 0)}%)")
    
    def _mostrar_validaciones_especificas(self, validaciones, configuracion):
        """Muestra las validaciones específicas realizadas - RECIBE CONFIGURACIÓN"""
        print("\n📋 VALIDACIONES ESPECÍFICAS:")
        
        # Duplicados
        if 'duplicados' in validaciones:
            print(f"   📊 Duplicados en orden_id:")
            print(f"      - Total de registros duplicados: {validaciones['duplicados']['total_duplicados']}")
            print(f"      - IDs únicos afectados: {validaciones['duplicados']['total_ids_afectados']}")
            print(f"      - Criterio: {validaciones['duplicados']['criterio']}")
            if validaciones['duplicados'].get('ids_duplicados'):
                print(f"      - Ejemplos de IDs duplicados: {validaciones['duplicados']['ids_duplicados'][:5]}")
        
        # Longitudes
        if 'longitud_orden_id' in validaciones:
            info = validaciones['longitud_orden_id']
            if info['valida']:
                print(f"   ✅ Longitud orden_id: {info['longitud_esperada']} (válida)")
            else:
                print(f"   ❌ Longitud orden_id: Esperado: {info['longitud_esperada']}, Mín: {info['min_len']}, Máx: {info['max_len']}")
                print(f"      Registros con error: {info['cantidad_errores']}")
                print(f"      Ejemplos: {info['ejemplos_incorrectos']}")
        
        if 'longitud_cliente_id' in validaciones:
            info = validaciones['longitud_cliente_id']
            if info['valida']:
                print(f"   ✅ Longitud cliente_id: {info['longitud_esperada']} (válida)")
            else:
                print(f"   ❌ Longitud cliente_id: Esperado: {info['longitud_esperada']}, Mín: {info['min_len']}, Máx: {info['max_len']}")
                print(f"      Registros con error: {info['cantidad_errores']}")
                print(f"      Ejemplos: {info['ejemplos_incorrectos']}")
        
        # Fechas
        if 'fechas' in validaciones:
            print("   📅 Procesamiento de fechas:")
            for col, info in validaciones['fechas'].items():
                if info['errores_conversion'] == 0:
                    print(f"      ✅ {col}: {info['fechas_validas']} válidas")
                else:
                    print(f"      ⚠️  {col}: {info['fechas_validas']} válidas, {info['errores_conversion']} errores")
        
        # Estados - AHORA CON CONFIGURACIÓN
        if 'estados' in validaciones:
            print("   📊 Validación de estados:")
            if validaciones['estados'].get('todos_validos', False):
                print("      ✅ Todos los estados son válidos")
                if 'distribucion' in validaciones['estados']:
                    for estado, count in validaciones['estados']['distribucion'].items():
                        print(f"      - {estado}: {count}")
            else:
                total_invalidos = validaciones['estados'].get('total_estados_invalidos', 0)
                print(f"      ❌ Se encontraron {total_invalidos} registros con estados inválidos")
                if 'estados_invalidos_encontrados' in validaciones['estados']:
                    print(f"      Estados inválidos encontrados:")
                    for estado in validaciones['estados']['estados_invalidos_encontrados']:
                        count = validaciones['estados']['conteo_estados_invalidos'].get(estado, 0)
                        print(f"         - '{estado}': {count} registros")
                # AHORA USAMOS LA CONFIGURACIÓN PASADA COMO PARÁMETRO
                estados_permitidos = configuracion.get('estados_validos', [])
                print(f"      Estados permitidos: {estados_permitidos}")
        
        # Montos
        if 'montos' in validaciones:
            print(f"   💰 Montos:")
            print(f"      - Válidos: {validaciones['montos']['montos_validos']}")
            if validaciones['montos']['montos_invalidos'] > 0:
                print(f"      ❌ Inválidos: {validaciones['montos']['montos_invalidos']}")
            print(f"      - Promedio: {validaciones['montos']['monto_promedio']:.2f}")
            print(f"      - Mínimo: {validaciones['montos']['monto_min']:.2f}")
            print(f"      - Máximo: {validaciones['montos']['monto_max']:.2f}")


# ============================================
# CONFIGURACIÓN PARA ORDENES
# ============================================

def get_configuracion():
    """Retorna la configuración para el archivo de ordenes"""
    return {
        'columnas': [
            'orden_id',
            'cliente_id',
            'fecha_pedido',
            'fecha_entrega',
            'fecha_proceso',
            'canal_venta',
            'estado',
            'monto_total'
        ],
        'tipos': {
            'orden_id': ['object', 'str'],
            'cliente_id': ['object', 'str'],
            'estado': ['object', 'str'],
            'monto_total': ['float64', 'float32']
        },
        'estados_validos': ['ENTREGADO', 'ANULADO', 'PENDIENTE', 'DEVUELTO'],
        'reglas': {
            'monto_total': 'estricto'
        }
    }


# ============================================
# FUNCIÓN MAIN
# ============================================

def main():
    """
    Función principal que procesa el archivo de ordenes
    """
    parser = argparse.ArgumentParser(
        description='Procesa el archivo ordenes CSV, valida, separa datos y genera reporte JSON'
    )
    
    parser.add_argument(
        '--archivo',
        type=str,
        default=r'D:\Github-Time\Solutions-to-Coding-Challenges\Data_Backus\data\1.raw\ordenes.csv',
        help='Ruta del archivo CSV a procesar'
    )
    
    parser.add_argument(
        '--salida',
        type=str,
        default=r'D:\Github-Time\Solutions-to-Coding-Challenges\Data_Backus\data\2.processed',
        help='Ruta de la carpeta donde guardar los archivos de salida'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Muestra información detallada en consola'
    )
    
    args = parser.parse_args()
    
    # Mostrar configuración
    if args.verbose:
        print("=" * 60)
        print("🔧 CONFIGURACIÓN DE EJECUCIÓN")
        print("=" * 60)
        print(f"📂 Archivo de entrada: {args.archivo}")
        print(f"📁 Carpeta de salida: {args.salida}")
        print("=" * 60)
    
    # Verificar que el archivo existe
    if not os.path.exists(args.archivo):
        print(f"❌ Error: El archivo '{args.archivo}' no existe")
        return 1
    
    # Inicializar procesador
    procesador = ProcesadorOrdenes(args.salida)
    
    # Obtener configuración
    configuracion = get_configuracion()
    
    # Procesar archivo
    print("\n🔄 Procesando archivo ordenes...")
    resultado = procesador.validar_y_extraer(args.archivo, configuracion)
    
    # Mostrar resumen de errores si los hay
    if resultado["errores"]:
        print("\n⚠️  Errores encontrados:")
        for i, error in enumerate(resultado["errores"], 1):
            print(f"   {i}. {error.get('tipo', 'Error')}")
            if 'columna' in error:
                print(f"      Columna: {error['columna']}")
            if 'cantidad_invalidos' in error:
                print(f"      Cantidad: {error['cantidad_invalidos']}")
            if 'descripcion' in error:
                print(f"      Descripción: {error['descripcion']}")
            if 'estados_invalidos_encontrados' in error:
                print(f"      Estados inválidos: {error['estados_invalidos_encontrados']}")
            if 'conteo_estados_invalidos' in error:
                print(f"      Conteo por estado: {error['conteo_estados_invalidos']}")
            if 'ids_duplicados' in error:
                print(f"      IDs duplicados: {error['ids_duplicados']}")
    
    # Mostrar información completa si verbose
    if args.verbose:
        print("\n📊 RESULTADO COMPLETO:")
        print(json.dumps(resultado, indent=4, ensure_ascii=False, default=str))
    
    print("\n✅ Procesamiento completado exitosamente")
    return 0


# ============================================
# PUNTO DE ENTRADA DEL PROGRAMA
# ============================================

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)