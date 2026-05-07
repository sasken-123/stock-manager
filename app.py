import streamlit as st
import pandas as pd
import json
import gspread
from google.oauth2.service_account import Credentials

st.title("在庫管理ツール（完全安定版）")

# =========================
# SESSION STATE
# =========================
if "page" not in st.session_state:
    st.session_state.page = 0

if "stock_state" not in st.session_state:
    st.session_state.stock_state = {}

# =========================
# GOOGLE SHEETS 接続
# =========================
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

creds = Credentials.from_service_account_info(
    st.secrets["gcp_service_account"],
    scopes=SCOPES
)

client = gspread.authorize(creds)

SHEET_ID = "1M4EXK_h-1L2b3aeUQnDsUEnAHtbiyxngota6nrTc8Fw"
sheet = client.open_by_key(SHEET_ID).sheet1


# =========================
# STOCK LOAD
# =========================
def load_stock():
    try:
        records = sheet.get_all_records()
        return {str(r["itemID"]): (str(r["stock"]).upper() == "TRUE") for r in records}
    except:
        return {}

stock = load_stock()


# =========================
# STOCK SAVE（完全安全版）
# =========================
def save_stock(data):

    sheet.clear()

    rows = [["itemID", "stock"]]

    for k, v in data.items():

        # ★完全安全変換（ここ重要）
        k = str(k).strip()
        v = "TRUE" if bool(v) else "FALSE"

        # None/空対策
        if k == "" or k.lower() == "none":
            continue

        rows.append([k, v])

    # ★Google Sheets安全更新（JSON事故防止）
    sheet.update(
        values=rows,
        range_name="A1"
    )


# =========================
# UPLOAD
# =========================
file_master = st.file_uploader("マスタ（itemID必須）")
file_check = st.file_uploader("チェック（itemID）")

if file_master:
    master = pd.read_excel(file_master, dtype=str)
else:
    master = None

if file_check:
    check = pd.read_excel(file_check, dtype=str)
else:
    check = None


# =========================
# MAIN
# =========================
PAGE_SIZE = 50

if master is not None and check is not None:

    # -------------------------
    # 前処理
    # -------------------------
    check_ids = set(check.iloc[:, 0].dropna().astype(str))
    master["itemID"] = master["itemID"].astype(str)

    result = master[~master["itemID"].isin(check_ids)].copy()
    result = result.reset_index(drop=True)

    # -------------------------
    # ★全件state初期化（重要）
    # -------------------------
    for itemid in result["itemID"]:
        if itemid not in st.session_state.stock_state:
            st.session_state.stock_state[itemid] = stock.get(itemid, False)

    # -------------------------
    # 保存ボタン
    # -------------------------
    if st.button("変更を保存"):
        save_stock(st.session_state.stock_state)
        st.success("保存しました")

    # -------------------------
    # ページング
    # -------------------------
    total = len(result)
    max_page = max(0, (total - 1) // PAGE_SIZE)

    st.session_state.page = max(0, min(st.session_state.page, max_page))

    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        if st.button("⬅️ 前へ"):
            st.session_state.page -= 1
            st.rerun()

    with col3:
        if st.button("次へ ➡️"):
            st.session_state.page += 1
            st.rerun()

    start = st.session_state.page * PAGE_SIZE
    end = start + PAGE_SIZE

    page = result.iloc[start:end]

    st.info(f"{start+1} - {min(end, total)} / {total}")

    # -------------------------
    # 表示 & 状態更新
    # -------------------------
    for _, row in page.iterrows():

        itemid = str(row["itemID"])

        current = st.session_state.stock_state.get(itemid, False)

        new_value = st.checkbox(
            itemid,
            value=current,
            key=f"cb_{itemid}"
        )

        st.session_state.stock_state[itemid] = new_value
