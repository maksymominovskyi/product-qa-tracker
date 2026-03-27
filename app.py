import streamlit as st
import pandas as pd

st.set_page_config(page_title="Product QA Tracker", layout="wide")

st.title("🛠️ Product QA Tracker")

# ---- Upload file ----
uploaded_file = st.file_uploader("Upload Excel file", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    # ---- Ensure columns exist ----
    for col in ["fix_comment", "qa_comment", "status"]:
        if col not in df.columns:
            df[col] = ""

    # ---- Default status ----
    df["status"] = df["status"].replace("", "New")

    # ---- Role selection ----
    role = st.selectbox("Select your role", ["Me", "Katya", "Sabine"])

    # ---- Filtering ----
    if role == "Me":
        df_view = df[df["status"].isin(["New", "Fixed"])]
    elif role == "Katya":
        df_view = df[df["status"].isin(["Need fix", "Ready to fill all languages"])]
    else:
        df_view = df[df["status"] == "Sabine, check DE"]

    st.write(f"Showing {len(df_view)} records")

    # ---- Editable table ----
    edited_df = st.data_editor(df_view, use_container_width=True)

    st.download_button(
        "💾 Download updated file",
        edited_df.to_excel(index=False),
        file_name="updated_products.xlsx"
    )
