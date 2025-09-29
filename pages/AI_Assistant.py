import streamlit as st
import pandas as pd
from utils import load_data_for_dashboard
import re
import matplotlib
import os

# Mengatur backend Matplotlib agar tidak memerlukan GUI.
matplotlib.use('Agg') 

# Impor library yang diperlukan dari LangChain
from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain_community.llms import Ollama
from langchain.agents.agent_types import AgentType

# --- Konfigurasi Halaman & Styling ---
# Menggunakan layout "wide"
st.set_page_config(page_title="AI Assistant", layout="wide")

# --- CSS KUSTOM UNTUK MEMPERCANTIK TAMPILAN ---
st.markdown("""
<style>
/* Sembunyikan header dan footer bawaan Streamlit */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* Style untuk tombol rekomendasi agar lebih modern dan lebih kecil */
.stButton>button {
    border: 1px solid #d0d0d0;
    border-radius: 12px;
    padding: 6px 14px;
    font-size: 14px;
    background-color: #f9f9f9;
    transition: all 0.2s ease-in-out;
    box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}
.stButton>button:hover {
    background-color: #f0f2f6;
    border-color: #b0b0b0;
    color: black;
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.08);
}
.stButton>button:focus {
    box-shadow: 0 0 0 2px #e0e0e0;
    outline: none;
}
</style>
""", unsafe_allow_html=True)


st.title("🤖 AI Assistant")
st.write("Ask questions about your PC market data, and the AI will answer.")

# --- Langkah 1: Setup LLM (Model Bahasa Lokal) ---
try:
    # DIKEMBALIKAN: Menggunakan model llama3 yang sudah terbukti stabil untuk tugas agen
    llm = Ollama(model="llama3.1:8b", temperature=0)
    st.success("Successfully connected to local Llama 3 model via Ollama.")
except Exception as e:
    st.error(f"Could not connect to Ollama. Please make sure the Ollama application is running. Error: {e}")
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

# --- Instruksi Khusus untuk Agen ---
PROMPT_PREFIX = """
You are a highly intelligent data analysis assistant. 
Your specialty is analyzing a dataset of scraped Gaming PC products from an e-commerce site.
You are given a pandas DataFrame named `df` and a question.
You should use the tools available to answer the question.
"""

PROMPT_SUFFIX = """
- When creating a plot, you MUST use `matplotlib` to save it to a file with a unique name.
- After saving, you MUST return the following markdown string as your final answer, and nothing else:
**[PLOT]filename.png**

- For any other request, you MUST format your final, human-readable answer by starting it with the exact prefix "Final Answer:".
"""

# --- Langkah 3: Buat Agen LangChain ---
agent = create_pandas_dataframe_agent(
    llm,
    df_original,
    verbose=True, 
    agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    handle_parsing_errors=True,
    allow_dangerous_code=True,
    max_iterations=30,
    agent_kwargs={
        "prefix": PROMPT_PREFIX,
        "suffix": PROMPT_SUFFIX
    }
)

# --- FUNGSI UTAMA UNTUK MENANGANI CHAT ---
def handle_chat(prompt):
    """Menyimpan prompt pengguna, menjalankan agen, dan menampilkan hasilnya."""
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
    
    with st.chat_message("assistant"):
        with st.spinner("AI Agent is thinking..."):
            response = agent.run(prompt)
            st.session_state.messages.append({"role": "assistant", "content": response})
            display_response(response)

def display_response(response_text):
    """Menganalisis respons dari agen dan menampilkannya dengan benar."""
    plot_match = re.search(r"\*\*\[PLOT\](.*?)\*\*", response_text)
    if plot_match:
        image_path = plot_match.group(1).strip()
        if os.path.exists(image_path):
            st.image(image_path)
        else:
            st.error(f"Plot image not found at path: {image_path}")
    else:
        cleaned_response = response_text.replace("Final Answer:", "").strip()
        st.markdown(cleaned_response)

# --- ANTARMUKA PENGGUNA ---

# Inisialisasi Riwayat Chat
if "messages" not in st.session_state:
    st.session_state.messages = []

# Tampilkan Riwayat Chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        display_response(message["content"])

# Tampilkan contoh prompt HANYA jika chat masih kosong
if not st.session_state.messages:
    st.write("Try one of these examples:")
    example_prompts = {
        "📊 Average price in Jakarta?": "What is the average price for products in 'Jakarta Pusat'?",
        "🏆 Top 5 most sold products?": "What are the top 5 products with the most sales?",
        "📈 Visualize top stores": "Visualize the top 10 stores by total sales using a bar chart."
    }
    
    # Gunakan 3 kolom agar tombol tidak terlalu lebar
    cols = st.columns(3)
    for i, (display_text, prompt_text) in enumerate(example_prompts.items()):
        with cols[i]:
            if st.button(display_text, use_container_width=True):
                handle_chat(prompt_text)
                st.rerun()

# Input Chat Utama
if prompt := st.chat_input("Ask a question about the PC market..."):
    handle_chat(prompt)