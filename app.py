import streamlit as st
import pandas as pd
from urllib.parse import urlparse
import json
from io import BytesIO
import os

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4

from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont

st.title("仕入れ × eBay 管理ツール")

# =========================
# SESSION STATE
# =========================
if "page" not in st.session_state:
    st.session_state.page = 0

if "stock_filter" not in st.session_state:
    st.session_state.stock_filter = "すべて"

if "site_filter" not in st.session_state:
    st.session_state.site_filter = "すべて"

if "stock_buffer" not in st.session_state:
    st.session_state.stock_buffer = {}

if "master_df" not in st.session_state:
    st.session_state.master_df = None

if "check_df" not in st.session_state:
    st.session_state.check_df = None

# =========================
# STOCK
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
# EXCEL TEMPLATE
# =========================
def create_master_template():
    df = pd.DataFrame({"itemID": [], "url": []})
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False)
    return buf.getvalue()

def create_check_template():
    df = pd.DataFrame({"itemID": []})
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False)
    return buf.getvalue()

# =========================
# PDF MANUAL
# =========================
def create_manual_pdf():

    pdfmetrics.registerFont(UnicodeCIDFont("HeiseiKakuGo-W5"))

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)

    styles = getSampleStyleSheet()
    style = styles["Normal"]
    style.fontName = "HeiseiKakuGo-W5"

    content = []

    def add(text):
        content.append(Paragraph(text, style))
        content.append(Spacer(1, 8))

    add("仕入れ × eBay 管理ツール マニュアル")
    add("このツールは仕入れ商品の管理・在庫確認・出品管理を行うためのシステムです。")

    add("■ Step1：データ準備")
    add("マスタ（itemID / url）とチェック（itemID）を準備してください。")

    if os.path.exists("images/step1.png"):
        content.append(Image("images/step1.png", width=400, height=220))

    add("■ Step2：アップロード")
    add("左側からマスタとチェックをアップロードします。")

    if os.path.exists("images/step2.png"):
        content.append(Image("images/step2.png", width=400, height=220))

    add("■ Step3：フィルター")
    add("在庫・仕入れ元・itemID検索で絞り込み可能です。")

    if os.path.exists("images/step3.png"):
        content.append(Image("images/step3.png", width=400, height=220))

    add("■ Step4：在庫チェック")
    add("チェックを入れると在庫なし扱いになります。")

    if os.path.exists("images/step4.png"):
        content.append(Image("images/step4.png", width=400, height=220))

    add("■ Step5：変更反映")
    add("必ず『変更を反映』を押してください。")

    if os.path.exists("images/step5.png"):
        content.append(Image("images/step5.png", width=400, height=220))

    doc.build(content)
    buffer.seek(0)
    return buffer.getvalue()

# =========================
# SIDEBAR
# =========================
st.sidebar.header("操作")

st.sidebar.download_button("📥 マスタテンプレDL", create_master_template(), file_name="master.xlsx")
st.sidebar.download_button("📥 チェックテンプレDL", create_check_template(), file_name="check.xlsx")
st.sidebar.download_button("📘 マニュアルDL", create_manual_pdf(), file_name="manual.pdf")

st.sidebar.divider()

# =========================
# UPLOAD
# =========================
file_master = st.file_uploader("マスタ")
file_check = st.file_uploader("チェック")

if file_master is not None:
    st.session_state.master_df = pd.read_excel(file_master, dtype=str) if not file_master.name.endswith("csv") else pd.read_csv(file_master, dtype=str)

if file_check is not None:
    st.session_state.check_df = pd.read_excel(file_check, dtype=str) if not file_check.name.endswith("csv") else pd.read_csv(file_check, dtype=str)

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

    # =========================
    # FILTER
    # =========================
    def is_out(x):
        return stock.get(x, False)

    st.session_state.stock_filter = st.sidebar.selectbox(
        "在庫フィルター",
        ["すべて", "在庫あり", "在庫なし"],
        index=["すべて", "在庫あり", "在庫なし"].index(st.session_state.stock_filter)
    )

    if st.session_state.stock_filter == "在庫あり":
        result = result[result["itemID"].apply(lambda x: not is_out(x))]
    elif st.session_state.stock_filter == "在庫なし":
        result = result[result["itemID"].apply(lambda x: is_out(x))]

    search_id = st.sidebar.text_input("itemID検索")

    if search_id:
        search_id = normalize_itemid(search_id)
        result = result[result["itemID"] == search_id]

    site_counts = result["site"].value_counts().to_dict()
    site_options = ["すべて"] + sorted(site_counts.keys())

    site_labels = {s: f"{s} ({site_counts.get(s,0)})" for s in site_options if s != "すべて"}
    label_list = ["すべて"] + [site_labels[s] for s in site_options if s != "すべて"]

    selected_label = st.sidebar.selectbox("仕入れフィルター", label_list)

    reverse = {v:k for k,v in site_labels.items()}
    selected_site = reverse.get(selected_label, "すべて")

    if selected_site != "すべて":
        result = result[result["site"] == selected_site]

    # =========================
    # SAVE
    # =========================
    if st.sidebar.button("💾 変更を反映"):
        stock.update(st.session_state.stock_buffer)
        save_stock(stock)
        st.session_state.stock_buffer = {}
        st.rerun()

    result = result.reset_index(drop=True)

    # =========================
    # PAGE CONTROL（復活部分）
    # =========================
    total = len(result)
    max_page = max(0, (total - 1) // PAGE_SIZE)

    st.session_state.page = max(0, min(st.session_state.page, max_page))

    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        if st.button("⬅️ 前へ"):
            st.session_state.page = max(0, st.session_state.page - 1)
            st.rerun()

    with col2:
        st.write(f"ページ: {st.session_state.page + 1} / {max_page + 1}")

    with col3:
        if st.button("次へ ➡️"):
            st.session_state.page = min(max_page, st.session_state.page + 1)
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
        url = row["url"]
        site = row["site"]
        ebay_url = row["ebay_url"]

        checked = st.session_state.stock_buffer.get(itemid, stock.get(itemid, False))

        if url:
            purchase_link = f"🔗 [仕入れリンク]({url})"
        else:
            purchase_link = "🔴 仕入れリンクなし"

        st.markdown(f"""
---
**No.{i}**  
{itemid} ｜ {site}  

{purchase_link}  
🛒 [eBay Seller Hub]({ebay_url})
""")

        checked = st.checkbox(
            "在庫なし",
            value=checked,
            key=f"stock_{itemid}"
        )

        # ★ここ修正済み
        st.session_state.stock_buffer[itemid] = checked