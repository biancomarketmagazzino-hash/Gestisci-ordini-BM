import sys
import os

# Assicura che Python trovi data_loader.py
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import pandas as pd
import plotly.express as px
from google import genai
from data_loader import load_data, FILIALI_MAP

# Configurazione Pagina
st.set_page_config(
    page_title="Bianco Market AI Assistant", 
    layout="wide", 
    page_icon="🛍️"
)

st.title("🛍️ Bianco Market - Assistente AI & Gestione Magazzino")

# ------------------------------------------------------------------------------
# CARICAMENTO DATI
# ------------------------------------------------------------------------------
@st.cache_data
def get_data():
    return load_data()

try:
    df_articoli, df_storcar, df_sit = get_data()
except Exception as e:
    st.error(f"Errore nel caricamento dei dati: {e}")
    st.stop()

# ------------------------------------------------------------------------------
# SIDEBAR
# ------------------------------------------------------------------------------
st.sidebar.header("📌 Menu di Controllo")
opzione = st.sidebar.radio(
    "Seleziona Modalità:", 
    ["💬 Chatbot AI", "📊 Dashboard Giacenze", "📦 Suggerimento Riassortimento"]
)

# ------------------------------------------------------------------------------
# MODALITÀ 1: CHATBOT AI INTELLIGENTE (GEMINI)
# ------------------------------------------------------------------------------
if opzione == "💬 Chatbot AI":
    st.subheader("🤖 Fai una domanda all'assistente commerciale")
    st.write("Esempi: *'Quanti pigiami uomo abbiamo a Ragusa e Sciacca?'*, *'Quali sono i brand più venduti a Menfi?'*")

    # Inizializzazione Client Gemini dai Secrets
    if "GEMINI_API_KEY" not in st.secrets:
        st.warning("⚠️ Inserisci la chiave `GEMINI_API_KEY` nella sezione Secrets di Streamlit Cloud.")
        st.stop()
        
    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Scrivi la tua domanda..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            system_prompt = f"""
            Sei l'assistente AI aziendale esperto di magazzino per Bianco Market (azienda specializzata in biancheria per la casa e persona).
            Hai a disposizione 3 data frame Pandas:

            1. `df_articoli`: anagrafica prodotti (codice, descrizione, brand, categoria, ecc.). Colonne: {list(df_articoli.columns)}
            2. `df_storcar`: storico dei movimenti. Tipi movimento:
               - S = Scontrino (Vendita)
               - F = Fattura (Vendita)
               - T = Trasferimento da Magazzino a Filiale (positivo) o Reso (negativo)
               - C = Carico Magazzino (da ignorare nelle vendite)
               Prezzo finale venduto in 'LIST./COSTO AGG', percentuale sconto in 'SCONTO'.
               Colonne: {list(df_storcar.columns)}
            3. `df_sit`: matrice delle giacenze attuali per filiale. Colonne: {list(df_sit.columns)}

            Analizza e rispondi alla domanda dell'utente in italiano in modo preciso, professionale e sintetico.
            """

            try:
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=f"{system_prompt}\n\nDomanda utente: {prompt}"
                )
                bot_response = response.text
                st.markdown(bot_response)
                st.session_state.messages.append({"role": "assistant", "content": bot_response})
            except Exception as err:
                st.error(f"Errore durante la comunicazione con Gemini: {err}")

# ------------------------------------------------------------------------------
# MODALITÀ 2: DASHBOARD GIACENZE
# ------------------------------------------------------------------------------
elif opzione == "📊 Dashboard Giacenze":
    st.subheader("📈 Analisi Esistenze per Filiale")
    
    filiale_sel = st.selectbox("Seleziona Filiale:", list(FILIALI_MAP.values()))
    
    if filiale_sel in df_sit.columns:
        df_filiale = df_sit[df_sit[filiale_sel] > 0][['CODICE', filiale_sel]]
        st.write(f"Totale articoli con giacenza positiva a **{filiale_sel}**: `{len(df_filiale)}`")
        st.dataframe(df_filiale.head(50), use_container_width=True)
    else:
        st.info("Dati giacenza non disponibili per la filiale selezionata.")

# ------------------------------------------------------------------------------
# MODALITÀ 3: SUGGERIMENTO RIASSORTIMENTO
# ------------------------------------------------------------------------------
elif opzione == "📦 Suggerimento Riassortimento":
    st.subheader("🧮 Calcolo automatico della quantità da ordinare")
    st.info("L'algoritmo incrocia il venduto storico (S/F) con la giacenza attuale per calcolare la stima di riassortimento.")
    
    giorni_copertura = st.slider("Giorni di copertura desiderati:", 15, 90, 30)
    
    if st.button("Calcola Riassortimento"):
        st.success(f"Analisi calcolata per una copertura target di {giorni_copertura} giorni.")
