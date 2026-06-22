import os
import pandas as pd
import pyodbc
from dotenv import load_dotenv
from sqlalchemy import create_engine
import json
import time
from datetime import datetime

def procesar_producto(ruta_archivo):
    """
    Procesa el archivo de productos_cleaned.csv y lo prepara para SQL Server
    """
    print(f"\n📂 Cargando archivo: {ruta_archivo}")
    
    # 1. Carga del archivo de productos
    df_producto = pd.read_csv(ruta_archivo, sep=',')
    print(f"   ✅ Archivo cargado: {len(df_producto)} filas, {len(df_producto.columns)} columnas")
    
    # 2. Selección de columnas necesarias
    cols_necesarias = [
        'producto_id', 'nombre_producto', 'categoria', 'marca', 'presentacion',
        'volumen', 'contenido_ml_new', 'unidades_por_caja', 'precio_lista'
    ]
    df_producto = df_producto[cols_necesarias].copy()
    
    # 3. Renombrar columnas
    df_producto = df_producto.rename(columns={'contenido_ml_new': 'contenido_ml'})
    
    # 4. Metadatos en JSON
    nombre_archivo = os.path.basename(ruta_archivo)
    numero_filas = len(df_producto)
    fecha_carga_str = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
    
    diccionario_metadatos = {
        "nombre_archivo": nombre_archivo,
        "numero_filas": numero_filas,
        "fecha_carga": fecha_carga_str
    }
    
    df_producto['metadatos_json'] = json.dumps(diccionario_metadatos)
    
    # 5. Columnas de auditoría
    df_producto['source_file'] = nombre_archivo
    df_producto['load_date'] = pd.Timestamp.now()
    df_producto['update_date'] = pd.Timestamp.now()
    df_producto['loaded_by'] = 'proceso_etl_python'
    df_producto['is_active'] = 1
    
    print(f"   ✅ Datos procesados: {len(df_producto)} filas listas para carga")
    
    return df_producto

def guardar_auditoria_json(auditoria, ruta_destino):
    """
    Guarda la auditoría de la carga en un archivo JSON
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre_completo = f"auditoria_carga_producto_{timestamp}.json"
    ruta_completa = os.path.join(ruta_destino, nombre_completo)
    
    with open(ruta_completa, "w", encoding="utf-8") as f:
        json.dump(auditoria, f, indent=4, ensure_ascii=False)
    
    print(f"   📄 Auditoría guardada en: {ruta_completa}")
    return ruta_completa

# ============================================
# EJECUCIÓN PRINCIPAL
# ============================================

if __name__ == "__main__":
    
    print("=" * 70)
    print("🚀 INICIANDO CARGA DE PRODUCTOS A SQL SERVER")
    print("=" * 70)
    
    # 1. Definir rutas
    url_origen = r'D:\Github-Time\Solutions-to-Coding-Challenges\Data_Backus\data\2.processed\productos_cleaned.csv'
    ruta_destino = r'D:\Github-Time\Solutions-to-Coding-Challenges\Data_Backus\data\3.final'
    
    # Crear carpeta de destino si no existe
    os.makedirs(ruta_destino, exist_ok=True)
    
    # 2. Procesar datos
    print("\n📊 PASO 1: Procesando datos de productos...")
    df_producto = procesar_producto(url_origen)
    
    # 3. Guardar datos finales en 3.final
    print("\n💾 PASO 2: Guardando datos finales...")
    ruta_final = os.path.join(ruta_destino, 'productos_final.csv')
    df_producto.to_csv(ruta_final, index=False, encoding='utf-8')
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
    
    # 6. Medir tiempo de carga
    inicio_carga = time.time()
    fecha_inicio = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        print(f"   🚀 Iniciando la carga de {len(df_producto)} filas a la tabla 'producto'...")
        print(f"   🕐 Inicio: {fecha_inicio}")
        
        # 7. Subir a SQL Server en bloques
        df_producto.to_sql(
            name='producto',
            con=engine,
            if_exists='append',
            index=False,
            chunksize=1000
        )
        
        # 8. Calcular tiempo
        fin_carga = time.time()
        fecha_fin = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        tiempo_total = fin_carga - inicio_carga
        
        print(f"\n   ✅ ¡Carga completada con éxito en bloques de 1000!")
        print(f"   ⏱️  Tiempo total: {round(tiempo_total, 2)} segundos ({round(tiempo_total / 60, 2)} minutos)")
        print(f"   📊 Filas por segundo: {round(len(df_producto) / tiempo_total, 2) if tiempo_total > 0 else 0}")
        print(f"   🕐 Fin: {fecha_fin}")
        
        # 9. Crear auditoría
        auditoria = {
            "fecha_auditoria": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "servidor": server,
            "base_datos": database,
            "tabla": "producto",
            "archivo_origen": url_origen,
            "nombre_archivo": os.path.basename(url_origen),
            "filas_cargadas": len(df_producto),
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "tiempo_total_segundos": round(tiempo_total, 2),
            "tiempo_total_minutos": round(tiempo_total / 60, 2),
            "tiempo_por_fila": round(tiempo_total / len(df_producto), 4) if len(df_producto) > 0 else 0,
            "bloques": (len(df_producto) // 1000) + 1 if len(df_producto) > 0 else 0,
            "estado": "EXITOSO",
            "mensaje": f"Carga completada exitosamente en {round(tiempo_total, 2)} segundos"
        }
        
        # 10. Guardar auditoría en 3.final
        print("\n📋 PASO 4: Guardando auditoría...")
        ruta_auditoria = guardar_auditoria_json(auditoria, ruta_destino)
        
        # 11. Resumen final
        print("\n" + "=" * 70)
        print("✅ PROCESO COMPLETADO EXITOSAMENTE")
        print("=" * 70)
        print(f"📂 Datos finales: {ruta_final}")
        print(f"📄 Auditoría: {ruta_auditoria}")
        print(f"⏱️  Tiempo total de carga: {auditoria['tiempo_total_segundos']} segundos")
        print(f"📊 Filas cargadas: {auditoria['filas_cargadas']}")
        print("=" * 70)
        
    except Exception as e:
        # Calcular tiempo aunque haya error
        fin_carga = time.time()
        tiempo_total = fin_carga - inicio_carga
        
        auditoria = {
            "fecha_auditoria": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "servidor": server,
            "base_datos": database,
            "tabla": "producto",
            "archivo_origen": url_origen,
            "nombre_archivo": os.path.basename(url_origen),
            "filas_cargadas": 0,
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