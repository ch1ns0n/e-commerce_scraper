import streamlit as st
import pandas as pd
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from sklearn.preprocessing import MinMaxScaler
import plotly.express as px

# --- Web Page Configuration ---
st.set_page_config(page_title="Analysis Dashboard", layout="wide")

# --- Data Loading Function ---
@st.cache_data
def load_data():
    """Connects to MongoDB and loads product data."""
    uri = "mongodb+srv://samuelchinson:test123@cluster0.bxaivdh.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
    client = MongoClient(uri, server_api=ServerApi('1'))
    db = client['tokopedia_db']
    collection = db['products']
    df = pd.DataFrame(list(collection.find({})))
    
    if '_id' in df.columns:
        df = df.drop(columns=['_id'])
    
    # Remove the 'Cluster' column if it exists
    if 'Cluster' in df.columns:
        df = df.drop(columns=['Cluster'])

    # Standardize column names from Indonesian to English
    column_mapping = {
        'Nama Produk': 'Product Name', 'Harga': 'Price', 'Toko': 'Store',
        'Lokasi': 'Location', 'Terjual': 'Sold', 'Rating': 'Rating'
    }
    df.rename(columns=column_mapping, inplace=True)
    return df

df = load_data()

# --- Page Display ---
st.title("📊 Gaming PC Market Analysis Dashboard")
st.write("This dashboard visualizes scraped product data for competitor analysis.")

# --- Sidebar for Filters ---
st.sidebar.header("Filter & Search")
search_query = st.sidebar.text_input("Search Product Name or Store:")

# 1. Filter by Location first
all_locations = sorted(df["Location"].unique())
select_all_option = "(Select All)"
options = [select_all_option] + all_locations

location_selection = st.sidebar.multiselect(
    "Select Store Location:",
    options=options,
    default=select_all_option,
    help="Filter the data to show products only from the selected store locations."
)

if select_all_option in location_selection or not location_selection:
    final_location_filter = all_locations
else:
    final_location_filter = location_selection

# Create a temporary DataFrame filtered by location
df_selection = df[df["Location"].isin(final_location_filter)]

# 2. Determine the price range from the already filtered DataFrame
min_price_available = int(df_selection["Price"].min()) if not df_selection.empty else 0
max_price_available = int(df_selection["Price"].max()) if not df_selection.empty else 0

# 3. Create the price input widgets using the correct range
st.sidebar.write("Price Range (IDR):")
col_min, col_max = st.sidebar.columns(2)

with col_min:
    price_min = st.number_input(
        "Minimum", 
        min_value=0,
        max_value=max_price_available,
        value=min_price_available,
        step=100000,
        label_visibility="collapsed"
    )

with col_max:
    price_max = st.number_input(
        "Maximum",
        min_value=0,
        max_value=max_price_available,
        value=max_price_available,
        step=100000,
        label_visibility="collapsed"
    )

# 4. Apply the remaining filters
df_selection = df_selection[df_selection["Price"].between(price_min, price_max)]

if search_query:
    words = [word for word in search_query.strip().split() if word]
    for word in words:
        word_mask = (df_selection['Product Name'].str.contains(word, case=False, na=False) |
                     df_selection['Store'].str.contains(word, case=False, na=False))
        df_selection = df_selection[word_mask]

df_display = df_selection.sort_values(by=["Sold", "Rating"], ascending=[False, False])

# --- Main Display ---
with st.container(border=True):
    total_products = len(df_display)
    avg_price = int(df_display["Price"].mean()) if total_products > 0 else 0
    avg_sales = int(df_display["Sold"].mean()) if total_products > 0 else 0

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Products Found", f"{total_products}")
    col2.metric("Average Price", f"IDR {avg_price:,}")
    col3.metric("Average Sales", f"{int(avg_sales)}")

if total_products > 0:
    # UPDATED: Simplified tabs after removing Cluster analysis
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Map & Rankings", "🕵️‍♂️ Competitor Spy", "💎 Opportunity Calculator", "📋 Raw Data"])

    with tab1:
        st.header("Main Market Visualization")
        
        # --- NEW VISUALIZATION ---
        # Scatter plot of Price vs. Sales, with bubble size representing Rating
        st.subheader("Market Map (Price vs. Sales, Sized by Rating)")
        fig_scatter = px.scatter(
            df_display[df_display['Rating'] > 0], # Filter out items with no rating for better viz
            x="Sold", 
            y="Price", 
            size="Rating",        # Rating determines the size of the bubble
            color="Location",     # Color bubbles by store location
            hover_name="Product Name",
            log_x=True,           # Use a log scale for 'Sold' to better see distribution
            size_max=60,          # Control the maximum size of the bubbles
            labels={"Sold": "Number of Items Sold (Log Scale)", "Price": "Price (IDR)"}
        )
        st.plotly_chart(fig_scatter, use_container_width=True)

        # Store Leaderboard (remains the same)
        st.subheader("Store Leaderboard (Top 10 by Number of Listings)")
        df_top_stores = df_display['Store'].value_counts().nlargest(10)
        fig_bar = px.bar(
            df_top_stores, orientation='h',
            labels={'value': 'Number of Products', 'index': 'Store'}
        )
        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_bar, use_container_width=True)
        
    with tab2:
        # This was originally tab3
        st.header("🕵️‍♂️ Competitor Spy")
        filtered_store_list = df_display['Store'].unique()
        selected_store = st.selectbox("Select a store to analyze:", options=filtered_store_list)
        if selected_store:
            df_store = df_display[df_display['Store'] == selected_store]
            st.subheader(f"Store Profile: {selected_store}")
            total_products_store = len(df_store)
            avg_price_store = int(df_store["Price"].mean()) if total_products_store > 0 else 0
            avg_sales_store = int(df_store["Sold"].mean()) if total_products_store > 0 else 0
            c1, c2, c3 = st.columns(3)
            c1.metric("Number of Listings", f"{total_products_store}")
            c2.metric("Average Price", f"IDR {avg_price_store:,}")
            c3.metric("Average Sales", f"{int(avg_sales_store)}")
            st.write("**Best-Selling Products from This Store:**")
            st.dataframe(df_store[['Product Name', 'Price', 'Rating', 'Sold']].sort_values(by="Sold", ascending=False).head(5))

    with tab3:
        # This was originally tab4
        st.header("💎 Opportunity Calculator (Best 'Value' Products)")
        df_score = df_display[(df_display['Price'] > 0) & (df_display['Sold'] > 0) & (df_display['Rating'] > 0)].copy()
        if not df_score.empty:
            scaler_norm = MinMaxScaler()
            df_score[['Price_norm', 'Rating_norm', 'Sold_norm']] = scaler_norm.fit_transform(df_score[['Price', 'Rating', 'Sold']])
            df_score['Opportunity Score'] = ((1 - df_score['Price_norm']) + df_score['Rating_norm'] + df_score['Sold_norm'])
            st.write("Top 10 products with the best 'value':")
            df_top_value = df_score.sort_values(by="Opportunity Score", ascending=False).head(10)
            st.dataframe(df_top_value[['Product Name', 'Price', 'Rating', 'Sold', 'Store']])
        else:
            st.write("Not enough data to calculate the opportunity score.")
    
    with tab4:
        # This was originally tab5
        st.subheader("Raw Data (Sorted by Sales & Rating)")
        with st.expander("Click to view the full raw data table"):
            st.dataframe(df_display)
else:
    st.warning("No data matches the selected filters.")