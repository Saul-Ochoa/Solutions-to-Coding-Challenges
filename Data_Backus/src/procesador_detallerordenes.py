import pandas as pd
import json
import os
from datetime import datetime
import argparse
import numpy as np

class ProcesadorArchivos:
    """Clase para procesar archivos CSV y extraer información"""
    
    def __init__(self, ruta_salida=None):
        if ruta_salida is None:
            self.ruta_salida = r"D:\Github-Time\Solutions-to-Coding-Challenges\Data_Backus\data\2.processed"
        else:
            self.ruta_salida = ruta_salida
        
        os.makedirs(self.ruta_salida, exist_ok=True)
    
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
                    "filas": df.shape[0],
                    "columnas": df.shape[1],
                    "lista_columnas": df.columns.tolist(),
                    "tipos_datos": df.dtypes.astype(str).to_dict(),
                    "datos_faltantes": df.isnull().sum().to_dict(),
                    "memoria_uso_kb": round(df.memory_usage(deep=True).sum() / 1024, 2)
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
    
    def validar_y_extraer(self, ruta_archivo, configuracion):
        """Extrae información, valida y separa datos limpios y sucios"""
        nombre = os.path.basename(ruta_archivo)
        
        try:
            # Leer el archivo sin forzar tipos
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
                resultado = {
                    "archivo": nombre,
                    "fecha_ejecucion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "estado": "error_estructura_critico",
                    "mensaje": "FALTAN COLUMNAS OBLIGATORIAS - No se puede procesar el archivo",
                    "informacion": {
                        "filas": df.shape[0],
                        "columnas": df.shape[1],
                        "lista_columnas": df.columns.tolist(),
                        "tipos_datos": df.dtypes.astype(str).to_dict(),
                    },
                    "errores": [{
                        "tipo": "estructura_columnas_critico",
                        "descripcion": "El archivo no contiene todas las columnas requeridas",
                        "columnas_faltantes": list(faltantes),
                        "columnas_sobrantes": list(sobrantes) if sobrantes else [],
                        "columnas_esperadas": list(columnas_esperadas),
                        "columnas_actuales": list(columnas_actuales),
                        "accion": "PROCESO DETENIDO - Se requiere corregir la estructura del archivo"
                    }],
                    "separacion_datos": {}
                }
                
                # Guardar JSON de error
                self._guardar_resultado(resultado, nombre)
                print(f"\n❌ ERROR CRÍTICO: Faltan columnas obligatorias")
                print(f"   Columnas faltantes: {list(faltantes)}")
                print(f"   Columnas esperadas: {list(columnas_esperadas)}")
                print(f"   Columnas actuales: {list(columnas_actuales)}")
                print(f"   ⛔ Proceso detenido - No se generaron archivos CSV")
                return resultado
            
            # =============================================
            # CONTINUAR CON EL PROCESAMIENTO NORMAL
            # =============================================
            
            # Construir resultado
            resultado = {
                "archivo": nombre,
                "fecha_ejecucion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "estado": "exitoso",
                "informacion": {
                    "filas": df.shape[0],
                    "columnas": df.shape[1],
                    "lista_columnas": df.columns.tolist(),
                    "tipos_datos": df.dtypes.astype(str).to_dict(),
                    "datos_faltantes": df.isnull().sum().to_dict(),
                    "memoria_uso_kb": round(df.memory_usage(deep=True).sum() / 1024, 2)
                },
                "errores": [],
                "separacion_datos": {},
                "validaciones_especificas": {}
            }
            
            # Si hay columnas sobrantes, solo advertencia
            if sobrantes:
                resultado["errores"].append({
                    "tipo": "estructura_columnas_advertencia",
                    "descripcion": "El archivo contiene columnas adicionales no esperadas",
                    "columnas_sobrantes": list(sobrantes)
                })
            
            # Validar estructura y reglas de negocio
            errores_validacion, df_limpio, df_sucios, validaciones = self._validar_y_separar(df, configuracion)
            
            if errores_validacion:
                resultado["estado"] = "error_validacion"
                resultado["errores"].extend(errores_validacion)
            
            resultado["validaciones_especificas"] = validaciones
            
            # Guardar datos separados
            self._guardar_datos_separados(df_limpio, df_sucios, nombre)
            
            # Actualizar información de separación
            resultado["separacion_datos"] = {
                "registros_limpios": len(df_limpio),
                "registros_sucios": len(df_sucios),
                "porcentaje_limpios": round(len(df_limpio) / len(df) * 100, 2) if len(df) > 0 else 0,
                "porcentaje_sucios": round(len(df_sucios) / len(df) * 100, 2) if len(df) > 0 else 0
            }
            
            # Guardar UN SOLO JSON con toda la información
            self._guardar_resultado(resultado, nombre)
            self._mostrar_resumen(df, nombre)
            self._mostrar_separacion(resultado["separacion_datos"])
            self._mostrar_validaciones_especificas(validaciones)
            
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
    
    def _validar_y_separar(self, df, configuracion):
        """
        Valida los datos y separa en limpios y sucios
        - Crea new_key para identificar registros únicos
        - Mantiene el primer registro de cada new_key en data limpia
        - Los duplicados van a data sucia
        """
        errores = []
        validaciones = {}
        
        # ============================================
        # 0. CREAR CLAVE ÚNICA Y DETECTAR DUPLICADOS
        # ============================================
        # Crear new_key combinando columnas clave
        df['new_key'] = (
            df['orden_id'].astype(str) + '_' +
            df['producto_id'].astype(str) + '_' +
            df['linea'].astype(str) + '_' +
            df['cantidad_unidades'].astype(str) + '_' +
            df['precio_unitario'].astype(str)
        )
        
        # Detectar duplicados en new_key
        mascara_duplicados = df.duplicated(subset=['new_key'], keep=False)
        duplicados_count = int(mascara_duplicados.sum())
        
        if duplicados_count > 0:
            # Obtener las claves duplicadas
            keys_duplicados = df[mascara_duplicados]['new_key'].unique().tolist()
            
            errores.append({
                "tipo": "registros_duplicados",
                "columna": "new_key",
                "descripcion": f"Se encontraron {duplicados_count} registros duplicados en detalle_ordenes",
                "cantidad_invalidos": duplicados_count,
                "keys_duplicados": keys_duplicados[:10],
                "total_keys_duplicados": len(keys_duplicados),
                "accion": "Se mantiene el primer registro en data limpia, los duplicados van a data sucia"
            })
            
            # Crear máscara para duplicados (keep='first' mantiene el primero)
            mascara_duplicados_a_eliminar = df.duplicated(subset=['new_key'], keep='first')
            
            # Guardar información de duplicados para validaciones
            validaciones["duplicados"] = {
                "total_registros_duplicados": duplicados_count,
                "keys_duplicados": keys_duplicados[:10],
                "total_keys_afectados": len(keys_duplicados),
                "criterio": "Se mantiene el primer registro en data limpia"
            }
            
            # Crear columna para identificar duplicados
            df['es_duplicado'] = False
            df.loc[mascara_duplicados_a_eliminar, 'es_duplicado'] = True
            
            # Guardar información del duplicado
            df.loc[mascara_duplicados_a_eliminar, 'new_key_original'] = df.loc[mascara_duplicados_a_eliminar, 'new_key']
            
            print(f"\n   ⚠️  Se encontraron {duplicados_count} registros duplicados en detalle_ordenes")
            print(f"   📊 Se mantiene el primer registro en data limpia")
            print(f"   📋 Los duplicados van a data sucia")
        else:
            df['es_duplicado'] = False
            validaciones["duplicados"] = {
                "total_registros_duplicados": 0,
                "mensaje": "No se encontraron registros duplicados"
            }
        
        # ============================================
        # 1. Validación de columnas
        # ============================================
        columnas_actuales = set(df.columns)
        columnas_esperadas = set(configuracion.get('columnas', []))
        
        faltantes = columnas_esperadas - columnas_actuales
        sobrantes = columnas_actuales - columnas_esperadas
        
        if faltantes:
            errores.append({
                "tipo": "estructura_columnas_critico",
                "faltantes": list(faltantes),
                "sobrantes": list(sobrantes)
            })
            return errores, df, pd.DataFrame()
        
        # Crear máscara para datos sucios (inicialmente los duplicados)
        mascara_sucia = df['es_duplicado'].copy()
        df_con_problemas = df.copy()
        
        # ============================================
        # 2. Validación de tipos y conversión para columnas numéricas
        # ============================================
        columnas_numericas = ['cantidad_unidades', 'precio_unitario', 'descuento_pct', 'linea']
        
        for col in columnas_numericas:
            if col not in df.columns:
                continue
            
            # Intentar convertir a numérico, los errores se convierten en NaN
            df_con_problemas[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Identificar filas que NO pudieron convertirse (texto, etc.)
            mascara_error_conversion = df[col].notna() & df_con_problemas[col].isna()
            
            if mascara_error_conversion.any():
                errores.append({
                    "tipo": "tipo_dato",
                    "columna": col,
                    "esperado": "numérico",
                    "actual": "texto u otro",
                    "cantidad_invalidos": int(mascara_error_conversion.sum()),
                    "ejemplos": df.loc[mascara_error_conversion, col].head(5).tolist()
                })
                mascara_sucia = mascara_sucia | mascara_error_conversion
        
        # ============================================
        # 3. Validación de reglas de negocio
        # ============================================
        for col, regla in configuracion.get('reglas', {}).items():
            if col not in df.columns:
                continue
            
            col_convertida = df_con_problemas[col]
            
            if regla == "estricto":
                invalidos = (col_convertida <= 0) & (col_convertida.notna())
                if invalidos.any():
                    errores.append({
                        "tipo": "regla_negocio",
                        "columna": col,
                        "regla": "estricto (>0)",
                        "cantidad_invalidos": int(invalidos.sum()),
                        "porcentaje_invalidos": round(invalidos.sum() / len(df) * 100, 2)
                    })
                    mascara_sucia = mascara_sucia | invalidos
            
            elif regla == "minimo_cero":
                invalidos = (col_convertida < 0) & (col_convertida.notna())
                if invalidos.any():
                    errores.append({
                        "tipo": "regla_negocio",
                        "columna": col,
                        "regla": "minimo_cero (>=0)",
                        "cantidad_invalidos": int(invalidos.sum()),
                        "porcentaje_invalidos": round(invalidos.sum() / len(df) * 100, 2)
                    })
                    mascara_sucia = mascara_sucia | invalidos
            
            elif regla == "no_nulos":
                invalidos = df[col].isnull()
                if invalidos.any():
                    errores.append({
                        "tipo": "regla_negocio",
                        "columna": col,
                        "regla": "no_nulos",
                        "cantidad_invalidos": int(invalidos.sum()),
                        "porcentaje_invalidos": round(invalidos.sum() / len(df) * 100, 2)
                    })
                    mascara_sucia = mascara_sucia | invalidos
        
        # ============================================
        # 4. Validación de tipos para columnas de texto (orden_id, producto_id)
        # ============================================
        for col in ['orden_id', 'producto_id']:
            if col in df.columns:
                if df[col].dtype not in ['object', 'str']:
                    errores.append({
                        "tipo": "tipo_dato",
                        "columna": col,
                        "esperado": "texto",
                        "actual": str(df[col].dtype),
                        "cantidad_invalidos": len(df)
                    })
                    mascara_sucia = mascara_sucia | pd.Series([True] * len(df), index=df.index)
        
        # ============================================
        # SEPARAR DATOS
        # ============================================
        df_limpio = df[~mascara_sucia].copy()
        df_sucios = df[mascara_sucia].copy()
        
        # Agregar columna de motivos a los datos sucios
        if not df_sucios.empty:
            df_sucios = self._agregar_motivos_rechazo(df_sucios, df, columnas_numericas, configuracion)
        
        return errores, df_limpio, df_sucios, validaciones
    
    def _agregar_motivos_rechazo(self, df_sucios, df_original, columnas_numericas, configuracion):
        """Agrega columna de motivos de rechazo"""
        df_sucios['motivo_rechazo'] = ''
        
        for idx in df_sucios.index:
            razones = []
            
            # Verificar duplicado
            if 'es_duplicado' in df_sucios.columns and df_sucios.loc[idx, 'es_duplicado'] == True:
                if 'new_key_original' in df_sucios.columns:
                    new_key = df_sucios.loc[idx, 'new_key_original']
                    razones.append(f"❌ Registro duplicado (CRÍTICO - {new_key} ya existe en data limpia)")
            
            # Verificar errores de conversión numérica
            for col in columnas_numericas:
                if col in df_original.columns:
                    if pd.isna(df_sucios.loc[idx, col]) and not pd.isna(df_original.loc[idx, col]):
                        razones.append(f"{col}: valor no numérico ('{df_original.loc[idx, col]}')")
            
            # Verificar reglas de negocio
            for col, regla in configuracion.get('reglas', {}).items():
                if col in df_original.columns and col in columnas_numericas:
                    valor = df_sucios.loc[idx, col]
                    try:
                        valor_num = pd.to_numeric(valor, errors='coerce')
                        if not pd.isna(valor_num):
                            if regla == "estricto" and valor_num <= 0:
                                razones.append(f"{col}: debe ser > 0 (valor: {valor_num})")
                            elif regla == "minimo_cero" and valor_num < 0:
                                razones.append(f"{col}: debe ser >= 0 (valor: {valor_num})")
                    except:
                        pass
            
            if not razones:
                razones.append("Error de tipo de dato o formato incorrecto")
            
            df_sucios.loc[idx, 'motivo_rechazo'] = ' | '.join(razones)
        
        return df_sucios
    
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
            json.dump(resultado, f, indent=4, ensure_ascii=False)
        
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
    
    def _mostrar_validaciones_especificas(self, validaciones):
        """Muestra las validaciones específicas realizadas"""
        print("\n📋 VALIDACIONES ESPECÍFICAS:")
        
        if 'duplicados' in validaciones:
            print(f"   📊 Duplicados en detalle_ordenes:")
            print(f"      - Total de registros duplicados: {validaciones['duplicados']['total_registros_duplicados']}")
            if validaciones['duplicados']['total_registros_duplicados'] > 0:
                print(f"      - Claves únicas afectadas: {validaciones['duplicados']['total_keys_afectados']}")
                print(f"      - Criterio: {validaciones['duplicados']['criterio']}")
                if validaciones['duplicados'].get('keys_duplicados'):
                    print(f"      - Ejemplos de claves duplicadas: {validaciones['duplicados']['keys_duplicados'][:3]}")


# ============================================
# CONFIGURACIÓN PARA DETALLE_ORDENES
# ============================================

def get_configuracion():
    """Retorna la configuración para el archivo de detalle_ordenes"""
    return {
        'columnas': [
            'producto_id',
            'linea',
            'descuento_pct',
            'cantidad_unidades',
            'precio_unitario',
            'orden_id'
        ],
        'tipos': {
            'orden_id': ['object', 'str'],
            'linea': ['int64'],
            'producto_id': ['object', 'str'],
            'cantidad_unidades': ['int64'],
            'precio_unitario': ['float64'],
            'descuento_pct': ['int64']
        },
        'reglas': {
            'cantidad_unidades': 'estricto',
            'precio_unitario': 'estricto',
            'descuento_pct': 'minimo_cero',
            'linea': 'estricto'
        }
    }


# ============================================
# FUNCIÓN MAIN
# ============================================

def main():
    """
    Función principal que procesa el archivo de detalle_ordenes
    """
    # Configurar el parser de argumentos
    parser = argparse.ArgumentParser(
        description='Procesa el archivo de detalle_ordenes CSV, valida, separa datos y genera reporte JSON'
    )
    
    parser.add_argument(
        '--archivo',
        type=str,
        default=r'D:\Github-Time\Solutions-to-Coding-Challenges\Data_Backus\data\1.raw\detalle_ordenes.csv',
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
    procesador = ProcesadorArchivos(args.salida)
    
    # Obtener configuración
    configuracion = get_configuracion()
    
    # Procesar archivo
    print("\n🔄 Procesando archivo detalle_ordenes...")
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
            if 'ejemplos' in error:
                print(f"      Ejemplos: {error['ejemplos']}")
            if 'columnas_faltantes' in error:
                print(f"      Columnas faltantes: {error['columnas_faltantes']}")
            if 'keys_duplicados' in error:
                print(f"      Claves duplicadas: {error['keys_duplicados']}")
    
    # Mostrar información completa si verbose
    if args.verbose:
        print("\n📊 RESULTADO COMPLETO:")
        print(json.dumps(resultado, indent=4, ensure_ascii=False))
    
    print("\n✅ Procesamiento completado exitosamente")
    return 0


# ============================================
# PUNTO DE ENTRADA DEL PROGRAMA
# ============================================

if __name__ == "__main__":
    # Ejecutar la función main
    exit_code = main()
    exit(exit_code)