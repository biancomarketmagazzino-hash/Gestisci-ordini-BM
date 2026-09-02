import streamlit as st
import pandas as pd
from dbfread import DBF
import os

st.set_page_config(page_title="Riassortimento Bianco Market", page_icon="📦", layout="wide")

# CSS personalizzato per interfaccia pulita e Stampa A4
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
st.caption("Dati sincronizzati dai file DBF aziendali")

# Funzione per caricare i file DBF se presenti
@st.cache_data(ttl=3600)
def carica_dati():
    if os.path.exists('Articoli.dbf') and os.path.exists('SIT_FILIALI.dbf'):
        # Lettura DBF
        art = pd.DataFrame(iter(DBF('Articoli.dbf', encoding='latin1')))
        sit = pd.DataFrame(iter(DBF('SIT_FILIALI.dbf', encoding='latin1')))
        
        # Mappatura delle colonne dei depositi
        mappa_depositi = {
            'C_01': 'MAGAZZINO', 'C_02': 'SCIACCA', 'C_03': 'MENFI',
            'C_04': 'MARSALA', 'C_05': 'TRAPANI', 'C_06': 'RAGUSA',
            'C_07': 'SABELLA', 'C_08': 'MAZARA', 'C_09': 'CASA MARKET', 'C_10': 'BM SPORT'
        }
        sit.rename(columns=mappa_depositi, inplace=True)
        return art, sit
    return None, None

art_df, sit_df = carica_dati()

# Input ricerca
query = st.chat_input("Scrivi qui la marca o il fornitore (es. DAG, COTONELLA)...")

if query:
    st.subheader(f"Risultati per: {query}")
    
    # Esempio dimostrativo se i DBF non sono ancora caricati
    dati_demo = [
        {"Codice": "DAG-102", "Articolo": "Calza Spugna Uomo Inverno", "Venduto": 140, "Giacenza": 10, "Ordina": 130},
        {"Codice": "DAG-105", "Articolo": "Calza Maglia Pesante", "Venduto": 80, "Giacenza": 5, "Ordina": 75},
        {"Codice": "DAG-201", "Articolo": "Calza Cotone Leggero", "Venduto": 12, "Giacenza": 20, "Ordina": 0}
    ]
    
    for item in dati_demo:
        if item["Ordina"] > 0:
            st.markdown(f"""
                <div class="card-ordina">
                    <h4>🟢 {item['Articolo']} (Cod. {item['Codice']})</h4>
                    <p>Venduto Staggione: <b>{item['Venduto']} pz</b> | Giacenza Attuale Filiali: <b>{item['Giacenza']} pz</b></p>
                    <h3>👉 CONSIQLIATO ORDINARE: {item['Ordina']} pz</h3>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
                <div class="card-no-ordina">
                    <h4>🔴 {item['Articolo']} (Cod. {item['Codice']})</h4>
                    <p>Venduto Stagione: <b>{item['Venduto']} pz</b> | Giacenza Attuale Filiali: <b>{item['Giacenza']} pz</b></p>
                    <p><b>Scorta sufficiente - Non ordinare</b></p>
                </div>
            """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.components.v1.html(
            '<button onclick="window.print()" style="background-color:#1a73e8;color:white;border:none;padding:12px;border-radius:5px;width:100%;font-weight:bold;cursor:pointer;">🖨️ Stampa Rapida Report A4</button>',
            height=50
        )
    with col2:
        df_export = pd.DataFrame(dati_demo)
        st.download_button("📊 Scarica Excel Ordine", data=df_export.to_csv(index=False).encode('utf-8'), file_name="ordine_riassortimento.csv", mime="text/csv", use_container_width=True)
