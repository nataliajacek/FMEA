import streamlit as st
import pandas as pd
from io import BytesIO
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openai import OpenAI
import json
import base64

# -----------------------------
# OPENAI CLIENT
# -----------------------------
client = OpenAI(api_key=st.secrets["openai"]["api_key"])

st.title("AI-Assisted FMEA Generator – Powered by GPT-4.1-mini")

# -----------------------------
# PROJECT INFO INPUTS
# -----------------------------
user_name = st.text_input("1. User Name")
product_name = st.text_input("2. Product / Prototype Name")
product_description = st.text_area("Product Description")
subsystem = st.text_input("3. Subsystem to perform FMEA")
parts_input = st.text_area("4. List of Parts / Components (one per line)")
functions_input = st.text_area("5. Functions (one per line)")
requirements_input = st.text_area("6. Main Specs / Requirements (one per line)")
version = st.text_input("7. Version / Date")

# -----------------------------
# OPTIONAL FILE UPLOAD
# -----------------------------
st.subheader("Optional: Upload files or images (PDF, TXT, JPG, PNG)")
uploaded_files = st.file_uploader(
    "Upload files/images for extra context",
    type=["pdf","txt","png","jpg","jpeg"],
    accept_multiple_files=True
)

def extract_text(files):
    text = ""
    images_base64 = []
    for file in files:
        try:
            if file.type == "text/plain":
                text += file.read().decode("utf-8") + "\n"
            elif file.type.startswith("image"):
                images_base64.append(base64.b64encode(file.read()).decode())
            elif file.type == "application/pdf":
                # fallback: just note the PDF was uploaded
                text += f"[PDF uploaded: {file.name}]\n"
        except:
            continue
    return text, images_base64

file_text, images_base64 = extract_text(uploaded_files) if uploaded_files else ("", [])

# -----------------------------
# TEST MATRIX
# -----------------------------
test_columns = [
    "INVESTIGATION & TESTING",
    "VENDOR - PART",
    "DESIGN CHANGE",
    "DIM & WORST CASE",
    "SIMULATION",
    "CHARACTERIZE",
    "CPPP",
    "DIAGNOSTICS",
    "FUNCTIONALITY",
    "OOBE & INSTALL",
    "SYSTEM TEST",
    "SIT E2E APP",
    "HALT",
    "ALT",
    "ROBUSTNESS",
    "REGS EMC",
    "REGSSAFETY",
    "USABILITY",
    "SW-FW TESTS",
    "MFG TESTS",
    "MAINTENANCE",
    "SERVICEABILITY"
]

# -----------------------------
# HELPER FUNCTIONS
# -----------------------------
def safe_json(text):
    try:
        start = text.find("[")
        end = text.rfind("]")
        if start != -1 and end != -1:
            return json.loads(text[start:end+1])
    except:
        pass
    return []

def expand_engineering_lists(functions, requirements, parts, file_text):
    prompt = f"""
Product: {product_name}
Description: {product_description}

Existing functions:
{functions}

Existing requirements:
{requirements}

Existing parts:
{parts}

Additional file information:
{file_text}

Check if important functions, requirements, or parts are missing.
Only add items if they are truly essential.

Return JSON:

{{
"functions":[],
"requirements":[],
"parts":[]
}}
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role":"user","content":prompt}],
            temperature=0.2
        )
        txt = response.choices[0].message.content
        data = json.loads(txt[txt.find("{"):txt.rfind("}")+1])
        functions += data.get("functions", [])
        requirements += data.get("requirements", [])
        parts += data.get("parts", [])
    except:
        pass
    return list(set(functions)), list(set(requirements)), list(set(parts))

# -----------------------------
# FMEA GENERATION
# -----------------------------
def generate_fmea():
    functions = [f.strip() for f in functions_input.split("\n") if f.strip()]
    requirements = [r.strip() for r in requirements_input.split("\n") if r.strip()]
    parts = [p.strip() for p in parts_input.split("\n") if p.strip()]

    functions, requirements, parts = expand_engineering_lists(functions, requirements, parts, file_text)

    if not functions:
        functions=["General product operation"]
    if not requirements:
        requirements=["General safety"]

    rows = []

    with st.spinner("Generating FMEA, please wait..."):
        for function in functions:
            for requirement in requirements:
                prompt = f"""
Product: {product_name}
Description: {product_description}
Subsystem: {subsystem}
Function: {function}
Requirement: {requirement}
Parts: {parts}
Additional info: {file_text}

Generate 5 realistic failure modes for this function/requirement.
Include:
- Failure Scenario
- Part
- Failure Mode
- End Effects
- 2-3 Causes
- Current Design Controls
- Recommended Actions (2-3)
- Owner (Mechanical, Electrical, Reliability, Quality, Manufacturing, Firmware/Software, UX)
- Execution Phase (Concept, Design, Prototype, Validation, Production, Field)
- Severity (1-5)
- Occurrence (1-4)
- Detectability (1-3)
- Estimated Cost (Low, Medium, High, Very High)
- Recommended tests from this list: {', '.join(test_columns)}
- References (at least 1 link if possible)

Return ONLY valid JSON list.
"""
                try:
                    response = client.chat.completions.create(
                        model="gpt-4.1-mini",
                        messages=[{"role":"user","content":prompt}],
                        temperature=0.3
                    )
                    failures = safe_json(response.choices[0].message.content)
                except Exception as e:
                    st.error(f"AI failed for {function} / {requirement}: {e}")
                    continue

                for f in failures:
                    causes = f.get("Causes", [])
                    if isinstance(causes, str):
                        causes = [causes]
                    causes = [c for c in causes if c.strip()]
                    causes = causes[:3]  # max 3 causes

                    for cause in causes:
                        S = int(f.get("Severity", 3))
                        O = int(f.get("Occurrence", 2))
                        D = int(f.get("Detectability", 2))
                        rpn = S*O*D
                        cost = f.get("Estimated Cost","Medium")

                        rows.append({
                            "Failure Scenario": f.get("Failure Scenario",""),
                            "Function": function,
                            "Requirement": requirement,
                            "Part": f.get("Part",""),
                            "Failure Mode": f.get("Failure Mode",""),
                            "End Effects": f.get("End Effects",""),
                            "Causes": cause,
                            "Current Design Controls": f.get("Controls",""),
                            "Severity (S)": S,
                            "Occurrence (O)": O,
                            "Detectability (D)": D,
                            "RPN": rpn,
                            "Estimated Cost": cost,
                            "Recommended Actions": ", ".join(f.get("Actions",[])),
                            "Owner": f.get("Owner",""),
                            "Execution Phase": f.get("Execution Phase",""),
                            "Tests": ", ".join(f.get("tests",[])),
                            "References": ", ".join(f.get("References",[]))
                        })
    return pd.DataFrame(rows)

# -----------------------------
# GENERATE BUTTON
# -----------------------------
if st.button("Generate FMEA"):
    df = generate_fmea()
    if df.empty:
        st.warning("Enter at least one function and requirement.")
    else:
        st.session_state.df = df

# -----------------------------
# EDITABLE TABLE
# -----------------------------
if "df" in st.session_state:
    edited_df = st.data_editor(
        st.session_state.df,
        use_container_width=True
    )

    # -----------------------------
    # EXCEL EXPORT
    # -----------------------------
    wb = Workbook()
    ws = wb.active
    ws.title = "FMEA"

    headers = list(edited_df.columns)
    ws.append(headers)

    for r_idx, row in enumerate(edited_df.values, start=2):
        for c_idx, val in enumerate(row, start=1):
            if val is None:
                val = ""
            if isinstance(val, list):
                val = ", ".join(val)
            ws.cell(row=r_idx, column=c_idx, value=str(val))

    # Format header row
    for col in range(1, len(headers)+1):
        cell = ws.cell(row=1, column=col)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="4F81BD", end_color="4F81BD", fill_type="solid")
        cell.alignment = Alignment(horizontal="center", vertical="center")

    output = BytesIO()
    wb.save(output)

    st.download_button(
        "Download Excel File",
        output.getvalue(),
        file_name=f"FMEA_{product_name}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
