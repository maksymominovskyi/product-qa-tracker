import streamlit as st
import pandas as pd
import io

STATUS_OPTIONS = [
    "New",
    "Need fix",
    "Fixed",
    "Sabine, check DE",
    "Ready to fill all languages",
    "Filled all languages",
]

st.set_page_config(page_title="Product QA Tracker", layout="wide")

st.title("🛠️ Product QA Tracker")

# ---- INIT SESSION STATE ----
if "data" not in st.session_state:
    st.session_state.data = pd.DataFrame(columns=[
        "primary_id", "name_de", "fix_comment", "qa_comment", "status"
    ])

# ---- ROLE FROM URL ----
ROLE_PARAM_TO_LABEL = {
    "me": "Me",
    "katya": "Katya",
    "sabine": "Sabine",
}

query_role = st.query_params.get("role", "me")
query_role = str(query_role).lower()

if query_role not in ROLE_PARAM_TO_LABEL:
    st.error(
        "Unknown role in URL. Allowed values: role=me, role=katya, role=sabine."
    )
    st.stop()

role = ROLE_PARAM_TO_LABEL[query_role]

# ---- PASTE BOX (Me & Katya only) ----
if role in ["Me", "Katya"]:
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

df = st.session_state.data.copy()
df["status"] = df["status"].fillna("").replace("", "New")

# ---- FILTERING ----
if role == "Me":
    df_view = df
elif role == "Katya":
    df_view = df[
        df["status"].isin([
            "New",
            "Need fix",
            "Fixed",
            "Sabine, check DE",
            "Ready to fill all languages",
            "Filled all languages",
        ])
    ]
else:
    df_view = df[
        df["status"].isin([
            "Sabine, check DE",
            "Ready to fill all languages",
            "Filled all languages",
        ])
    ]

# ---- COLUMN FILTERS ----
st.subheader("🔎 Filters")
filtered_df = df_view.copy()

filter_columns = st.columns(len(filtered_df.columns))
for idx, col_name in enumerate(filtered_df.columns):
    filter_value = filter_columns[idx].text_input(
        col_name,
        key=f"filter_{role}_{col_name}"
    ).strip()
    if filter_value:
        filtered_df = filtered_df[
            filtered_df[col_name].astype(str).str.contains(
                filter_value,
                case=False,
                na=False
            )
        ]

st.write(f"Showing {len(filtered_df)} records")

# ---- EDIT TABLE ----
if role == "Me":
    disabled_columns = []
    status_select_options = STATUS_OPTIONS
elif role == "Katya":
    disabled_columns = ["fix_comment", "qa_comment"]
    status_select_options = ["Fixed", "Filled all languages"]
else:
    disabled_columns = ["primary_id", "name_de", "fix_comment"]
    status_select_options = ["Sabine, check DE", "Ready to fill all languages"]

edited_df = st.data_editor(
    filtered_df,
    use_container_width=True,
    num_rows="dynamic",
    disabled=disabled_columns,
    column_config={
        "status": st.column_config.SelectboxColumn(
            "status",
            options=status_select_options,
            required=True,
        ),
    },
)

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
