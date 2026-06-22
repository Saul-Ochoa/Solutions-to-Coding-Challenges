import os
import pandas as pd
import pyodbc
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import json
import time
from datetime import datetime

def procesar_ordenes(ruta_archivo):
    """
    Procesa el archivo de ordenes_cleaned.csv y lo prepara para SQL Server
    """
    print(f"\n📂 Cargando archivo: {ruta_archivo}")
    
    # 1. Carga del archivo
    df_ordenes = pd.read_csv(ruta_archivo, sep=',')
    print(f"   ✅ Archivo cargado: {len(df_ordenes)} filas, {len(df_ordenes.columns)} columnas")
    
    # 2. Selección de columnas necesarias
    cols_necesarias = [
        'orden_id', 'cliente_id', 'fecha_pedido', 'fecha_entrega',
        'fecha_proceso', 'canal_venta', 'estado', 'monto_total'
    ]
    # Verificar qué columnas existen
    cols_existentes = [col for col in cols_necesarias if col in df_ordenes.columns]
    df_ordenes = df_ordenes[cols_existentes].copy()
    print(f"   📋 Columnas seleccionadas: {cols_existentes}")
    
    # 3. Transformar fechas
    columnas_fechas = ['fecha_pedido', 'fecha_entrega', 'fecha_proceso']
    for col in columnas_fechas:
        if col in df_ordenes.columns:
            df_ordenes[col] = pd.to_datetime(df_ordenes[col], errors='coerce', format='%Y-%m-%d')
    
    # 4. Metadatos en JSON
    nombre_archivo = os.path.basename(ruta_archivo)
    numero_filas = len(df_ordenes)
    fecha_carga_str = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
    
    diccionario_metadatos = {
        "nombre_archivo": nombre_archivo,
        "numero_filas": numero_filas,
        "fecha_carga": fecha_carga_str
    }
    
    df_ordenes['metadatos_json'] = json.dumps(diccionario_metadatos)
    
    # 5. Columnas de auditoría
    df_ordenes['source_file'] = nombre_archivo
    df_ordenes['load_date'] = pd.Timestamp.now()
    df_ordenes['update_date'] = pd.Timestamp.now()
    df_ordenes['loaded_by'] = 'proceso_etl_python'
    df_ordenes['is_active'] = 1
    
    print(f"   ✅ Datos procesados: {len(df_ordenes)} filas listas para carga")
    
    return df_ordenes

def guardar_auditoria_json(auditoria, ruta_destino):
    """
    Guarda la auditoría de la carga en un archivo JSON
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_completo = f"auditoria_carga_ordenes_{timestamp}.json"
    ruta_completa = os.path.join(ruta_destino, nombre_completo)
    
    with open(ruta_completa, "w", encoding="utf-8") as f:
        json.dump(auditoria, f, indent=4, ensure_ascii=False)
    
    print(f"   📄 Auditoría guardada en: {ruta_completa}")
    return ruta_completa

def verificar_ordenes_existentes(df, server, database):
    """
    Verifica qué órdenes ya existen en la tabla para evitar duplicados
    """
    try:
        connection_string = f"mssql+pyodbc://{server}/{database}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"
        engine = create_engine(connection_string)
        
        with engine.connect() as conn:
            existing_ids = pd.read_sql("SELECT orden_id FROM ordenes", conn)
            
        if existing_ids.empty:
            print("   ℹ️  La tabla está vacía. Todos los registros serán cargados.")
            return df, pd.DataFrame(), 0
        
        existing_set = set(existing_ids['orden_id'].astype(str))
        
        df['orden_id_str'] = df['orden_id'].astype(str)
        df_nuevos = df[~df['orden_id_str'].isin(existing_set)].copy()
        df_existentes = df[df['orden_id_str'].isin(existing_set)].copy()
        
        df_nuevos = df_nuevos.drop(columns=['orden_id_str'])
        df_existentes = df_existentes.drop(columns=['orden_id_str'])
        
        print(f"   📊 Registros a cargar: {len(df_nuevos)} nuevos")
        print(f"   ⚠️  Registros ya existentes (omitidos): {len(df_existentes)}")
        
        if len(df_existentes) > 0:
            print(f"   ℹ️  Ejemplos de IDs ya existentes: {df_existentes['orden_id'].head(3).tolist()}")
        
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
    print("🚀 INICIANDO CARGA DE ÓRDENES A SQL SERVER")
    print("=" * 70)
    
    # 1. Definir rutas
    url_origen = r'D:\Github-Time\Solutions-to-Coding-Challenges\Data_Backus\data\2.processed\ordenes_cleaned.csv'
    ruta_destino = r'D:\Github-Time\Solutions-to-Coding-Challenges\Data_Backus\data\3.final'
    
    # Crear carpeta de destino si no existe
    os.makedirs(ruta_destino, exist_ok=True)
    
    # 2. Procesar datos
    print("\n📊 PASO 1: Procesando datos de órdenes...")
    df_ordenes = procesar_ordenes(url_origen)
    
    # 3. Guardar datos finales en 3.final
    print("\n💾 PASO 2: Guardando datos finales...")
    ruta_final = os.path.join(ruta_destino, 'ordenes_final.csv')
    df_ordenes.to_csv(ruta_final, index=False, encoding='utf-8')
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
    
    # 6. Verificar órdenes existentes
    print("\n🔍 PASO 4: Verificando órdenes existentes...")
    df_nuevos, df_existentes, total_existentes = verificar_ordenes_existentes(df_ordenes, server, database)
    
    # 7. Si no hay órdenes nuevas, terminar
    if len(df_nuevos) == 0:
        print("\n   ℹ️  No hay órdenes nuevas para cargar. Todos los IDs ya existen.")
        
        auditoria = {
            "fecha_auditoria": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "servidor": server,
            "base_datos": database,
            "tabla": "ordenes",
            "archivo_origen": url_origen,
            "nombre_archivo": os.path.basename(url_origen),
            "filas_cargadas": 0,
            "filas_existentes": total_existentes,
            "estado": "EXITOSO_SIN_CAMBIOS",
            "mensaje": f"No hay órdenes nuevas para cargar. {total_existentes} órdenes ya existentes."
        }
        
        print("\n📋 PASO 5: Guardando auditoría...")
        ruta_auditoria = guardar_auditoria_json(auditoria, ruta_destino)
        
        print("\n" + "=" * 70)
        print("✅ PROCESO COMPLETADO - SIN CAMBIOS")
        print("=" * 70)
        print(f"📂 Datos finales: {ruta_final}")
        print(f"📄 Auditoría: {ruta_auditoria}")
        print(f"📊 Órdenes existentes: {total_existentes}")
        print(f"📋 Estado: {auditoria['estado']}")
        print("=" * 70)
        
        exit(0)
    
    # 8. Medir tiempo de carga
    inicio_carga = time.time()
    fecha_inicio = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        print(f"\n🔄 PASO 5: Cargando {len(df_nuevos)} órdenes nuevas a SQL Server...")
        print(f"   📊 Tabla: ordenes")
        print(f"   🕐 Inicio: {fecha_inicio}")
        
        # 9. Probar conexión antes de cargar
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("   ✅ Conexión exitosa a SQL Server")
        
        # 10. Subir SOLO las órdenes nuevas a SQL Server
        df_nuevos.to_sql(
            name='ordenes',
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
            "tabla": "ordenes",
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
            "mensaje": f"Carga completada exitosamente. {len(df_nuevos)} nuevas órdenes insertadas."
        }
        
        if total_existentes > 0:
            auditoria["mensaje"] += f" {total_existentes} órdenes ya existentes fueron omitidas."
        
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
        print(f"📊 Órdenes nuevas cargadas: {auditoria['filas_cargadas']}")
        if total_existentes > 0:
            print(f"⚠️  Órdenes ya existentes (omitidas): {total_existentes}")
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
            "tabla": "ordenes",
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