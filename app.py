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
        "_row_id", "primary_id", "name_de", "fix_comment", "qa_comment", "status"
    ])
if "next_row_id" not in st.session_state:
    st.session_state.next_row_id = 1

if "_row_id" not in st.session_state.data.columns:
    st.session_state.data["_row_id"] = range(
        st.session_state.next_row_id,
        st.session_state.next_row_id + len(st.session_state.data)
    )
    st.session_state.next_row_id += len(st.session_state.data)

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
                        "_row_id": st.session_state.next_row_id,
                        "primary_id": parts[0],
                        "name_de": "",
                        "fix_comment": "",
                        "qa_comment": "",
                        "status": "New"
                    })
                    st.session_state.next_row_id += 1
                else:
                    new_data.append({
                        "_row_id": st.session_state.next_row_id,
                        "primary_id": parts[0],
                        "name_de": parts[1],
                        "fix_comment": "",
                        "qa_comment": "",
                        "status": "New"
                    })
                    st.session_state.next_row_id += 1

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

# ---- COLUMN FILTERS (Excel-like dropdowns) ----
st.subheader("🔎 Filters")
filtered_df = df_view.copy()

filter_column_names = [c for c in filtered_df.columns if c != "_row_id"]
filter_columns = st.columns(len(filter_column_names))
selected_filters = {}

for idx, col_name in enumerate(filter_column_names):
    available_values = sorted(
        df_view[col_name].dropna().astype(str).unique().tolist()
    )
    with filter_columns[idx]:
        with st.popover(f"🔽 {col_name}"):
            selected_filters[col_name] = st.multiselect(
                f"Values for {col_name}",
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
    status_select_options = ["Fixed", "Filled all languages"]
else:
    disabled_columns = ["primary_id", "name_de", "fix_comment"]
    status_select_options = ["Sabine, check DE", "Ready to fill all languages"]

allow_row_delete = role in ["Me", "Katya"]

edited_df = st.data_editor(
    filtered_df.set_index("_row_id"),
    use_container_width=True,
    num_rows="dynamic" if allow_row_delete else "fixed",
    hide_index=True,
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
edited_df = edited_df.reset_index()

current_df = st.session_state.data.copy()
current_df = current_df.set_index("_row_id")
edited_df_indexed = edited_df.set_index("_row_id")
visible_ids_before_edit = set(filtered_df["_row_id"].tolist())

# Update existing rows.
common_ids = current_df.index.intersection(edited_df_indexed.index)
current_df.update(edited_df_indexed.loc[common_ids])

# Apply deletions for roles that are allowed to delete rows.
if allow_row_delete:
    existing_ids_after_edit = set(common_ids.tolist())
    deleted_ids = visible_ids_before_edit - existing_ids_after_edit
    if deleted_ids:
        current_df = current_df.drop(index=list(deleted_ids), errors="ignore")

# Append newly added rows from editor.
new_rows = edited_df_indexed.loc[~edited_df_indexed.index.isin(current_df.index)].copy()
if not new_rows.empty:
    new_rows = new_rows[~new_rows.index.to_series().isna()]
    if not new_rows.empty:
        new_rows = new_rows.reset_index(drop=True)
        new_ids = range(
            st.session_state.next_row_id,
            st.session_state.next_row_id + len(new_rows)
        )
        new_rows.insert(0, "_row_id", list(new_ids))
        new_rows["status"] = new_rows["status"].fillna("").replace("", "New")
        st.session_state.next_row_id += len(new_rows)
        new_rows = new_rows.set_index("_row_id")
        current_df = pd.concat([current_df, new_rows], axis=0)

current_df["status"] = current_df["status"].fillna("").replace("", "New")
st.session_state.data = current_df.reset_index()

# ---- DOWNLOAD ----
st.subheader("💾 Export")

output = io.BytesIO()
with pd.ExcelWriter(output, engine='openpyxl') as writer:
    st.session_state.data.drop(columns=["_row_id"], errors="ignore").to_excel(
        writer,
        index=False
    )
output.seek(0)

st.download_button(
    "Download Excel",
    data=output,
    file_name="product_tracker.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
