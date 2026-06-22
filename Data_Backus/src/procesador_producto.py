import pandas as pd
import json
import os
from datetime import datetime
import argparse
import numpy as np
import re

class ProcesadorProductos:
    """Clase para procesar el archivo de productos CSV y extraer información"""
    
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
        """Extrae información, valida y separa datos limpios y sucios para PRODUCTOS"""
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
        Valida los datos de productos y separa en limpios y sucios
        - producto_id: NO puede ser nulo ni duplicado (crítico)
        - contenido_ml: > 0 (si es nulo se corrige con contenido_ml_new)
        - unidades_por_caja: > 0
        - precio_lista: > 0
        - Otras columnas: Pueden tener nulos (se aceptan en limpia)
        """
        errores = []
        validaciones = {}
        mascara_sucia = pd.Series([False] * len(df), index=df.index)
        df_con_problemas = df.copy()
        
        # ============================================
        # 1. VALIDACIÓN CRÍTICA: producto_id
        # ============================================
        if 'producto_id' in df.columns:
            # 1.1 Validar que producto_id NO sea nulo
            producto_id_nulo = df['producto_id'].isnull()
            
            if producto_id_nulo.any():
                errores.append({
                    "tipo": "producto_id_nulo",
                    "columna": "producto_id",
                    "descripcion": "producto_id no puede ser nulo - Estos registros NO pasarán a la data limpia",
                    "cantidad_invalidos": int(producto_id_nulo.sum()),
                    "porcentaje_invalidos": round(producto_id_nulo.sum() / len(df) * 100, 2)
                })
                mascara_sucia = mascara_sucia | producto_id_nulo
            
            # 1.2 Validar que producto_id sea único (sin duplicados)
            mascara_duplicados = df.duplicated(subset=['producto_id'], keep='first')
            
            if mascara_duplicados.any():
                ids_duplicados = df[mascara_duplicados]['producto_id'].unique().tolist()
                
                errores.append({
                    "tipo": "producto_id_duplicado",
                    "columna": "producto_id",
                    "descripcion": "producto_id duplicado - Solo el primer registro va a cleaned, los duplicados a dirty",
                    "cantidad_invalidos": int(mascara_duplicados.sum()),
                    "ids_duplicados": ids_duplicados[:10],
                    "total_ids_unicos": df['producto_id'].nunique(),
                    "total_registros": len(df)
                })
                mascara_sucia = mascara_sucia | mascara_duplicados
        
        # ============================================
        # 2. VALIDACIÓN DE TIPOS
        # ============================================
        
        # 2.1 Columnas de texto
        columnas_texto = ['producto_id', 'nombre_producto', 'categoria', 'marca', 'presentacion']
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
        
        # 2.2 Columnas float
        columnas_float = ['contenido_ml', 'precio_lista']
        for col in columnas_float:
            if col in df.columns:
                if not ('float' in str(df[col].dtype)):
                    errores.append({
                        "tipo": "tipo_dato",
                        "columna": col,
                        "esperado": "float",
                        "actual": str(df[col].dtype),
                        "cantidad_invalidos": len(df)
                    })
                    mascara_sucia = mascara_sucia | pd.Series([True] * len(df), index=df.index)
        
        # 2.3 Columna int
        if 'unidades_por_caja' in df.columns:
            if not ('int64' in str(df['unidades_por_caja'].dtype)):
                errores.append({
                    "tipo": "tipo_dato",
                    "columna": "unidades_por_caja",
                    "esperado": "int64",
                    "actual": str(df['unidades_por_caja'].dtype),
                    "cantidad_invalidos": len(df)
                })
                mascara_sucia = mascara_sucia | pd.Series([True] * len(df), index=df.index)
        
        # ============================================
        # 3. PROCESAMIENTO DE CONTENIDO_ML
        # ============================================
        contenido_ml_nulo = pd.Series([False] * len(df), index=df.index)
        contenido_ml_invalido = pd.Series([False] * len(df), index=df.index)
        
        if 'presentacion' in df.columns:
            # Extraer volumen de la presentación
            df['volumen'] = df['presentacion'].str.extract(r'(\d+\.?\d*\s*(?:ml|l|L|mL))', expand=False)
            
            # Función para convertir a ml
            def convertir_a_ml(valor):
                if pd.isna(valor):
                    return None
                valor_str = str(valor).strip().lower()
                try:
                    numero = float(re.search(r'\d+\.?\d*', valor_str).group())
                    if 'ml' in valor_str:
                        return numero
                    elif 'l' in valor_str:
                        return numero * 1000
                    return numero
                except:
                    return None
            
            # Crear columna corregida
            df['contenido_ml_new'] = df['volumen'].apply(convertir_a_ml)
            
            # Identificar registros con contenido_ml nulo original
            if 'contenido_ml' in df.columns:
                contenido_ml_nulo = df['contenido_ml'].isna()
                
                if contenido_ml_nulo.any():
                    corregidos = contenido_ml_nulo & df['contenido_ml_new'].notna()
                    
                    errores.append({
                        "tipo": "contenido_ml_nulo",
                        "columna": "contenido_ml",
                        "descripcion": f"Registros con contenido_ml nulo - {corregidos.sum()} fueron corregidos en contenido_ml_new",
                        "cantidad_invalidos": int(contenido_ml_nulo.sum()),
                        "corregidos": int(corregidos.sum()),
                        "porcentaje_invalidos": round(contenido_ml_nulo.sum() / len(df) * 100, 2),
                        "accion_sugerida": "Los registros con contenido_ml nulo van a cleaned (con contenido_ml_new) y a dirty para corrección"
                    })
                    
                    # NO marcar como sucios los nulos de contenido_ml
                    # para que vayan a cleaned con el valor corregido
                    
                    # Para los que NO se pudieron corregir, marcarlos como sucios
                    no_corregidos = contenido_ml_nulo & df['contenido_ml_new'].isna()
                    if no_corregidos.any():
                        mascara_sucia = mascara_sucia | no_corregidos
        
        # ============================================
        # 4. VALIDACIONES DE NEGOCIO (VALORES > 0)
        # ============================================
        
        # 4.1 Validar contenido_ml > 0 (usando contenido_ml_new si existe)
        columna_ml = 'contenido_ml_new' if 'contenido_ml_new' in df.columns else 'contenido_ml'
        if columna_ml in df.columns:
            # Solo validar valores no nulos
            ml_invalido = (df[columna_ml] <= 0) & (df[columna_ml].notna())
            
            if ml_invalido.any():
                errores.append({
                    "tipo": "contenido_ml_negativo_o_cero",
                    "columna": "contenido_ml",
                    "descripcion": f"contenido_ml debe ser mayor a 0 - {ml_invalido.sum()} registros con valores inválidos",
                    "cantidad_invalidos": int(ml_invalido.sum()),
                    "porcentaje_invalidos": round(ml_invalido.sum() / len(df) * 100, 2),
                    "ejemplos": df.loc[ml_invalido, columna_ml].head(5).tolist()
                })
                mascara_sucia = mascara_sucia | ml_invalido
        
        # 4.2 Validar unidades_por_caja > 0
        if 'unidades_por_caja' in df.columns:
            unidades_invalidas = (df['unidades_por_caja'] <= 0) & (df['unidades_por_caja'].notna())
            
            if unidades_invalidas.any():
                errores.append({
                    "tipo": "unidades_por_caja_negativo_o_cero",
                    "columna": "unidades_por_caja",
                    "descripcion": "unidades_por_caja debe ser mayor a 0",
                    "cantidad_invalidos": int(unidades_invalidas.sum()),
                    "porcentaje_invalidos": round(unidades_invalidas.sum() / len(df) * 100, 2),
                    "ejemplos": df.loc[unidades_invalidas, 'unidades_por_caja'].head(5).tolist()
                })
                mascara_sucia = mascara_sucia | unidades_invalidas
        
        # 4.3 Validar precio_lista > 0
        if 'precio_lista' in df.columns:
            precio_invalido = (df['precio_lista'] <= 0) & (df['precio_lista'].notna())
            
            if precio_invalido.any():
                errores.append({
                    "tipo": "precio_lista_negativo_o_cero",
                    "columna": "precio_lista",
                    "descripcion": "precio_lista debe ser mayor a 0",
                    "cantidad_invalidos": int(precio_invalido.sum()),
                    "porcentaje_invalidos": round(precio_invalido.sum() / len(df) * 100, 2),
                    "ejemplos": df.loc[precio_invalido, 'precio_lista'].head(5).tolist()
                })
                mascara_sucia = mascara_sucia | precio_invalido
        
        # ============================================
        # 5. DETECCIÓN DE NULOS EN OTRAS COLUMNAS
        # ============================================
        columnas_para_reporte = ['nombre_producto', 'categoria', 'marca', 'presentacion']
        filas_con_nulos = df[columnas_para_reporte].isnull().any(axis=1)
        
        nulos_por_columna = {}
        if filas_con_nulos.any():
            nulos_por_columna = df[filas_con_nulos][columnas_para_reporte].isnull().sum()
            nulos_por_columna = nulos_por_columna[nulos_por_columna > 0].to_dict()
            
            if nulos_por_columna:
                errores.append({
                    "tipo": "datos_nulos_advertencia",
                    "descripcion": "Se encontraron registros con valores nulos en columnas no críticas",
                    "total_registros_con_nulos": int(filas_con_nulos.sum()),
                    "porcentaje_registros_con_nulos": round(filas_con_nulos.sum() / len(df) * 100, 2),
                    "nulos_por_columna": nulos_por_columna,
                    "nota": "Estos registros van a cleaned (con nulos) y también a dirty para corrección"
                })
        
        # ============================================
        # SEPARAR DATOS
        # ============================================
        # Los registros con contenido_ml nulo NO van a mascara_sucia
        # para que también estén en cleaned con el valor corregido
        df_limpio = df[~mascara_sucia].copy()
        
        # Para dirty: incluimos TODOS los que tienen algún problema
        mascara_para_dirty = mascara_sucia | contenido_ml_nulo | filas_con_nulos
        df_sucios = df[mascara_para_dirty].copy()
        
        # Agregar columna de motivos a los datos sucios
        if not df_sucios.empty:
            df_sucios = self._agregar_motivos_rechazo(
                df_sucios, df, contenido_ml_nulo, filas_con_nulos,
                ml_invalido if 'ml_invalido' in locals() else pd.Series([False] * len(df), index=df.index),
                unidades_invalidas if 'unidades_invalidas' in locals() else pd.Series([False] * len(df), index=df.index),
                precio_invalido if 'precio_invalido' in locals() else pd.Series([False] * len(df), index=df.index)
            )
        
        # Guardar validaciones
        validaciones = {
            "total_registros": len(df),
            "registros_limpios": len(df_limpio),
            "registros_sucios": len(df_sucios),
            "criterios_rechazo": {
                "producto_id_nulo": int(producto_id_nulo.sum()) if 'producto_id_nulo' in locals() else 0,
                "producto_id_duplicado": int(mascara_duplicados.sum()) if 'mascara_duplicados' in locals() else 0,
                "contenido_ml_nulo": int(contenido_ml_nulo.sum()) if 'contenido_ml_nulo' in locals() else 0,
                "contenido_ml_invalido": int(ml_invalido.sum()) if 'ml_invalido' in locals() else 0,
                "unidades_por_caja_invalido": int(unidades_invalidas.sum()) if 'unidades_invalidas' in locals() else 0,
                "precio_lista_invalido": int(precio_invalido.sum()) if 'precio_invalido' in locals() else 0,
                "otros_nulos": int(filas_con_nulos.sum()) if 'filas_con_nulos' in locals() else 0
            },
            "nota_contenido_ml": "Los registros con contenido_ml nulo fueron corregidos en contenido_ml_new y aparecen en cleaned y dirty"
        }
        
        if nulos_por_columna:
            validaciones["detalle_nulos_aceptados"] = nulos_por_columna
        
        return errores, df_limpio, df_sucios, validaciones
    
    # ============================================
    # MÉTODOS AUXILIARES
    # ============================================
    
    def _agregar_motivos_rechazo(self, df_sucios, df_original, contenido_ml_nulo, filas_con_nulos,
                                  ml_invalido, unidades_invalidas, precio_invalido):
        """Agrega columna de motivos de rechazo para productos"""
        df_sucios['motivo_rechazo'] = ''
        
        for idx in df_sucios.index:
            razones = []
            
            # Verificar producto_id nulo (crítico)
            if 'producto_id' in df_original.columns:
                if pd.isna(df_sucios.loc[idx, 'producto_id']):
                    razones.append("❌ producto_id: valor nulo (CRÍTICO - no puede ser nulo, NO está en cleaned)")
            
            # Verificar producto_id duplicado (crítico)
            if 'producto_id' in df_original.columns:
                if not pd.isna(df_sucios.loc[idx, 'producto_id']):
                    count = df_original[df_original['producto_id'] == df_sucios.loc[idx, 'producto_id']].shape[0]
                    if count > 1:
                        first_idx = df_original[df_original['producto_id'] == df_sucios.loc[idx, 'producto_id']].index[0]
                        if idx != first_idx:
                            razones.append(f"❌ producto_id: duplicado (CRÍTICO - aparece {count} veces, solo el primero va a cleaned)")
            
            # Verificar contenido_ml nulo (va a cleaned y dirty)
            if 'contenido_ml' in df_original.columns:
                if idx in contenido_ml_nulo.index and contenido_ml_nulo.loc[idx]:
                    if 'contenido_ml_new' in df_sucios.columns:
                        valor_corregido = df_sucios.loc[idx, 'contenido_ml_new']
                        if pd.notna(valor_corregido):
                            razones.append(f"⚠️ contenido_ml: valor nulo (corregido en contenido_ml_new = {valor_corregido} - Está en cleaned y dirty)")
                        else:
                            razones.append(f"⚠️ contenido_ml: valor nulo (NO se pudo corregir - verificar presentación)")
            
            # Verificar contenido_ml <= 0
            if idx in ml_invalido.index and ml_invalido.loc[idx]:
                columna_ml = 'contenido_ml_new' if 'contenido_ml_new' in df_sucios.columns else 'contenido_ml'
                valor = df_sucios.loc[idx, columna_ml] if columna_ml in df_sucios.columns else None
                razones.append(f"❌ contenido_ml: debe ser > 0 (valor: {valor}) - NO está en cleaned")
            
            # Verificar unidades_por_caja <= 0
            if idx in unidades_invalidas.index and unidades_invalidas.loc[idx]:
                valor = df_sucios.loc[idx, 'unidades_por_caja'] if 'unidades_por_caja' in df_sucios.columns else None
                razones.append(f"❌ unidades_por_caja: debe ser > 0 (valor: {valor}) - NO está en cleaned")
            
            # Verificar precio_lista <= 0
            if idx in precio_invalido.index and precio_invalido.loc[idx]:
                valor = df_sucios.loc[idx, 'precio_lista'] if 'precio_lista' in df_sucios.columns else None
                razones.append(f"❌ precio_lista: debe ser > 0 (valor: {valor}) - NO está en cleaned")
            
            # Verificar nulos en otras columnas
            if idx in filas_con_nulos.index and filas_con_nulos.loc[idx]:
                for col in ['nombre_producto', 'categoria', 'marca', 'presentacion']:
                    if col in df_original.columns and pd.isna(df_sucios.loc[idx, col]):
                        razones.append(f"⚠️ {col}: valor nulo (Está en cleaned y dirty - corregir)")
            
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
            
            # Mostrar cuántos tienen contenido_ml corregido
            if 'contenido_ml_new' in df_limpio.columns:
                corregidos = df_limpio['contenido_ml'].isna() & df_limpio['contenido_ml_new'].notna()
                if corregidos.any():
                    print(f"   ℹ️  {corregidos.sum()} registros en cleaned tienen contenido_ml corregido desde la presentación")
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
        
        if 'nota_contenido_ml' in separacion:
            print(f"   ℹ️  {separacion['nota_contenido_ml']}")
    
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
            if criterios.get('producto_id_nulo', 0) > 0:
                print(f"      - ❌ producto_id nulo: {criterios['producto_id_nulo']} (NO están en cleaned)")
            if criterios.get('producto_id_duplicado', 0) > 0:
                print(f"      - ❌ producto_id duplicado: {criterios['producto_id_duplicado']} (NO están en cleaned)")
            if criterios.get('contenido_ml_nulo', 0) > 0:
                print(f"      - ⚠️  contenido_ml nulo: {criterios['contenido_ml_nulo']} (Están en cleaned Y dirty - corregidos en contenido_ml_new)")
            if criterios.get('contenido_ml_invalido', 0) > 0:
                print(f"      - ❌ contenido_ml <= 0: {criterios['contenido_ml_invalido']} (NO están en cleaned)")
            if criterios.get('unidades_por_caja_invalido', 0) > 0:
                print(f"      - ❌ unidades_por_caja <= 0: {criterios['unidades_por_caja_invalido']} (NO están en cleaned)")
            if criterios.get('precio_lista_invalido', 0) > 0:
                print(f"      - ❌ precio_lista <= 0: {criterios['precio_lista_invalido']} (NO están en cleaned)")
            if criterios.get('otros_nulos', 0) > 0:
                print(f"      - ⚠️  otros nulos: {criterios['otros_nulos']} (Están en cleaned Y dirty)")
        
        if 'detalle_nulos_aceptados' in validaciones and validaciones['detalle_nulos_aceptados']:
            print("   📋 Nulos aceptados en data limpia:")
            for col, count in validaciones['detalle_nulos_aceptados'].items():
                print(f"      - {col}: {count} nulos (aceptados)")


# ============================================
# CONFIGURACIÓN PARA PRODUCTOS
# ============================================

def get_configuracion():
    """Retorna la configuración para el archivo de productos"""
    return {
        'columnas': [
            'producto_id',
            'nombre_producto',
            'categoria',
            'marca',
            'presentacion',
            'contenido_ml',
            'unidades_por_caja',
            'precio_lista'
        ]
    }


# ============================================
# FUNCIÓN MAIN
# ============================================

def main():
    """
    Función principal que procesa el archivo de productos
    """
    parser = argparse.ArgumentParser(
        description='Procesa el archivo de productos CSV, valida, separa datos y genera reporte JSON'
    )
    
    parser.add_argument(
        '--archivo',
        type=str,
        default=r'D:\Github-Time\Solutions-to-Coding-Challenges\Data_Backus\data\1.raw\productos.csv',
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
    
    procesador = ProcesadorProductos(args.salida)
    configuracion = get_configuracion()
    
    print("\n🔄 Procesando archivo productos...")
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