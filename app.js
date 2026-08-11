const fs = require('fs');
const path = require('path');
const express = require('express');
const mammoth = require('mammoth');
const cheerio = require('cheerio');

const app = express();
const staticDir = path.join(__dirname, 'static');
const docxDir = __dirname;
const performanceDb = {};

app.use(express.urlencoded({ extended: true }));
app.use('/static', express.static(staticDir));

function ensureDirectoryExists(dirPath) {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
  }
}

ensureDirectoryExists(staticDir);

function getSubjectFile(subjectKeyword, stream) {
  const files = fs.readdirSync(docxDir).filter((file) => file.toLowerCase().endsWith('.docx'));
  const keyword = String(subjectKeyword || '').toLowerCase().trim();
  const streamSuffix = String(stream || '').toLowerCase().trim();

  let matchTokens;
  if (keyword.includes('phy')) {
    matchTokens = ['phy', streamSuffix];
  } else if (keyword.includes('chem')) {
    matchTokens = ['chem', streamSuffix];
  } else if (keyword.includes('math')) {
    matchTokens = ['math', streamSuffix];
  } else if (keyword.includes('bio')) {
    matchTokens = ['bio', streamSuffix];
  } else {
    matchTokens = [keyword.slice(0, 3), streamSuffix];
  }

  for (const file of files) {
    const filename = path.basename(file);
    if (filename.startsWith('~$')) {
      continue;
    }
    const lower = filename.toLowerCase();
    if (matchTokens.every((token) => token && lower.includes(token))) {
      return path.join(docxDir, filename);
    }
  }

  return null;
}

function preserveHtmlTags(text) {
  const tags = [];
  const protectedText = text.replace(/<[^>]+>/g, (match) => {
    tags.push(match);
    return `___HTML_TAG_${tags.length - 1}___`;
  });
  return { protectedText, tags };
}

function restoreHtmlTags(text, tags) {
  return text.replace(/___HTML_TAG_(\d+)___/g, (match, index) => tags[Number(index)] || '');
}

function wrapLatexInDollars(text) {
  if (!text) return text;
  if (text.includes('\\') && !text.includes('$')) {
    return text.replace(/(\\[a-zA-Z]+(?:\{[^{}]*\}|\^\{[^{}]*\}|_[^{}]*|[\\s\\d\\w\\+\-\=\|\(\)])+)/g, '$$$1$');
  }
  return text;
}

function addUnitVectorHats(text) {
  if (!text) return text;

  const lower = text.toLowerCase();
  const complexMarkers = [
    'complex number',
    'complex no',
    'iota',
    'imaginary',
    'argand',
    'conjugate',
    '\u221a-1',
    '\u221a(-1)',
    'modulus of z',
    'modulus of the complex'
  ];

  if (complexMarkers.some((marker) => lower.includes(marker))) {
    return text;
  }

  const pattern = /(?<![A-Za-z])([ijk])(?![A-Za-z])/gi;
  const distinctLetters = new Set((text.match(pattern) || []).map((m) => m.toLowerCase()));
  const looksLikeVector = lower.includes('vector') || distinctLetters.size >= 2;
  if (!looksLikeVector) {
    return text;
  }

  return text.replace(pattern, (_, letter) => `${letter}\u0302`);
}

function addVectorArrows(text) {
  if (!text) return text;

  text = text.replace(/\b(vectors?)\b((?:\s*(?:and|\+|-|\u2212|,)\s*[A-Z]\b)+)/gi, (match, prefix, rest) => {
    const transformed = rest.replace(/\b([A-Z])\b/g, (m, letter) => `${letter}\u20d7`);
    return `${prefix}${transformed}`;
  });

  text = text.replace(/\b([A-Z])(\s*)\u00d7(\s*)([A-Z])\b/g, (match, a, s1, s2, b) => `${a}\u20d7${s1}\u00d7${s2}${b}\u20d7`);

  text = text.replace(/\b(angle\s+between)\s+([A-Z])(\s+and\s+)([A-Z])\b/gi, (match, prefix, a, middle, b) => `${prefix} ${a}\u20d7${middle}${b}\u20d7`);

  const eqMatches = [];
  const regex = /\b([A-Z])\s*=/g;
  let m;
  while ((m = regex.exec(text))) {
    eqMatches.push({ index: m.index, letter: m[1], end: m.index + m[0].length });
  }

  for (let idx = eqMatches.length - 1; idx >= 0; idx -= 1) {
    const start = eqMatches[idx].end;
    const end = idx + 1 < eqMatches.length ? eqMatches[idx + 1].index : text.length;
    const segment = text.slice(start, end);
    const cut = segment.search(/[,.;]/);
    const segmentCheck = cut >= 0 ? segment.slice(0, cut) : segment;
    if (/\u0302/.test(segmentCheck)) {
      const letterPos = eqMatches[idx].index;
      text = `${text.slice(0, letterPos)}${eqMatches[idx].letter}\u20d7${text.slice(letterPos + 1)}`;
    }
  }

  const arrowedLetters = new Set((text.match(/([A-Z])\u20d7/g) || []).map((m) => m[1]));
  if (arrowedLetters.size > 0) {
    text = text.replace(/\b([A-Z])\b(?!\u20d7)/g, (match, letter) => (arrowedLetters.has(letter) ? `${letter}\u20d7` : letter));
  }

  return text;
}

function formatLogSubscripts(text) {
  if (!text) return text;
  const { protectedText, tags } = preserveHtmlTags(text);
  let result = protectedText;

  if (result.includes('\\') && !result.includes('$')) {
    result = wrapLatexInDollars(result);
  }

  result = addUnitVectorHats(result);
  result = addVectorArrows(result);

  result = result.replace(/5\s*log\s*5\s*\(([^)]+)\)/g, '5<sup>log<sub>5</sub>($1)</sup>');
  result = result.replace(/4\s*log\s*2\s*\(([^)]+)\)\]?/g, '4<sup>log<sub>2</sub>($1)</sup>');
  result = result.replace(/\blog\s*([0-9]+)\s*(\([^)]+\)|[a-zA-Z𝑥xVariable𝑋])/g, 'log<sub>$1</sub>$2');
  result = result.replace(/\blog\s*([√\u221A]\s*[a-zA-Z𝑥xVariable𝑋])/g, 'log<sub>$1</sub>');
  result = result.replace(/([a-zA-Z0-9𝑥xVariable𝑋\)\s\.\+\-\[\]\{\}]+)\s*\^\s*([+\-]?[0-9a-zA-Z\s\.\+\-\[\]\{\}]+)/g, '$1<sup>$2</sup>');
  result = result.replace(/(?<![\d\.])10([2-9]\d|\-\d+)(?![\d\.])/g, '10<sup>$1</sup>');
  result = result.replace(/\b([MLT])\s*([+\-]?[0-9]+)/g, '$1<sup>$2</sup>');
  result = result.replace(/\b(m|cm|dm|mm|km|s|sec)([23])\b/g, '$1<sup>$2</sup>');
  result = result.replace(/(?<![0-9\.])\b([a-zA-Z𝑥XVariable𝑋vtaxfghzVGP])([2345])\b/g, '$1<sup>$2</sup>');
  result = result.replace(/\b([a-zA-Z𝑥xVariable𝑋]+)-\s*([0-9]+)\b/g, '$1<sup>-$2</sup>');
  result = result.replace(/(?<=[A-Za-z])([0-9]+)(?![0-9]*\.)/g, '<sub>$1</sub>');
  result = result.replace(/\b([A-Z][a-z]?)([0-9]*[+-])/g, '$1<sup>$2</sup>');
  result = result.replace(/\b([FF])([12])\b/g, '$1<sub>$2</sub>');
  result = result.replace(/\^/g, '');

  return restoreHtmlTags(result, tags);
}

function _parseNumericToken(text) {
  if (!text) return null;
  const m = text.match(/^\s*([+-]?(?:\d+\s*\/\s*\d+|\d+\.\d+|\d+))/);
  if (!m) return null;
  const tok = m[1].replace(/\s+/g, '');
  try {
    if (tok.includes('/')) {
      const [num, den] = tok.split('/');
      return parseFloat(num) / parseFloat(den);
    }
    return parseFloat(tok);
  } catch (e) {
    return null;
  }
}

function _parseNumericTokenStrict(text) {
  if (!text) return null;
  const m = text.match(/^\s*([+-]?(?:\d+\s*\/\s*\d+|\d+\.\d+|\d+))\s*[a-zA-Z°%Ωμ]*\s*$/u);
  if (!m) return null;
  const tok = m[1].replace(/\s+/g, '');
  try {
    if (tok.includes('/')) {
      const [num, den] = tok.split('/');
      return parseFloat(num) / parseFloat(den);
    }
    return parseFloat(tok);
  } catch (e) {
    return null;
  }
}

function typeinAnswersMatch(correctAnswer, studentAnswer) {
  const c = String(correctAnswer || '').trim().toLowerCase();
  const s = String(studentAnswer || '').trim().toLowerCase();
  if (!s) return false;
  if (c === s) return true;
  if (c.replace(/\s+/g, '') === s.replace(/\s+/g, '')) return true;
  const cNum = _parseNumericTokenStrict(c);
  const sNum = _parseNumericToken(s);
  if (cNum !== null && sNum !== null) {
    return Math.abs(cNum - sNum) < 1e-6;
  }
  return false;
}

async function loadQuestionsFromDocx(filePath) {
  if (!filePath || !fs.existsSync(filePath)) {
    return [];
  }
  ensureDirectoryExists(staticDir);

  let imageCounter = 1;
  const result = await mammoth.convertToHtml({ path: filePath }, {
    convertImage: mammoth.images.imgElement(async (image) => {
      const imageBuffer = await image.read('base64');
      const extension = image.contentType.split('/')[1] || 'png';
      const imageFilename = `extracted_${path.basename(filePath, '.docx')}_${Date.now()}_${imageCounter}.${extension}`;
      const targetPath = path.join(staticDir, imageFilename);
      fs.writeFileSync(targetPath, Buffer.from(imageBuffer, 'base64'));
      imageCounter += 1;
      return { src: `/static/${imageFilename}` };
    })
  });

  const htmlContent = result.value;
  const $ = cheerio.load(htmlContent);
  const questions = [];
  let currentQuestionText = null;
  let currentOptions = [];
  let currentCorrect = '';
  let qCounter = 1;

  const flushQuestion = () => {
    if (currentQuestionText !== null) {
      const stored = {
        id: qCounter,
        question: formatLogSubscripts(currentQuestionText),
        options: currentOptions.map((opt) => formatLogSubscripts(opt)),
        correct: currentCorrect.trim()
      };
      questions.push(stored);
      qCounter += 1;
    }
  };

  $('p').each((_, p) => {
    const paragraph = $(p);
    const rawText = paragraph.text().trim();
    const paragraphHtml = paragraph.html().trim();
    const hasImage = paragraph.find('img').length > 0;
    const extractedText = wrapLatexInDollars(rawText);
    const answerCandidate = extractedText.toLowerCase();
    const isNewQuestion = /^\s*(?:Q|q)?\d+[\.\)\:]\s+/.test(extractedText);
    const isOptionLine = /^\s*[\(\[\{]?[A-Da-d][\)\]\}]?[\s\.]|^\s*\([A-Da-d]\)/.test(extractedText);
    const isAnswerLine = /correct answer/i.test(extractedText) || /^\s*answer\s*:/i.test(extractedText) || /^\s*\([A-Da-d]\)\s*$/i.test(extractedText);
    const imagesHtml = paragraph.find('img').map((_, img) => $.html(img)).get().join('');

    if (isNewQuestion || (extractedText === '' && hasImage && currentQuestionText === null)) {
      flushQuestion();
      currentQuestionText = extractedText ? extractedText.replace(/^\s*(?:Q|q)?\d+[\.\)\:]\s*/, '').trim() : '';
      currentOptions = [];
      currentCorrect = '';
    } else if (isOptionLine) {
      currentOptions.push(extractedText);
    } else if (isAnswerLine) {
      const ansMatch = extractedText.match(/\(([A-Da-d])\)|:\s*([A-Da-d])|\[([A-Da-d])\]/i);
      if (ansMatch) {
        currentCorrect = (ansMatch[1] || ansMatch[2] || ansMatch[3] || '').toUpperCase();
      } else {
        const cleaned = extractedText.replace(/^\s*(correct\s+answer|answer)\s*:?	*/i, '').trim();
        currentCorrect = cleaned || extractedText;
      }
    } else {
      if (currentQuestionText !== null && currentOptions.length === 0 && extractedText) {
        currentQuestionText = currentQuestionText ? `${currentQuestionText}<br>${extractedText}` : extractedText;
      }
    }

    if (hasImage && currentQuestionText !== null && imagesHtml) {
      currentQuestionText = currentQuestionText ? `${currentQuestionText}<br>${imagesHtml}` : imagesHtml;
    }
  });

  flushQuestion();
  return questions;
}

function renderMainPortal() {
  return `<!DOCTYPE html>
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
    <script src="https://static.zohocdn.com/catalyst/sdk/js/4.6.2/catalystWebSDK.js"></script>
    <script src="/__catalyst/sdk/init.js"></script>
</body>
</html>`}]}{;
}

function renderUnifiedExamPanel(name, stream, segments) {
  const subjectButtons = [];
  const sections = [];
  const subjects = ['Physics', 'Chemistry', 'Mathematics', 'Biology'];

  subjects.forEach((sub) => {
    if (sub === 'Biology' && stream !== 'NEET') return;
    if (sub === 'Mathematics' && stream !== 'JEE') return;
    const activeClass = sub === 'Physics' ? 'active' : '';
    subjectButtons.push(`<button type="button" class="tab-btn ${activeClass}" onclick="switchSubject('${sub}', event)">${sub} Section</button>`);

    const segment = segments[sub] || [];
    let contentHtml;
    if (segment.length > 0) {
      contentHtml = segment.map((q, index) => {
        const questionBlock = [];
        questionBlock.push(`<div class="question-block">
                                <p><strong>Q${index + 1}. ${q.question}</strong>${stream === 'JEE' && q.options.length === 0 ? '<span class="badge-info">Type-in Answer (No Negative Marks)</span>' : ''}</p>`);
        if (stream === 'JEE' && q.options.length === 0) {
          questionBlock.push(`<input type="text" class="typein-input" name="${sub}_q_${q.id}" placeholder="Type your numerical answer here...">`);
        } else {
          const optionsHtml = q.options.map((option, optionIdx) => {
            const letter = ['A', 'B', 'C', 'D'][optionIdx] || String.fromCharCode(65 + optionIdx);
            return `<div class="option">
                        <input type="radio" id="${sub}_q_${q.id}_${optionIdx}" name="${sub}_q_${q.id}" value="${letter}">
                        <label style="cursor:pointer;" for="${sub}_q_${q.id}_${optionIdx}">${option}</label>
                    </div>`;
          }).join('');
          questionBlock.push(optionsHtml);
        }
        questionBlock.push('</div>');
        return questionBlock.join('\n');
      }).join('\n');
    } else {
      contentHtml = `<p class="err-msg">Error: Missing or unreadable Word (.docx) file matching key '${sub}' in workspace folder.</p>`;
    }
    sections.push(`<div id="section_${sub}" class="subject-section ${sub === 'Physics' ? 'active' : ''}">
                    <h3>${sub} Assessment Pool</h3>
                    ${contentHtml}
                </div>`);
  });

  return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Unified Examination Board</title>
    <script>
        window.MathJax = {
            tex: {
                inlineMath: [['$', '$'], ['\\(', '\\)']],
                displayMath: [['$$', '$$'], ['\\[', '\\]']]
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
        <div class="welcome">Candidate: <strong>${name}</strong> | Target Stream: <span class="meta-tag">${stream}</span></div>
        <div class="marking-scheme">
            ${stream === 'JEE' ? '⚠️ Core Rules Matrix: MCQ Sections (+4 / -1 Mark) | Last 5 Questions (+4 / 0 No Negative Marks)' : '⚠️ Core Rules Matrix: All Questions MCQ (+4 / -1 Mark Negative Marks Apply Throughout)'}
        </div>
        <div class="timer-box" id="countdown-display">Remaining Time: 03:00:00</div>
        <div class="subject-tabs">
            ${subjectButtons.join('\n')}
        </div>
        <form id="exam-form" action="/submit-unified-exam" method="POST">
            <input type="hidden" name="student_name" value="${name}">
            <input type="hidden" name="stream" value="${stream}">
            ${sections.join('\n')}
            <button type="submit" id="submit-btn" disabled>Submission Locked (Enabled after 2h 50m)</button>
            <span class="lock-warning" id="lock-text">🔒 Early submission is locked. You can submit when the countdown reaches 00:10:00.</span>
        </form>
    </div>
    <script>
        function switchSubject(subjectName, event) {
            const sections = document.getElementsByClassName('subject-section');
            const tabs = document.getElementsByClassName('tab-btn');
            for (let i = 0; i < sections.length; i += 1) {
                sections[i].style.display = 'none';
            }
            for (let i = 0; i < tabs.length; i += 1) {
                tabs[i].classList.remove('active');
            }
            document.getElementById('section_' + subjectName).style.display = 'block';
            event.currentTarget.classList.add('active');
        }

        let totalSeconds = 10 * 60;
        const lockThresholdSeconds = 10 * 60;
        const timerInterval = setInterval(() => {
            if (totalSeconds <= 0) {
                clearInterval(timerInterval);
                document.getElementById('lock-screen').style.display = 'block';
                setTimeout(() => document.getElementById('exam-form').submit(), 4000);
            } else {
                totalSeconds -= 1;
                const hrs = Math.floor(totalSeconds / 3600);
                const mins = Math.floor((totalSeconds % 3600) / 60);
                const secs = totalSeconds % 60;
                document.getElementById('countdown-display').innerHTML = 'Remaining Time: ' +
                    (hrs < 10 ? '0' : '') + hrs + ':' +
                    (mins < 10 ? '0' : '') + mins + ':' +
                    (secs < 10 ? '0' : '') + secs;
                if (totalSeconds <= lockThresholdSeconds) {
                    const btn = document.getElementById('submit-btn');
                    if (btn.hasAttribute('disabled')) {
                        btn.removeAttribute('disabled');
                        btn.className = 'ready';
                        btn.innerHTML = 'Finalize Assessment Submission';
                        document.getElementById('lock-text').style.display = 'none';
                    }
                }
            }
        }, 1000);
    </script>
    <script src="https://static.zohocdn.com/catalyst/sdk/js/4.6.2/catalystWebSDK.js"></script>
    <script src="/__catalyst/sdk/init.js"></script>
</body>
</html>`;
}

function renderAssessmentResult(name, stream, breakdown, detailedReport, grandTotal, timestamp) {
  const breakdownRows = Object.entries(breakdown).map(([subject, score]) => `
            <tr>
                <td><strong>${subject} Category Total</strong></td>
                <td><span class="score-positive">${score} Marks</span></td>
            </tr>`).join('');

  const detailedSections = Object.entries(detailedReport).map(([subject, items]) => {
    const rows = items.map((item) => `
                    <tr>
                        <td><strong>${item.q_index}</strong></td>
                        <td style="font-size:13px; color:#4b5563;">${item.q_snippet}...</td>
                        <td class="answer-text">${item.marked_answer}</td>
                        <td class="answer-text">${item.correct_answer}</td>
                        <td>${item.status === 'Correct' ? '<span class="status-correct">✔ Correct</span>' : item.status === 'Wrong' ? '<span class="status-wrong">❌ Wrong</span>' : '<span class="status-unattended">⚪ None</span>'}</td>
                    </tr>`).join('');
    return `
            <h4 style="color:#334155; margin-bottom:5px; margin-top:20px;">📌 ${subject} Section</h4>
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
                    ${rows}
                </tbody>
            </table>`;
  }).join('');

  return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Assessment Verification Report</title>
    <script>
        window.MathJax = {
            tex: {
                inlineMath: [['$', '$'], ['\\(', '\\)']],
                displayMath: [['$$', '$$'], ['\\[', '\\]']]
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
            <strong>Candidate Name:</strong> ${name}<br>
            <strong>Exam Variant:</strong> ${stream}<br>
            <strong>Evaluation Timestamp:</strong> ${timestamp}
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
                ${breakdownRows}
                <tr style="background-color: #f1f5f9; font-size: 16px;">
                    <td><strong>Grand Cumulative Score Metric</strong></td>
                    <td><strong style="color:#1e40af;">${grandTotal} Marks</strong></td>
                </tr>
            </tbody>
        </table>
        <div class="summary-card">Grand Final Score: ${grandTotal} Marks</div>
        <h3>Itemized Question Evaluation Ledger</h3>
        ${detailedSections}
        <div class="admin-link">
            📢 <strong>Instructor Live Registry Ledger Link:</strong><br>
            To review aggregate rankings and global analytics metrics, go to: 
            <a href="/dashboard" target="_blank">http://127.0.0.1:5000/dashboard</a>
        </div>
        <div style="text-align:center; margin-top: 35px; margin-bottom: 15px;">
            <a href="/" style="background-color:#1f497d; color:white; text-decoration:none; padding:12px 28px; border-radius:4px; font-weight:bold;">Return to Portal</a>
        </div>
    </div>
    <script src="https://static.zohocdn.com/catalyst/sdk/js/4.6.2/catalystWebSDK.js"></script>
    <script src="/__catalyst/sdk/init.js"></script>
</body>
</html>`;
}

function renderTeacherDashboard(data) {
  const rows = Object.entries(data).map(([student, profile]) => `
            <tr>
                <td><strong>${student}</strong></td>
                <td><span style="font-weight:600; color:#475569;">${profile.stream}</span></td>
                <td>${profile.Physics || 'Not Attempted'}</td>
                <td>${profile.Chemistry || 'Not Attempted'}</td>
                <td>${profile.Mathematics || 'Not Attempted'}</td>
                <td>${profile.Biology || 'Not Attempted'}</td>
                <td><strong style="color:#1e40af; font-size:15px;">${profile.GrandTotal || 0}</strong></td>
                <td>
                    <div class="analysis-box">
                        <strong>Status:</strong> ${profile.Analysis?.Accuracy || 'N/A'}<br>
                        ${profile.Analysis?.Strengths ? `<span class="badge-strength">Strength:</span> ${profile.Analysis.Strengths}<br>` : ''}
                        ${profile.Analysis?.Weaknesses ? `<span class="badge-weakness">Focus Area:</span> ${profile.Analysis.Weaknesses}` : ''}
                    </div>
                </td>
            </tr>`).join('');

  return `<!DOCTYPE html>
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
                ${rows}
            </tbody>
        </table>
    </div>
    <script src="https://static.zohocdn.com/catalyst/sdk/js/4.6.2/catalystWebSDK.js"></script>
    <script src="/__catalyst/sdk/init.js"></script>
</body>
</html>`}]}{;
}

app.get('/', (req, res) => {
  res.send(renderMainPortal());
});

app.post('/unified-test-board', async (req, res) => {
  const studentName = String(req.body.student_name || '').trim();
  const streamChoice = String(req.body.stream || 'NEET').trim();
  const subjects = ['Physics', 'Chemistry', 'Mathematics', 'Biology'];
  const segments = {};

  for (const subject of subjects) {
    const fileMatch = getSubjectFile(subject, streamChoice);
    segments[subject] = fileMatch ? await loadQuestionsFromDocx(fileMatch) : [];
  }

  res.send(renderUnifiedExamPanel(studentName, streamChoice, segments));
});

app.post('/submit-unified-exam', async (req, res) => {
  const studentName = String(req.body.student_name || 'Anonymous Student').trim();
  const streamChoice = String(req.body.stream || 'NEET').trim();
  const subjects = ['Physics', 'Chemistry', 'Mathematics', 'Biology'];
  const letterToIdx = { A: 0, B: 1, C: 2, D: 3 };

  const breakdown = {};
  const detailedReport = {};
  let grandTotal = 0;
  const scoresForAnalysis = {};

  for (const subject of subjects) {
    if (subject === 'Biology' && streamChoice !== 'NEET') continue;
    if (subject === 'Mathematics' && streamChoice !== 'JEE') continue;

    const fileMatch = getSubjectFile(subject, streamChoice);
    const questions = fileMatch ? await loadQuestionsFromDocx(fileMatch) : [];
    let subjectScore = 0;
    let hasAttemptedSubject = false;
    detailedReport[subject] = [];

    for (let idx = 0; idx < questions.length; idx += 1) {
      const q = questions[idx];
      const fieldName = `${subject}_q_${q.id}`;
      const studentAnswerRaw = String(req.body[fieldName] || '').trim();
      const studentAnswer = studentAnswerRaw.toUpperCase();
      const cleanCorrect = String(q.correct || '').replace(/[\\$]/g, '').trim();
      const correctLetter = String(q.correct || '').trim().toUpperCase();
      const isNumericInput = /^-?\d+(?:\.\d+)?$/.test(studentAnswerRaw);
      const isTypeinQuestion = streamChoice === 'JEE' && (q.options.length === 0 || isNumericInput);
      const qSnippet = q.question.replace(/<[^>]+>/g, '').slice(0, 55);
      let markedDisplayText = '<em style="color:#94a3b8;">Not Attempted</em>';
      let correctDisplayText = `<strong>(${correctLetter})</strong>`;

      if (letterToIdx[correctLetter] !== undefined && letterToIdx[correctLetter] < q.options.length) {
        correctDisplayText = `<strong>(${correctLetter})</strong> ${q.options[letterToIdx[correctLetter]]}`;
      } else if (q.correct) {
        correctDisplayText = q.correct;
      }

      let marksAwarded = 0;
      let statusLabel = 'Not Attended';

      if (studentAnswer) {
        hasAttemptedSubject = true;
        if (letterToIdx[studentAnswer] !== undefined && letterToIdx[studentAnswer] < q.options.length) {
          markedDisplayText = `<strong>(${studentAnswer})</strong> ${q.options[letterToIdx[studentAnswer]]}`;
        } else {
          markedDisplayText = studentAnswerRaw;
        }

        if (isTypeinQuestion) {
          if (typeinAnswersMatch(cleanCorrect, studentAnswerRaw)) {
            marksAwarded = 4;
            statusLabel = 'Correct';
          } else {
            marksAwarded = 0;
            statusLabel = 'Wrong';
          }
        } else {
          if (studentAnswer === correctLetter) {
            marksAwarded = 4;
            statusLabel = 'Correct';
          } else {
            marksAwarded = -1;
            statusLabel = 'Wrong';
          }
        }
      }

      subjectScore += marksAwarded;
      detailedReport[subject].push({
        q_index: idx + 1,
        q_snippet: qSnippet,
        marked_answer: markedDisplayText,
        correct_answer: correctDisplayText,
        status: statusLabel,
        marks: marksAwarded
      });
    }

    if (hasAttemptedSubject || questions.length > 0) {
      breakdown[subject] = subjectScore;
      scoresForAnalysis[subject] = subjectScore;
      grandTotal += subjectScore;
    } else {
      breakdown[subject] = 'Not Attempted';
    }
  }

  const strengths = [];
  const weaknesses = [];
  Object.entries(scoresForAnalysis).forEach(([subject, score]) => {
    if (typeof score === 'number') {
      if (score >= 12) strengths.push(subject);
      else if (score < 4) weaknesses.push(subject);
    }
  });

  const accuracyRating = grandTotal >= 36 ? 'Excellent Balance' : grandTotal >= 16 ? 'Moderate Progress' : 'Needs Remedial Support';
  const analysisPayload = {
    Accuracy: accuracyRating,
    Strengths: strengths.length ? strengths.join(', ') : 'Consistent Across Units',
    Weaknesses: weaknesses.length ? weaknesses.join(', ') : 'No Critical Weaknesses Identified'
  };

  performanceDb[studentName] = {
    stream: streamChoice,
    GrandTotal: grandTotal,
    Analysis: analysisPayload,
    Physics: breakdown.Physics || 'Not Attempted',
    Chemistry: breakdown.Chemistry || 'Not Attempted',
    Mathematics: breakdown.Mathematics || 'Not Attempted',
    Biology: breakdown.Biology || 'Not Attempted'
  };

  const timestampStr = new Date().toISOString().replace('T', ' ').slice(0, 19);
  res.send(renderAssessmentResult(studentName, streamChoice, breakdown, detailedReport, grandTotal, timestampStr));
});

app.get('/dashboard', (req, res) => {
  res.send(renderTeacherDashboard(performanceDb));
});

app.get('/download-excel', (req, res) => {
  const rows = ['Student Name,Target Stream,Physics Score,Chemistry Score,Mathematics Score,Biology Score,Grand Total'];
  Object.entries(performanceDb).forEach(([student, profile]) => {
    rows.push(`"${student}","${profile.stream}","${profile.Physics}","${profile.Chemistry}","${profile.Mathematics}","${profile.Biology}","${profile.GrandTotal}"`);
  });
  const csv = rows.join('\n');
  res.setHeader('Content-Type', 'text/csv');
  res.setHeader('Content-Disposition', 'attachment; filename=assessment_registry.csv');
  res.send(csv);
});

const PORT = process.env.PORT || 5000;
app.listen(PORT, () => {
  console.log(`Server started on port ${PORT}`);
});
