import streamlit as st
import pandas as pd
from dbfread import DBF
import os
import struct

st.set_page_config(page_title="Riassortimento Bianco Market", page_icon="📦", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    .card-ordina {
        background-color: #e6f4ea;
        border-left: 6px solid #34a853;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    .card-no-ordina {
        background-color: #fce8e6;
        border-left: 6px solid #ea4335;
        padding: 15px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    @media print {
        .stChatInput, .stButton, header, footer, .no-print, [data-testid="stSidebar"] {
            display: none !important;
        }
        body { background-color: white; }
    }
    </style>
""", unsafe_allow_html=True)

st.title("📦 Assistente Riassortimenti Bianco Market")

def trova_file(nome_target):
    for f in os.listdir('.'):
        if f.lower() == nome_target.lower():
            return f
    return None

def carica_dbf_robusto(filepath):
    """Tenta la lettura con dbfread e, in caso di errore di buffer, passa a un parser di ripiego."""
    if not filepath or not os.path.exists(filepath):
        return pd.DataFrame()
    
    # Tentativo 1: Lettura standard tollerante
    try:
        table = DBF(filepath, encoding='latin1', ignore_missing_memofile=True, char_decode_errors='ignore')
        return pd.DataFrame(iter(table))
    except Exception:
        pass

    # Tentativo 2: Lettura binaria tollerante per header personalizzati/FoxPro
    try:
        with open(filepath, 'rb') as f:
            data = f.read()
            if len(data) < 32:
                return pd.DataFrame()
            
            # Estrazione parametri header DBF
            num_rec, header_len, rec_len = struct.unpack('<IHH', data[4:12])
            
            fields = []
            offset = 32
            while offset < header_len - 1:
                field_data = data[offset:offset+32]
                if len(field_data) < 32 or field_data[0] == 0x0D:
                    break
                name = field_data[:11].replace(b'\x00', b'').decode('latin1', errors='ignore').strip()
                f_type = chr(field_data[11])
                f_len = field_data[16]
                if name:
                    fields.append((name, f_type, f_len))
                offset += 32
            
            records = []
            curr = header_len
            for _ in range(num_rec):
                if curr + rec_len > len(data):
                    break
                rec = data[curr:curr+rec_len]
                if rec and rec[0] != 0x2A: # Salva i record non cancellati
                    row = {}
                    r_off = 1
                    for name, f_type, f_len in fields:
                        val = rec[r_off:r_off+f_len].decode('latin1', errors='ignore').strip()
                        row[name] = val
                        r_off += f_len
                    records.append(row)
                curr += rec_len
            return pd.DataFrame(records)
    except Exception as e:
        st.warning(f"⚠️ Impossibile elaborare {filepath}: {str(e)}")
        return pd.DataFrame()

@st.cache_data(ttl=3600)
def elabora_dati():
    file_art = trova_file('ARTICOLI.DBF')
    file_sit = trova_file('Sit_filiali.DBF')
    file_stor = trova_file('STOR_CAR.DBF')
    
    if not file_art or not file_sit:
        return None, f"⚠️ File non trovati nel repository. File presenti: {os.listdir('.')}"
    
    art_df = carica_dbf_robusto(file_art)
    sit_df = carica_dbf_robusto(file_sit)
    stor_df = carica_dbf_robusto(file_stor)
    
    if art_df.empty or sit_df.empty:
        return None, "❌ Errore nella lettura della struttura dei file DBF. Verificare che i file non siano in uso da altri programmi."

    try:
        mappa_depositi = {
            'C_01': 'MAGAZZINO', 'C_02': 'SCIACCA', 'C_03': 'MENFI',
            'C_04': 'MARSALA', 'C_05': 'TRAPANI', 'C_06': 'RAGUSA',
            'C_07': 'SABELLA', 'C_08': 'MAZARA', 'C_09': 'CASA MARKET', 'C_10': 'BM SPORT'
        }
        sit_df.rename(columns=mappa_depositi, inplace=True)
        
        col_art = [c for c in art_df.columns if 'cod' in c.lower() or 'art' in c.lower()][0]
        col_sit = [c for c in sit_df.columns if 'cod' in c.lower() or 'art' in c.lower()][0]
        
        df_merged = pd.merge(art_df, sit_df, left_on=col_art, right_on=col_sit, how='inner')
        
        col_presenti = [c for c in mappa_depositi.values() if c in df_merged.columns]
        df_merged['GIACENZA_TOTALE'] = df_merged[col_presenti].apply(pd.to_numeric, errors='coerce').fillna(0).sum(axis=1)
        
        if not stor_df.empty:
            col_stor_cod = [c for c in stor_df.columns if 'cod' in c.lower() or 'art' in c.lower()][0]
            col_qta = [c for c in stor_df.columns if 'qta' in c.lower() or 'quant' in c.lower() or 'mov' in c.lower()]
            col_qta_nome = col_qta[0] if col_qta else stor_df.columns[-1]
            
            stor_df[col_qta_nome] = pd.to_numeric(stor_df[col_qta_nome], errors='coerce').fillna(0)
            venduto_agg = stor_df.groupby(col_stor_cod)[col_qta_nome].sum().reset_index()
            venduto_agg.columns = [col_art, 'VENDUTO_STAGIONE']
            
            df_merged = pd.merge(df_merged, venduto_agg, on=col_art, how='left')
            df_merged['VENDUTO_STAGIONE'] = df_merged['VENDUTO_STAGIONE'].fillna(0)
        else:
            df_merged['VENDUTO_STAGIONE'] = 0

        return df_merged, None
    except Exception as e:
        return None, f"Errore nell'elaborazione: {str(e)}"

df, errore = elabora_dati()

if errore:
    st.error(errore)
else:
    st.success("✅ File DBF elaborati con successo!")

query = st.chat_input("Scrivi qui la marca, il fornitore o l'articolo...")

if query and df is not None:
    parole_chiave = query.lower().split()
    colonne_txt = df.select_dtypes(include=['object']).columns
    df['TESTO_RICERCA'] = df[colonne_txt].astype(str).agg(' '.join, axis=1).str.lower()
    
    maschera = df['TESTO_RICERCA'].apply(lambda txt: all(p in txt for p in parole_chiave))
    risultati = df[maschera].copy()
    
    if risultati.empty:
        st.warning("⚠️ Nessun articolo trovato.")
    else:
        if 'VENDUTO_STAGIONE' in risultati.columns:
            risultati = risultati.sort_values(by='VENDUTO_STAGIONE', ascending=False)
            
        st.subheader(f"📊 Articoli trovati: {len(risultati)}")
        
        dati_export = []
        for _, row in risultati.head(40).iterrows():
            desc = row.get('DESCRIZIONE', row.get('DESCR', row.get('ARTICOLO', 'Articolo')))
            cod = row.get('Codice_art', row.get('CODICE', 'N/D'))
            giac = int(row.get('GIACENZA_TOTALE', 0))
            venduto = int(row.get('VENDUTO_STAGIONE', 0))
            proposta = max(0, venduto - giac) if venduto > 0 else (10 if giac == 0 else 0)
            
            dati_export.append({
                "Codice": cod,
                "Descrizione": desc,
                "Venduto": venduto,
                "Giacenza Totale": giac,
                "Proposta Ordine": proposta
            })
            
            if proposta > 0:
                st.markdown(f"""
                    <div class="card-ordina">
                        <h4>🟢 {desc} (Cod. {cod})</h4>
                        <p>📦 Venduto Registrato: <b>{venduto} pz</b> | Giacenza Totale: <b>{giac} pz</b></p>
                        <h3>👉 CONSIGLIO RIASSORTIMENTO: Ordina {proposta} pz</h3>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                    <div class="card-no-ordina">
                        <h4>🔴 {desc} (Cod. {cod})</h4>
                        <p>📦 Venduto Registrato: <b>{venduto} pz</b> | Giacenza Totale: <b>{giac} pz</b></p>
                        <p><b>❌ NON ORDINARE: Scorta sufficiente</b></p>
                    </div>
                """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.components.v1.html(
                '<button onclick="window.print()" style="background-color:#1a73e8;color:white;border:none;padding:12px;border-radius:5px;width:100%;font-weight:bold;cursor:pointer;">🖨️ Stampa Rapida Report A4</button>',
                height=50
            )
        with col2:
            df_exp = pd.DataFrame(dati_export)
            st.download_button("📊 Scarica Excel Ordine", data=df_exp.to_csv(index=False).encode('utf-8'), file_name="ordine_fornitore.csv", mime="text/csv", use_container_width=True)
