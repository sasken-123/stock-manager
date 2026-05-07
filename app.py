import streamlit as st
import pandas as pd
import json
from urllib.parse import urlparse

st.title("在庫管理ツール（クラウド版）")

# =========================
# SESSION STATE
# =========================
if "page" not in st.session_state:
    st.session_state.page = 0

if "stock_buffer" not in st.session_state:
    st.session_state.stock_buffer = {}

if "stock_data" not in st.session_state:
    st.session_state.stock_data = {}


# =========================
# CLOUD STORAGE（JSON）
# =========================
def load_stock():
    try:
        with open("stock.json", "r") as f:
            return json.load(f)
    except:
        return {}


def save_stock(data):
    with open("stock.json", "w") as f:
        json.dump(data, f)


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
    return normalize(x)


# =========================
# UPLOAD
# =========================
file_master = st.file_uploader("マスタ")
file_check = st.file_uploader("チェック")

if file_master is not None:
    master = pd.read_excel(file_master, dtype=str)
else:
    master = None

if file_check is not None:
    check = pd.read_excel(file_check, dtype=str)
else:
    check = None


# =========================
# MAIN
# =========================
PAGE_SIZE = 50

if master is not None and check is not None:

    check_ids = set(check.iloc[:, 0].astype(str).apply(normalize_itemid))
    master["itemID"] = master["itemID"].astype(str).apply(normalize_itemid)

    result = master[~master["itemID"].isin(check_ids)].copy()

    total = len(result)

    # =========================
    # SAVE BUTTON
    # =========================
    if st.sidebar.button("変更を保存"):
        stock.update(st.session_state.stock_buffer)
        save_stock(stock)
        st.session_state.stock_buffer = {}
        st.rerun()

    # =========================
    # PAGINATION
    # =========================
    max_page = max(0, (total - 1) // PAGE_SIZE)
    st.session_state.page = max(0, min(st.session_state.page, max_page))

    col1, col2, col3 = st.columns(3)

    with col1:
        if st.button("前へ"):
            st.session_state.page -= 1
            st.rerun()

    with col3:
        if st.button("次へ"):
            st.session_state.page += 1
            st.rerun()

    start = st.session_state.page * PAGE_SIZE
    end = start + PAGE_SIZE

    st.info(f"{start+1}-{min(end,total)} / {total}")

    page = result.iloc[start:end]

    # =========================
    # DISPLAY
    # =========================
    for i, (_, row) in enumerate(page.iterrows(), start=start+1):

        itemid = normalize_itemid(row["itemID"])

        checked = st.session_state.stock_buffer.get(
            itemid,
            stock.get(itemid, False)
        )

        st.markdown(f"---\nNo.{i}  \n{itemid}")

        checked = st.checkbox(
            "在庫なし",
            value=checked,
            key=f"stock_{itemid}"
        )

        st.session_state.stock_buffer[itemid] = checked
