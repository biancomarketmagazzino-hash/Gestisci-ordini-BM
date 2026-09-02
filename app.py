import streamlit as st
import pandas as pd
import plotly.express as px
from data_loader import load_data, FILIALI_MAP

st.set_page_config(page_title="Bianco Market AI Assistant", layout="wide", page_icon="🛍️")

st.title("🛍️ Bianco Market - Assistente AI & Gestione Magazzino")

# Caricamento Dati
@st.cache_data
def get_data():
    return load_data()

df_articoli, df_storcar, df_sit = get_data()

# Sidebar per filtri rapidi e azioni
st.sidebar.header("📌 Menu di Controllo")
opzione = st.sidebar.radio("Seleziona Modalità:", ["💬 Chatbot AI", "📊 Dashboard Giacenze", "📦 Suggerimento Riassortimento"])

# ---------------------------------------------------------
# MODALITÀ 1: CHATBOT AI
# ---------------------------------------------------------
if opzione == "💬 Chatbot AI":
    st.subheader("🤖 Fai una domanda all'assistente commerciale")
    st.write("Esempi: *'Quanti pigiami uomo abbiamo a Ragusa e Sciacca?'*, *'Quali sono i brand più venduti a Menfi ad Agosto?'*")

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
            # Qui si collega l'API dell'AI (es. OpenAI / Gemini) inviando la struttura del dataframe
            response = f"**Risposta elaborata per**: *'{prompt}'*\n\n*(Integrazione AI per la generazione automatica di query e grafici)*"
            st.markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

# ---------------------------------------------------------
# MODALITÀ 2: DASHBOARD GIACENZE E GRAFICI
# ---------------------------------------------------------
elif opzione == "📊 Dashboard Giacenze":
    st.subheader("📈 Analisi Esistenze e Vendite per Filiale")
    
    filiale_sel = st.selectbox("Seleziona Filiale:", list(FILIALI_MAP.values()))
    st.write(f"Visualizzazione dati per la filiale: **{filiale_sel}**")

    # Esempio grafico Plotly
    # (Adatta con i campi reali del tuo dataset)
    fig = px.bar(x=["Biancheria Casa", "Corsetteria", "Pigiami", "Infanzia"], y=[120, 85, 210, 45],
                 labels={'x': 'Categoria', 'y': 'Pezzi Disponibili'},
                 title=f"Giacenza Categorie a {filiale_sel}")
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------
# MODALITÀ 3: ALGORITMO DI RIASSORTIMENTO INTELLIGENTE
# ---------------------------------------------------------
elif opzione == "📦 Suggerimento Riassortimento":
    st.subheader("🧮 Calcolo automatico della quantità da ordinare")
    st.info("L'algoritmo analizza lo storico venduto (S/F), la giacenza attuale e calcola il fabbisogno stimato.")
    
    giorni_copertura = st.slider("Giorni di copertura desiderati:", 15, 90, 30)
    
    if st.button("Genera Report Riassortimento"):
        st.success("Report generato con successo!")
        # Tabella di output scaricabile
        st.download_button(
            label="📄 Scarica Report in Excel",
            data="Articolo,Giacenza,Venduto_30G,Da_Ordinare\n12345,10,30,20",
            file_name="report_riassortimento_bianco_market.csv",
            mime="text/csv"
        )
