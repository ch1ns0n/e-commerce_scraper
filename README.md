# 🛒 E-commerce Data Scraper

An automated **web scraping tool** built with **Python** to collect structured product data (name, price, rating, stock status, etc.) from e-commerce websites.  
This project demonstrates practical skills in **data engineering, automation, and data collection** for analytics and business insights.

---

## 🚀 Project Overview

The **E-commerce Data Scraper** automates product data extraction from online marketplaces and stores it in a clean, tabular format ready for analysis.  
It can be used to track product prices, monitor competitors, or perform market trend analysis.

---

## 🧩 Features

- 🧭 Automatically navigates through product listings or category pages  
- 🧹 Extracts relevant information: product name, price, rating, availability, and URL  
- 💾 Saves results in CSV or JSON format  
- 🕒 Configurable request delay to prevent blocking  
- 📦 Easily extendable to support multiple e-commerce sites  
- 🧠 Generates data ready for use in BI dashboards or ML pipelines  

---

## 🧰 Tech Stack

| Category | Technology |
|-----------|-------------|
| Language | Python 3.10+ |
| Libraries | Requests, BeautifulSoup, Pandas |
| Utilities | Logging, Time, Random |
| Output | CSV / JSON |

---

## 📂 Project Structure

e-commerce_scraper/
├── scraper.py # Main script for scraping product data
├── utils.py # Helper functions for cleaning and logging
├── requirements.txt # Project dependencies
├── data/ # Folder for storing scraped data
│ └── products.csv
└── README.md

---

## ⚙️ Installation & Usage

1. Clone the repo
```bash
git clone https://github.com/ch1ns0n/e-commerce_scraper.git
```

2. Change directory
```bash
cd e-commerce_scraper
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Run the Scraper
```bash
python scraper.py
```
