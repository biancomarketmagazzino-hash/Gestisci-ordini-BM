import streamlit as st
import pandas as pd
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

st.title("📦 Assistente Riassortimenti Bianco Market")

def trova_file_csv(nomi_possibili):
    files_presenti = os.listdir('.')
    for nome in nomi_possibili:
        for f in files_presenti:
            if f.lower() == nome.lower():
                return f
    return None

def leggi_csv_flessibile(percorso):
    if not percorso or not os.path.exists(percorso):
        return pd.DataFrame()
    try:
        try:
            return pd.read_csv(percorso, sep=',', encoding='latin1', low_memory=False)
        except Exception:
            return pd.read_csv(percorso, sep=';', encoding='latin1', low_memory=False)
    except Exception as e:
        st.error(f"Errore nella lettura del file {percorso}: {e}")
        return pd.DataFrame()

# Individuazione file
file_art = trova_file_csv(['ARTICOLI.csv', 'ARTICOLI.CSV'])
file_sit = trova_file_csv(['SITUAZIONI FILIALI.csv', 'Sit_filiali.csv', 'SITUAZIONI_FILIALI.csv'])
file_stor = trova_file_csv(['STORICO.csv', 'STOR_CAR.csv'])

if not file_art or not file_sit:
    st.warning("⚠️ Impossibile trovare i file principali. Verificare che 'ARTICOLI.csv' e 'SITUAZIONI FILIALI.csv' siano presenti sul repository.")
else:
    df_art = leggi_csv_flessibile(file_art)
    df_sit = leggi_csv_flessibile(file_sit)
    df_stor = leggi_csv_flessibile(file_stor) if file_stor else pd.DataFrame()

    if df_art.empty or df_sit.empty:
        st.error("❌ Errore durante il caricamento dei dati. Verificare il formato dei file CSV.")
    else:
        st.success("✅ Dati di magazzino e vendite sincronizzati con successo!")

        # Normalizzazione codici articolo
        col_art_cod = [c for c in df_art.columns if 'cod' in c.lower()][0]
        col_sit_cod = [c for c in df_sit.columns if 'cod' in c.lower()][0]

        df_art[col_art_cod] = df_art[col_art_cod].astype(str).str.strip()
        df_sit[col_sit_cod] = df_sit[col_sit_cod].astype(str).str.strip()

        # Mappatura Depositi / Negozi
        mappa_depositi = {
            'C_01': 'MAGAZZINO', 'C_02': 'SCIACCA', 'C_03': 'MENFI',
            'C_04': 'MARSALA', 'C_05': 'TRAPANI', 'C_06': 'RAGUSA',
            'C_07': 'SABELLA', 'C_08': 'MAZARA', 'C_09': 'CASA MARKET', 'C_10': 'BM SPORT'
        }
        df_sit.rename(columns=mappa_depositi, inplace=True)

        # Unione Anagrafica e Situazione Filiali
        df_merged = pd.merge(df_art, df_sit, left_on=col_art_cod, right_on=col_sit_cod, how='left')

        # Calcolo Giacenza Totale
        col_presenti = [c for c in mappa_depositi.values() if c in df_merged.columns]
        if col_presenti:
            df_merged['GIACENZA_TOTALE'] = df_merged[col_presenti].apply(pd.to_numeric, errors='coerce').fillna(0).sum(axis=1)
        else:
            col_esi = [c for c in df_art.columns if 'esisten' in c.lower() or 'giac' in c.lower()]
            df_merged['GIACENZA_TOTALE'] = pd.to_numeric(df_merged[col_esi[0]], errors='coerce').fillna(0) if col_esi else 0

        # Elaborazione Venduto da STORICO
        if not df_stor.empty:
            col_stor_cod = [c for c in df_stor.columns if 'cod' in c.lower()][0]
            col_qta = [c for c in df_stor.columns if 'qta' in c.lower() or 'quant' in c.lower()][0]

            df_stor[col_stor_cod] = df_stor[col_stor_cod].astype(str).str.strip()
            df_stor[col_qta] = pd.to_numeric(df_stor[col_qta], errors='coerce').fillna(0)

            venduto_agg = df_stor.groupby(col_stor_cod)[col_qta].sum().reset_index()
            venduto_agg.columns = [col_art_cod, 'VENDUTO_STAGIONE']

            df_merged = pd.merge(df_merged, venduto_agg, on=col_art_cod, how='left')
            df_merged['VENDUTO_STAGIONE'] = df_merged['VENDUTO_STAGIONE'].fillna(0)
        else:
            df_merged['VENDUTO_STAGIONE'] = 0

        # Campo Ricerca
        query = st.chat_input("Scrivi una marca, fornitore o articolo (es. STROFINACCI, BASSETTI, TOVAGLIA)...")

        if query:
            parole_chiave = query.lower().split()
            colonne_txt = df_merged.select_dtypes(include=['object']).columns
            
            # Applicazione corretta per concatenazione righe senza errore di tipo
            df_merged['TESTO_RICERCA'] = df_merged[colonne_txt].astype(str).apply(lambda row: ' '.join(row), axis=1).str.lower()

            maschera = df_merged['TESTO_RICERCA'].apply(lambda txt: all(p in txt for p in parole_chiave))
            risultati = df_merged[maschera].copy()

            if risultati.empty:
                st.warning("⚠️ Nessun articolo trovato.")
            else:
                st.subheader(f"📊 Articoli trovati: {len(risultati)}")

                dati_export = []
                col_desc = [c for c in df_art.columns if 'desc' in c.lower() or 'art' in c.lower()][0]

                for _, row in risultati.head(50).iterrows():
                    desc = str(row.get(col_desc, 'Articolo')).strip()
                    cod = str(row.get(col_art_cod, 'N/D')).strip()
                    giac = int(row.get('GIACENZA_TOTALE', 0))
                    venduto = int(row.get('VENDUTO_STAGIONE', 0))
                    
                    col_scorta = [c for c in df_art.columns if 'scorta' in c.lower()]
                    s_scorta = int(row.get(col_scorta[0], 0)) if col_scorta else 0

                    # Calcolo Proposta Ordine
                    if venduto > 0:
                        proposta = max(0, venduto - giac)
                    elif giac <= s_scorta:
                        proposta = max(1, s_scorta - giac) if s_scorta > 0 else 5
                    else:
                        proposta = 0

                    dati_export.append({
                        "Codice": cod,
                        "Descrizione": desc,
                        "Venduto": venduto,
                        "Giacenza Totale": giac,
                        "Scorta Minima": s_scorta,
                        "Proposta Ordine": proposta
                    })

                    if proposta > 0:
                        st.markdown(f"""
                            <div class="card-ordina">
                                <h4>🟢 {desc} (Cod. {cod})</h4>
                                <p>📦 Venduto Registrato: <b>{venduto} pz</b> | Giacenza Totale: <b>{giac} pz</b> | Scorta Minima: <b>{s_scorta} pz</b></p>
                                <h3>👉 CONSIGLIO RIASSORTIMENTO: Ordina {proposta} pz</h3>
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                            <div class="card-no-ordina">
                                <h4>🔴 {desc} (Cod. {cod})</h4>
                                <p>📦 Venduto Registrato: <b>{venduto} pz</b> | Giacenza Totale: <b>{giac} pz</b> | Scorta Minima: <b>{s_scorta} pz</b></p>
                                <p><b>❌ NON ORDINARE: Scorta sufficiente</b></p>
                            </div>
                        """, unsafe_allow_html=True)

                col1, col2 = st.columns(2)
                with col1:
                    st.components.v1.html(
                        '<button onclick="window.print()" style="background-color:#1a73e8;color:white;border:none;padding:12px;border-radius:5px;width:100%;font-weight:bold;cursor:pointer;">🖨️ Stampa Report A4</button>',
                        height=50
                    )
                with col2:
                    df_exp = pd.DataFrame(dati_export)
                    st.download_button("📊 Scarica Ordine CSV", data=df_exp.to_csv(index=False).encode('utf-8'), file_name="proposta_ordine.csv", mime="text/csv", use_container_width=True)
