from flask import Flask, render_template, request, send_file
import os
from Traductor import parse_xmi, extract_classes, generate_clips_facts, write_clips_file

app = Flask(__name__)

UPLOAD_FOLDER_XMI = "generated/xmi"
UPLOAD_FOLDER_CLP = "generated/clp"
os.makedirs(UPLOAD_FOLDER_XMI, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_CLP, exist_ok=True)

@app.route('/')
def index():
    return render_template('UML.html')

@app.route('/upload_xmi', methods=['POST'])
def upload_xmi():
    if 'file' not in request.files:
        return "No file uploaded", 400
    
    file = request.files['file']
    if file.filename == '':
        return "No selected file", 400

    file_path = os.path.join("generated/xmi", "diagram.xmi")
    file.save(file_path)

    root = parse_xmi(file_path)
    classes, _ = extract_classes(root)
    relationships = []
    
    clips_facts = generate_clips_facts(classes, relationships)
    write_clips_file(clips_facts, "generated/clp/output.clp")

    return "Archivo XMI procesado y convertido a CLIPS", 200


@app.route('/download_clp')
def download_clp():
    return send_file(os.path.join(UPLOAD_FOLDER_CLP, "output.clp"), as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
