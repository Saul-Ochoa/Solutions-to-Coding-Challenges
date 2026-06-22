import os
import pandas as pd
import pyodbc
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import json
import time
from datetime import datetime

class CargadorSQL:
    """Clase para cargar datos limpios a SQL Server"""
    
    def __init__(self, ruta_destino=None):
        if ruta_destino is None:
            self.ruta_destino = r"D:\Github-Time\Solutions-to-Coding-Challenges\Data_Backus\data\3.final"
        else:
            self.ruta_destino = ruta_destino
        
        # Crear carpeta de destino si no existe
        os.makedirs(self.ruta_destino, exist_ok=True)
        
        # Cargar variables de entorno
        load_dotenv()
        self.server = os.getenv('DB_SERVER')
        self.database = os.getenv('DB_DATABASE')
        
        # Validar que las variables existan
        if not self.server or not self.database:
            raise ValueError("❌ No se encontraron las variables de entorno DB_SERVER o DB_DATABASE.")
    
    def procesar_cliente(self, ruta_archivo):
        """
        Procesa el archivo de clientes_cleaned.csv y lo prepara para SQL Server
        """
        print(f"\n📂 Cargando archivo: {ruta_archivo}")
        
        # 1. Carga
        df = pd.read_csv(ruta_archivo, sep=',')
        print(f"   ✅ Archivo cargado: {len(df)} filas, {len(df.columns)} columnas")
        
        # Transformacion region
        df['region'] = df['region'].str.strip()
        cambios_region = {
        'lima-c': 'lima centro',
        'lima-n': 'lima norte',
        'lima-s': 'lima sur'}
        
        df['region'] = df['region'].replace(cambios_region)
                
        # 2. Seleccionar columnas necesarias
        cols_necesarias = ['cliente_id', 'nombre_comercial', 'canal', 'region', 'distrito', 'fecha_alta','estado']
        df = df[cols_necesarias].copy()
        
        # 3. Renombrar
        # df = df.rename(columns={'fecha_alta_original': 'fecha_alta', 'estado_original': 'estado'})
        
        # 4. Procesamiento de fechas 
        df['fecha_alta'] = pd.to_datetime(df['fecha_alta'], errors='coerce', format='%Y-%m-%d')
        
        # 5. Metadatos en JSON
        nombre_archivo = os.path.basename(ruta_archivo)
        numero_filas = len(df)
        fecha_carga_str = pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')
        
        diccionario_metadatos = {
            "nombre_archivo": nombre_archivo,
            "numero_filas": numero_filas,
            "fecha_carga": fecha_carga_str
        }
        
        df['metadatos_json'] = json.dumps(diccionario_metadatos)
        
        # 6. Columnas de auditoría
        df['source_file'] = nombre_archivo
        df['load_date'] = pd.Timestamp.now()
        df['update_date'] = pd.Timestamp.now()
        df['loaded_by'] = 'proceso_etl_python'
        df['is_active'] = 1
        
        print(f"   ✅ Datos procesados: {len(df)} filas listas para carga")
        
        return df
    
    def guardar_datos_finales(self, df, nombre_archivo="clientes_final.csv"):
        """
        Guarda los datos procesados en la carpeta 3.final
        """
        ruta_completa = os.path.join(self.ruta_destino, nombre_archivo)
        df.to_csv(ruta_completa, index=False, encoding='utf-8')
        print(f"   💾 Datos guardados en: {ruta_completa}")
        return ruta_completa
    
    def cargar_a_sql_server(self, df, tabla='cliente'):
        """
        Carga los datos a SQL Server y mide el tiempo
        Retorna un diccionario con la auditoría de la carga
        """
        # Iniciar temporizador
        inicio_carga = time.time()
        fecha_inicio = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"\n🔄 Iniciando carga a SQL Server...")
        print(f"   📊 Tabla: {tabla}")
        print(f"   📋 Filas a cargar: {len(df)}")
        print(f"   🕐 Inicio: {fecha_inicio}")
        
        try:
            # Crear cadena de conexión
            connection_string = f"mssql+pyodbc://{self.server}/{self.database}?driver=ODBC+Driver+17+for+SQL+Server&trusted_connection=yes"
            engine = create_engine(connection_string)
            
            # Probar conexión
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                print("   ✅ Conexión exitosa a SQL Server")
            
            # Cargar datos en bloques
            df.to_sql(
                name=tabla,
                con=engine,
                if_exists='append',
                index=False,
                chunksize=1000
            )
            
            # Calcular tiempo de carga
            fin_carga = time.time()
            fecha_fin = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            tiempo_total = fin_carga - inicio_carga
            
            # Resultados
            resultado = {
                "exito": True,
                "tabla": tabla,
                "filas_cargadas": len(df),
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                "tiempo_total_segundos": round(tiempo_total, 2),
                "tiempo_total_minutos": round(tiempo_total / 60, 2),
                "tiempo_por_fila": round(tiempo_total / len(df), 4) if len(df) > 0 else 0,
                "bloques": (len(df) // 1000) + 1 if len(df) > 0 else 0,
                "estado": "EXITOSO",
                "mensaje": f"Carga completada exitosamente en {round(tiempo_total, 2)} segundos"
            }
            
            print(f"\n   ✅ ¡Carga completada con éxito!")
            print(f"   ⏱️  Tiempo total: {resultado['tiempo_total_segundos']} segundos ({resultado['tiempo_total_minutos']} minutos)")
            print(f"   📊 Filas por segundo: {round(len(df) / tiempo_total, 2) if tiempo_total > 0 else 0}")
            
            return resultado
            
        except Exception as e:
            # Calcular tiempo aunque haya error
            fin_carga = time.time()
            tiempo_total = fin_carga - inicio_carga
            
            resultado = {
                "exito": False,
                "tabla": tabla,
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
            
            return resultado
    
    def guardar_auditoria_json(self, auditoria, nombre_archivo="auditoria_carga_cliente.json"):
        """
        Guarda la auditoría de la carga en un archivo JSON
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_completo = f"auditoria_carga_cliente_{timestamp}.json"
        ruta_completa = os.path.join(self.ruta_destino, nombre_completo)
        
        auditoria_completa = {
            "fecha_auditoria": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "servidor": self.server,
            "base_datos": self.database,
            **auditoria
        }
        
        with open(ruta_completa, "w", encoding="utf-8") as f:
            json.dump(auditoria_completa, f, indent=4, ensure_ascii=False)
        
        print(f"   📄 Auditoría guardada en: {ruta_completa}")
        return ruta_completa
    
    def ejecutar_carga(self, ruta_archivo=None, tabla='cliente'):
        """
        Ejecuta el proceso completo de carga:
        1. Carga y procesa los datos
        2. Guarda en 3.final
        3. Carga a SQL Server
        4. Genera auditoría
        """
        print("=" * 70)
        print("🚀 INICIANDO CARGA A SQL SERVER")
        print("=" * 70)
        
        # 1. Definir archivo de origen
        if ruta_archivo is None:
            ruta_archivo = r'D:\Github-Time\Solutions-to-Coding-Challenges\Data_Backus\data\2.processed\clientes_cleaned.csv'
        
        # 2. Verificar que el archivo existe
        if not os.path.exists(ruta_archivo):
            print(f"❌ Error: El archivo '{ruta_archivo}' no existe")
            return None
        
        # 3. Procesar datos
        print("\n📊 PASO 1: Procesando datos...")
        df = self.procesar_cliente(ruta_archivo)
        
        # 4. Guardar datos finales
        print("\n💾 PASO 2: Guardando datos finales...")
        ruta_final = self.guardar_datos_finales(df)
        
        # 5. Cargar a SQL Server
        print("\n☁️  PASO 3: Cargando a SQL Server...")
        auditoria = self.cargar_a_sql_server(df, tabla)
        
        # 6. Guardar auditoría
        print("\n📋 PASO 4: Guardando auditoría...")
        ruta_auditoria = self.guardar_auditoria_json(auditoria)
        
        # 7. Resumen final
        print("\n" + "=" * 70)
        print("✅ PROCESO COMPLETADO EXITOSAMENTE")
        print("=" * 70)
        print(f"📂 Datos finales: {ruta_final}")
        print(f"📄 Auditoría: {ruta_auditoria}")
        print(f"⏱️  Tiempo total de carga: {auditoria.get('tiempo_total_segundos', 0)} segundos")
        print(f"📊 Filas cargadas: {auditoria.get('filas_cargadas', 0)}")
        print(f"📋 Estado: {auditoria.get('estado', 'DESCONOCIDO')}")
        
        return {
            "df": df,
            "ruta_final": ruta_final,
            "auditoria": auditoria,
            "ruta_auditoria": ruta_auditoria
        }


# ============================================
# FUNCIÓN MAIN
# ============================================

def main():
    """
    Función principal que ejecuta la carga a SQL Server
    """
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Carga los datos de clientes a SQL Server'
    )
    
    parser.add_argument(
        '--archivo',
        type=str,
        default=r'D:\Github-Time\Solutions-to-Coding-Challenges\Data_Backus\data\2.processed\clientes_cleaned.csv',
        help='Ruta del archivo CSV a cargar'
    )
    
    parser.add_argument(
        '--destino',
        type=str,
        default=r'D:\Github-Time\Solutions-to-Coding-Challenges\Data_Backus\data\3.final',
        help='Ruta de la carpeta donde guardar los archivos finales'
    )
    
    parser.add_argument(
        '--tabla',
        type=str,
        default='cliente',
        help='Nombre de la tabla en SQL Server'
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
        print(f"📂 Archivo de origen: {args.archivo}")
        print(f"📁 Carpeta de destino: {args.destino}")
        print(f"📋 Tabla destino: {args.tabla}")
        print("=" * 60)
    
    # Verificar que el archivo existe
    if not os.path.exists(args.archivo):
        print(f"❌ Error: El archivo '{args.archivo}' no existe")
        return 1
    
    try:
        # Inicializar cargador
        cargador = CargadorSQL(args.destino)
        
        # Ejecutar carga
        resultado = cargador.ejecutar_carga(args.archivo, args.tabla)
        
        if resultado and args.verbose:
            print("\n📊 DETALLES DEL PROCESO:")
            print(f"   Filas procesadas: {len(resultado['df'])}")
            print(f"   Columnas: {list(resultado['df'].columns)}")
            print(f"   Auditoría: {json.dumps(resultado['auditoria'], indent=2, ensure_ascii=False)}")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Error en el proceso: {e}")
        return 1


# ============================================
# EJECUCIÓN
# ============================================

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)