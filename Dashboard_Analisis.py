import streamlit as st
import pandas as pd
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
from sklearn.preprocessing import MinMaxScaler
from utils import load_data_for_dashboard  # Assuming this function exists and works
import plotly.express as px

# --- Web Page Configuration ---
st.set_page_config(page_title="Analysis Dashboard", layout="wide")

# Load data using the utility function
df = load_data_for_dashboard()

# Rename columns to English for consistency
# Create a mapping for original Indonesian names to new English names
column_mapping = {
    'Nama Produk': 'Product Name',
    'Harga': 'Price',
    'Toko': 'Store',
    'Lokasi': 'Location',
    'Terjual': 'Sold'
}
df.rename(columns=column_mapping, inplace=True)


# --- Page Display ---
st.title("📊 Gaming PC Market Analysis Dashboard")
st.write("This dashboard visualizes scraped product data for competitor analysis.")

# --- Sidebar for Filters ---
st.sidebar.header("Filter & Search")
search_query = st.sidebar.text_input("Search Product Name or Store:")

# Ensure 'Location' column exists before proceeding
if 'Location' in df.columns:
    all_locations = sorted(df["Location"].unique())
    select_all_option = "(Select All)"
    options = [select_all_option] + all_locations

    location_selection = st.sidebar.multiselect(
        "Select Store Location:",
        options=options,
        default=select_all_option
    )

    if select_all_option in location_selection or not location_selection:
        final_location_filter = all_locations
    else:
        final_location_filter = location_selection
else:
    final_location_filter = []

# Ensure 'Price' column exists before creating the slider
if 'Price' in df.columns and not df.empty:
    price_min, price_max = st.sidebar.slider(
        "Price Range (IDR):",
        min_value=int(df["Price"].min()),
        max_value=int(df["Price"].max()),
        value=(int(df["Price"].min()), int(df["Price"].max()))
    )
else:
    price_min, price_max = 0, 100000000 # Default values if no data

# Apply initial filters
df_selection = df.copy()
if 'Location' in df.columns:
    df_selection = df_selection[df_selection["Location"].isin(final_location_filter)]
if 'Price' in df.columns:
    df_selection = df_selection[df_selection["Price"].between(price_min, price_max)]


# Apply search filter
if search_query:
    words = [word for word in search_query.strip().split() if word]
    for word in words:
        word_mask = (df_selection['Product Name'].str.contains(word, case=False, na=False) |
                     df_selection['Store'].str.contains(word, case=False, na=False))
        df_selection = df_selection[word_mask]

# Sort the displayed data
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
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["📈 Map & Rankings", "🔬 Segment Analysis", "🕵️‍♂️ Competitor Spy", "💎 Opportunity Calculator", "📋 Raw Data"])

    with tab1:
        st.header("Main Market Visualization")
        fig_scatter = px.scatter(
            df_display[df_display.get('Cluster', pd.Series([-1])).ne(-1)],
            x="Sold", y="Price", color="Cluster", hover_name="Product Name",
            title="Market Segment Map (Price vs. Sales)"
        )
        df_top_stores = df_display['Store'].value_counts().nlargest(10)
        fig_bar = px.bar(
            df_top_stores, orientation='h', title="Store Leaderboard (Top 10)",
            labels={'value': 'Number of Products', 'index': 'Store'}
        )
        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
        
        left_column, right_column = st.columns(2)
        left_column.plotly_chart(fig_scatter, use_container_width=True)
        right_column.plotly_chart(fig_bar, use_container_width=True)
        
    with tab2:
        st.header("In-depth Analysis per Market Segment")
        st.subheader("Price Distribution Comparison per Segment")
        fig_box = px.box(
            df_display[df_display['Cluster'] > 0], x="Cluster", y="Price", color="Cluster",
            points="all", notched=True, title="Price Distribution in Each Cluster"
        )
        st.plotly_chart(fig_box, use_container_width=True)
        
        st.subheader("Market Structure by Total Store Sales")
        df_treemap = df_display[df_display['Cluster'] > 0].groupby(['Cluster', 'Store'])['Sold'].sum().reset_index()
        if not df_treemap.empty:
            fig_treemap = px.treemap(
                df_treemap, path=[px.Constant("All Markets"), 'Cluster', 'Store'],
                values='Sold', title="Market Share Map per Segment"
            )
            st.plotly_chart(fig_treemap, use_container_width=True)

    with tab3:
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

    with tab4:
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
    
    with tab5:
        st.subheader("Raw Data (Sorted by Sales & Rating)")
        st.dataframe(df_display)
else:
    st.warning("No data matches your selected filters.")