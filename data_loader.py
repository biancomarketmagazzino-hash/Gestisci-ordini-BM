import pandas as pd

FILIALI_MAP = {
    '00': 'Magazzino', '01': 'Menfi', '02': 'Mazara del Vallo', '03': 'Marsala',
    '04': 'Casa Market', '05': 'Sabella', '06': 'Sciacca', '07': 'Ragusa',
    '08': 'Sport Market', '09': 'Trapani'
}

COL_FILIALI_MAP = {
    'C_01': 'Magazzino', 'C_02': 'Sciacca', 'C_03': 'Menfi', 'C_04': 'Marsala',
    'C_05': 'Trapani', 'C_06': 'Ragusa', 'C_07': 'Sabella', 'C_08': 'Mazara del Vallo',
    'C_09': 'Casa Market', 'C_10': 'Sport Market'
}

def load_data():
    # Caricamento file TXT (formato con separatore TAB)
    df_articoli = pd.read_csv("data/ARTICOLI.TXT", sep="\t", on_bad_lines="skip", low_memory=False)
    df_storcar = pd.read_csv("data/STOR_CAR.TXT", sep="\t", on_bad_lines="skip", low_memory=False)
    df_sit = pd.read_csv("data/Sit_filiali.TXT", sep="\t", on_bad_lines="skip", low_memory=False)
    
    return df_articoli, df_storcar, df_sit
