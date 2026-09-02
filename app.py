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

@st.cache_data(ttl=3600)
def carica_e_elabora_dbf():
    # Verifica presenza file
    if not (os.path.exists('Articoli.dbf') and os.path.exists('SIT_FILIALI.dbf')):
        return None, "⚠️ File DBF non rilevati. Controlla che siano stati caricati con GitHub Desktop."
    
    try:
        # Caricamento DBF
        art_df = pd.DataFrame(iter(DBF('Articoli.dbf', encoding='latin1', ignore_missing_memofile=True)))
        sit_df = pd.DataFrame(iter(DBF('SIT_FILIALI.dbf', encoding='latin1', ignore_missing_memofile=True)))
        
        # Gestione storico venduto se presente
        if os.path.exists('storcar.dbf'):
            stor_df = pd.DataFrame(iter(DBF('storcar.dbf', encoding='latin1', ignore_missing_memofile=True)))
        else:
            stor_df = pd.DataFrame()

        # Mappatura depositi
        mappa_depositi = {
            'C_01': 'MAGAZZINO', 'C_02': 'SCIACCA', 'C_03': 'MENFI',
            'C_04': 'MARSALA', 'C_05': 'TRAPANI', 'C_06': 'RAGUSA',
            'C_07': 'SABELLA', 'C_08': 'MAZARA', 'C_09': 'CASA MARKET', 'C_10': 'BM SPORT'
        }
        sit_df.rename(columns=mappa_depositi, inplace=True)
        
        # Identificazione colonne chiave per la fusione
        col_art = [c for c in art_df.columns if 'cod' in c.lower() or 'art' in c.lower()][0]
        col_sit = [c for c in sit_df.columns if 'cod' in c.lower() or 'art' in c.lower()][0]
        
        # Unione Anagrafica + Giacenze Filiali
        df_merged = pd.merge(art_df, sit_df, left_on=col_art, right_on=col_sit, how='inner')
        
        # Calcolo Giacenza Totale attuale nei negozi
        col_presenti = [c for c in mappa_depositi.values() if c in df_merged.columns]
        df_merged['GIACENZA_TOTALE'] = df_merged[col_presenti].apply(pd.to_numeric, errors='coerce').fillna(0).sum(axis=1)
        
        # Calcolo Venduto da storcar se disponibile
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
        return None, f"Errore durante l'elaborazione dei dati: {str(e)}"

df, errore = carica_e_elabora_dbf()

if errore:
    st.error(errore)
else:
    st.success("✅ Dati reali sincronizzati con successo dai file DBF!")

query = st.chat_input("Esempio: Quante calze invernali abbiamo venduto della marca DAG?")

if query and df is not None:
    parole_chiave = query.lower().split()
    
    # Creazione colonna di testo unificata per la ricerca
    colonne_txt = df.select_dtypes(include=['object']).columns
    df['TESTO_RICERCA'] = df[colonne_txt].astype(str).agg(' '.join, axis=1).str.lower()
    
    # Filtro dinamico su tutte le parole digitate dall'utente
    maschera = df['TESTO_RICERCA'].apply(lambda txt: all(p in txt for p in parole_chiave))
    risultati = df[maschera].copy()
    
    if risultati.empty:
        st.warning("⚠️ Nessun articolo trovato con i criteri cercati. Prova ad usare termini più generici o il codice del fornitore.")
    else:
        # Ordinamento dal più venduto al meno venduto
        if 'VENDUTO_STAGIONE' in risultati.columns:
            risultati = risultati.sort_values(by='VENDUTO_STAGIONE', ascending=False)
            
        st.subheader(f"📊 Analisi Vendite e Riassortimento ({len(risultati)} articoli trovati)")
        
        dati_export = []
        for _, row in risultati.head(30).iterrows():
            desc = row.get('DESCRIZIONE', row.get('DESCR', 'Articolo'))
            cod = row.get('Codice_art', row.get('CODICE', 'N/D'))
            giac = int(row.get('GIACENZA_TOTALE', 0))
            venduto = int(row.get('VENDUTO_STAGIONE', 0))
            
            # Calcolo proposta ordine: Venduto - Giacenza Attuale
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
                        <p>📦 Venduto Registrato: <b>{venduto} pz</b> | Giacenza Attuale nei Negozi: <b>{giac} pz</b></p>
                        <h3>👉 CONSIGLIO RIASSORTIMENTO: Ordina {proposta} pz</h3>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                    <div class="card-no-ordina">
                        <h4>🔴 {desc} (Cod. {cod})</h4>
                        <p>📦 Venduto Registrato: <b>{venduto} pz</b> | Giacenza Attuale nei Negozi: <b>{giac} pz</b></p>
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
