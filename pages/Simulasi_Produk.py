import streamlit as st
import pandas as pd
import joblib
import numpy as np

# --- 1. FUNCTION TO LOAD MODEL ASSETS ---
@st.cache_resource
def load_prediction_assets():
    """Loads the trained prediction model and preprocessor."""
    try:
        model = joblib.load('price_model.pkl')
        preprocessor = joblib.load('preprocessor.pkl')
        return model, preprocessor
    except FileNotFoundError:
        return None, None

# --- 2. LOAD MODEL & PREPROCESSOR ---
model, preprocessor = load_prediction_assets()

# --- APPLICATION PAGE DISPLAY ---
st.set_page_config(page_title="PC Price Prediction", layout="centered")
st.title("🤖 Gaming PC Price Prediction Assistant")
st.write("Enter the PC component specifications to get a fair market price estimate based on the Machine Learning model.")

# Display an error message if the model is not found
if model is None or preprocessor is None:
    st.error(
        "Model file 'price_model.pkl' or 'preprocessor.pkl' not found. "
        "Please ensure you have run the training notebook and placed these files in the correct directory."
    )
else:
    # --- 3. CREATE USER INPUT FORM ---
    with st.form("prediction_form"):
        st.subheader("Enter Your PC Specifications")

        # Access the 'onehot' step within the pipeline to get categories
        ohe = preprocessor.named_transformers_['cat'].named_steps['onehot']
        cpu_options = list(ohe.categories_[0])
        gpu_options = list(ohe.categories_[1])
        storage_options = list(ohe.categories_[2])
        
        col1, col2 = st.columns(2)
        with col1:
            cpu_model = st.selectbox("Select CPU Model:", options=cpu_options)
            ram_size = st.number_input("RAM Size (GB):", min_value=4, max_value=128, value=16, step=4)
            rating = st.slider("Your Product's Target Rating:", 1.0, 5.0, 4.8, 0.1)
        
        with col2:
            gpu_model = st.selectbox("Select GPU Model:", options=gpu_options)
            storage = st.selectbox("Select Storage:", options=storage_options)
            sold = st.number_input("Estimated Monthly Sales:", min_value=0, max_value=1000, value=10)
        
        submitted = st.form_submit_button("Predict Price")

        # --- 4. PREDICTION PROCESS AFTER BUTTON IS CLICKED ---
        if submitted:
            # Create a DataFrame from user input
            input_data = pd.DataFrame({
                'CPU_Model': [cpu_model],
                'GPU_Model': [gpu_model],
                'Storage': [storage],
                'RAM_Size': [ram_size],
                'Rating': [rating],
                'Terjual': [sold] # Changed variable name to 'sold' for clarity
            })

            # Transform the input data using the preprocessor
            input_processed = preprocessor.transform(input_data)
            
            # Make a prediction using the model
            predicted_price = model.predict(input_processed)
            
            # Get the first prediction value
            price = int(predicted_price[0])

            # Determine a fair price range based on the RMSE (approx. 7.5 million)
            price_error_margin = 7500000 
            lower_bound = int(price - price_error_margin)
            upper_bound = int(price + price_error_margin)

            # --- 5. DISPLAY THE PREDICTION RESULT ---
            st.success("Analysis complete!")
            st.header(f"Estimated Market Price: IDR {price:,}")
            
            st.info(
                f"Based on the model, the competitive price range for this specification is between **IDR {lower_bound:,}** and **IDR {upper_bound:,}**."
            )
            st.write("This recommendation is made based on a comparison with thousands of similar products in the market.")