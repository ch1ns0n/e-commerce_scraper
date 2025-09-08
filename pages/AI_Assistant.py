import streamlit as st
import pandas as pd
from utils import load_data_for_dashboard
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain_groq import ChatGroq
from langchain.agents.agent_types import AgentType

# --- Konfigurasi Halaman ---
st.set_page_config(page_title="LangChain AI Assistant", layout="wide")
st.title("🤖 LangChain AI Assistant (Powered by Llama 3.1 via Groq)")
st.write("Ask complex questions about your data. The AI will write and execute Python code to answer them.")

# --- Langkah 1: Setup LLM (Model Bahasa) ---
try:
    api_key = st.secrets["GROQ_API_KEY"]
    llm = ChatGroq(
        model_name="llama-3.1-8b-instant", 
        groq_api_key=api_key,
        temperature=0,
    )
except Exception as e:
    st.error("Groq API Key not found. Please add it to your .streamlit/secrets.toml file.")
    st.stop()

# --- Langkah 2: Muat Data ---
@st.cache_data
def load_data():
    df = load_data_for_dashboard()
    column_mapping = {
        'Nama Produk': 'Product_Name', 'Harga': 'Price', 'Toko': 'Store',
        'Lokasi': 'Location', 'Terjual': 'Sold', 'Rating': 'Rating', 'Cluster': 'Cluster'
    }
    df.rename(columns={k: v for k, v in column_mapping.items() if k in df.columns}, inplace=True)
    return df

df_original = load_data()

# --- Langkah 3: Buat Agen LangChain ---
agent = create_pandas_dataframe_agent(
    llm,
    df_original,
    verbose=True, 
    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    handle_parsing_errors=True,
    allow_dangerous_code=True,
    # --- PERBAIKAN: Memberi agen lebih banyak langkah untuk berpikir ---
    max_iterations=30 
)

# --- Langkah 4: Buat Antarmuka Chat ---
if "lc_messages" not in st.session_state:
    st.session_state.lc_messages = []

# Tampilkan riwayat chat
for message in st.session_state.lc_messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Terima input baru dari pengguna
if prompt := st.chat_input("Example: What are the top 5 most expensive products?"):
    st.session_state.lc_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Proses prompt dan tampilkan jawaban
    with st.chat_message("assistant"):
        with st.spinner("AI Agent is thinking and executing code..."):
            try:
                response = agent.run(prompt)
                st.markdown(response)
                st.session_state.lc_messages.append({"role": "assistant", "content": response})
            except Exception as e:
                error_message = f"Sorry, I encountered an error: {e}"
                st.error(error_message)
                st.session_state.lc_messages.append({"role": "assistant", "content": error_message})