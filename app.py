import streamlit as st
import pandas as pd
from dbfread import DBF
import os

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

st.title("📦 Assistente Riassortimenti")

# Caricamento e unione dei file DBF reali
@st.cache_data(ttl=3600)
def carica_dati_reali():
    # Verifica presenza dei file
    if not (os.path.exists('Articoli.dbf') and os.path.exists('SIT_FILIALI.dbf')):
        return None, "⚠️ File DBF non trovati su GitHub! Assicurati di aver caricato Articoli.dbf e SIT_FILIALI.dbf."
    
    try:
        # Lettura file DBF
        art_table = DBF('Articoli.dbf', encoding='latin1', ignore_missing_memofile=True)
        sit_table = DBF('SIT_FILIALI.dbf', encoding='latin1', ignore_missing_memofile=True)
        
        df_art = pd.DataFrame(iter(art_table))
        df_sit = pd.DataFrame(iter(sit_table))
        
        # Mappatura colonne giacenze
        mappa_depositi = {
            'C_01': 'MAGAZZINO', 'C_02': 'SCIACCA', 'C_03': 'MENFI',
            'C_04': 'MARSALA', 'C_05': 'TRAPANI', 'C_06': 'RAGUSA',
            'C_07': 'SABELLA', 'C_08': 'MAZARA', 'C_09': 'CASA MARKET', 'C_10': 'BM SPORT'
        }
        df_sit.rename(columns=mappa_depositi, inplace=True)
        
        # Unione dei dati sul codice articolo
        col_codice_art = [c for c in df_art.columns if 'cod' in c.lower() or 'art' in c.lower()][0]
        col_codice_sit = [c for c in df_sit.columns if 'cod' in c.lower() or 'art' in c.lower()][0]
        
        df_merged = pd.merge(df_art, df_sit, left_on=col_codice_art, right_on=col_codice_sit, how='inner')
        
        # Calcolo Giacenza Totale
        colonne_depositi = list(mappa_depositi.values())
        colonne_presenti = [c for c in colonne_depositi if c in df_merged.columns]
        df_merged['GIACENZA_TOTALE'] = df_merged[colonne_presenti].sum(axis=1)
        
        return df_merged, None
    except Exception as e:
        return None, f"Errore nella lettura dei file DBF: {str(e)}"

df_completo, errore = carica_dati_reali()

if errore:
    st.error(errore)
    st.info("👉 Per far funzionare l'app con i tuoi dati reali, carica i file 'Articoli.dbf' e 'SIT_FILIALI.dbf' nella cartella del tuo repository GitHub.")
else:
    st.success("✅ Dati DBF caricati e sincronizzati correttamente!")

# Ricerca dinamica sui dati veri
query = st.chat_input("Scrivi una marca, fornitore o tipo di articolo (es. 100 SBADIGLI, DAG, PIGIAMA)...")

if query and df_completo is not None:
    st.subheader(f"Risultati per la ricerca: \"{query}\"")
    
    # Filtro parole chiave cercate dall'utente su tutte le colonne di testo
    query_words = query.lower().split()
    
    # Crea una colonna unica di testo per cercare la descrizione/marca/fornitore
    colonne_testo = df_completo.select_dtypes(include=['object']).columns
    df_completo['TESTO_RICERCA'] = df_completo[colonne_testo].astype(str).agg(' '.join, axis=1).str.lower()
    
    # Applica il filtro
    maschera = df_completo['TESTO_RICERCA'].apply(lambda x: all(word in x for word in query_words))
    risultati = df_completo[maschera]
    
    if risultati.empty:
        st.warning("Nessun articolo trovato per la ricerca inserita.")
    else:
        # Mostra i primi 20 articoli trovati sui dati reali
        dati_export = []
        for _, row in risultati.head(20).iterrows():
            desc = row.get('DESCRIZIONE', row.get('DESCR', 'Articolo senza descrizione'))
            cod = row.get('Codice_art', row.get('CODICE', 'N/D'))
            giac = row.get('GIACENZA_TOTALE', 0)
            
            # Calcolo di esempio del fabbisogno (puoi personalizzarlo)
            consiglio = 12 if giac < 5 else 0 
            
            dati_export.append({
                "Codice": cod,
                "Articolo": desc,
                "Giacenza Totale": giac,
                "Consiglio Ordine": consiglio
            })
            
            if consiglio > 0:
                st.markdown(f"""
                    <div class="card-ordina">
                        <h4>🟢 {desc} (Cod. {cod})</h4>
                        <p>Giacenza Attuale nei 10 punti vendita: <b>{giac} pz</b></p>
                        <h3>👉 CONSIGLIATO ORDINARE: {consiglio} pz</h3>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                    <div class="card-no-ordina">
                        <h4>🔴 {desc} (Cod. {cod})</h4>
                        <p>Giacenza Attuale nei 10 punti vendita: <b>{giac} pz</b></p>
                        <p><b>Scorta sufficiente - Non ordinare</b></p>
                    </div>
                """, unsafe_allow_html=True)
        
        # Pulsanti Stampa ed Export
        col1, col2 = st.columns(2)
        with col1:
            st.components.v1.html(
                '<button onclick="window.print()" style="background-color:#1a73e8;color:white;border:none;padding:12px;border-radius:5px;width:100%;font-weight:bold;cursor:pointer;">🖨️ Stampa Rapida Report A4</button>',
                height=50
            )
        with col2:
            df_exp = pd.DataFrame(dati_export)
            st.download_button("📊 Scarica Excel Ordine", data=df_exp.to_csv(index=False).encode('utf-8'), file_name="ordine_riassortimento.csv", mime="text/csv", use_container_width=True)
