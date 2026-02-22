import os
import json
import tempfile
from datetime import datetime
from flask import Flask, render_template, request, send_file, flash, redirect, url_for
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

app = Flask(__name__)
app.secret_key = 'chiave_segreta_per_sessioni'

# Carica le traduzioni
with open('translations.json', 'r', encoding='utf-8') as f:
    TRANSLATIONS = json.load(f)

# Cartelle temporanee
UPLOAD_FOLDER = tempfile.gettempdir()
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

ALLOWED_EXTENSIONS = {'json'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def format_timestamp(ts):
    try:
        dt = datetime.fromtimestamp(ts / 1000)
        return dt.strftime("%d/%m/%Y %H:%M:%S")
    except:
        return str(ts)

def get_text(key, lang='it'):
    return TRANSLATIONS.get(lang, TRANSLATIONS['it']).get(key, key)

def convert_json_to_docx(json_data, doc, options, lang):
    t = lambda k: get_text(k, lang)
    
    # Informazioni sulla conversazione
    conv = json_data.get('conv', {})
    
    # Titolo del documento
    title = doc.add_heading(t('doc_title'), 0)
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    
    # Informazioni della conversazione
    doc.add_paragraph()
    p_info = doc.add_paragraph()
    run = p_info.add_run(t('doc_info'))
    run.bold = True
    run.font.size = Pt(14)
    
    # Tabella metadati
    table_meta = doc.add_table(rows=4, cols=2)
    table_meta.style = 'Table Grid'
    
    meta_data = [
        (t('conv_id'), conv.get('id', 'N/A')),
        (t('conv_name'), conv.get('name', 'N/A')),
        (t('conv_last_mod'), format_timestamp(conv.get('lastModified', 0))),
        (t('conv_node'), conv.get('currNode', 'N/A')[:20] + '...' if len(conv.get('currNode', '')) > 20 else conv.get('currNode', 'N/A'))
    ]
    
    for i, (label, value) in enumerate(meta_data):
        row = table_meta.rows[i]
        row.cells[0].text = label
        row.cells[1].text = value
        for cell in row.cells:
            if cell.paragraphs and cell.paragraphs[0].runs:
                cell.paragraphs[0].runs[0].font.bold = True

    if options.get('show_divider'):
        doc.add_paragraph()
        doc.add_paragraph('━' * 60)
        doc.add_paragraph()

    # Processa i messaggi
    messages = json_data.get('messages', [])
    
    # Determina nomi personalizzati o default
    user_label = options.get('custom_user_name', '').strip() or t('default_user')
    assistant_label = options.get('custom_assistant_name', '').strip() or t('default_assistant')

    for idx, msg in enumerate(messages, 1):
        role = msg.get('role', 'unknown')
        content = msg.get('content', '')
        msg_type = msg.get('type', 'text')
        timestamp = msg.get('timestamp', 0)
        
        if not content and msg_type != 'text':
            continue
        
        # Colori
        if role == 'user':
            role_display = user_label
            role_color = RGBColor(33, 150, 243)
        elif role == 'assistant':
            role_display = assistant_label
            role_color = RGBColor(76, 175, 80)
        else:
            role_display = f"📋 {role.upper()}"
            role_color = RGBColor(158, 158, 158)
        
        # Intestazione del messaggio
        doc.add_paragraph()
        p = doc.add_paragraph()
        
        # Numero messaggio
        if options.get('show_numbers'):
            run_num = p.add_run(f"[{idx}] ")
            run_num.font.size = Pt(10)
            run_num.font.color.rgb = RGBColor(158, 158, 158)
        
        run_role = p.add_run(f"{role_display}")
        run_role.font.size = Pt(12)
        run_role.font.bold = True
        run_role.font.color.rgb = role_color
        
        # Data e Ora
        if options.get('show_date'):
            run_time = p.add_run(f" • {format_timestamp(timestamp)}")
            run_time.font.size = Pt(9)
            run_time.font.color.rgb = RGBColor(158, 158, 158)
        
        # Modello AI
        if options.get('show_model') and role == 'assistant' and msg.get('model'):
            p_model = doc.add_paragraph()
            run_model = p_model.add_run(f"   📡 {msg.get('model')}")
            run_model.font.size = Pt(9)
            run_model.font.italic = True
            run_model.font.color.rgb = RGBColor(158, 158, 158)
        
        # Contenuto del messaggio
        if content:
            content_clean = content.replace('\\n', '\n').replace('\\t', '\t')
            for line in content_clean.split('\n'):
                if line.strip():
                    p_line = doc.add_paragraph(line.strip())
                    p_line.paragraph_format.space_before = Pt(3)
                    p_line.paragraph_format.space_after = Pt(3)
                    for run in p_line.runs:
                        run.font.size = Pt(11)
        
        # Contenuto Extra
        extra = msg.get('extra', [])
        if extra:
            doc.add_paragraph()
            p_extra = doc.add_paragraph()
            run_extra = p_extra.add_run(t('extra_content'))
            run_extra.font.bold = True
            run_extra.font.size = Pt(10)
            
            for item in extra:
                if isinstance(item, dict):
                    if item.get('type') == 'TEXT' and item.get('name') == 'Pasted':
                        extra_content = item.get('content', '')
                        if extra_content:
                            extra_clean = extra_content.replace('\\n', '\n')
                            for line in extra_clean.split('\n'):
                                if line.strip():
                                    p_line = doc.add_paragraph(line.strip())
                                    p_line.paragraph_format.left_indent = Inches(0.3)
                                    for run in p_line.runs:
                                        run.font.size = Pt(10)
                                        run.font.italic = True
        
        # Dati Prompt (Timing)
        if options.get('show_prompt'):
            timings = msg.get('timings', {})
            if timings and role == 'assistant':
                p_timing = doc.add_paragraph()
                run_timing = p_timing.add_run("⏱️ ")
                run_timing.font.size = Pt(9)
                
                timing_text = f"Prompt: {timings.get('prompt_n', 'N/A')} token ({timings.get('prompt_ms', 0):.1f}ms) | "
                timing_text += f"Output: {timings.get('predicted_n', 'N/A')} token ({timings.get('predicted_ms', 0):.1f}ms)"
                
                run_timing_val = p_timing.add_run(timing_text)
                run_timing_val.font.size = Pt(9)
                run_timing_val.font.color.rgb = RGBColor(158, 158, 158)
        
        # Separatore finale
        if options.get('show_divider'):
            doc.add_paragraph()
            p_sep = doc.add_paragraph('─' * 60)
            p_sep.alignment = WD_ALIGN_PARAGRAPH.CENTER

def process_json(json_file_path, options, lang):
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    doc = Document()
    
    for section in doc.sections:
        section.top_margin = Inches(1)
        section.bottom_margin = Inches(1)
        section.left_margin = Inches(1)
        section.right_margin = Inches(1)
    
    convert_json_to_docx(data, doc, options, lang)
    
    doc.add_paragraph()
    if options.get('show_divider'):
        doc.add_paragraph('━' * 60)
    p_footnote = doc.add_paragraph()
    run_footnote = p_footnote.add_run("📄 " + get_text('generated_at', lang))
    run_footnote.font.size = Pt(9)
    run_footnote.font.italic = True
    run_footnote.font.color.rgb = RGBColor(158, 158, 158)
    
    return doc

@app.route('/')
def index():
    # Passa le lingue disponibili al template
    return render_template('index.html', languages=TRANSLATIONS.keys())

@app.route('/convert', methods=['POST'])
def convert():
    try:
        if 'file' not in request.files:
            flash('❌ Nessun file caricato', 'error')
            return redirect(url_for('index'))
        
        file = request.files['file']
        
        if file.filename == '':
            flash('❌ Nessun file selezionato', 'error')
            return redirect(url_for('index'))
        
        if file and allowed_file(file.filename):
            # Estrai opzioni
            options = {
                'show_date': request.form.get('show_date') == 'on',
                'show_divider': request.form.get('show_divider') == 'on',
                'show_model': request.form.get('show_model') == 'on',
                'show_prompt': request.form.get('show_prompt') == 'on',
                'show_numbers': request.form.get('show_numbers') == 'on',
                'custom_user_name': request.form.get('custom_user_name', ''),
                'custom_assistant_name': request.form.get('custom_assistant_name', '')
            }
            lang = request.form.get('language', 'it')
            
            filename = f"input_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            
            try:
                doc = process_json(filepath, options, lang)
                
                output_filename = f"conversazione_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
                output_path = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
                
                doc.save(output_path)
                
                flash('✅ Conversione completata con successo!', 'success')
                
                return send_file(
                    output_path,
                    as_attachment=True,
                    download_name=output_filename,
                    mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                )
                
            except Exception as e:
                flash(f'❌ Errore durante l\'elaborazione: {str(e)}', 'error')
                return redirect(url_for('index'))
            
            finally:
                if os.path.exists(filepath):
                    os.remove(filepath)
        else:
            flash('❌ Formato file non consentito.', 'error')
            return redirect(url_for('index'))
    
    except Exception as e:
        flash(f'❌ Errore: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/sample')
def download_sample():
    sample_json = {
        "conv": {
            "id": "sample-id",
            "name": "esempio",
            "lastModified": 1771702156904,
            "currNode": "sample-node"
        },
        "messages": [
            {
                "convId": "sample-id",
                "role": "user",
                "content": "Ciao! Questo è un messaggio di esempio.",
                "type": "text",
                "timestamp": 1771702156956
            },
            {
                "convId": "sample-id",
                "role": "assistant",
                "content": "Ciao! Sono un assistente virtuale. Come posso aiutarti?",
                "type": "text",
                "timestamp": 1771702156981,
                "model": "Modello-Esempio",
                "timings": {"prompt_n": 10, "prompt_ms": 50.5, "predicted_n": 20, "predicted_ms": 100.2}
            }
        ]
    }
    
    sample_path = os.path.join(app.config['UPLOAD_FOLDER'], 'sample_conversation.json')
    with open(sample_path, 'w', encoding='utf-8') as f:
        json.dump(sample_json, f, indent=2, ensure_ascii=False)
    
    return send_file(
        sample_path,
        as_attachment=True,
        download_name='sample_conversation.json',
        mimetype='application/json'
    )

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
