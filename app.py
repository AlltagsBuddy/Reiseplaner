# reiseplaner/app.py

from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
from dotenv import load_dotenv
from io import BytesIO
from docx import Document
from docx.shared import Pt
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from openai import OpenAI
import os
import logging

# === Konfiguration ===

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)

# === Routen ===

@app.route('/')
def index():
    return render_template('reiseplaner.html')


@app.route('/api/generate', methods=['POST'])
def generate():
    try:
        data = request.get_json()
        inhalt = data.get('inhalt', '').strip()
        stil = data.get('stil', 'Strand').strip()

        if not inhalt:
            return jsonify({'error': 'Keine Inhalte übergeben'}), 400

        prompt = f"""
Du bist ein smarter Reiseassistent. Der Nutzer plant eine Reise im Stil: {stil}.

Erstelle basierend auf den Angaben:
- ein konkretes Reiseziel inkl. Kurzbeschreibung
- 3–5 passende Aktivitäten
- optimaler Reisezeitraum
- realistisches Gesamtbudget (Hin- und Rückreise + Unterkunft + Aktivitäten)
- sinnvolle Reiseroute inkl. Hinweise zu Mautpflicht

Angaben des Nutzers:
{inhalt}

Antworte klar strukturiert in folgendem Format:

Ziel:
[...]
Aktivitäten:
[...]
Zeitraum:
[...]
Budget:
[...]
Route:
[...]
"""

        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Du bist ein professioneller Reiseberater und planst perfekte Urlaube."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1500
        )

        plan = response.choices[0].message.content.strip()
        return jsonify({'reiseplan': plan})

    except Exception as e:
        logging.exception("Fehler bei der Reiseplan-Generierung")
        return jsonify({'error': str(e)}), 500


@app.route('/api/export/docx', methods=['POST'])
def export_docx():
    try:
        data = request.get_json()
        plan = data.get('reiseplan', 'Kein Inhalt')

        doc = Document()
        style = doc.styles['Normal']
        font = style.font
        font.name = 'Calibri'
        font.size = Pt(11)

        doc.add_heading('Dein Reiseplan', level=1)
        for line in plan.split('\n'):
            if line.strip():
                doc.add_paragraph(line.strip())

        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name="reiseplan.docx",
            mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

    except Exception as e:
        logging.exception("Fehler beim DOCX-Export")
        return jsonify({'error': str(e)}), 500


@app.route('/api/export/pdf', methods=['POST'])
def export_pdf():
    try:
        data = request.get_json()
        plan = data.get('reiseplan', 'Kein Inhalt')

        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=2 * cm,
            leftMargin=2 * cm,
            topMargin=2.5 * cm,
            bottomMargin=2.5 * cm
        )

        styles = getSampleStyleSheet()
        story = [Paragraph("Dein Reiseplan", styles['Heading1'])]

        for line in plan.split('\n'):
            if line.strip():
                story.append(Paragraph(line.strip(), styles['Normal']))
                story.append(Spacer(1, 6))

        doc.build(story)

        buffer.seek(0)
        return send_file(
            buffer,
            as_attachment=True,
            download_name="reiseplan.pdf",
            mimetype="application/pdf"
        )

    except Exception as e:
        logging.exception("Fehler beim PDF-Export")
        return jsonify({'error': str(e)}), 500


# === Startserver ===
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))

