import streamlit as st
import pandas as pd
import openai
import json
import os
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.utils import get_column_letter

openai.api_key = os.getenv("OPENAI_API_KEY")

# -------------------------------------------------
# TEST MATRIX (from your friend's Excel generator)
# -------------------------------------------------

TESTS_LIST = [
"DESIGN CHANGE","DIM & WORST CASE","SIMULATION","REDESIGN","CHARACTERIZE",
"CPPP","WORST CASING-TOLERANCE","FUNCTIONALITY TEST","DOE - SIGNAL LOSS TESTS",
"OOBE & INSTALL","SYSTEM TEST WORKFLOWS","SPECS PERFORMANCE XPUT","SIT E2E APP",
"USER ABUSE - TORTURE","HALT - HIGH ACCELERATED","BEST-BOARDS STRIFE TEST",
"ALT - LIFE TEST","ROBUSTNESS","REGS EMC","REGS SAFETY","USABILITY",
"SW-FW TESTS","DATA QUALITY","VENDOR PQAP","HASS MFG TESTS","MFG LINE TESTS",
"MFG PPA","MAINTENANCE","DIAGNOSABILITY","SERVICEABILITY"
]

FAILURE_MODES = [
"degradation",
"partial degradation",
"total failure-breakage"
]

# -------------------------------------------------
# AI FMEA ENGINE (from fmea_engine.py)
# -------------------------------------------------

def clamp(value):
    value = int(value)
    return max(1,min(5,value))

def build_prompt(form_data, part):

    return f"""
You are an expert FMEA engineer.

Product: {form_data.get('object_name')}
Part: {part}
Specifications: {form_data.get('specs')}
Requirements: {form_data.get('requirements')}
Reliability: {form_data.get('reliability')}
Safety: {form_data.get('safety')}

Generate multiple realistic failure scenarios.

Return ONLY JSON:

[
{{
"Failure":"",
"Function":"",
"Failure Mode":"degradation | partial degradation | total failure-breakage",
"Effects":"",
"Causes":"",
"Severity":1,
"Occurrence":1,
"Detectability":1,
"Cost":1,
"Links":""
}}
]
"""

def generate_fmea(form_data):

    parts = form_data.get("piezas","").split(",")

    all_failures = []

    for part in parts:

        part = part.strip()

        if part == "":
            continue

        prompt = build_prompt(form_data, part)

        response = openai.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role":"user","content":prompt}],
            temperature=0.3
        )

        text = response.choices[0].message.content

        # Clean markdown formatting
        if "```" in text:
            text = text.split("```")[1]
            text = text.replace("json","")

        text = text.strip()

        try:
            failures = json.loads(text)
        except:
            st.warning("AI returned invalid JSON. Showing raw response.")
            st.write(text)
            continue

        for f in failures:

            if f.get("Failure Mode") not in FAILURE_MODES:
                f["Failure Mode"] = "degradation"

            f["Severity"] = clamp(f.get("Severity",1))
            f["Occurrence"] = clamp(f.get("Occurrence",1))
            f["Detectability"] = clamp(f.get("Detectability",1))

            f["Part"] = part

            all_failures.append(f)

    return all_failures

# -------------------------------------------------
# PROFESSIONAL EXCEL GENERATOR (from excel_formatter)
# -------------------------------------------------

def create_fmea_excel(data, form_data):

    df = pd.DataFrame(data)

    calc_cols=['RPN','Priority','Risk Level','Ranking']

    for col in calc_cols:
        df[col]=""

    for t in TESTS_LIST:
        df[t]=""

    base_cols = [
        "Part","Failure","Function","Failure Mode","Effects","Causes",
        "Severity","Occurrence","Detectability","Cost",
        "RPN","Priority","Risk Level","Ranking","Links"
    ]

    file_name = f"FMEA_{form_data.get('project','Project')}.xlsx"

    df[base_cols+TESTS_LIST].to_excel(file_name,index=False,startrow=5)

    wb = load_workbook(file_name)
    ws = wb.active

    # Header Info
    info = [
        ("PROJECT:",form_data.get("project")),
        ("USER NAME:",form_data.get("user_name")),
        ("VERSION:",form_data.get("version")),
        ("OBJECT NAME:",form_data.get("object_name"))
    ]

    for i,(l,v) in enumerate(info,1):
        ws[f"A{i}"],ws[f"B{i}"]=l,v
        ws[f"A{i}"].font=Font(bold=True)

    # Title format
    blue_fill = PatternFill(start_color="1F4E78",fill_type="solid")
    white_font = Font(color="FFFFFF",bold=True)

    for col in range(1,16):
        cell=ws.cell(row=6,column=col)
        cell.fill=blue_fill
        cell.font=white_font
        cell.alignment=Alignment(horizontal="center")

    last_row = ws.max_row

    for r in range(7,last_row+1):

        ws[f"K{r}"]=f"=G{r}*H{r}*I{r}"
        ws[f"L{r}"]=f"=J{r}*K{r}"
        ws[f"M{r}"]=f'=IF(K{r}<=8,"LOW",IF(K{r}<=18,"MEDIUM",IF(K{r}<=27,"URGENT","CRITICAL")))'
        ws[f"N{r}"]=f"=RANK(L{r},$L$7:$L${last_row},0)"

    # TEST MATRIX

    start_test_col=16

    ws.merge_cells(
        start_row=1,
        start_column=start_test_col,
        end_row=5,
        end_column=start_test_col+len(TESTS_LIST)-1
    )

    top_title = ws.cell(row=1,column=start_test_col)
    top_title.value="INVESTIGATION & TESTING"
    top_title.font=Font(bold=True,size=14)
    top_title.alignment=Alignment(horizontal="center",vertical="center")

    for i,test in enumerate(TESTS_LIST):

        col=start_test_col+i

        cell=ws.cell(row=6,column=col)

        cell.value=test

        cell.alignment=Alignment(textRotation=90,horizontal="center",vertical="center")

        ws.column_dimensions[get_column_letter(col)].width=5

    wb.save(file_name)

    return file_name


# -------------------------------------------------
# STREAMLIT WEB UI (your style)
# -------------------------------------------------

st.title("AI Assisted FMEA Generator")

project = st.text_input("Project")
user_name = st.text_input("User Name")
version = st.text_input("Version")
object_name = st.text_input("Object Name")

st.subheader("Technical Inputs")

piezas = st.text_input("Parts (comma separated)")
specs = st.text_area("Specifications")
requirements = st.text_area("Requirements")
reliability = st.text_area("Reliability")
safety = st.text_area("Safety")
maintainability = st.text_area("Maintainability")
usability = st.text_area("Usability")

# -------------------------------------------------

if st.button("Generate FMEA & Download Excel"):

    form_data = {
        "project":project,
        "user_name":user_name,
        "version":version,
        "object_name":object_name,
        "piezas":piezas,
        "specs":specs,
        "requirements":requirements,
        "reliability":reliability,
        "safety":safety,
        "maintainability":maintainability,
        "usability":usability
    }

    with st.spinner("Generating AI FMEA..."):

        data = generate_fmea(form_data)

        file_path = create_fmea_excel(data,form_data)

    with open(file_path,"rb") as f:
        st.download_button(
            "Download Excel",
            f,
            file_name=file_path
        )

    st.success("FMEA Generated Successfully!")
