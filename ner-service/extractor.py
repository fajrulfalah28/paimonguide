import ast
import re

with open('app.py', 'r', encoding='utf-8') as f:
    source = f.read()

tree = ast.parse(source)

# We want to keep:
# - Variable assignments for ALIAS_MAP, LOCATION_CONNECTORS, LABELS, _ABBREV_RE, RESOLVER_STOPWORDS, NON_LOCATION_QUERY_WORDS, GENERIC_GAZETTEER_TOKENS, and all the MIN_ constants.
# - All function definitions.
# - The Flask app wrapper.

variables_to_keep = {
    'LABELS', 'LOCATION_CONNECTORS', 'ALIAS_MAP', '_ABBREV_RE',
    'RESOLVER_STOPWORDS', 'NON_LOCATION_QUERY_WORDS', 'GENERIC_GAZETTEER_TOKENS',
    'OVERLAP_MIN_SCORE', 'FUZZY_OVERLAP_MIN_SCORE', 'RAW_RESOLVED_NAME_FLOOR',
    'AMBIGUITY_MARGIN', 'MAX_RESOLVER_CANDIDATES', 'ALIAS_CONFIDENCE',
    'FUZZY_CONFIDENCE_PENALTY', 'MIN_FUZZY_TOKEN_LENGTH'
}

keep_nodes = []

for node in tree.body:
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id in variables_to_keep:
                keep_nodes.append(node)
                break
    elif isinstance(node, ast.FunctionDef):
        # We want to skip some functions if they are strictly for training/eval.
        # But keeping them is also fine (they won't be called).
        # We'll skip: train_crf, flatten_labels, evaluate, save_model, train_pipeline, validate_uploaded_dataset_file, preview_text_file
        skip = {'train_crf', 'flatten_labels', 'evaluate', 'save_model', 'train_pipeline', 'validate_uploaded_dataset_file', 'preview_text_file', 'display', 'build_feature_matrices', 'augment_with_gazetteer', 'build_augmented_sentence', 'extract_first_location_span', 'parse_tsv_dataset'}
        if node.name not in skip:
            keep_nodes.append(node)

clean_code = '''from flask import Flask, request, jsonify
import json
import pickle
import re
import random
import nltk
from pathlib import Path

app = Flask(__name__)

# Try to download NLTK data on startup
try:
    nltk.data.find('taggers/averaged_perceptron_tagger_eng')
except LookupError:
    try:
        nltk.download('averaged_perceptron_tagger_eng', quiet=True)
    except Exception:
        nltk.download('averaged_perceptron_tagger', quiet=True)

'''

for node in keep_nodes:
    clean_code += ast.unparse(node) + '\\n\\n'

clean_code += '''
# Load model and gazetteer paths
BASE_DIR = Path('../').resolve()
GAZETTEER_PATH = BASE_DIR / 'genshin_areas.json'
MODEL_PATH = BASE_DIR / 'outputs' / 'genshin_location_crf.pkl'

print(f"Loading Gazetteer from {GAZETTEER_PATH}")
gazetteer_names, gazetteer_tokens = load_gazetteer(str(GAZETTEER_PATH))

print(f"Loading Model from {MODEL_PATH}")
with open(MODEL_PATH, 'rb') as f:
    crf_model = pickle.load(f)

@app.route('/extract', methods=['POST'])
def extract():
    data = request.get_json()
    if not data or 'text' not in data:
        return jsonify({'error': 'Missing text field'}), 400
        
    text = data['text']
    try:
        locations = extract_locations(text, crf_model, gazetteer_names, gazetteer_tokens)
        return jsonify({'locations': locations})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)
'''

with open('clean_app.py', 'w', encoding='utf-8') as f:
    f.write(clean_code)

print("Generated clean_app.py!")
