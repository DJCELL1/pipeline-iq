"""
Upload Jobs page — CSV import from ProMaster with column mapping + preview.
"""
import io
import streamlit as st
import pandas as pd
from utils.auth import require_auth, has_role
from utils import api_client as api

# Expected columns and their display names
EXPECTED_COLUMNS = {
    "job_number":   "Job Number",
    "job_name":     "Job Name",
    "company_name": "Company Name",
    "qs_name":      "QS Name",
    "quote_value":  "Quote Value",
    "quote_date":   "Quote Date",
    "status":       "Status",
}

# Common ProMaster / export header variants
AUTO_MAP = {
    "job number":    "job_number",
    "job no":        "job_number",
    "job no.":       "job_number",
    "reference":     "job_number",
    "ref":           "job_number",
    "job name":      "job_name",
    "description":   "job_name",
    "job description": "job_name",
    "client":        "company_name",
    "company":       "company_name",
    "client name":   "company_name",
    "qs":            "qs_name",
    "quantity surveyor": "qs_name",
    "qs name":       "qs_name",
    "value":         "quote_value",
    "quote value":   "quote_value",
    "tender value":  "quote_value",
    "amount":        "quote_value",
    "date":          "quote_date",
    "quote date":    "quote_date",
    "tender date":   "quote_date",
    "status":        "status",
}


def auto_detect_mapping(columns: list[str]) -> dict:
    mapping = {}
    for col in columns:
        key = AUTO_MAP.get(col.strip().lower())
        if key:
            mapping[col] = key
    return mapping


def show():
    require_auth()
    if not has_role("estimator", "admin"):
        st.error("Only Estimators and Admins can upload jobs.")
        return

    st.title("Upload Jobs")
    st.caption("Import jobs from ProMaster CSV export")

    uploaded = st.file_uploader(
        "Choose a CSV file",
        type=["csv"],
        help="ProMaster export CSV. Column headers will be auto-detected where possible.",
    )

    if not uploaded:
        st.info("Upload a CSV file to begin. Required columns: Job Number, Job Name. Optional: Company Name, QS Name, Quote Value, Quote Date, Status.")
        with st.expander("Expected CSV format"):
            sample = pd.DataFrame([
                {"Job Number": "HD-101", "Job Name": "Office Fitout", "Company Name": "BuildCo",
                 "QS Name": "John Smith", "Quote Value": "125000", "Quote Date": "01/06/2024", "Status": "Won"},
                {"Job Number": "HD-102", "Job Name": "Warehouse Fit", "Company Name": "Metro",
                 "QS Name": "Mike Brown", "Quote Value": "340000", "Quote Date": "15/06/2024", "Status": "At Quote"},
            ])
            st.dataframe(sample, hide_index=True)
        return

    try:
        df = pd.read_csv(uploaded)
    except Exception as e:
        st.error(f"Could not read CSV: {e}")
        return

    if df.empty:
        st.warning("The uploaded file is empty.")
        return

    st.success(f"File loaded: **{len(df)} rows**, **{len(df.columns)} columns**")
    st.subheader("Raw Preview (first 5 rows)")
    st.dataframe(df.head(5), use_container_width=True, hide_index=True)

    st.divider()
    st.subheader("Column Mapping")
    st.caption("Map your CSV columns to Pipeline IQ fields. Auto-detected where possible.")

    detected = auto_detect_mapping(list(df.columns))
    col_options = ["(skip)"] + list(df.columns)

    mapping = {}
    mc1, mc2 = st.columns(2)
    for i, (field, label) in enumerate(EXPECTED_COLUMNS.items()):
        col = mc1 if i % 2 == 0 else mc2
        with col:
            detected_col = next((c for c, f in detected.items() if f == field), "(skip)")
            selected = st.selectbox(
                f"{label} {'*' if field in ('job_number','job_name') else ''}",
                col_options,
                index=col_options.index(detected_col) if detected_col in col_options else 0,
                key=f"map_{field}",
            )
            if selected != "(skip)":
                mapping[field] = selected

    if "job_number" not in mapping or "job_name" not in mapping:
        st.warning("You must map at least **Job Number** and **Job Name** to proceed.")
        return

    st.divider()
    st.subheader("Mapped Preview")
    preview_df = pd.DataFrame()
    for field, col in mapping.items():
        preview_df[EXPECTED_COLUMNS[field]] = df[col]
    st.dataframe(preview_df.head(10), use_container_width=True, hide_index=True)

    st.divider()
    if st.button("🚀 Import Jobs", use_container_width=True, type="primary"):
        rows = []
        for _, row in df.iterrows():
            item = {}
            for field, col in mapping.items():
                val = row.get(col)
                if pd.isna(val):
                    val = None
                else:
                    val = str(val).strip()
                    if val == "":
                        val = None
                item[field] = val

            # Type coerce
            if item.get("quote_value"):
                try:
                    item["quote_value"] = float(str(item["quote_value"]).replace(",", "").replace("$", ""))
                except ValueError:
                    item["quote_value"] = None

            rows.append(item)

        with st.spinner(f"Importing {len(rows)} jobs…"):
            result = api.import_jobs(rows)

        if result:
            st.success(f"✅ Imported **{result['imported']}** jobs")
            if result["skipped"]:
                st.info(f"Skipped **{len(result['skipped'])}** duplicate job numbers: {', '.join(result['skipped_numbers'][:10])}")
            if result["errors"]:
                st.warning(f"**{len(result['errors'])}** errors occurred:")
                for e in result["errors"][:5]:
                    st.text(f"  {e['job_number']}: {e['error']}")
