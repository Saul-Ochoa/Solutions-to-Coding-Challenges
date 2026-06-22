import os
import pandas as pd
import pyodbc
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import json
import time
from datetime import datetime

def procesar_detalleordenes(ruta_archivo):
    """
    Procesa el archivo de detalle_ordenes_cleaned.csv y lo prepara para SQL Server
    """
    print(f"\n📂 Cargando archivo: {ruta_archivo}")
    
    # 1. Carga del archivo
    df_detalleordenes = pd.read_csv(ruta_archivo, sep=',')
    print(f"   ✅ Archivo cargado: {len(df_detalleordenes)} filas, {len(df_detalleordenes.columns)} columnas")
    
    # 2. Selección de columnas necesarias
    cols_necesarias = [
        'orden_id', 'linea', 'producto_id', 'cantidad_unidades',
        'precio_unitario', 'descuento_pct'
    ]
    # Verificar qué columnas existen
    cols_existentes = [col for col in cols_necesarias if col in df_detalleordenes.columns]
    df_detalleordenes = df_detalleordenes[cols_existentes].copy()
    print(f"   📋 Columnas seleccionadas: {cols_existentes}")
    
    # 3. Asegurar tipos de datos
    if 'linea' in df_detalleordenes.columns:
        df_detalleordenes['linea'] = df_detalleordenes['linea'].astype(int)
    if 'cantidad_unidades' in df_detalleordenes.columns:
        df_detalleordenes['cantidad_unidades'] = df_detalleordenes['cantidad_unidades'].astype(int)
    if 'precio_unitario' in df_detalleordenes.columns:
        df_detalleordenes['precio_unitario'] = df_detalleordenes['precio_unitario'].astype(float)
    if 'descuento_pct' in df_detalleordenes.columns:
        df_detalleordenes['descuento_pct'] = df_detalleordenes['descuento_pct'].astype(int)
    
    # 4. Metadatos en JSON
    nombre_archivo = os.path.basename(ruta_archivo)
    numero_filas = len(df_detalleordenes)
    fecha_carga_str = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
    
    diccionario_metadatos = {
        "nombre_archivo": nombre_archivo,
        "numero_filas": numero_filas,
        "fecha_carga": fecha_carga_str
    }
    
    df_detalleordenes['metadatos_json'] = json.dumps(diccionario_metadatos)
    
    # 5. Columnas de auditoría
    df_detalleordenes['source_file'] = nombre_archivo
    df_detalleordenes['load_date'] = pd.Timestamp.now()
    df_detalleordenes['update_date'] = pd.Timestamp.now()
    df_detalleordenes['loaded_by'] = 'proceso_etl_python'
    df_detalleordenes['is_active'] = 1
    
    print(f"   ✅ Datos procesados: {len(df_detalleordenes)} filas listas para carga")
    
    return df_detalleordenes

def guardar_auditoria_json(auditoria, ruta_destino):
    """
    Guarda la auditoría de la carga en un archivo JSON
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_completo = f"auditoria_carga_detalle_ordenes_{timestamp}.json"
    ruta_completa = os.path.join(ruta_destino, nombre_completo)
    
    with open(ruta_completa, "w", encoding="utf-8") as f:
        json.dump(auditoria, f, indent=4, ensure_ascii=False)
    
    print(f"   📄 Auditoría guardada en: {ruta_completa}")
    return ruta_completa

def verificar_detalle_existente(df, server, database):
    """
    Verifica qué registros ya existen en la tabla para evitar duplicados
    Usa la combinación de orden_id + linea como clave compuesta
    """
    try:
        connection_string = f"mssql+pyodbc://{server}/{database}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"
        engine = create_engine(connection_string)
        
        with engine.connect() as conn:
            # Obtener registros existentes
            existing = pd.read_sql("SELECT orden_id, linea FROM detalle_ordenes", conn)
            
        if existing.empty:
            print("   ℹ️  La tabla está vacía. Todos los registros serán cargados.")
            return df, pd.DataFrame(), 0
        
        # Crear clave compuesta para comparación
        df['clave_compuesta'] = df['orden_id'].astype(str) + '_' + df['linea'].astype(str)
        existing['clave_compuesta'] = existing['orden_id'].astype(str) + '_' + existing['linea'].astype(str)
        
        existing_set = set(existing['clave_compuesta'])
        
        df_nuevos = df[~df['clave_compuesta'].isin(existing_set)].copy()
        df_existentes = df[df['clave_compuesta'].isin(existing_set)].copy()
        
        # Eliminar columna auxiliar
        df_nuevos = df_nuevos.drop(columns=['clave_compuesta'])
        df_existentes = df_existentes.drop(columns=['clave_compuesta'])
        
        print(f"   📊 Registros a cargar: {len(df_nuevos)} nuevos")
        print(f"   ⚠️  Registros ya existentes (omitidos): {len(df_existentes)}")
        
        if len(df_existentes) > 0:
            print(f"   ℹ️  Ejemplos de claves ya existentes: {df_existentes['orden_id'].head(3).tolist()}")
        
        return df_nuevos, df_existentes, len(df_existentes)
        
    except Exception as e:
        print(f"   ⚠️  No se pudo verificar duplicados: {e}")
        print(f"   ℹ️  Se intentará cargar todos los registros")
        return df, pd.DataFrame(), 0

# ============================================
# EJECUCIÓN PRINCIPAL
# ============================================

if __name__ == "__main__":
    
    print("=" * 70)
    print("🚀 INICIANDO CARGA DE DETALLE_ÓRDENES A SQL SERVER")
    print("=" * 70)
    
    # 1. Definir rutas
    url_origen = r'D:\Github-Time\Solutions-to-Coding-Challenges\Data_Backus\data\2.processed\detalle_ordenes_cleaned.csv'
    ruta_destino = r'D:\Github-Time\Solutions-to-Coding-Challenges\Data_Backus\data\3.final'
    
    # Crear carpeta de destino si no existe
    os.makedirs(ruta_destino, exist_ok=True)
    
    # 2. Procesar datos
    print("\n📊 PASO 1: Procesando datos de detalle_órdenes...")
    df_detalleordenes = procesar_detalleordenes(url_origen)
    
    # 3. Guardar datos finales en 3.final
    print("\n💾 PASO 2: Guardando datos finales...")
    ruta_final = os.path.join(ruta_destino, 'detalle_ordenes_final.csv')
    df_detalleordenes.to_csv(ruta_final, index=False, encoding='utf-8')
    print(f"   💾 Datos guardados en: {ruta_final}")
    
    # 4. Cargar variables de entorno
    print("\n☁️  PASO 3: Conectando a SQL Server...")
    load_dotenv()
    server = os.getenv('DB_SERVER')
    database = os.getenv('DB_DATABASE')
    
    # Validar que las variables existan
    if not server or not database:
        raise ValueError("❌ No se encontraron las variables de entorno DB_SERVER o DB_DATABASE.")
    
    print(f"   🔄 Conectando al servidor '{server}' en la base de datos '{database}'...")
    
    # 5. Crear cadena de conexión
    connection_string = f"mssql+pyodbc://{server}/{database}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"
    engine = create_engine(connection_string)
    
    # 6. Verificar registros existentes
    print("\n🔍 PASO 4: Verificando registros existentes...")
    df_nuevos, df_existentes, total_existentes = verificar_detalle_existente(df_detalleordenes, server, database)
    
    # 7. Si no hay registros nuevos, terminar
    if len(df_nuevos) == 0:
        print("\n   ℹ️  No hay registros nuevos para cargar. Todos los IDs ya existen.")
        
        auditoria = {
            "fecha_auditoria": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "servidor": server,
            "base_datos": database,
            "tabla": "detalle_ordenes",
            "archivo_origen": url_origen,
            "nombre_archivo": os.path.basename(url_origen),
            "filas_cargadas": 0,
            "filas_existentes": total_existentes,
            "estado": "EXITOSO_SIN_CAMBIOS",
            "mensaje": f"No hay registros nuevos para cargar. {total_existentes} registros ya existentes."
        }
        
        print("\n📋 PASO 5: Guardando auditoría...")
        ruta_auditoria = guardar_auditoria_json(auditoria, ruta_destino)
        
        print("\n" + "=" * 70)
        print("✅ PROCESO COMPLETADO - SIN CAMBIOS")
        print("=" * 70)
        print(f"📂 Datos finales: {ruta_final}")
        print(f"📄 Auditoría: {ruta_auditoria}")
        print(f"📊 Registros existentes: {total_existentes}")
        print(f"📋 Estado: {auditoria['estado']}")
        print("=" * 70)
        
        exit(0)
    
    # 8. Medir tiempo de carga
    inicio_carga = time.time()
    fecha_inicio = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        print(f"\n🔄 PASO 5: Cargando {len(df_nuevos)} registros a SQL Server...")
        print(f"   📊 Tabla: detalle_ordenes")
        print(f"   🕐 Inicio: {fecha_inicio}")
        
        # 9. Probar conexión antes de cargar
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("   ✅ Conexión exitosa a SQL Server")
        
        # 10. Subir SOLO los registros nuevos a SQL Server
        df_nuevos.to_sql(
            name='detalle_ordenes',
            con=engine,
            if_exists='append',
            index=False,
            chunksize=1000
        )
        
        # 11. Calcular tiempo
        fin_carga = time.time()
        fecha_fin = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        tiempo_total = fin_carga - inicio_carga
        
        print(f"\n   ✅ ¡Carga completada con éxito en bloques de 1000!")
        print(f"   ⏱️  Tiempo total: {round(tiempo_total, 2)} segundos ({round(tiempo_total / 60, 2)} minutos)")
        print(f"   📊 Filas por segundo: {round(len(df_nuevos) / tiempo_total, 2) if tiempo_total > 0 else 0}")
        print(f"   🕐 Fin: {fecha_fin}")
        
        # 12. Crear auditoría
        auditoria = {
            "fecha_auditoria": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "servidor": server,
            "base_datos": database,
            "tabla": "detalle_ordenes",
            "archivo_origen": url_origen,
            "nombre_archivo": os.path.basename(url_origen),
            "filas_cargadas": len(df_nuevos),
            "filas_existentes": total_existentes,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "tiempo_total_segundos": round(tiempo_total, 2),
            "tiempo_total_minutos": round(tiempo_total / 60, 2),
            "tiempo_por_fila": round(tiempo_total / len(df_nuevos), 4) if len(df_nuevos) > 0 else 0,
            "bloques": (len(df_nuevos) // 1000) + 1 if len(df_nuevos) > 0 else 0,
            "estado": "EXITOSO",
            "mensaje": f"Carga completada exitosamente. {len(df_nuevos)} nuevos registros insertados."
        }
        
        if total_existentes > 0:
            auditoria["mensaje"] += f" {total_existentes} registros ya existentes fueron omitidos."
        
        # 13. Guardar auditoría en 3.final
        print("\n📋 PASO 6: Guardando auditoría...")
        ruta_auditoria = guardar_auditoria_json(auditoria, ruta_destino)
        
        # 14. Resumen final
        print("\n" + "=" * 70)
        print("✅ PROCESO COMPLETADO EXITOSAMENTE")
        print("=" * 70)
        print(f"📂 Datos finales: {ruta_final}")
        print(f"📄 Auditoría: {ruta_auditoria}")
        print(f"⏱️  Tiempo total de carga: {auditoria['tiempo_total_segundos']} segundos")
        print(f"📊 Registros nuevos cargados: {auditoria['filas_cargadas']}")
        if total_existentes > 0:
            print(f"⚠️  Registros ya existentes (omitidos): {total_existentes}")
        print(f"📋 Estado: {auditoria['estado']}")
        print("=" * 70)
        
    except Exception as e:
        # Calcular tiempo aunque haya error
        fin_carga = time.time()
        tiempo_total = fin_carga - inicio_carga
        
        auditoria = {
            "fecha_auditoria": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "servidor": server,
            "base_datos": database,
            "tabla": "detalle_ordenes",
            "archivo_origen": url_origen,
            "nombre_archivo": os.path.basename(url_origen),
            "filas_cargadas": 0,
            "filas_existentes": total_existentes,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "tiempo_total_segundos": round(tiempo_total, 2),
            "tiempo_total_minutos": round(tiempo_total / 60, 2),
            "tiempo_por_fila": 0,
            "bloques": 0,
            "estado": "ERROR",
            "mensaje": str(e),
            "error": str(e)
        }
        
        print(f"\n   ❌ Error en la carga: {e}")
        
        # Guardar auditoría de error
        print("\n📋 Guardando auditoría de error...")
        ruta_auditoria = guardar_auditoria_json(auditoria, ruta_destino)
        
        print("\n" + "=" * 70)
        print("❌ PROCESO FALLÓ")
        print("=" * 70)
        print(f"📄 Auditoría de error: {ruta_auditoria}")
        print(f"⏱️  Tiempo hasta el error: {auditoria['tiempo_total_segundos']} segundos")
        print(f"❌ Error: {e}")
        print("=" * 70)
        
        raise