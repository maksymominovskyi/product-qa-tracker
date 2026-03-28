import streamlit as st
import pandas as pd
import io

st.set_page_config(page_title="Product QA Tracker", layout="wide")

st.title("🛠️ Product QA Tracker")

# ---- INIT SESSION STATE ----
if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=[
        "primary_id", "name_de", "fix_comment", "qa_comment", "status"
    ])

# ---- PASTE BOX ----
st.subheader("📥 Paste data")

paste_input = st.text_area(
    "Paste primary_id or primary_id + name_de (tab separated):",
    height=150
)

if st.button("➕ Add data"):
    if paste_input.strip() != "":
        rows = paste_input.strip().split("\n")

        new_data = []

        for row in rows:
            parts = row.split("\t")

            if len(parts) == 1:
                new_data.append({
                    "primary_id": parts[0],
                    "name_de": "",
                    "fix_comment": "",
                    "qa_comment": "",
                    "status": "New"
                })
            else:
                new_data.append({
                    "primary_id": parts[0],
                    "name_de": parts[1],
                    "fix_comment": "",
                    "qa_comment": "",
                    "status": "New"
                })

        df_new = pd.DataFrame(new_data)

        st.session_state.data = pd.concat(
            [st.session_state.data, df_new],
            ignore_index=True
        )

        st.success(f"Added {len(df_new)} rows")

# ---- ROLE SELECTOR ----
st.subheader("👤 Role")

role = st.selectbox("Select your role", ["Me", "Katya", "Sabine"])

df = st.session_state.data.copy()

# ---- FILTERING ----
if role == "Me":
    df_view = df[df["status"].isin(["New", "Fixed"])]
elif role == "Katya":
    df_view = df[df["status"].isin(["Need fix", "Ready to fill all languages"])]
else:
    df_view = df[df["status"] == "Sabine, check DE"]

st.write(f"Showing {len(df_view)} records")

# ---- EDIT TABLE ----
edited_df = st.data_editor(df_view, use_container_width=True, num_rows="dynamic")

# ---- UPDATE DATA ----
st.session_state.data.update(edited_df)

# ---- DOWNLOAD ----
st.subheader("💾 Export")

output = io.BytesIO()
with pd.ExcelWriter(output, engine='openpyxl') as writer:
    st.session_state.data.to_excel(writer, index=False)
output.seek(0)

st.download_button(
    "Download Excel",
    data=output,
    file_name="product_tracker.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
