"""
This code collects and calculates the primary characteristics for a ZFER produced 
in AGP SGlass CO. It makes a recollection of all the critical variables in the 
different databases that the company has and combines them into a single dataframe 
that is to be exported to a SQL Server table. 

The use of this code is exclusive for AGP Glass and cannot be sold or 
distributed to other companies. Unauthorized distribution of this code is a 
violation of AGP intellectual property.

Author: Juan Pablo Rodriguez Garcia (jpgarcia@agpglass.com)
"""
import pandas as pd
import parameters
from databases import Databases
from functions import Functions

def main():
    print('Inicializando programa...\n')
    db = Databases()
    functions = Functions(db.engines['conn_smartfa'])
    
    with db.engines['conn_calenda'].connect() as connection:
        df_base = pd.read_sql(parameters.queries['query_cal_acabados'], connection)
        
    df_base = df_base.drop_duplicates(subset=['ZFER'], keep='first').fillna('')
    unique_zfer = df_base['ZFER'].unique().tolist()
    cal_unique_zfer = str(unique_zfer)[1:-1] # This ZFER list filter all of the queries from now on    
    # Create a query for the ZFER_HEAD dataframe - START
    print('Descargando información desde ingeniería (ZFER-HEAD)...\n')   
    df_zfer_head = db.crear_dataframe(parameters.queries['zfer_head'], 'conn_colsap')
    # Create a query for the ZFER_HEAD dataframe - END
    print('Descargando información desde ingeniería (ZFER-BOM)...\n')
    # Create a query for the ZFER_bom dataframe - START
    parameters.create_query(query="""SELECT MATERIAL as ZFER, POSICION, CLASE, CAST(DIMEN_BRUTA_1 as float) as ANCHO, 
                            CAST(DIMEN_BRUTA_2 as float) as LARGO, CAST(CANT_PIEZAS_BRUTA as float) as Area FROM ODATA_ZFER_BOM""",
                            where="""WHERE CLASE like 'Z_VD%' AND CENTRO = 'CO01'""", dict_name='zfer_bom')
    
    with db.engines['conn_colsap'].connect() as connection:
        df_zfer_bom = pd.read_sql(parameters.queries['zfer_bom'], connection)
        
    df_zfer_bom['CLASE'] = df_zfer_bom.apply(lambda x: x['CLASE'][0:-1] if x['CLASE'][-1] == "_" else x['CLASE'], axis=1) #Eliminar lineas al final del texto
    
    # Create a query for the ZFER_bom dataframe - END
    with db.engines['conn_colsap'].connect() as connection:
        df_caracteristicas = pd.read_sql(parameters.queries['query_caracteristicas'], connection)
    
    print('Unificando tablas...\n')
    # Merging the base dataframe into one
    df = pd.merge(df_base.astype({'ZFER': int}), df_zfer_head, on='ZFER', how='left')
    df = pd.merge(df, df_zfer_bom, on='ZFER', how='left').drop_duplicates()
    df = pd.merge(df, df_caracteristicas, on='ZFER', how='left')
    df['ClaveModelo'] = df['POSICION'].map(parameters.dict_clavesmodelo)
    df = df.fillna({'BordePintura': '', 'BordePaquete': '', 'ClaveModelo':'', 'PartShort':'', 'ENG_GeometricDiffs':'', 'ZFOR': 0, 'C_Caja': 0, 'C_Chaflan': 0, 'Tiempo': 0})
    df = df.dropna(subset=['ANCHO', 'LARGO'])
    df = functions.definir_cantos(df)    
    df = functions.agregar_pasadas(df)
    df = df.apply(functions.tiempo_acabado, axis=1)
    df = df.reset_index()
    df2 = df.drop(['BrilloP', 'AcabadoPlano', 'BrilloC', 'AcabadoC', 'BiselBrillo', 
                   'BiselP2', 'BiselP1', 'Chaflan2', 'Chaflan1', 'Desbaste', 'POSICION', 'index'], axis=1)
    df2 = df2.rename({'PartShort': 'Parte', 'CLASE': 'Material', 'ANCHO': 'Ancho', 
                      'LARGO': 'Largo', 'Tiempo': 'TiempoMecanizado', 
                      'ENG_BehaviorDiffs': 'BehaviorDiffs',
                      'ENG_GeometricDiffs': 'GeometricDiffs',
                      }, axis=1)
    df2 = df2.drop_duplicates(subset=['ZFER', 'ClaveModelo'], keep='first')
    df2 = df2.fillna({'BordePintura': '', 'BordePaquete': '', 'ClaveModelo':'', 'Operacion1':'', 'Operacion2':'', 'ZFOR': 0, 'Caja': 0, 'Tiempo': 0})
    df2 = df2.astype({'ZFER': int, 'ZFOR': int, 'Material': str, 'Ancho': str,
                      'Largo': str, 'Area': str, 'ClaveModelo': str, 'Perimetro': str, 'TiempoMecanizado': float})
    df2.index = df2.index.rename('ID')
    return df2