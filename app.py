from flask import Flask, render_template, request, send_file
from fmea_engine import generate_fmea
from excel_formatter import create_fmea_excel

app = Flask(__name__)

@app.route("/", methods=["GET", "POST"])
def index():

    if request.method == "POST":

        form_data = request.form.to_dict()

        # Generar análisis FMEA con IA
        fmea_data = generate_fmea(form_data)

        # Crear Excel profesional
        file_path = create_fmea_excel(fmea_data, form_data["project"])

        return send_file(file_path, as_attachment=True)

    return render_template("index.html")


if __name__ == "__main__":
    app.run(debug=True, port=5001)
