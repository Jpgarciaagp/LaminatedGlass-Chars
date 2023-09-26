
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
    functions = Functions(db.conns['conn_smartfa'])
    df_base = pd.read_sql(parameters.queries['query_acabados'], db.conns['conn_genesis'])
    # Create a query for the ZFER_HEAD dataframe - START
    print('Descargando información desde ingeniería (ZFER-HEAD)...\n')   
    df_zfer_head = pd.read_sql(parameters.queries['zfer_head'], db.conns['conn_colsap']).drop_duplicates('ZFER', keep='first')
    # Create a query for the ZFER_HEAD dataframe - END
    print('Descargando información desde ingeniería (ZFER-BOM)...\n')
    # Create a query for the ZFER_bom dataframe - START
    parameters.create_query(query="""SELECT MATERIAL as ZFER, POSICION, CLASE, CAST(DIMEN_BRUTA_1 as float) as ANCHO, 
                            CAST(DIMEN_BRUTA_2 as float) as LARGO FROM ODATA_ZFER_BOM""",
                            where="""WHERE CLASE like 'Z_VD%' AND CENTRO = 'CO01'""", dict_name='zfer_bom')    
    df_zfer_bom = pd.read_sql(parameters.queries['zfer_bom'], db.conns['conn_colsap'])
    df_zfer_bom['CLASE'] = df_zfer_bom.apply(lambda x: x['CLASE'][0:-1] if x['CLASE'][-1] == "_" else x['CLASE'], axis=1) #Eliminar lineas al final del texto
    # Create a query for the ZFER_bom dataframe - END
    print('Unificando tablas...\n')
    # Merging the base dataframe into one
    df = pd.merge(df_base.astype({'ZFER': int}), df_zfer_head, on='ZFER', how='outer')
    df = pd.merge(df, df_zfer_bom, on='ZFER', how='outer').drop_duplicates()
    df['ClaveModelo'] = df['POSICION'].map(parameters.dict_clavesmodelo)
    df = df.fillna({'BordePintura': '', 'BordePaquete': '', 'ClaveModelo':'', 'ZFOR': 0, 'Caja': 0, 'Tiempo': 0})    
    df = functions.definir_cantos(df)    
    df = df.apply(functions.agregar_pasadas, axis=1)
    df = df.apply(functions.tiempo_acabado, axis=1)
    df = df.reset_index()
    df2 = df.drop(['Cambios', 'Area', 'index', 'Posicion', 'CantoP'], axis=1)
    df2 = df2.rename({'POSICION': 'Posicion', 'CLASE': 'Material', 'ANCHO': 'Ancho', 'LARGO': 'Largo', 'Tiempo': 'TiempoMecanizado'}, axis=1)
    df2 = df2.drop_duplicates(subset=['ZFER', 'ClaveModelo'], keep='first')
    df2 = df2.fillna({'BordePintura': '', 'BordePaquete': '', 'ClaveModelo':'', 'Operacion1':'', 'Operacion2':'', 'ZFOR': 0, 'Caja': 0, 'Tiempo': 0})
    df2 = df2.astype({'ZFER': int, 'ZFOR': int, 'Posicion': str, 'Material': str, 'Ancho': str,
                      'Largo': str, 'ClaveModelo': str, 'Perimetro': str, 'TiempoMecanizado': float,
                      'BrilloC': bool, 'BrilloP': bool, 'Bisel': bool, 'CantoC': bool, 'CantoP': bool})
    df2 = df2.rename({'ENG_BehaviorDiffs': 'BehaviorDiffs', 'ENG_GeometricDiffs': 'GeometricDiffs'}, axis=1)
    df2.index = df2.index.rename('ID')
    return df2