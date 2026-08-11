import os
import sys
sys.stdout.reconfigure(encoding='utf-8')
import glob
import re
import csv
import io
from datetime import datetime
from docx import Document  
from docx.oxml.ns import qn
from flask import Flask, render_template_string, request, redirect, url_for, Response

app = Flask(__name__)
 
performance_db = {}
 
def get_subject_file(subject_keyword, stream):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    search_path = os.path.join(script_dir, "*.docx")
    files = glob.glob(search_path)
    
    keyword = subject_keyword.lower().strip()
    stream_suffix = stream.lower().strip()
    
    if "phy" in keyword:
        match_tokens = ["phy", stream_suffix]
    elif "chem" in keyword:
        match_tokens = ["chem", stream_suffix]
    elif "math" in keyword:
        match_tokens = ["math", stream_suffix]
    elif "bio" in keyword:
        match_tokens = ["bio", stream_suffix]
    else:
        match_tokens = [keyword[:3], stream_suffix]
 
    for f in files:
        filename = os.path.basename(f)
        if filename.startswith("~$"): 
            continue
        if all(token in filename.lower() for token in match_tokens):
            return f
    return None
 
def add_unit_vector_hats(text):
    if not text:
        return text
 
    lower = text.lower()
    complex_markers = (
        'complex number', 'complex no', 'iota', 'imaginary',
        'argand', 'conjugate', '\u221a-1', '\u221a(-1)', 'modulus of z', 'modulus of the complex'
    )
    if any(marker in lower for marker in complex_markers):
        return text
 
    pattern = r'(?<![A-Za-z])([ijk])(?![A-Za-z])'
    distinct_letters = {m.lower() for m in re.findall(pattern, text)}
    looks_like_vector = ('vector' in lower) or (len(distinct_letters) >= 2)
    if not looks_like_vector:
        return text
 
    def _hat(match):
        letter = match.group(1)
        return f"{letter}\u0302"
 
    return re.sub(pattern, _hat, text)
 
def add_vector_arrows(text):
    if not text:
        return text
 
    def _arrow_after_vector_word(match):
        prefix, rest = match.group(1), match.group(2)
        rest = re.sub(r'\b([A-Z])\b', lambda m: m.group(1) + '\u20d7', rest)
        return prefix + rest
 
    text = re.sub(
        r'\b(vectors?)\b((?:\s*(?:and|\+|-|\u2212|,)?\s*[A-Z]\b)+)',
        _arrow_after_vector_word,
        text
    )
    text = re.sub(
        r'\b([A-Z])(\s*)\u00d7(\s*)([A-Z])\b',
        lambda m: f"{m.group(1)}\u20d7{m.group(2)}\u00d7{m.group(3)}{m.group(4)}\u20d7",
        text
    )
    text = re.sub(
        r'((?i:angle\s+between)\s+)([A-Z])(\s+and\s+)([A-Z])\b',
        lambda m: f"{m.group(1)}{m.group(2)}\u20d7{m.group(3)}{m.group(4)}\u20d7",
        text
    )
 
    eq_matches = list(re.finditer(r'\b([A-Z])\s*=', text))
    for idx in range(len(eq_matches) - 1, -1, -1):
        m = eq_matches[idx]
        start_expr = m.end()
        end_expr = eq_matches[idx + 1].start() if idx + 1 < len(eq_matches) else len(text)
        segment = text[start_expr:end_expr]
        cut = re.search(r'[,.;]', segment)
        segment_check = segment[:cut.start()] if cut else segment
        if re.search(r'[ijk]\u0302', segment_check):
            letter_pos = m.start(1)
            text = text[:letter_pos] + m.group(1) + '\u20d7' + text[letter_pos + 1:]
 
    arrowed_letters = set(re.findall(r'([A-Z])\u20d7', text))
    if arrowed_letters:
        def _sweep(m):
            letter = m.group(1)
            return letter + '\u20d7' if letter in arrowed_letters else letter
        text = re.sub(r'\b([A-Z])\b(?!\u20d7)', _sweep, text)
 
    return text

def wrap_latex_in_dollars(text):
    """Ensures raw LaTeX structures containing backslashes are properly enclosed in dollar signs for MathJax."""
    if not text:
        return text
    if '\\' in text and '$' not in text:
        return re.sub(r'(\\[a-zA-Z]+(?:\{[^{}]*\}|\^\{[^{}]*\}|_[^{}]*|[\s\d\w\+\-\=\|\(\)])+)', r'$\1$', text)
    return text

def format_log_subscripts_safe(text):
    """Format subscripts and superscripts while preserving HTML img tags."""
    if not text:
        return text
    
    # Extract and protect img tags to prevent corruption of filenames
    img_tags = []
    img_pattern = r'<img\s+[^>]*>'
    
    def save_img(match):
        img_tags.append(match.group(0))
        return f"__IMG_PLACEHOLDER_{len(img_tags) - 1}__"
    
    # Replace img tags with placeholders
    text = re.sub(img_pattern, save_img, text)
    
    # Apply normal formatting
    text = format_log_subscripts(text)
    
    # Restore img tags
    for idx, img_tag in enumerate(img_tags):
        text = text.replace(f"__IMG_PLACEHOLDER_{idx}__", img_tag)
    
    return text

def format_log_subscripts(text):
    if not text:
        return text

    if '\\' in text:
        return wrap_latex_in_dollars(text)

    text = add_unit_vector_hats(text)
    text = add_vector_arrows(text)
    text = re.sub(r'5\s*log\s*5\s*\(([^)]+)\)', r'5<sup>log<sub>5</sub>(\1)</sup>', text)
    text = re.sub(r'4\s*log\s*2\s*\(([^)]+)\)\]?', r'4<sup>log<sub>2</sub>(\1)</sup>', text)
    text = re.sub(r'\blog\s*([0-9]+)\s*(\([^)]+\)|[a-zA-Z𝑥xVariable𝑋])', r'log<sub>\1</sub>\2', text)
    text = re.sub(r'\blog\s*([√\u221A]\s*[a-zA-Z𝑥xVariable𝑋])', r'log<sub>\1</sub>', text)
    text = re.sub(r'([a-zA-Z0-9𝑥xVariable𝑋\)\s\.\+\-\[\]\{\}]+)\s*\^\s*([+\-]?[0-9a-zA-Z\s\.\+\-\[\]\{\}]+)', r'\1<sup>\2</sup>', text)
    
    # Safe 10^x Exponent Replacement (only whole integer powers)
    text = re.sub(r'(?<![\d\.])10([2-9]\d|\-\d+)(?![\d\.])', r'10<sup>\1</sup>', text)
    
    # Dimensional formulas (M1 L2 T-2)
    text = re.sub(r'\b([MLT])\s*([+\-]?[0-9]+)', r'\1<sup>\2</sup>', text)
    
    # Standard Units (m2, cm3, mm2)
    text = re.sub(r'\b(m|cm|dm|mm|km|s|sec)([23])\b', r'\1<sup>\2</sup>', text)
    
    # CLEANED VARIABLE EXPONENT MATCH: Excludes decimal points completely
    text = re.sub(r'(?<![0-9\.])\b([a-zA-Z𝑥XVariable𝑋vtaxfghzVGP])([2345])\b', r'\1<sup>\2</sup>', text)
    
    # Negative exponents on unit words (e.g., s-1, m-2)
    text = re.sub(r'\b([a-zA-Z𝑥xVariable𝑋]+)-\s*([0-9]+)\b', r'\1<sup>-\2</sup>', text)
    
    # Chemical formula subscripts (H2O, CO2)
    text = re.sub(r'(?<=[A-Za-z])([0-9]+)(?![0-9]*\.)', r'<sub>\1</sub>', text)
    
    # Ion charges (Na+, Ca2+)
    text = re.sub(r'\b([A-Z][a-z]?)([0-9]*[\+\-])', r'\1<sup>\2</sup>', text)
    text = re.sub(r'\b([FF])([12])\b', r'\1<sub>\2</sub>', text)
    
    text = text.replace("^", "")
    return text
 
def _parse_numeric_token(text):
    if not text:
        return None
    m = re.match(r'^\s*[+-]?(\d+\s*/\s*\d+|\d+\.\d+|\d+)', text)
    if not m:
        return None
    tok = m.group(1).replace(' ', '')
    try:
        if '/' in tok:
            num, den = tok.split('/')
            return float(num) / float(den)
        return float(tok)
    except (ValueError, ZeroDivisionError):
        return None
 
def _parse_numeric_token_strict(text):
    if not text:
        return None
    m = re.match(r'^\s*[+-]?(\d+\s*/\s*\d+|\d+\.\d+|\d+)\s*[a-zA-Z°%\u03a9\u00b5]*\s*$', text)
    if not m:
        return None
    tok = m.group(1).replace(' ', '')
    try:
        if '/' in tok:
            num, den = tok.split('/')
            return float(num) / float(den)
        return float(tok)
    except (ValueError, ZeroDivisionError):
        return None
 
def typein_answers_match(correct_answer, student_answer):
    c = (correct_answer or '').strip().lower()
    s = (student_answer or '').strip().lower()
    if not s:
        return False
    if c == s:
        return True
    if re.sub(r'\s+', '', c) == re.sub(r'\s+', '', s):
        return True
    c_num = _parse_numeric_token_strict(c)
    s_num = _parse_numeric_token(s)
    if c_num is not None and s_num is not None:
        return abs(c_num - s_num) < 1e-6
    return False

def load_questions_from_docx(file_path):
    if not file_path or not os.path.exists(file_path):
        return []
    try:
        static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")
        os.makedirs(static_dir, exist_ok=True)

        from docx import Document as StandardDocument
        doc = StandardDocument(file_path)

        questions_list = []
        current_question = None
        current_options = []
        current_correct = ""
        q_counter = 1
        image_counter = 1

        for p in doc.paragraphs:
            raw_p_text = p.text.strip()
            
            # Extract embedded images specifically from this paragraph
            rel_ids = re.findall(r'r:embed="([^"]+)"', p._p.xml)
            has_inline_image = False
            image_filename = ""

            if rel_ids:
                for r_id in rel_ids:
                    if r_id in doc.part.rels:
                        rel = doc.part.rels[r_id]
                        if "image" in rel.target_ref:
                            image_filename = f"extracted_{os.path.basename(file_path).split('.')[0]}_{image_counter}.png"
                            target_path = os.path.join(static_dir, image_filename)
                            with open(target_path, "wb") as f:
                                f.write(rel.target_part.blob)
                            has_inline_image = True
                            image_counter += 1
                            break

            extracted_text = wrap_latex_in_dollars(raw_p_text)

            # STRICT QUESTION DETECTION: Ensures numbers in chemical formulas (e.g. 2H2 + O2) or isotopes do not create false questions
            is_new_question = bool(re.match(r'^\s*(?:Q|q)?\d+[\.\)\:]\s+', extracted_text))

            if is_new_question or (extracted_text == "" and has_inline_image and current_question is None):
                if current_question:
                    questions_list.append({
                        "id": q_counter,
                        "question": format_log_subscripts_safe(current_question),
                        "options": [format_log_subscripts(opt) for opt in current_options],
                        "correct": current_correct.strip()
                    })
                    q_counter += 1
                
                if extracted_text:
                    current_question = re.sub(r'^\s*(?:Q|q)?\d+[\.\)\:]\s*', '', extracted_text).strip()
                else:
                    current_question = ""
                current_options = []
                current_correct = ""

            elif re.match(r'^\s*[\(\[\{]?([A-Da-d])[\)\]\}]?[\s\.]|^\s*\([A-Da-d]\)', extracted_text):
                current_options.append(extracted_text)
            
            elif "correct answer" in extracted_text.lower() or extracted_text.lower().startswith("answer:") or re.match(r'^\s*\([A-Da-d]\)\s*$', extracted_text):
                ans_match = re.search(r'\(([A-Da-d])\)|:\s*([A-Da-d])|\[([A-Da-d])\]', extracted_text, re.IGNORECASE)
                if ans_match:
                    ans_letter = ans_match.group(1) or ans_match.group(2) or ans_match.group(3)
                    current_correct = ans_letter.upper().strip()
                else:
                    cleaned = re.sub(r'^\s*(correct\s+answer|answer)\s*:?\s*', '', extracted_text, flags=re.IGNORECASE).strip()
                    current_correct = cleaned if cleaned else extracted_text.strip()
            else:
                if current_question is not None and not current_options:
                    if extracted_text:
                        if current_question:
                            current_question += "<br>" + extracted_text
                        else:
                            current_question = extracted_text

            # Embed the image right into the current question context where it appears
            if has_inline_image and current_question is not None:
                current_question += f'<br><img src="/static/{image_filename}" style="max-width:100%; max-height:250px; height:auto; margin:15px 0; display:block; border:1px solid #cbd5e1; border-radius:4px;">'

        if current_question:
            questions_list.append({
                "id": q_counter,
                "question": format_log_subscripts_safe(current_question),
                "options": [format_log_subscripts(opt) for opt in current_options],
                "correct": current_correct.strip()
            })
        return questions_list
    except Exception as e:
        print(f"Error parsing inline media from file {file_path}: {e}")
        return []

# --- HTML TEMPLATES ---
 
MAIN_PORTAL_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Competitive Assessment Portal</title>
    <style>
        body { font-family: 'Segoe UI', 'Segoe UI Symbol', 'Cambria Math', Arial, sans-serif; background-color: #f5f7fa; color: #333; margin: 0; padding: 20px; }
        .container { max-width: 600px; background: white; padding: 35px; margin: 40px auto; border-radius: 6px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
        h2 { color: #1f497d; text-align: center; margin-bottom: 25px; }
        .form-group { margin-bottom: 20px; }
        label { font-weight: 600; display: block; margin-bottom: 8px; }
        input[type="text"] { width: 100%; padding: 12px; border: 1px solid #ccd4dc; border-radius: 4px; box-sizing: border-box; font-size: 14px; }
        .radio-group { display: flex; gap: 20px; margin-top: 5px; }
        .radio-opt { display: flex; align-items: center; gap: 6px; font-weight: bold; cursor: pointer; }
        button { width: 100%; background-color: #1f497d; color: white; border: none; padding: 14px; font-size: 16px; font-weight: bold; border-radius: 4px; cursor: pointer; margin-top: 20px; }
        button:hover { background-color: #153356; }
    </style>
</head>
<body>
    <div class="container">
        <h2>Weekly Examination Portal</h2>
        <form action="/unified-test-board" method="POST">
            <div class="form-group">
                <label for="student_name">Student Name / Roll Number:</label>
                <input type="text" id="student_name" name="student_name" required placeholder="Enter student token">
            </div>
            <div class="form-group">
                <label>Select Examination Stream Target:</label>
                <div class="radio-group">
                    <label class="radio-opt"><input type="radio" name="stream" value="NEET" required> NEET (Medical)</label>
                    <label class="radio-opt"><input type="radio" name="stream" value="JEE" required> JEE (Engineering)</label>
                </div>
            </div>
            <button type="submit">Proceed to Examination Board</button>
        </form>
    </div>
</body>
</html>
"""
 
UNIFIED_EXAM_PANEL_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Unified Examination Board</title>
    
    <script>
        window.MathJax = {
            tex: {
                inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
                displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']]
            },
            options: {
                ignoreHtmlClass: 'tex2jax_ignore',
                processHtmlClass: 'tex2jax_process'
            }
        };
    </script>
    <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>

    <style>
        body { font-family: 'Segoe UI', 'Segoe UI Symbol', 'Cambria Math', Arial, sans-serif; background-color: #f5f7fa; color: #333; padding: 20px; }
        .container { max-width: 800px; background: white; padding: 35px; margin: 20px auto; border-radius: 6px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); position: relative; }
        h2 { color: #1f497d; text-align: center; margin-bottom: 5px; }
        .welcome { text-align: center; margin-bottom: 25px; color: #555; font-size: 15px; }
        .meta-tag { background: #eef3f7; padding: 4px 10px; border-radius: 4px; font-weight: bold; color: #1f497d; }
        .marking-scheme { color: #d9534f; font-size: 13px; font-weight: bold; text-align: center; margin-bottom: 15px; }
        .timer-box { position: sticky; top: 0; background: #fff3cd; color: #856404; border: 1px solid #ffeeba; padding: 12px; border-radius: 4px; text-align: center; font-size: 18px; font-weight: bold; margin-bottom: 25px; z-index: 1000; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
        .lock-warning { font-size: 13px; color: #a94442; font-weight: bold; margin-top: 5px; text-align: center; display: block; }
        .subject-tabs { display: flex; gap: 10px; justify-content: center; margin-bottom: 30px; border-bottom: 2px solid #cbd5e1; padding-bottom: 12px; }
        .tab-btn { background-color: #e2e8f0; color: #334155; padding: 12px 24px; border: none; border-radius: 5px; font-size: 15px; font-weight: bold; cursor: pointer; transition: all 0.2s; }
        .tab-btn:hover { background-color: #cbd5e1; }
        .tab-btn.active { background-color: #1f497d; color: white; box-shadow: 0 3px 6px rgba(0,0,0,0.1); }
        .subject-section { display: none; }
        .subject-section.active { display: block; }
        .question-block { margin-top: 25px; padding-top: 20px; border-top: 1px solid #e6ecf0; }
        .option { margin-bottom: 10px; display: flex; align-items: center; gap: 10px; }
        .typein-input { width: 100%; max-width: 300px; padding: 10px; border: 1px solid #ccd4dc; border-radius: 4px; font-size: 14px; margin-top: 5px; }
        .badge-info { background-color: #0284c7; color: white; padding: 2px 6px; font-size: 11px; border-radius: 4px; margin-left: 5px; }
        #submit-btn { display: block; width: 100%; background-color: #94a3b8; color: white; border: none; padding: 16px; font-size: 18px; font-weight: bold; border-radius: 5px; cursor: not-allowed; margin-top: 40px; }
        #submit-btn.ready { background-color: #16a34a; cursor: pointer; }
        #submit-btn.ready:hover { background-color: #15803d; }
        #lock-screen { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0, 0, 0, 0.9); color: white; z-index: 9999; text-align: center; padding-top: 20vh; }
        #lock-screen h1 { font-size: 48px; color: #ffc107; }
        sub, sup { font-size: 75%; line-height: 0; position: relative; vertical-align: baseline; }
        sub { bottom: -0.25em; }
        sup { top: -0.5em; }
        .err-msg { color: red; font-weight: bold; padding: 15px; background: #fdf2f2; border-radius: 4px; margin-top: 10px; }
    </style>
</head>
<body>
    <div id="lock-screen">
        <h1>⏳ Time Expired!</h1>
        <p>The examination timeframe has finished. Consolidating options automatically...</p>
    </div>
    
    <div class="container">
        <h2>Weekly Examination Workspace</h2>
        <div class="welcome">Candidate: <strong>{{ name }}</strong> | Target Stream: <span class="meta-tag">{{ stream }}</span></div>
        <div class="marking-scheme">
            {% if stream == 'JEE' %}
                ⚠️ Core Rules Matrix: MCQ Sections (+4 / -1 Mark) | Last 5 Questions (+4 / 0 No Negative Marks)
            {% else %}
                ⚠️ Core Rules Matrix: All Questions MCQ (+4 / -1 Mark Negative Marks Apply Throughout)
            {% endif %}
        </div>
        <div class="timer-box" id="countdown-display">Remaining Time: 03:00:00</div>
        
        <div class="subject-tabs">
            <button type="button" class="tab-btn active" onclick="switchSubject('Physics', event)">Physics Section</button>
            <button type="button" class="tab-btn" onclick="switchSubject('Chemistry', event)">Chemistry Section</button>
            {% if stream == 'NEET' %}
                <button type="button" class="tab-btn" onclick="switchSubject('Biology', event)">Biology Section</button>
            {% else %}
                <button type="button" class="tab-btn" onclick="switchSubject('Mathematics', event)">Mathematics Section</button>
            {% endif %}
        </div>
 
        <form id="exam-form" action="/submit-unified-exam" method="POST">
            <input type="hidden" name="student_name" value="{{ name }}">
            <input type="hidden" name="stream" value="{{ stream }}">
 
            {% for sub in ['Physics', 'Chemistry', 'Mathematics', 'Biology'] %}
                {% if sub == 'Physics' or sub == 'Chemistry' or (stream == 'NEET' and sub == 'Biology') or (stream == 'JEE' and sub == 'Mathematics') %}
                <div id="section_{{ sub }}" class="subject-section {% if sub == 'Physics' %}active{% endif %}">
                    <h3>{{ sub }} Assessment Pool</h3>
                    {% if segments[sub] %}
                        {% set total_qs = segments[sub]|length %}
                        {% for q in segments[sub] %}
                            <div class="question-block">
                                <p><strong>Q{{ loop.index }}. {{ q.question|safe }}</strong>
                                {% if stream == 'JEE' and not q.options %}
                                    <span class="badge-info">Type-in Answer (No Negative Marks)</span>
                                {% endif %}</p>
                                
                                {% if stream == 'JEE' and not q.options %}
                                    <input type="text" class="typein-input" name="{{ sub }}_q_{{ q.id }}" placeholder="Type your numerical answer here...">
                                {% else %}
                                    {% for option in q.options %}
                                    <div class="option">
                                        {% set letter = ['A', 'B', 'C', 'D'][loop.index0] %}
                                        <input type="radio" id="{{ sub }}_q_{{ q.id }}_{{ loop.index }}" name="{{ sub }}_q_{{ q.id }}" value="{{ letter }}">
                                        <label style="cursor:pointer;" for="{{ sub }}_q_{{ q.id }}_{{ loop.index }}">{{ option|safe }}</label>
                                    </div>
                                    {% endfor %}
                                {% endif %}
                            </div>
                        {% endfor %}
                    {% else %}
                        <p class="err-msg">Error: Missing or unreadable Word (.docx) file matching key '{{ sub }}' in workspace folder.</p>
                    {% endif %}
                </div>
                {% endif %}
            {% endfor %}
 
            <button type="submit" id="submit-btn" disabled>Submission Locked (Enabled after 2h 50m)</button>
            <span class="lock-warning" id="lock-text">🔒 Early submission is locked. You can submit when the countdown reaches 00:10:00.</span>
        </form>
    </div>
 
    <script>
        function switchSubject(subjectName, event) {
            var i, sections, tabs;
            sections = document.getElementsByClassName("subject-section");
            for (i = 0; i < sections.length; i++) {
                sections[i].style.display = "none";
            }
            tabs = document.getElementsByClassName("tab-btn");
            for (i = 0; i < tabs.length; i++) {
                tabs[i].classList.remove("active");
            }
            document.getElementById("section_" + subjectName).style.display = "block";
            event.currentTarget.classList.add("active");
        }
 
        var totalSeconds = 10 * 60; 
        var lockThresholdSeconds = 10 * 60; 
 
        var timerInterval = setInterval(function() {
            if (totalSeconds <= 0) {
                clearInterval(timerInterval);
                document.getElementById("lock-screen").style.display = "block";
                setTimeout(function() {
                    document.getElementById("exam-form").submit();
                }, 4000);
            } else {
                totalSeconds--;
                var hrs = Math.floor(totalSeconds / 3600);
                var mins = Math.floor((totalSeconds % 3600) / 60);
                var secs = totalSeconds % 60;
                
                document.getElementById("countdown-display").innerHTML = "Remaining Time: " +
                    (hrs < 10 ? "0" : "") + hrs + ":" +
                    (mins < 10 ? "0" : "") + mins + ":" +
                    (secs < 10 ? "0" : "") + secs;
 
                if (totalSeconds <= lockThresholdSeconds) {
                    var btn = document.getElementById("submit-btn");
                    if (btn.hasAttribute("disabled")) {
                        btn.removeAttribute("disabled");
                        btn.className = "ready";
                        btn.innerHTML = "Finalize Assessment Submission";
                        document.getElementById("lock-text").style.display = "none";
                    }
                }
            }
        }, 1000);
    </script>
</body>
</html>
"""
 
ASSESSMENT_RESULT_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Assessment Verification Report</title>
    
    <script>
        window.MathJax = {
            tex: {
                inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
                displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']]
            },
            options: {
                ignoreHtmlClass: 'tex2jax_ignore',
                processHtmlClass: 'tex2jax_process'
            }
        };
    </script>
    <script id="MathJax-script" async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>

    <style>
        body { font-family: 'Segoe UI', 'Segoe UI Symbol', 'Cambria Math', Arial, sans-serif; background-color: #f5f7fa; color: #333; padding: 20px; }
        .container { max-width: 950px; background: white; padding: 40px; margin: 30px auto; border-radius: 6px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
        h2, h3 { color: #1f497d; text-align: center; }
        h3 { border-bottom: 2px solid #1f497d; padding-bottom: 6px; text-align: left; margin-top: 35px; }
        .meta-info { margin-bottom: 25px; padding: 15px; background: #eef3f7; border-radius: 4px; font-size: 15px; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; margin-bottom: 20px; }
        th, td { padding: 10px 14px; border: 1px solid #cbd5e1; text-align: left; vertical-align: top; }
        th { background-color: #1f497d; color: white; }
        .status-correct { color: #155724; background-color: #d4edda; border: 1px solid #c3e6cb; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 13px; display: inline-block; }
        .status-wrong { color: #721c24; background-color: #f8d7da; border: 1px solid #f5c6cb; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 13px; display: inline-block; }
        .status-unattended { color: #383d41; background-color: #e2e3e5; border: 1px solid #d6d8db; padding: 3px 8px; border-radius: 4px; font-weight: bold; font-size: 13px; display: inline-block; }
        .score-positive { color: #15803d; font-weight: bold; }
        .score-negative { color: #b91c1c; font-weight: bold; }
        .score-zero { color: #475569; }
        .answer-text { font-size: 13px; color: #1e293b; line-height: 1.4; }
        .summary-card { font-size: 22px; text-align: center; color: #16a34a; font-weight: bold; margin: 30px 0; padding: 20px; background: #f0fdf4; border-radius: 6px; border: 1px solid #bbf7d0; }
        .category-totals-table th { background-color: #475569; }
        .admin-link { background: #fffbeb; border-left: 4px solid #d97706; padding: 15px; margin-top: 30px; font-size: 14px; border-radius: 4px; }
        sub, sup { font-size: 75%; line-height: 0; position: relative; vertical-align: baseline; }
        sub { bottom: -0.25em; }
        sup { top: -0.5em; }
    </style>
</head>
<body>
    <div class="container">
        <h2>Performance Evaluation Dashboard</h2>
        
        <div class="meta-info">
            <strong>Candidate Name:</strong> {{ name }}<br>
            <strong>Exam Variant:</strong> {{ stream }}<br>
            <strong>Evaluation Timestamp:</strong> {{ timestamp }}
        </div>
 
        <h3>Category Summary Breakdown</h3>
        <table class="category-totals-table">
            <thead>
                <tr>
                    <th>Subject Section Category</th>
                    <th>Earned Mark Component</th>
                </tr>
            </thead>
            <tbody>
                {% for subject, score in breakdown.items() %}
                <tr>
                    <td><strong>{{ subject }} Category Total</strong></td>
                    <td><span class="score-positive">{{ score }} Marks</span></td>
                </tr>
                {% endfor %}
                <tr style="background-color: #f1f5f9; font-size: 16px;">
                    <td><strong>Grand Cumulative Score Metric</strong></td>
                    <td><strong style="color:#1e40af;">{{ grand_total }} Marks</strong></td>
                </tr>
            </tbody>
        </table>
 
        <div class="summary-card">Grand Final Score: {{ grand_total }} Marks</div>
 
        <h3>Itemized Question Evaluation Ledger</h3>
        {% for subject, items in detailed_report.items() %}
            <h4 style="color:#334155; margin-bottom:5px; margin-top:20px;">📌 {{ subject }} Section</h4>
            <table>
                <thead>
                    <tr style="font-size: 13px;">
                        <th style="width: 6%;">Q.No.</th>
                        <th style="width: 34%;">Question Fragment</th>
                        <th style="width: 24%;">Answer Marked</th>
                        <th style="width: 24%;">Correct Answer</th>
                        <th style="width: 12%;">Status</th>
                    </tr>
                </thead>
                <tbody>
                    {% for item in items %}
                    <tr>
                        <td><strong>{{ item.q_index }}</strong></td>
                        <td style="font-size:13px; color:#4b5563;">{{ item.q_snippet|safe }}...</td>
                        <td class="answer-text">{{ item.marked_answer|safe }}</td>
                        <td class="answer-text">{{ item.correct_answer|safe }}</td>
                        <td>
                            {% if item.status == 'Correct' %}
                                <span class="status-correct">✔ Correct</span>
                            {% elif item.status == 'Wrong' %}
                                <span class="status-wrong">❌ Wrong</span>
                            {% else %}
                                <span class="status-unattended">⚪ None</span>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        {% endfor %}
        
        <div class="admin-link">
            📢 <strong>Instructor Live Registry Ledger Link:</strong><br>
            To review aggregate rankings and global analytics metrics, go to: 
            <a href="/dashboard" target="_blank">http://127.0.0.1:5000/dashboard</a>
        </div>
 
        <div style="text-align:center; margin-top: 35px; margin-bottom: 15px;">
            <a href="/" style="background-color:#1f497d; color:white; text-decoration:none; padding:12px 28px; border-radius:4px; font-weight:bold;">Return to Portal</a>
        </div>
    </div>
</body>
</html>
"""
 
TEACHER_DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Instructor Ledger Overview & Analytics</title>
    <style>
        body { font-family: 'Segoe UI', 'Segoe UI Symbol', 'Cambria Math', Arial, sans-serif; background-color: #f5f7fa; color: #333; padding: 20px; }
        .container { max-width: 1100px; background: white; padding: 35px; margin: 20px auto; border-radius: 6px; box-shadow: 0 4px 12px rgba(0,0,0,0.08); }
        h2 { color: #1f497d; margin-bottom: 10px; }
        .url-badge { background: #e2e8f0; color: #0f172a; padding: 6px 12px; border-radius: 4px; font-family: monospace; font-size: 14px; margin-bottom: 20px; display: inline-block; }
        table { width: 100%; border-collapse: collapse; margin-top: 15px; margin-bottom: 20px; }
        th, td { padding: 12px; border: 1px solid #cbd5e1; text-align: left; font-size: 14px; }
        th { background-color: #1f497d; color: white; }
        .badge-strength { background-color: #dcfce7; color: #166534; padding: 3px 6px; border-radius: 4px; font-weight: bold; font-size: 12px; }
        .badge-weakness { background-color: #fee2e2; color: #991b1b; padding: 3px 6px; border-radius: 4px; font-weight: bold; font-size: 12px; }
        .analysis-box { font-size: 13px; line-height: 1.4; }
    </style>
</head>
<body>
    <div class="container">
        <h2>Evaluated Scoreboard Registry & Analytics Panel</h2>
        <div>Localhost Address URL: <span class="url-badge">http://127.0.0.1:5000/dashboard</span></div>
        
        <a href="/download-excel" style="background-color:#16a34a; color:white; text-decoration:none; padding:10px 18px; border-radius:4px; font-weight:bold; display:inline-block; margin-bottom:20px;">Export Registry via CSV</a>
        
        <table>
            <thead>
                <tr>
                    <th>Candidate</th>
                    <th>Stream</th>
                    <th>Physics</th>
                    <th>Chemistry</th>
                    <th>Mathematics</th>
                    <th>Biology</th>
                    <th>Aggregate Total</th>
                    <th>Performance Diagnostics Summary</th>
                </tr>
            </thead>
            <tbody>
                {% for student, data in data.items() %}
                <tr>
                    <td><strong>{{ student }}</strong></td>
                    <td><span style="font-weight:600; color:#475569;">{{ data.stream }}</span></td>
                    <td>{{ data.Physics }}</td>
                    <td>{{ data.Chemistry }}</td>
                    <td>{{ data.Mathematics }}</td>
                    <td>{{ data.Biology }}</td>
                    <td><strong style="color:#1e40af; font-size:15px;">{{ data.GrandTotal }}</strong></td>
                    <td>
                        <div class="analysis-box">
                            <strong>Status:</strong> {{ data.Analysis.Accuracy }}<br>
                            {% if data.Analysis.Strengths %}
                                <span class="badge-strength">Strength:</span> {{ data.Analysis.Strengths }}<br>
                            {% endif %}
                            {% if data.Analysis.Weaknesses %}
                                <span class="badge-weakness">Focus Area:</span> {{ data.Analysis.Weaknesses }}
                            {% endif %}
                        </div>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</body>
</html>
"""
 
@app.route('/')
def main_portal():
    return render_template_string(MAIN_PORTAL_TEMPLATE)
 
@app.route('/unified-test-board', methods=['POST'])
def launch_board():
    student_name = request.form.get('student_name', '').strip()
    stream_choice = request.form.get('stream', 'NEET')
    
    subjects = ['Physics', 'Chemistry', 'Mathematics', 'Biology']
    segments = {}
    
    for s in subjects:
        file_match = get_subject_file(s, stream_choice)
        segments[s] = load_questions_from_docx(file_match) if file_match else []
            
    return render_template_string(
        UNIFIED_EXAM_PANEL_TEMPLATE, 
        name=student_name, 
        stream=stream_choice, 
        segments=segments
    )
 
@app.route('/submit-unified-exam', methods=['POST'])
def process_assessment():
    student_name = request.form.get('student_name', 'Anonymous Student').strip()
    stream_choice = request.form.get('stream', 'NEET')
    
    subjects = ['Physics', 'Chemistry', 'Mathematics', 'Biology']
    breakdown = {}
    detailed_report = {}
    grand_total = 0
    scores_for_analysis = {}
 
    letter_to_idx = {'A': 0, 'B': 1, 'C': 2, 'D': 3}
 
    for s in subjects:
        if s == 'Biology' and stream_choice != 'NEET':
            continue
        if s == 'Mathematics' and stream_choice != 'JEE':
            continue
            
        file_match = get_subject_file(s, stream_choice)
        questions = load_questions_from_docx(file_match) if file_match else []
        
        subject_score = 0
        has_attempted_subject = False
        detailed_report[s] = []
        
        for idx, q in enumerate(questions):
            field_name = f"{s}_q_{q['id']}"
            student_answer = request.form.get(field_name, '').strip().upper()
            
            # Clean LaTeX tokens and markers from raw correct answer string
            clean_correct = re.sub(r'[\$\\]', '', q['correct']).strip()
            
            # Detect numerical type-in inputs automatically
            is_numeric_input = student_answer.replace('.', '', 1).replace('-', '', 1).isdigit()
            is_typein_question = (stream_choice == 'JEE') and (len(q['options']) == 0 or is_numeric_input)
            
            q_index = idx + 1
            q_snippet = re.sub('<[^<]+?>', '', q['question'])[:55] 
            
            correct_letter = q['correct'].strip().upper()
            
            marked_display_text = '<em style="color:#94a3b8;">Not Attempted</em>'
            correct_display_text = f"<strong>({correct_letter})</strong>"
 
            if correct_letter in letter_to_idx:
                c_idx = letter_to_idx[correct_letter]
                if c_idx < len(q['options']):
                    correct_display_text = f"<strong>({correct_letter})</strong> {q['options'][c_idx]}"
            else:
                correct_display_text = q['correct']
            
            if student_answer:
                has_attempted_subject = True
                
                if student_answer in letter_to_idx:
                    s_idx = letter_to_idx[student_answer]
                    if s_idx < len(q['options']):
                        marked_display_text = f"<strong>({student_answer})</strong> {q['options'][s_idx]}"
                else:
                    marked_display_text = student_answer
 
                if is_typein_question:
                    if typein_answers_match(clean_correct, student_answer):
                        marks_awarded = 4
                        status_label = "Correct"
                    else:
                        marks_awarded = 0
                        status_label = "Wrong"
                else:
                    if student_answer == correct_letter:
                        marks_awarded = 4
                        status_label = "Correct"
                    else:
                        marks_awarded = -1
                        status_label = "Wrong"
            else:
                marks_awarded = 0
                status_label = "Not Attended"
                
            subject_score += marks_awarded
            detailed_report[s].append({
                "q_index": q_index,
                "q_snippet": q_snippet,
                "marked_answer": marked_display_text,
                "correct_answer": correct_display_text,
                "status": status_label,
                "marks": marks_awarded
            })
                        
        if has_attempted_subject or questions:
            breakdown[s] = subject_score
            scores_for_analysis[s] = subject_score
            grand_total += subject_score
        else:
            breakdown[s] = 'Not Attempted'
            
    strengths = []
    weaknesses = []
    for sub, val in scores_for_analysis.items():
        if isinstance(val, int):
            if val >= 12:  
                strengths.append(sub)
            elif val < 4:
                weaknesses.append(sub)
 
    accuracy_rating = "Excellent Balance" if grand_total >= 36 else "Moderate Progress" if grand_total >= 16 else "Needs Remedial Support"
    
    analysis_payload = {
        "Accuracy": accuracy_rating,
        "Strengths": ", ".join(strengths) if strengths else "Consistent Across Units",
        "Weaknesses": ", ".join(weaknesses) if weaknesses else "No Critical Weaknesses Identified"
    }
 
    if student_name not in performance_db:
        performance_db[student_name] = {'stream': stream_choice}
    
    performance_db[student_name]['GrandTotal'] = grand_total
    performance_db[student_name]['Analysis'] = analysis_payload
 
    for s in ['Physics', 'Chemistry', 'Mathematics', 'Biology']:
        performance_db[student_name][s] = breakdown.get(s, 'Not Attempted')
            
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return render_template_string(
        ASSESSMENT_RESULT_TEMPLATE,
        name=student_name,
        stream=stream_choice,
        breakdown=breakdown,
        detailed_report=detailed_report,
        grand_total=grand_total,
        timestamp=timestamp_str
    )
 
@app.route('/dashboard')
def teacher_dashboard():
    return render_template_string(TEACHER_DASHBOARD_TEMPLATE, data=performance_db)
 
@app.route('/download-excel')
def download_excel():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Student Name', 'Target Stream', 'Physics Score', 'Chemistry Score', 'Mathematics Score', 'Biology Score', 'Grand Total'])
    for student, profile in performance_db.items():
        writer.writerow([
            student,
            profile.get('stream', 'N/A'),
            profile.get('Physics', 'Not Attempted'),
            profile.get('Chemistry', 'Not Attempted'),
            profile.get('Mathematics', 'Not Attempted'),
            profile.get('Biology', 'Not Attempted'),
            profile.get('GrandTotal', 0)
        ])
    response = Response(output.getvalue(), mimetype="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=assessment_registry.csv"
    return response
 
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)