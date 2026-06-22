data_backus/
│
├── data/                   # Directorio de datos (¡Asegúrate de ignorarlo en Git!)
│   ├── raw/                # Aquí van los CSV originales que te dio Backus.
│   ├── processed/          # Datos intermedios limpios o transformados.
│   └── final/              # El output final, listo para dashboards o inserción.
│
├── notebooks/              # Jupyter Notebooks (Solo para exploración inicial)
│   └── 01_eda_inicial.ipynb # Análisis exploratorio de los CSV (EDA).
│
├── src/                    # El corazón de tu ETL (Código fuente modular)
│   ├── __init__.py
│   ├── extract.py          # Lógica para leer los CSVs desde data/raw/.
│   ├── transform.py        # Limpieza, cruces y reglas de negocio (ej. usando Pandas).
│   ├── load.py             # Lógica para insertar a BD (SQL) o guardar en data/final/.
│   ├── main.py             # Script principal que orquesta: Extract -> Transform -> Load.
│   └── config.py           # Rutas, variables de entorno y credenciales (sin hardcodear).
│
├── sql/                    # Consultas o scripts de base de datos
│   ├── ddl_tables.sql      # Creación de tablas de destino.
│   └── queries.sql         # Cualquier query compleja que necesites ejecutar.
│
├── .gitignore              # Archivo crítico: ignora la carpeta data/, __pycache__, .env, etc.
├── .env.example            # Plantilla para que el evaluador sepa qué variables de entorno necesitas.
├── requirements.txt        # Tus dependencias precisas (pandas, sqlalchemy, psycopg2, etc.).
├── Dockerfile              # Excelente plus para empaquetar el ETL y garantizar que corra en cualquier máquina.
└── README.md               # Tu carta de presentación.