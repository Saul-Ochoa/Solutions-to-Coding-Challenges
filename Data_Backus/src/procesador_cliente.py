import pandas as pd
import json
import os
from datetime import datetime
import argparse
import numpy as np

class ProcesadorClientes:
    """Clase para procesar el archivo de clientes CSV y extraer información"""
    
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
        """Extrae información, valida y separa datos limpios y sucios para CLIENTES"""
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
            
            if sobrantes:
                resultado["errores"].append({
                    "tipo": "estructura_columnas_advertencia",
                    "descripcion": "El archivo contiene columnas adicionales no esperadas",
                    "columnas_sobrantes": list(sobrantes)
                })
            
            # Validar y separar datos
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
        Valida los datos de clientes y separa en limpios y sucios
        - cliente_id: NO puede ser nulo ni duplicado (crítico)
        - fecha_alta: Puede ser nula (va a cleaned Y dirty para corrección)
        - Otras columnas: Pueden tener nulos (se aceptan en limpia)
        - Estados inválidos: Van a sucios
        """
        errores = []
        validaciones = {}
        mascara_sucia = pd.Series([False] * len(df), index=df.index)
        df_con_problemas = df.copy()
        
        # ============================================
        # 1. VALIDACIÓN CRÍTICA: cliente_id
        # ============================================
        if 'cliente_id' in df.columns:
            # 1.1 Validar que cliente_id NO sea nulo
            cliente_id_nulo = df['cliente_id'].isnull()
            
            if cliente_id_nulo.any():
                errores.append({
                    "tipo": "cliente_id_nulo",
                    "columna": "cliente_id",
                    "descripcion": "cliente_id no puede ser nulo - Estos registros NO pasarán a la data limpia",
                    "cantidad_invalidos": int(cliente_id_nulo.sum()),
                    "porcentaje_invalidos": round(cliente_id_nulo.sum() / len(df) * 100, 2)
                })
                mascara_sucia = mascara_sucia | cliente_id_nulo
            
            # 1.2 Validar que cliente_id sea único (sin duplicados)
            mascara_duplicados = df.duplicated(subset=['cliente_id'], keep='first')
            
            if mascara_duplicados.any():
                ids_duplicados = df[mascara_duplicados]['cliente_id'].unique().tolist()
                
                errores.append({
                    "tipo": "cliente_id_duplicado",
                    "columna": "cliente_id",
                    "descripcion": "cliente_id duplicado - Estos registros NO pasarán a la data limpia",
                    "cantidad_invalidos": int(mascara_duplicados.sum()),
                    "ids_duplicados": ids_duplicados[:10],
                    "total_ids_unicos": df['cliente_id'].nunique(),
                    "total_registros": len(df)
                })
                mascara_sucia = mascara_sucia | mascara_duplicados
        
        # ============================================
        # 2. VALIDACIÓN DE TIPOS Y CONVERSIÓN
        # ============================================
        
        # Validar que las columnas de texto sean object/str
        columnas_texto = ['cliente_id', 'nombre_comercial', 'canal', 'region', 'distrito', 'estado']
        for col in columnas_texto:
            if col in df.columns:
                if df[col].dtype not in ['object', 'str']:
                    errores.append({
                        "tipo": "tipo_dato",
                        "columna": col,
                        "esperado": "texto (object/str)",
                        "actual": str(df[col].dtype),
                        "cantidad_invalidos": len(df)
                    })
                    mascara_sucia = mascara_sucia | pd.Series([True] * len(df), index=df.index)
        
        # ============================================
        # 3. PROCESAMIENTO DE FECHA_ALTA
        # ============================================
        fecha_alta_nula = pd.Series([False] * len(df), index=df.index)
        fecha_alta_invalida = pd.Series([False] * len(df), index=df.index)
        
        if 'fecha_alta' in df.columns:
            df['fecha_alta_original'] = df['fecha_alta']
            
            # Intentar convertir a datetime
            df['fecha_alta'] = pd.to_datetime(df['fecha_alta'], format='%Y-%m-%d', errors='coerce')
            
            # Identificar registros con fecha nula (originalmente vacíos)
            fecha_alta_nula = df['fecha_alta_original'].isna()
            
            # Identificar registros con fecha inválida (formato incorrecto)
            fecha_alta_invalida = df['fecha_alta'].isna() & df['fecha_alta_original'].notna()
            
            # Si hay fechas inválidas (formato incorrecto)
            if fecha_alta_invalida.any():
                errores.append({
                    "tipo": "fecha_alta_invalida",
                    "columna": "fecha_alta",
                    "descripcion": "Fechas con formato inválido - Estos registros van a dirty para corrección (y también a cleaned)",
                    "cantidad_invalidos": int(fecha_alta_invalida.sum()),
                    "porcentaje_invalidos": round(fecha_alta_invalida.sum() / len(df) * 100, 2),
                    "ejemplos": df.loc[fecha_alta_invalida, 'fecha_alta_original'].head(5).tolist()
                })
                # Marcar como sucios SOLO las fechas inválidas (no los nulos)
                mascara_sucia = mascara_sucia | fecha_alta_invalida
            
            # Si hay fechas nulas (registro sin fecha)
            if fecha_alta_nula.any():
                errores.append({
                    "tipo": "fecha_alta_nula",
                    "columna": "fecha_alta",
                    "descripcion": f"Registros con fecha_alta vacía - Van a cleaned y también a dirty para que puedas actualizarlos",
                    "cantidad_invalidos": int(fecha_alta_nula.sum()),
                    "porcentaje_invalidos": round(fecha_alta_nula.sum() / len(df) * 100, 2),
                    "accion_sugerida": "Actualizar la fecha en los registros dirty y luego actualizar cleaned"
                })
                # NO marcar como sucios los nulos, SOLO van a dirty para corrección
                # pero NO se marcan con mascara_sucia para que también vayan a cleaned
        
        # ============================================
        # 4. VALIDACIÓN DE ESTADOS
        # ============================================
        if 'estado' in df.columns:
            estados_validos = configuracion.get('estados_validos', ['ACTIVO', 'INACTIVO'])
            
            df['estado_original'] = df['estado']
            df['estado'] = df['estado'].str.strip().str.upper()
            
            # Identificar estados inválidos (ignorando nulos)
            estados_invalidos = ~df['estado'].isin(estados_validos) & df['estado'].notna()
            
            if estados_invalidos.any():
                valores_invalidos = df[estados_invalidos]['estado'].unique().tolist()
                conteo_estados_invalidos = df[estados_invalidos]['estado'].value_counts().to_dict()
                
                errores.append({
                    "tipo": "estado_invalido",
                    "columna": "estado",
                    "descripcion": "Estados no reconocidos en el sistema - Estos registros NO pasarán a la data limpia",
                    "estados_validos": estados_validos,
                    "estados_invalidos_encontrados": valores_invalidos,
                    "conteo_estados_invalidos": conteo_estados_invalidos,
                    "cantidad_invalidos": int(estados_invalidos.sum()),
                    "porcentaje_invalidos": round(estados_invalidos.sum() / len(df) * 100, 2)
                })
                
                mascara_sucia = mascara_sucia | estados_invalidos
                df.loc[estados_invalidos, 'estado_original_invalido'] = df.loc[estados_invalidos, 'estado']
        
        # ============================================
        # 5. TRANSFORMACIÓN A MINÚSCULAS
        # ============================================
        columnas_minusculas = ['region', 'distrito', 'canal']
        for col in columnas_minusculas:
            if col in df.columns:
                df[col] = df[col].str.lower()
        
        # ============================================
        # 6. DETECCIÓN DE NULOS EN OTRAS COLUMNAS (SOLO REPORTE)
        # ============================================
        columnas_para_reporte = [col for col in df.columns if col not in ['cliente_id', 'fecha_alta']]
        filas_con_nulos = df[columnas_para_reporte].isnull().any(axis=1)
        
        nulos_por_columna = {}
        if filas_con_nulos.any():
            nulos_por_columna = df[filas_con_nulos][columnas_para_reporte].isnull().sum()
            nulos_por_columna = nulos_por_columna[nulos_por_columna > 0].to_dict()
            
            if nulos_por_columna:
                errores.append({
                    "tipo": "datos_nulos_advertencia",
                    "descripcion": "Se encontraron registros con valores nulos en columnas no críticas (pasan a cleaned)",
                    "total_registros_con_nulos": int(filas_con_nulos.sum()),
                    "porcentaje_registros_con_nulos": round(filas_con_nulos.sum() / len(df) * 100, 2),
                    "nulos_por_columna": nulos_por_columna,
                    "nota": "Estos registros SI pasan a la data limpia"
                })
        
        # ============================================
        # SEPARAR DATOS
        # ============================================
        # IMPORTANTE: Los registros con fecha_alta nula NO van a mascara_sucia
        # para que también estén en cleaned
        df_limpio = df[~mascara_sucia].copy()
        
        # Para dirty: incluimos TODOS los que tienen algún problema
        # (incluyendo fecha_alta nula para que se puedan corregir)
        mascara_para_dirty = mascara_sucia | fecha_alta_nula | fecha_alta_invalida
        df_sucios = df[mascara_para_dirty].copy()
        
        # Agregar columna de motivos a los datos sucios
        if not df_sucios.empty:
            df_sucios = self._agregar_motivos_rechazo(df_sucios, df, fecha_alta_nula, fecha_alta_invalida)
        
        # Guardar validaciones
        validaciones = {
            "total_registros": len(df),
            "registros_limpios": len(df_limpio),
            "registros_sucios": len(df_sucios),
            "criterios_rechazo": {
                "cliente_id_nulo": int(cliente_id_nulo.sum()) if 'cliente_id_nulo' in locals() else 0,
                "cliente_id_duplicado": int(mascara_duplicados.sum()) if 'mascara_duplicados' in locals() else 0,
                "estado_invalido": int(estados_invalidos.sum()) if 'estados_invalidos' in locals() else 0,
                "fecha_alta_invalida": int(fecha_alta_invalida.sum()) if 'fecha_alta_invalida' in locals() else 0,
                "fecha_alta_nula": int(fecha_alta_nula.sum()) if 'fecha_alta_nula' in locals() else 0
            },
            "nota_fechas_nulas": "Los registros con fecha_alta nula aparecen en cleaned (para uso) y en dirty (para corrección)"
        }
        
        if nulos_por_columna:
            validaciones["detalle_nulos_aceptados"] = nulos_por_columna
        
        return errores, df_limpio, df_sucios, validaciones
    
    # ============================================
    # MÉTODOS AUXILIARES
    # ============================================
    
    def _agregar_motivos_rechazo(self, df_sucios, df_original, fecha_alta_nula, fecha_alta_invalida):
        """Agrega columna de motivos de rechazo para clientes"""
        df_sucios['motivo_rechazo'] = ''
        
        for idx in df_sucios.index:
            razones = []
            
            # Verificar cliente_id nulo (crítico)
            if 'cliente_id' in df_original.columns:
                if pd.isna(df_sucios.loc[idx, 'cliente_id']):
                    razones.append("❌ cliente_id: valor nulo (CRÍTICO - no puede ser nulo, NO está en cleaned)")
            
            # Verificar cliente_id duplicado (crítico)
            if 'cliente_id' in df_original.columns:
                if not pd.isna(df_sucios.loc[idx, 'cliente_id']):
                    count = df_original[df_original['cliente_id'] == df_sucios.loc[idx, 'cliente_id']].shape[0]
                    if count > 1:
                        razones.append(f"❌ cliente_id: duplicado (CRÍTICO - aparece {count} veces, NO está en cleaned)")
            
            # Verificar fecha_alta nula (va a cleaned y dirty)
            if 'fecha_alta' in df_original.columns:
                if idx in fecha_alta_nula.index and fecha_alta_nula.loc[idx]:
                    razones.append("⚠️ fecha_alta: valor nulo (Está en cleaned y en dirty - actualizar en dirty y luego pasar a cleaned)")
            
            # Verificar fecha_alta inválida (va a cleaned y dirty)
            if 'fecha_alta' in df_original.columns:
                if idx in fecha_alta_invalida.index and fecha_alta_invalida.loc[idx]:
                    valor_original = df_original.loc[idx, 'fecha_alta_original']
                    razones.append(f"⚠️ fecha_alta: formato inválido ('{valor_original}') - Está en cleaned y en dirty - corregir formato YYYY-MM-DD")
            
            # Verificar estado inválido
            if 'estado' in df_original.columns:
                if 'estado_original_invalido' in df_sucios.columns and pd.notna(df_sucios.loc[idx, 'estado_original_invalido']):
                    estado_invalido = df_sucios.loc[idx, 'estado_original_invalido']
                    razones.append(f"❌ estado: valor inválido ('{estado_invalido}') - Solo se permiten: ACTIVO, INACTIVO")
            
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
            
            # Mostrar cuántos tienen fecha nula en cleaned
            if 'fecha_alta' in df_limpio.columns:
                nulos_fecha = df_limpio['fecha_alta'].isna().sum()
                if nulos_fecha > 0:
                    print(f"   ℹ️  {nulos_fecha} registros en cleaned tienen fecha_alta nula (pueden actualizarse)")
        else:
            print("⚠️  No hay datos limpios para guardar")
        
        # Guardar datos sucios
        if not df_sucios.empty:
            path_dirty = os.path.join(self.ruta_salida, f'{nombre_base}_dirty.csv')
            df_sucios.to_csv(path_dirty, index=False, encoding='utf-8')
            print(f"⚠️  Datos sucios guardados: {path_dirty} ({len(df_sucios)} registros)")
            print(f"   ℹ️  Corrige los problemas en este archivo y luego actualiza cleaned")
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
        
        if 'nota_fechas_nulas' in separacion:
            print(f"   ℹ️  {separacion['nota_fechas_nulas']}")
    
    def _mostrar_validaciones_especificas(self, validaciones):
        """Muestra las validaciones específicas realizadas"""
        print("\n📋 VALIDACIONES ESPECÍFICAS:")
        
        if 'total_registros' in validaciones:
            print(f"   📊 Total de registros: {validaciones['total_registros']}")
        
        if 'registros_limpios' in validaciones:
            print(f"   ✅ Registros limpios: {validaciones['registros_limpios']}")
        
        if 'registros_sucios' in validaciones:
            print(f"   ❌ Registros sucios: {validaciones['registros_sucios']}")
        
        if 'criterios_rechazo' in validaciones:
            print("   📋 Detalle de problemas:")
            criterios = validaciones['criterios_rechazo']
            if criterios.get('cliente_id_nulo', 0) > 0:
                print(f"      - ❌ cliente_id nulo: {criterios['cliente_id_nulo']} (NO están en cleaned)")
            if criterios.get('cliente_id_duplicado', 0) > 0:
                print(f"      - ❌ cliente_id duplicado: {criterios['cliente_id_duplicado']} (NO están en cleaned)")
            if criterios.get('estado_invalido', 0) > 0:
                print(f"      - ❌ estado inválido: {criterios['estado_invalido']} (NO están en cleaned)")
            if criterios.get('fecha_alta_invalida', 0) > 0:
                print(f"      - ⚠️  fecha_alta inválida: {criterios['fecha_alta_invalida']} (Están en cleaned Y dirty)")
            if criterios.get('fecha_alta_nula', 0) > 0:
                print(f"      - ⚠️  fecha_alta nula: {criterios['fecha_alta_nula']} (Están en cleaned Y dirty - actualizar en dirty)")
        
        if 'detalle_nulos_aceptados' in validaciones and validaciones['detalle_nulos_aceptados']:
            print("   📋 Nulos aceptados en data limpia:")
            for col, count in validaciones['detalle_nulos_aceptados'].items():
                print(f"      - {col}: {count} nulos (aceptados)")

# ============================================
# CONFIGURACIÓN PARA CLIENTES
# ============================================

def get_configuracion():
    """Retorna la configuración para el archivo de clientes"""
    return {
        'columnas': [
            'cliente_id',
            'nombre_comercial',
            'canal',
            'region',
            'distrito',
            'fecha_alta',
            'estado'
        ],
        'estados_validos': ['ACTIVO', 'INACTIVO']
    }


# ============================================
# FUNCIÓN MAIN
# ============================================

def main():
    """
    Función principal que procesa el archivo de clientes
    """
    parser = argparse.ArgumentParser(
        description='Procesa el archivo de clientes CSV, valida, separa datos y genera reporte JSON'
    )
    
    parser.add_argument(
        '--archivo',
        type=str,
        default=r'D:\Github-Time\Solutions-to-Coding-Challenges\Data_Backus\data\1.raw\clientes.csv',
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
    
    if args.verbose:
        print("=" * 60)
        print("🔧 CONFIGURACIÓN DE EJECUCIÓN")
        print("=" * 60)
        print(f"📂 Archivo de entrada: {args.archivo}")
        print(f"📁 Carpeta de salida: {args.salida}")
        print("=" * 60)
    
    if not os.path.exists(args.archivo):
        print(f"❌ Error: El archivo '{args.archivo}' no existe")
        return 1
    
    procesador = ProcesadorClientes(args.salida)
    configuracion = get_configuracion()
    
    print("\n🔄 Procesando archivo clientes...")
    resultado = procesador.validar_y_extraer(args.archivo, configuracion)
    
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
            if 'ids_duplicados' in error:
                print(f"      IDs duplicados (ejemplos): {error['ids_duplicados']}")
            if 'ejemplos' in error:
                print(f"      Ejemplos: {error['ejemplos']}")
            if 'accion_sugerida' in error:
                print(f"      💡 Acción sugerida: {error['accion_sugerida']}")
    
    if args.verbose:
        print("\n📊 RESULTADO COMPLETO:")
        print(json.dumps(resultado, indent=4, ensure_ascii=False))
    
    print("\n✅ Procesamiento completado exitosamente")
    return 0


if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)