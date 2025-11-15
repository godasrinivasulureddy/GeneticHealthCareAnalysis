from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import json
import random
from googletrans import Translator

app = Flask(__name__)
CORS(app)
translator = Translator()

# Load static data
with open('data/symptoms.json', 'r', encoding='utf-8') as f:
    SYMPTOMS_DB = json.load(f)

with open('data/food.json', 'r', encoding='utf-8') as f:
    FOOD_DB = json.load(f)

with open('data/doctors.json', 'r', encoding='utf-8') as f:
    DOCS_DB = json.load(f)


def simple_analyze(text, lang='en'):
    """
    Basic rule-based analyzer:
    - Detect disease by keywords
    - Score risk based on keyword hits
    - Return disease name, risk (0-100), top factors
    """
    txt = text.lower()
    score = 0
    detected = None
    factors = []

    # Keyword-based detection
    for disease, info in SYMPTOMS_DB.items():
        for kw in info.get('keywords', []):
            if kw.lower() in txt:
                detected = disease
                score += 30
                factors.append(f"Contains keyword: {kw}")
        # count symptoms words match
        for s in info.get('symptoms', []):
            if s.lower() in txt:
                score += 10
                if s not in factors:
                    factors.append(f"Symptom: {s}")

    # If none matched, check common words mapping
    if not detected:
        # fallback: if 'anemia' or 'blood' present suggest thalassemia/sickle
        if 'blood' in txt or 'anemia' in txt or 'pale' in txt:
            detected = 'Thalassemia'
            score += 40
            factors.append('Mentions anemia/blood')

    # clamp
    risk = max(5, min(95, score + random.randint(-5, 10)))
    if not detected:
        detected = 'General Illness'
        factors.append('No specific disease keywords — general analysis')

    # generate 2-4 point summary (rule-based)
    summary_points = []
    disease_info = SYMPTOMS_DB.get(detected, {})
    bullets = disease_info.get('summary', [])
    if bullets:
        summary_points = bullets[:4]
    else:
        summary_points = [
            f"Possible condition: {detected}.",
            "Further clinical tests are recommended.",
            "This is an educational prediction, not a diagnosis."
        ]

    # Food suggestions
    food_suggestions = FOOD_DB.get(detected, FOOD_DB.get('General Illness', []))

    # Doctor recommendation
    doctor_type = DOCS_DB.get(detected, DOCS_DB.get('General Illness', {}))

    result = {
        "disease": detected,
        "risk": risk,
        "factors": factors[:4],
        "summary": summary_points[:4],
        "food": food_suggestions[:4],
        "doctor": doctor_type
    }
    return result


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.json or {}
    text = data.get('text', '')
    lang = data.get('lang', 'en')

    # If text in non-english and googletrans available: translate to english for keyword analysis
    try:
        if lang != 'en':
            trans = translator.translate(text, src=lang, dest='en')
            text_en = trans.text
        else:
            text_en = text
    except Exception as e:
        # translation failed -> fallback
        text_en = text

    # simple analyzer
    res = simple_analyze(text_en, lang=lang)

    # If user wants output in their language, translate summary back
    try:
        if lang != 'en':
            translated_summary = []
            for s in res['summary']:
                t = translator.translate(s, src='en', dest=lang).text
                translated_summary.append(t)
            res['summary_local'] = translated_summary
            # translate food suggestions too
            res['food_local'] = [translator.translate(s, src='en', dest=lang).text for s in res['food']]
            res['disease_local'] = translator.translate(res['disease'], src='en', dest=lang).text
        else:
            res['summary_local'] = res['summary']
            res['food_local'] = res['food']
            res['disease_local'] = res['disease']
    except Exception:
        res['summary_local'] = res['summary']
        res['food_local'] = res['food']
        res['disease_local'] = res['disease']

    return jsonify(res)


if __name__ == "__main__":
    app.run(host='0.0.0.0', port=3000, debug=True)
