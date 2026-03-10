import openai
import json
import os

openai.api_key = os.getenv("OPENAI_API_KEY")

FAILURE_MODES = [
    "degradation",
    "partial degradation",
    "total failure-breakage"
]

def clamp(value):
    value = int(value)
    return max(1, min(5, value))

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

Return ONLY valid JSON in this format:

[
  {{
    "Failure": "",
    "Function": "",
    "Failure Mode": "degradation | partial degradation | total failure-breakage",
    "Effects": "",
    "Causes": "",
    "Sources": "",
    "Severity": integer 1-5,
    "Occurrence": integer 1-5,
    "Detectability": integer 1-5,
    "Cost": number
  }}
]

Rules:
- Use strictly 1-5 scale
- Failure Mode must be one of the 3 allowed values
- Values must be realistic and technically justified
"""

def generate_fmea(form_data):

    parts = form_data.get("piezas", "").split(",")
    all_failures = []

    for part in parts:
        part = part.strip()

        prompt = build_prompt(form_data, part)

        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )

        failures = json.loads(response.choices[0].message.content)

        for f in failures:

            # Validaciones
            if f["Failure Mode"] not in FAILURE_MODES:
                f["Failure Mode"] = "degradation"

            f["Severity"] = clamp(f["Severity"])
            f["Occurrence"] = clamp(f["Occurrence"])
            f["Detectability"] = clamp(f["Detectability"])

            f["Part"] = part

            all_failures.append(f)

    return all_failures
