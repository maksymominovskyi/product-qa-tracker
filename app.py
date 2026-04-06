import streamlit as st
import pandas as pd
import io
from pathlib import Path
import sqlite3

STATUS_OPTIONS = [
    "New",
    "Need fix",
    "Fixed",
    "Sabine, check DE",
    "Ready to fill all languages",
    "Filled all languages",
]
DB_FILE = Path("product_tracker_data.db")
TABLE_NAME = "tracker_rows"


def load_persistent_data() -> pd.DataFrame:
    expected_cols = ["primary_id", "name_de", "fix_comment", "qa_comment", "status"]
    if not DB_FILE.exists():
        return pd.DataFrame(columns=expected_cols)

    with sqlite3.connect(DB_FILE) as conn:
        loaded_df = pd.read_sql_query(
            f"SELECT primary_id, name_de, fix_comment, qa_comment, status FROM {TABLE_NAME} ORDER BY id",
            conn
        )

    for col in expected_cols:
        if col not in loaded_df.columns:
            loaded_df[col] = ""
    return loaded_df[expected_cols]


def save_persistent_data(df: pd.DataFrame) -> None:
    export_df = df[["primary_id", "name_de", "fix_comment", "qa_comment", "status"]].copy()
    export_df = export_df.fillna("")
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(f"DELETE FROM {TABLE_NAME}")
        conn.commit()
        export_df.to_sql(TABLE_NAME, conn, if_exists="append", index=False)


def init_db() -> None:
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                primary_id TEXT,
                name_de TEXT,
                fix_comment TEXT,
                qa_comment TEXT,
                status TEXT
            )
            """
        )
        conn.commit()


st.set_page_config(page_title="Product QA Tracker", layout="wide")

st.title("🛠️ Product QA Tracker")
init_db()

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

# ---- COLUMN FILTERS ----
st.subheader("🔎 Filters")
filtered_df = df_view.copy()

filter_column_names = list(filtered_df.columns)
selected_filters = {}

with st.expander("Open filters", expanded=False):
    for col_name in filter_column_names:
        available_values = sorted(df_view[col_name].dropna().astype(str).unique().tolist())
        selected_filters[col_name] = st.multiselect(
            f"{col_name}",
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
for text_col in ["fix_comment", "qa_comment"]:
    if text_col in filtered_df.columns:
        filtered_df[text_col] = filtered_df[text_col].fillna("").astype(str)

if "status" in filtered_df.columns:
    filtered_df["status"] = filtered_df["status"].fillna("").astype(str)

if role == "Me":
    disabled_columns = []
    allowed_status_options = STATUS_OPTIONS
elif role == "Katya":
    disabled_columns = ["fix_comment", "qa_comment"]
    allowed_status_options = ["New", "Fixed", "Filled all languages"]
else:
    disabled_columns = ["primary_id", "name_de"]
    allowed_status_options = ["Sabine, check DE", "Ready to fill all languages"]

current_visible_statuses = []
if "status" in filtered_df.columns:
    current_visible_statuses = filtered_df["status"].dropna().astype(str).unique().tolist()

status_option_set = set(allowed_status_options).union(set(current_visible_statuses))
status_select_options = [status for status in STATUS_OPTIONS if status in status_option_set]

allow_row_delete = role in ["Me", "Katya"]

edited_df = st.data_editor(
    filtered_df,
    key="qa_editor_table",
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

save_clicked = st.button("💾 Save changes")
if save_clicked:
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
    current_df = current_df.reset_index(drop=True)
    st.session_state.data = current_df

    save_persistent_data(st.session_state.data)
    st.success("Changes saved.")

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
