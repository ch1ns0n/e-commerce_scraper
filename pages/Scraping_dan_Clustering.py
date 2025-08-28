import streamlit as st
from utils import connect_to_mongodb, scrape_and_save, jalankan_clustering, hapus_data_dibawah_harga

# --- Page Configuration ---
st.set_page_config(page_title="Data Control", layout="centered")

# --- Page Display ---
st.title("⚙️ Data Control Center: Scraping & Clustering")
st.write("Use this page to fetch the latest product data or to retrain the market segmentation model (clustering).")

# --- Scraping Section ---
st.header("1. Scrape New Product Data")
with st.form("scraping_form"):
    keyword = st.text_input("Enter a product keyword (e.g., gaming pc)", "laptop gaming")
    submitted = st.form_submit_button("🚀 Start Scraping")

    if submitted:
        if not keyword:
            st.error("Keyword cannot be empty!")
        else:
            # Use st.spinner to show progress
            with st.spinner(f"Searching for products with keyword '{keyword}'... This may take a few minutes."):
                st.info("Connecting to the database...")
                db, client = connect_to_mongodb()
                if db is not None:
                    st.info("Starting the scraping process... The browser is running in the background (headless).")
                    
                    # Call the function from utils.py
                    inserted, updated = scrape_and_save(keyword, db)
                    
                    st.success("✅ Scraping Process Complete!")
                    st.write(f"- **New products added:** {inserted}")
                    st.write(f"- **Existing products updated:** {updated}")
                    
                    if client:
                        client.close()
                        st.info("Connection to the database is closed.")
                else:
                    st.error("Failed to connect to the database. Process aborted.")

# --- Clustering Section ---
st.header("2. Retrain Segmentation Model (Clustering)")
st.warning("This process will retrain the K-Means model based on the latest data in the database and update the 'Cluster' label for each product.")

if st.button("🧠 Retrain Model"):
    with st.spinner("Processing clustering... This might take a while if the dataset is large."):
        # Call the clustering function from utils.py
        result_message = jalankan_clustering()
        st.success("✅ Clustering Process Complete!")
        st.info(result_message)

# --- Data Cleaning Section ---
st.markdown("---")
st.header("3. Clean Illogical Data")
st.write("Use this feature to permanently delete products with unreasonable prices (e.g., below a certain threshold) from the database.")

# Use a form to group the input and button
with st.form("cleaning_form"):
    min_price_input = st.number_input(
        "Delete all products with a price below (IDR):",
        min_value=0,
        max_value=150000000,
        value=1500000,
        step=100000
    )
    
    # Confirmation checkbox for safety
    confirmation = st.checkbox("⚠️ I understand that this action cannot be undone.")
    
    submitted_delete = st.form_submit_button("Permanently Delete Data")

    if submitted_delete:
        if confirmation:
            with st.spinner(f"Finding and deleting products below IDR {min_price_input:,}..."):
                db, client = connect_to_mongodb()
                if db is not None:
                    # Call the function from utils
                    found, deleted = hapus_data_dibawah_harga(db, min_price_input)
                    
                    if found > 0:
                        st.success(f"✅ Done! Found {found} products and successfully deleted {deleted} products.")
                    else:
                        st.info("✅ No products matched the criteria for deletion.")
                    
                    if client:
                        client.close()
                else:
                    st.error("Failed to connect to the database.")
        else:
            st.error("Please check the confirmation box to proceed with the deletion.")