import streamlit as st
import pandas as pd
from urllib.parse import urlparse
import json
from io import BytesIO
import os

import gspread
from google.oauth2.service_account import Credentials

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

st.title("在庫管理ツール")

# =========================
# SESSION STATE
# =========================
if "page" not in st.session_state:
    st.session_state.page = 0

if "stock_buffer" not in st.session_state:
    st.session_state.stock_buffer = {}

if "master_df" not in st.session_state:
    st.session_state.master_df = None

if "check_df" not in st.session_state:
    st.session_state.check_df = None

# =========================
# GOOGLE SHEETS CONNECT
# =========================
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=scope
)

client = gspread.authorize(creds)

SPREADSHEET_ID = "1M4EXK_h-1L2b3aeUQnDsUEnAHtbiyxngota6nrTc8Fw"
sheet = client.open_by_key(SPREADSHEET_ID).worksheet("stock")


# =========================
# STOCK (Google Sheets)
# =========================
def load_stock():
    data = sheet.get_all_records()
    return {row["itemID"]: row["stock"] for row in data}

def save_stock(data_dict):
    sheet.clear()
    sheet.append_row(["itemID", "stock"])
    for k, v in data_dict.items():
        sheet.append_row([k, v])

stock = load_stock()

# =========================
# UTIL
# =========================
def normalize(x):
    x = str(x).strip()
    if x.lower() in ["nan", "none", "", "na"]:
        return ""
    if x.endswith(".0"):
        x = x[:-2]
    return x

def normalize_itemid(x):
    x = normalize(x)
    try:
        if "e+" in x.lower():
            x = str(int(float(x)))
    except:
        pass
    return x

def classify_site(url):
    url = normalize(url)
    if url == "":
        return "空欄"

    d = urlparse(url).netloc.replace("www.", "").lower()

    if "2ndstreet" in d: return "2ndstreet"
    if "mercari" in d: return "メルカリ"
    if "rakuma" in d or "fril" in d: return "ラクマ"
    if "amazon" in d: return "Amazon"
    if "rakuten" in d: return "楽天"
    if "auctions.yahoo" in d: return "ヤフオク"
    if "shopping.yahoo" in d: return "ヤフショ"
    if "paypayfleamarket" in d: return "ヤフフリ"

    return "その他"

def make_ebay_link(itemid):
    return f"https://www.ebay.com/sh/lst/active?keyword={itemid}&source=filterbar&action=search"


# =========================
# UPLOAD
# =========================
file_master = st.file_uploader("マスタ")
file_check = st.file_uploader("チェック")

if file_master is not None:
    st.session_state.master_df = pd.read_excel(file_master, dtype=str)

if file_check is not None:
    st.session_state.check_df = pd.read_excel(file_check, dtype=str)


# =========================
# MAIN
# =========================
PAGE_SIZE = 50

if st.session_state.master_df is not None and st.session_state.check_df is not None:

    master = st.session_state.master_df
    check = st.session_state.check_df

    check_ids = set(check.iloc[:, 0].dropna().astype(str).apply(normalize_itemid))
    master["itemID"] = master["itemID"].astype(str).apply(normalize_itemid)

    result = master[~master["itemID"].isin(check_ids)].copy()

    result["url"] = result["url"].astype(str).apply(normalize)
    result["site"] = result["url"].apply(classify_site)
    result["ebay_url"] = result["itemID"].apply(make_ebay_link)

    def is_out(x):
        return stock.get(x, False)

    if st.sidebar.button("変更を反映"):
        stock.update(st.session_state.stock_buffer)
        save_stock(stock)
        st.session_state.stock_buffer = {}
        st.rerun()

    result = result.reset_index(drop=True)

    total = len(result)
    max_page = max(0, (total - 1) // PAGE_SIZE)

    st.session_state.page = max(0, min(st.session_state.page, max_page))

    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        if st.button("前へ"):
            st.session_state.page = max(0, st.session_state.page - 1)
            st.rerun()

    with col2:
        st.write(f"ページ: {st.session_state.page + 1} / {max_page + 1}")

    with col3:
        if st.button("次へ"):
            st.session_state.page = min(max_page, st.session_state.page + 1)
            st.rerun()

    start = st.session_state.page * PAGE_SIZE
    end = start + PAGE_SIZE

    st.info(f"{start+1}-{min(end,total)} / {total}")

    page = result.iloc[start:end]

    for i, (_, row) in enumerate(page.iterrows(), start=start+1):

        itemid = normalize_itemid(row["itemID"])
        url = row["url"]
        site = row["site"]
        ebay_url = row["ebay_url"]

        checked = st.session_state.stock_buffer.get(itemid, stock.get(itemid, False))

        if url:
            purchase_link = f"[仕入れリンク]({url})"
        else:
            purchase_link = "仕入れリンクなし"

        st.markdown(f"""
---
No.{i}  
{itemid} ｜ {site}  

{purchase_link}  
[eBay Seller Hub]({ebay_url})
""")

        checked = st.checkbox(
            "在庫なし",
            value=checked,
            key=f"stock_{itemid}"
        )

        st.session_state.stock_buffer[itemid] = checked
