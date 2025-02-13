from flask import Flask, render_template, request, send_file, redirect, url_for
import os
import clips  # clipspy
from Traductor import parse_xmi, extract_classes, generate_clips_facts, write_clips_file, run_clips_and_get_java

app = Flask(__name__)

UPLOAD_FOLDER_XMI = "generated/xmi/"
UPLOAD_FOLDER_CLP = "generated/clp/"
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

    file_path = os.path.join(UPLOAD_FOLDER_XMI, "diagram.xmi")
    file.save(file_path)

    root = parse_xmi(file_path)
    classes, relationships = extract_classes(root)

    # 🔍 Verificar si las relaciones llegan correctamente
    print(f"📌 Relaciones extraídas del XMI: {relationships}")

    clips_facts = generate_clips_facts(classes, relationships)
    clips_file = os.path.join(UPLOAD_FOLDER_CLP, "output.clp")
    write_clips_file(clips_facts, clips_file)

    if not os.path.exists(clips_file):
        return "Error: No se generó el archivo CLIPS.", 500

    print(f"✅ Archivo CLIPS generado correctamente: {clips_file}")

    java_code = run_clips_and_get_java(clips_file)
    print("📝 Código Java recibido en Flask:")
    print(java_code)

    return render_template('java_output.html', java_code=java_code)

@app.route('/run_clips')
def run_clips():
    clips_file_path = os.path.join(UPLOAD_FOLDER_CLP, "output.clp")
    
    if not os.path.exists(clips_file_path):
        return "Archivo CLIPS no encontrado", 404

    try:
        # Ejecutar CLIPS
        env = clips.Environment()
        env.clear()  # Limpia el entorno de CLIPS antes de cargar nuevos hechos
        env.load(clips_file_path)
        env.reset()
        env.run()

        # Redirigir a la página de resultados
        return redirect(url_for('view_results'))

    except Exception as e:
        return f"Error ejecutando CLIPS: {str(e)}", 500

@app.route('/view_results')
def view_results():
    clips_file_path = os.path.join(UPLOAD_FOLDER_CLP, "output.clp")
    if not os.path.exists(clips_file_path):
        return "Archivo CLIPS no encontrado", 404

    try:
        # Cargar los hechos generados
        env = clips.Environment()
        env.clear()
        env.load(clips_file_path)
        env.reset()
        env.run()

        output = [str(fact) for fact in env.facts()]  # Capturar hechos generados

        # Renderizar los resultados en una página HTML
        return render_template('results.html', results=output)

    except Exception as e:
        return f"Error mostrando resultados: {str(e)}", 500

@app.route('/download_clp')
def download_clp():
    clp_path = os.path.join(UPLOAD_FOLDER_CLP, "output.clp")
    if not os.path.exists(clp_path):
        return "Archivo CLIPS no encontrado", 404
    return send_file(clp_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)