import streamlit as st
import pandas as pd
import dbfread
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

def cerca_file_case_insensitive(nome_target):
    for f in os.listdir('.'):
        if f.lower() == nome_target.lower():
            return f
    return None

def leggi_dbf_semplice(percorso):
    if not percorso or not os.path.exists(percorso):
        return pd.DataFrame()
    try:
        table = dbfread.DBF(percorso, encoding='latin1', ignore_missing_memofile=True, raw=False)
        return pd.DataFrame(list(table))
    except Exception as e:
        st.warning(f"Avviso lettura {percorso}: {str(e)}")
        return pd.DataFrame()

# Caricamento diretto senza st.cache_data per evitare crash di memoria
file_art = cerca_file_case_insensitive('ARTICOLI.DBF')
file_sit = cerca_file_case_insensitive('Sit_filiali.DBF')
file_stor = cerca_file_case_insensitive('STOR_CAR.DBF')

if not file_art or not file_sit:
    st.error(f"⚠️ Impossibile trovare i file DBF. File presenti nella cartella: {os.listdir('.')}")
else:
    with st.spinner("Caricamento ed elaborazione dati in corso..."):
        df_art = leggi_dbf_semplice(file_art)
        df_sit = leggi_dbf_semplice(file_sit)
        df_stor = leggi_dbf_semplice(file_stor)

    if df_art.empty or df_sit.empty:
        st.error("❌ Impossibile caricare le tabelle principali. Verifica che i file sul repository non siano corrotti.")
    else:
        st.success("✅ Dati DBF caricati correttamente!")

        # Mappatura colonne depositi
        mappa_depositi = {
            'C_01': 'MAGAZZINO', 'C_02': 'SCIACCA', 'C_03': 'MENFI',
            'C_04': 'MARSALA', 'C_05': 'TRAPANI', 'C_06': 'RAGUSA',
            'C_07': 'SABELLA', 'C_08': 'MAZARA', 'C_09': 'CASA MARKET', 'C_10': 'BM SPORT'
        }
        df_sit.rename(columns=mappa_depositi, inplace=True)

        # Trova colonne di unione
        col_art = [c for c in df_art.columns if 'cod' in c.lower() or 'art' in c.lower()][0]
        col_sit = [c for c in df_sit.columns if 'cod' in c.lower() or 'art' in c.lower()][0]

        df_merged = pd.merge(df_art, df_sit, left_on=col_art, right_on=col_sit, how='inner')

        # Calcolo Giacenza Totale
        col_presenti = [c for c in mappa_depositi.values() if c in df_merged.columns]
        df_merged['GIACENZA_TOTALE'] = df_merged[col_presenti].apply(pd.to_numeric, errors='coerce').fillna(0).sum(axis=1)

        # Calcolo Venduto da STOR_CAR
        if not df_stor.empty:
            col_stor_cod = [c for c in df_stor.columns if 'cod' in c.lower() or 'art' in c.lower()][0]
            col_qta = [c for c in df_stor.columns if 'qta' in c.lower() or 'quant' in c.lower() or 'mov' in c.lower()]
            col_qta_nome = col_qta[0] if col_qta else df_stor.columns[-1]

            df_stor[col_qta_nome] = pd.to_numeric(df_stor[col_qta_nome], errors='coerce').fillna(0)
            venduto_agg = df_stor.groupby(col_stor_cod)[col_qta_nome].sum().reset_index()
            venduto_agg.columns = [col_art, 'VENDUTO_STAGIONE']

            df_merged = pd.merge(df_merged, venduto_agg, on=col_art, how='left')
            df_merged['VENDUTO_STAGIONE'] = df_merged['VENDUTO_STAGIONE'].fillna(0)
        else:
            df_merged['VENDUTO_STAGIONE'] = 0

        # Barra di Ricerca
        query = st.chat_input("Scrivi una marca, fornitore o articolo (es. 100 SBADIGLI, DAG, PIGIAMA)...")

        if query:
            parole_chiave = query.lower().split()
            colonne_txt = df_merged.select_dtypes(include=['object']).columns
            df_merged['TESTO_RICERCA'] = df_merged[colonne_txt].astype(str).agg(' '.join, axis=1).str.lower()

            maschera = df_merged['TESTO_RICERCA'].apply(lambda txt: all(p in txt for p in parole_chiave))
            risultati = df_merged[maschera].copy()

            if risultati.empty:
                st.warning("⚠️ Nessun articolo trovato.")
            else:
                risultati = risultati.sort_values(by='VENDUTO_STAGIONE', ascending=False)
                st.subheader(f"📊 Articoli trovati: {len(risultati)}")

                dati_export = []
                for _, row in risultati.head(40).iterrows():
                    desc = row.get('DESCRIZIONE', row.get('DESCR', row.get('ARTICOLO', 'Articolo')))
                    cod = row.get(col_art, 'N/D')
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
                                <p>📦 Venduto Registrato: <b>{venduto} pz</b> | Giacenza Totale Negozi: <b>{giac} pz</b></p>
                                <h3>👉 CONSIGLIO RIASSORTIMENTO: Ordina {proposta} pz</h3>
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown(f"""
                            <div class="card-no-ordina">
                                <h4>🔴 {desc} (Cod. {cod})</h4>
                                <p>📦 Venduto Registrato: <b>{venduto} pz</b> | Giacenza Totale Negozi: <b>{giac} pz</b></p>
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
