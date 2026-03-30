import streamlit as st
import pandas as pd
import io
from pathlib import Path

STATUS_OPTIONS = [
    "New",
    "Need fix",
    "Fixed",
    "Sabine, check DE",
    "Ready to fill all languages",
    "Filled all languages",
]
DATA_FILE = Path("product_tracker_data.xlsx")


def load_persistent_data() -> pd.DataFrame:
    if DATA_FILE.exists():
        loaded_df = pd.read_excel(DATA_FILE)
        expected_cols = ["primary_id", "name_de", "fix_comment", "qa_comment", "status"]
        for col in expected_cols:
            if col not in loaded_df.columns:
                loaded_df[col] = ""
        return loaded_df[expected_cols]
    return pd.DataFrame(
        columns=["primary_id", "name_de", "fix_comment", "qa_comment", "status"]
    )


def save_persistent_data(df: pd.DataFrame) -> None:
    export_df = df[["primary_id", "name_de", "fix_comment", "qa_comment", "status"]].copy()
    export_df.to_excel(DATA_FILE, index=False)

st.set_page_config(page_title="Product QA Tracker", layout="wide")

st.title("🛠️ Product QA Tracker")

# ---- INIT SESSION STATE ----
if "data" not in st.session_state:
    st.session_state.data = load_persistent_data()

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
            save_persistent_data(st.session_state.data)
            st.success(f"Added {len(df_new)} rows")

# Keep indexes stable and status normalized.
st.session_state.data = st.session_state.data.reset_index(drop=True)
st.session_state.data["status"] = (
    st.session_state.data["status"].fillna("").replace("", "New")
)

df = st.session_state.data.copy()

# ---- FILTERING BY ROLE ----
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
    df_view = df_view.drop(columns=["fix_comment"], errors="ignore")

# ---- COLUMN FILTERS (dropdown near each column name) ----
st.subheader("🔎 Filters")
filtered_df = df_view.copy()

filter_column_names = list(filtered_df.columns)
filter_columns = st.columns(len(filter_column_names))
selected_filters = {}

for idx, col_name in enumerate(filter_column_names):
    available_values = sorted(df_view[col_name].dropna().astype(str).unique().tolist())
    with filter_columns[idx]:
        with st.popover(f"{col_name} ⏷"):
            selected_filters[col_name] = st.multiselect(
                "Select values",
                options=available_values,
                key=f"filter_values_{role}_{col_name}"
            )

for col_name, selected_values in selected_filters.items():
    if selected_values:
        filtered_df = filtered_df[
            filtered_df[col_name].astype(str).isin(selected_values)
        ]

st.write(f"Showing {len(filtered_df)} records")

# ---- EDIT TABLE ----
if role == "Me":
    disabled_columns = []
    status_select_options = STATUS_OPTIONS
elif role == "Katya":
    disabled_columns = ["fix_comment", "qa_comment"]
    status_select_options = ["New", "Fixed", "Filled all languages"]
else:
    disabled_columns = ["primary_id", "name_de"]
    status_select_options = ["Sabine, check DE", "Ready to fill all languages"]

allow_row_delete = role in ["Me", "Katya"]

edited_df = st.data_editor(
    filtered_df,
    use_container_width=True,
    num_rows="dynamic" if allow_row_delete else "fixed",
    hide_index=True,
    disabled=disabled_columns,
    column_config={
        "fix_comment": st.column_config.TextColumn("fix_comment"),
        "qa_comment": st.column_config.TextColumn("qa_comment"),
        "status": st.column_config.SelectboxColumn(
            "status",
            options=status_select_options,
            required=True,
        ),
    },
)

# ---- UPDATE DATA ----
current_df = st.session_state.data.copy()
visible_ids_before_edit = set(filtered_df.index.tolist())
edited_existing = edited_df[edited_df.index.isin(current_df.index)]

# Update existing rows by index.
current_df.update(edited_existing)

# Apply deletions for roles that are allowed to delete rows.
if allow_row_delete:
    existing_ids_after_edit = set(edited_existing.index.tolist())
    deleted_ids = visible_ids_before_edit - existing_ids_after_edit
    if deleted_ids:
        current_df = current_df.drop(index=list(deleted_ids), errors="ignore")

# Append newly added rows from editor.
new_rows = edited_df[~edited_df.index.isin(current_df.index)].copy()
if not new_rows.empty:
    new_rows = new_rows.reset_index(drop=True)
    new_rows["status"] = new_rows["status"].fillna("").replace("", "New")
    current_df = pd.concat([current_df, new_rows], ignore_index=True)

current_df["status"] = current_df["status"].fillna("").replace("", "New")
st.session_state.data = current_df.reset_index(drop=True)
save_persistent_data(st.session_state.data)

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
