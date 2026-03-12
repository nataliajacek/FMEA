import streamlit as st
import pandas as pd
from io import BytesIO
from openpyxl import Workbook
from openai import OpenAI
import json
import base64
import pdfplumber

client = OpenAI(api_key=st.secrets["openai"]["api_key"])

st.title("AI-Assisted FMEA Generator – Powered by GPT-4.1-mini")

# ----------------------------
# INPUTS
# ----------------------------

user_name = st.text_input("1. User name")

product_name = st.text_input("2. Product / Prototype name")

product_description = st.text_area("Product description")

subsystem = st.text_input("3. Subsystem to perform FMEA")

parts_input = st.text_area("4. List of parts (one per line)")

functions_input = st.text_area("5. Functions (one per line)")

requirements_input = st.text_area("6. Main specs / requirements (one per line)")

version = st.text_input("7. Version / date")

# ----------------------------
# FILE UPLOAD
# ----------------------------

st.subheader("Optional files or images")

uploaded_files = st.file_uploader(
"Upload diagrams, datasheets or photos",
type=["png","jpg","jpeg","pdf","txt"],
accept_multiple_files=True
)

# ----------------------------
# FILE PROCESSING
# ----------------------------

def extract_text(files):

    text = ""
    images = []

    for file in files:

        if file.type == "application/pdf":

            try:
                with pdfplumber.open(file) as pdf:
                    for page in pdf.pages:
                        page_text = page.extract_text()
                        if page_text:
                            text += page_text + "\n"
            except:
                pass

        elif file.type == "text/plain":

            try:
                text += file.read().decode("utf-8")
            except:
                pass

        elif file.type.startswith("image"):

            try:
                img = base64.b64encode(file.read()).decode()
                images.append(img)
            except:
                pass

    return text, images

# ----------------------------
# SAFE JSON PARSER
# ----------------------------

def safe_json(text):

    try:

        start = text.find("[")
        end = text.rfind("]")

        if start != -1 and end != -1:
            return json.loads(text[start:end+1])

    except:
        pass

    return []

# ----------------------------
# ADD MISSING ENGINEERING ITEMS
# ----------------------------

def expand_engineering_lists(functions,requirements,parts,file_text):

    prompt=f"""
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

        r = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role":"user","content":prompt}],
        temperature=0.2
        )

        txt = r.choices[0].message.content
        data = json.loads(txt[txt.find("{"):txt.rfind("}")+1])

        functions += data["functions"]
        requirements += data["requirements"]
        parts += data["parts"]

    except:
        pass

    return list(set(functions)), list(set(requirements)), list(set(parts))

# ----------------------------
# FMEA GENERATION
# ----------------------------

def generate_fmea():

    functions=[f.strip() for f in functions_input.split("\n") if f.strip()]
    requirements=[r.strip() for r in requirements_input.split("\n") if r.strip()]
    parts=[p.strip() for p in parts_input.split("\n") if p.strip()]

    file_text=""
    images=[]

    if uploaded_files:
        file_text,images = extract_text(uploaded_files)

    functions,requirements,parts = expand_engineering_lists(
        functions,requirements,parts,file_text
    )

    if not functions:
        functions=["General product operation"]

    if not requirements:
        requirements=["General safety"]

    rows=[]

    for function in functions:

        prompt=f"""
Product: {product_name}
Description: {product_description}
Subsystem: {subsystem}

Parts:
{parts}

Function:
{function}

Requirements:
{requirements}

Additional info:
{file_text}

Generate MANY realistic engineering FMEA failures.

For EACH requirement generate 5-8 failures.

Return JSON list with:

Failure Scenario
Requirement
Part
Failure Mode
End Effects
Causes
Controls
Actions
Owner
Execution Phase
Severity
Occurrence
Detectability
Estimated Cost
tests
References
"""

        content=[{"type":"text","text":prompt}]

        for img in images:
            content.append({
                "type":"image_url",
                "image_url":{"url":f"data:image/jpeg;base64,{img}"}
            })

        r = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role":"user","content":content}],
            temperature=0.3
        )

        failures=safe_json(r.choices[0].message.content)

        for f in failures:

            causes=f.get("Causes",[""])

            for cause in causes:

                S=int(f.get("Severity",3))
                O=int(f.get("Occurrence",2))
                D=int(f.get("Detectability",2))

                rpn=S*O*D

                rows.append({
                "Failure Scenario":f.get("Failure Scenario",""),
                "Function":function,
                "Requirement":f.get("Requirement",""),
                "Part":f.get("Part",""),
                "Failure Mode":f.get("Failure Mode",""),
                "End Effects":f.get("End Effects",""),
                "Causes":cause,
                "Controls":f.get("Controls",""),
                "Severity":S,
                "Occurrence":O,
                "Detectability":D,
                "RPN":rpn,
                "Recommended Actions":",".join(f.get("Actions",[])),
                "Owner":f.get("Owner",""),
                "Execution Phase":f.get("Execution Phase",""),
                "Tests":",".join(f.get("tests",[])),
                "References":",".join(f.get("References",[])),
                "Estimated Cost":f.get("Estimated Cost","Medium")
                })

    return pd.DataFrame(rows)

# ----------------------------
# GENERATE BUTTON
# ----------------------------

if st.button("Generate FMEA"):

    df = generate_fmea()

    if df.empty:
        st.warning("AI returned no results. Try again.")
    else:
        st.session_state.df=df

# ----------------------------
# EDITABLE TABLE
# ----------------------------

if "df" in st.session_state:

    edited_df = st.data_editor(
        st.session_state.df,
        use_container_width=True
    )

# ----------------------------
# EXCEL EXPORT
# ----------------------------

    wb=Workbook()
    ws=wb.active

    ws.append(list(edited_df.columns))

    for r,row in enumerate(edited_df.values,2):
        for c,val in enumerate(row,1):

            if isinstance(val,list):
                val=", ".join(val)

            if val is None:
                val=""

            ws.cell(row=r,column=c,value=str(val))

    buffer=BytesIO()
    wb.save(buffer)

    st.download_button(
        "Download Excel",
        buffer.getvalue(),
        file_name=f"FMEA_{product_name}.xlsx"
    )
