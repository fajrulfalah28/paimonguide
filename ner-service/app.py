from flask import Flask, request, jsonify
import json
import pickle
import re
import nltk
from pathlib import Path
import os
import numpy as np
from scipy.optimize import minimize

app = Flask(__name__)

# Try to download NLTK data on startup
try:
    nltk.data.find('taggers/averaged_perceptron_tagger_eng')
except LookupError:
    try:
        nltk.download('averaged_perceptron_tagger_eng', quiet=True)
    except Exception:
        nltk.download('averaged_perceptron_tagger', quiet=True)

LABELS = ["O", "B-LOC", "I-LOC"]
LOCATION_CONNECTORS = {"of", "de", "al", "al-", "the"}
ALIAS_MAP = {
    # === MONDSTADT ===
    "mondo": "mondstadt",
    "mond": "mondstadt",
    "mondstat": "mondstadt", # Typo yang sangat sering terjadi
    "dragon spine": "dragonspine",
    "stormterror": "stormterror's lair",
    "dvalin lair": "stormterror's lair",
    "dvalin's lair": "stormterror's lair",
    
    # === LIYUE ===
    "chasm": "the chasm",
    "chasm underground": "the chasm: underground mines",
    "underground mines": "the chasm: underground mines",
    "chasm maw": "the chasm's maw",
    "liyue city": "liyue harbor",
    "chenyu": "chenyu vale: upper vale", # Biasanya player menyebut chenyu merujuk ke area utamanya
    
    # === INAZUMA ===
    "enka": "enkanomiya",
    "watatsumi": "watatsumi island",
    "narukami": "narukami island",
    "seirai": "seirai island",
    "yashiori": "yashiori island",
    "tsurumi": "tsurumi island",
    "narukami shrine": "grand narukami shrine (subarea)",
    "grand narukami shrine": "grand narukami shrine (subarea)",
    
    # === SUMERU ===
    "sumeru desert": "hypostyle desert",
    "hadramaveth": "desert of hadramaveth",
    "king deshret": "the mausoleum of king deshret",
    "mausoleum": "the mausoleum of king deshret",
    "pyramid": "the mausoleum of king deshret", # Sering disebut pyramid di komunitas
    "farakhkert": "realm of farakhkert",
    "oasis": "vourukasha oasis",
    "vanarana": "vanarana (subarea)",
    "old vanarana": "lost nursery",
    
    # === FONTAINE ===
    "fri": "fontaine research institute of kinetic energy engineering region",
    "research institute": "fontaine research institute of kinetic energy engineering region",
    "kinetic institute": "fontaine research institute of kinetic energy engineering region",
    "meropide": "fortress of meropide",
    "prison": "fortress of meropide", # Sering disebut prison/penjara
    "remuria": "sea of bygone eras", # Remuria adalah nama lore dari map ini
    "bygone eras": "sea of bygone eras",
    "court of fontaine": "court of fontaine region",
    
    # === NATLAN ===
    "stadium": "stadium of the sacred flame",
    "scions": "\"scions of the canopy\"",
    "canopy": "\"scions of the canopy\"",
    "echoes": "\"children of echoes\"",
    "springs": "\"people of the springs\"",
    "night wind": "\"masters of the night-wind\"",
    "flower feather": "\"flower-feather clan\"",
    "collective": "\"collective of plenty\"",
    "night kingdom": "night kingdom",
    
    # === NOD-KRAI ===
    "nod krai": "nod-krai",
    "nodkrai": "nod-krai",
    "kuuvahki": "kuuvahki experimental design bureau",
    "design bureau": "kuuvahki experimental design bureau",
    "research institute nod krai": "special territory research institute",
    "special territory": "special territory research institute"
}
_ABBREV_RE = re.compile(r"^[A-Z][a-z]{0,3}\.$")

def normalize_name(name: str) -> str:
    name = name.lower().strip()
    if name.startswith('"') and name.endswith('"'):
        name = name[1:-1]
    name = re.sub(r"\s*\([^)]*\)\s*$", "", name)
    name = name.strip("[]")
    name = re.sub(r'\b(mt|st|dr|ft)\.', r'\1', name)
    name = name.strip(".:,;!?")
    return name.strip()

def load_gazetteer(json_path: str) -> tuple[set[str], set[str]]:
    with open(json_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    names = flatten_gazetteer(data)
    for expansion in ALIAS_MAP.values():
        names.add(normalize_name(expansion))

    return names, build_token_set(names)

def flatten_gazetteer(data: dict) -> set[str]:
    names: set[str] = set()
    for region_name, region_data in data.items():
        names.add(normalize_name(region_name))
        if not isinstance(region_data, dict):
            continue
        for area_name, area_data in region_data.get("areas", {}).items():
            names.add(normalize_name(area_name))
            if isinstance(area_data, dict):
                for sub_area in area_data.get("sub_areas", []):
                    cleaned = normalize_name(sub_area)
                    if cleaned:
                        names.add(cleaned)
    names.discard("")
    return names

def build_token_set(names: set[str]) -> set[str]:
    tokens: set[str] = set()
    for name in names:
        for word in name.split():
            cleaned = word.strip(':.,;"\'()')
            if cleaned and len(cleaned) > 1:
                tokens.add(cleaned)
    return tokens

def ensure_pos_tagger() -> None:
    try:
        nltk.data.find("taggers/averaged_perceptron_tagger_eng")
    except LookupError:
        try:
            nltk.download("averaged_perceptron_tagger_eng", quiet=True)
        except Exception:
            nltk.download("averaged_perceptron_tagger", quiet=True)

def tokenize_locations(text: str) -> list[str]:
    for old, new in (("\u201c", '"'), ("\u201d", '"'), ("\u2018", "'"), ("\u2019", "'")):
        text = text.replace(old, new)

    tokens: list[str] = []
    for token in text.split():
        while len(token) > 1 and token[0] == '"' and token[-1] == '"':
            token = token[1:-1]
        token = token.strip('"')

        if token.startswith("(") and token.endswith(")"):
            continue
        token = re.sub(r"\([^)]*\)$", "", token)

        if not _ABBREV_RE.match(token):
            token = token.rstrip("?!,;.")

        if token:
            tokens.append(token)

    merged_tokens: list[str] = []
    idx = 0
    while idx < len(tokens):
        if idx + 1 < len(tokens) and tokens[idx] == "Mt." and tokens[idx + 1] and tokens[idx + 1][0].isalpha():
            merged_tokens.append(f"{tokens[idx]} {tokens[idx + 1]}")
            idx += 2
            continue
        merged_tokens.append(tokens[idx])
        idx += 1

    return merged_tokens

def get_pos_tags(tokens: list[str]) -> list[str]:
    ensure_pos_tagger()
    return [tag for _, tag in nltk.pos_tag(tokens)]


def normalize_token(token: str) -> str:
    return normalize_name(token).strip(':.,;!?"')

def build_sentence_lookup(tokens: list[str]) -> set[str]:
    cleaned = [normalize_token(token) for token in tokens if normalize_token(token)]
    phrases: set[str] = set()
    for start in range(len(cleaned)):
        current = []
        for end in range(start, min(len(cleaned), start + 5)):
            current.append(cleaned[end])
            phrases.add(" ".join(current))
    return phrases

def is_fuzzy_gazetteer_token(normalized: str, gazetteer_tokens: set[str]) -> bool:
    if len(normalized) < 4:
        return False
        
    import nltk
    max_ed = 2
    norm_len = len(normalized)
    
    for gaz_token in gazetteer_tokens:
        if abs(norm_len - len(gaz_token)) > max_ed:
            continue
        if nltk.edit_distance(normalized, gaz_token) <= max_ed:
            return True
    return False

def word2features(
    sentence: list[str],
    pos_tags: list[str],
    index: int,
    gazetteer_names: set[str],
    gazetteer_tokens: set[str],
    sentence_lookup: set[str],
) -> dict[str, object]:
    word = sentence[index]
    normalized = normalize_token(word)
    postag = pos_tags[index]

    in_token_set = normalized in gazetteer_tokens
    in_full_name = normalized in gazetteer_names
    in_sentence_gazetteer = any(
        phrase in gazetteer_names for phrase in sentence_lookup if normalized and normalized in phrase.split()
    )
    
    is_fuzzy = in_token_set or is_fuzzy_gazetteer_token(normalized, gazetteer_tokens)

    features = {
        "bias": 1.0,
        "word.prefix2": normalized[:2],
        "word.prefix3": normalized[:3],
        "word.suffix2": normalized[-2:],
        "word.suffix3": normalized[-3:],
        "postag": postag,
        "postag[:2]": postag[:2],
    }

    if word.isdigit():
        features["word.isdigit()"] = True
    if index == 0:
        features["is_sentence_start"] = True
    if index == len(sentence) - 1:
        features["is_sentence_end"] = True
    if normalized in LOCATION_CONNECTORS:
        features["is_location_connector"] = True
    if is_fuzzy or in_full_name:
        features["is_in_genshin_map"] = True
    if is_fuzzy:
        features["gazetteer_word_overlap"] = True
    if is_fuzzy or in_sentence_gazetteer:
        features["gazetteer_phrase_overlap"] = True

    if len(normalized) >= 4:
        for i in range(len(normalized) - 2):
            trigram = normalized[i:i+3]
            features[f"word.trigram:{trigram}"] = True

    if index > 0:
        prev_word = sentence[index - 1]
        prev_norm = normalize_token(prev_word)
        features.update({
            "-1:postag": pos_tags[index - 1],
            "-1:postag[:2]": pos_tags[index - 1][:2],
        })
        if prev_norm in LOCATION_CONNECTORS:
            features["-1:is_connector"] = True
        if prev_norm in gazetteer_tokens:
            features["-1:gazetteer_word_overlap"] = True
    else:
        features["BOS"] = True

    if index < len(sentence) - 1:
        next_word = sentence[index + 1]
        next_norm = normalize_token(next_word)
        features.update({
            "+1:postag": pos_tags[index + 1],
            "+1:postag[:2]": pos_tags[index + 1][:2],
        })
        if next_norm in LOCATION_CONNECTORS:
            features["+1:is_connector"] = True
        if next_norm in gazetteer_tokens:
            features["+1:gazetteer_word_overlap"] = True
    else:
        features["EOS"] = True

    return features

def sent2features(sentence: list[str], gazetteer_names: set[str], gazetteer_tokens: set[str]) -> list[dict[str, object]]:
    pos_tags = get_pos_tags(sentence)
    sentence_lookup = build_sentence_lookup(sentence)
    return [
        word2features(sentence, pos_tags, idx, gazetteer_names, gazetteer_tokens, sentence_lookup)
        for idx in range(len(sentence))
    ]

class LinearChainCRF:
    # l2_reg jadi sigma (bobot) untuk L2 Regularization
    def __init__(self, l2_reg=0.1, max_iter=200):
        self.l2_reg = l2_reg
        self.max_iter = max_iter
        self.feature_to_idx = {}
        self.label_to_idx = {}
        self.idx_to_label = {}
        self.weights = None
        self.num_labels = 0
        self.num_features = 0

    def _flatten_features(self, features_dict):
        flat = {}
        for k, v in features_dict.items():
            # Kalo string
            if isinstance(v, str):
                flat[f"{k}={v}"] = 1.0
            # Kalo boolean
            elif isinstance(v, bool):
                flat[f"{k}={str(v)}"] = 1.0
            # Kalo udh numerik gausah
            elif isinstance(v, (int, float)):
                flat[k] = float(v)
        return flat

    def _preprocess_X(self, X):
        processed_X = []
        for seq in X:
            processed_seq = []
            for features in seq:
                processed_seq.append(self._flatten_features(features))
            processed_X.append(processed_seq)
        return processed_X

    def _get_potentials(self, x, W_node, W_trans):
        # Menghitung probabilitas kondisional p(y|x) dari label y terhadap data masukan x
        # W_node bobot fitur node (lamda k)
        # Kalau W_trans buat bobot fitur edge (lambda k')
        N = len(x)
        node_score = np.zeros((N, self.num_labels))
        for t in range(N):
            for feat, val in x[t].items():
                if feat in self.feature_to_idx:
                    feat_idx = self.feature_to_idx[feat]
                    # Rumus Node: Sum k lambda k * fk (yt,x,t)
                    node_score[t, :] += W_node[feat_idx, :] * val
        
        # Di logsumexp biar pas di lakuin exponen nilainya ga gede
        node_shift = np.max(node_score, axis=1, keepdims=True)
        # Rumus Node Potential: phi t (yt, x) = exp (Sum k lamda k fk)
        node_potential = np.exp(node_score - node_shift)
        
        # Di logsumexp biar pas di lakuin exponen nilainya ga gede
        edge_shift = np.max(W_trans)
        # Rumus Edge Potential : psit(yt, yt+1, x) = exp(sum k' lambda k' fk'(yt, yt+1, x, t))
        # Diabaikan token masukan (x) dan waktu (t) biar hanya menghitung transisi antar label
        # Fitur fk' diasumsikan konstan (=1) untuk setiap pasangan label yang valid
        # Sehingga persamaannya disederhanakan murni menjadi: exp(lambda k')
        edge_potential = np.exp(W_trans - edge_shift)
        
        return node_potential, edge_potential, node_shift.flatten(), edge_shift

    def _forward_backward(self, node_potential, edge_potential):
        N = node_potential.shape[0]
        Y = self.num_labels
        
        alpha = np.zeros((N, Y))
        k = np.zeros(N) # Array untuk menyimpan Scaling Factor (kt)
        
        # Inisialisasi nilai forward pass pada urutan pertama (t=1)
        # alpha 1 [y1] = phi 1 (y1,x)
        alpha[0] = node_potential[0]
        k[0] = np.sum(alpha[0])
        # normalisasi untuk t=1
        alpha[0] /= k[0] if k[0] != 0 else 1e-100

        
        for t in range(1, N):
            # Menghitung nilai forward pass pada urutan ke-t (t >= 2) dengan scaling factor kt
            # Rumus: alpha t[yt] = kt * sum yt-1 alpha t-1 [yt-1] * phi t(yt, x) * psi t-1 (yt-1, yt, x))
            alpha[t] = np.dot(alpha[t-1], edge_potential) * node_potential[t]
            k_t = np.sum(alpha[t])
            # Menerapkan pembagian dengan scaling factor kt
            alpha[t] /= k_t if k_t != 0 else 1e-100
            k[t] = k_t
            
        beta = np.zeros((N, Y))
        mu = np.zeros(N) # Array untuk menyimpan scaling factor mu t
        
        # Inisialisasi nilai backward pass pada urutan terakhir (t=T)
        # Rumus: betaT[yT] = 1 / S (Di sini disederhanakan menjadi 1.0 sebelum scaling)
        beta[N-1] = 1.0
        mu_t = np.sum(beta[N-1])
        # Normalisasi untuk t=T
        beta[N-1] /= mu_t if mu_t != 0 else 1e-100
        mu[N-1] = mu_t
        
        for t in range(N-2, -1, -1):
            # Menghitung nilai backward pass pada urutan ke-t (t<T) dengan scaling factor mut
            # Rumus: betat[yt] = mut * sum yt+1 (beta t+1 [yt+1] * phi t+1(yt+1, x) * psit(yt, yt+1, x))
            beta[t] = np.dot(edge_potential, beta[t+1] * node_potential[t+1])
            mu_t = np.sum(beta[t])
            # Menerapkan pembagian dengan scaling factor mut
            beta[t] /= mu_t if mu_t != 0 else 1e-100
            mu[t] = mu_t
            
        # Menghitung fungsi normalisasi Z(x) dari distribusi probabilitas kondisional
        # Rumus log Z(x) dihitung dengan mengakumulasikan nilai log dari seluruh scaling factor
        Z_x = np.sum(np.log(k))
        
        return alpha, beta, k, mu, Z_x

    def _marginal_probabilities(self, alpha, beta, node_potential, edge_potential):
        N = alpha.shape[0]
        Y = self.num_labels
        
        node_marginals = np.zeros((N, Y))
        edge_marginals = np.zeros((N-1, Y, Y))
        
        for t in range(N):
            # Menghitung probabilitas node yakni peluang kemunculan label kelas kata yt
            # Rumus: P(yt|x) = (alpha t[yt] * beta t[yt]) / Z(x)
            # Pembagian Z(x) ditangani oleh sum_node karena alpha dan beta sudah di-scale
            node_marginals[t] = alpha[t] * beta[t]
            sum_node = np.sum(node_marginals[t])
            if sum_node > 0: node_marginals[t] /= sum_node
            
        for t in range(N - 1):
            # Menghitung probabilitas edge yakni peluang transisi dari label yt ke yt+1.
            # Rumus: P(yt, yt+1|x) = (alpha t * psi * phi t+1 * beta t+1) / Z(x)
            edge_marg = np.outer(alpha[t], beta[t+1] * node_potential[t+1]) * edge_potential
            sum_edge = np.sum(edge_marg)
            if sum_edge > 0: edge_marg /= sum_edge
            edge_marginals[t] = edge_marg
            
        return node_marginals, edge_marginals

    def gradient(self, weights, proc_X, y_idx):
        # Ekstrak matriks bobot lambda k dan lambda k'
        W_node = weights[:self.num_features * self.num_labels].reshape((self.num_features, self.num_labels))
        W_trans = weights[self.num_features * self.num_labels:].reshape((self.num_labels, self.num_labels))
        
        # Inisialisasi matriks gradien Gk dan G k'
        grad_node = np.zeros_like(W_node)
        grad_trans = np.zeros_like(W_trans)
        
        # Inisialisasi nilai Log-Likelihood
        log_likelihood = 0.0
        
        for i in range(len(proc_X)):
            x_seq = proc_X[i]
            y_seq = y_idx[i]
            N = len(x_seq)
            
            node_potential, edge_potential, node_shift, edge_shift = self._get_potentials(x_seq, W_node, W_trans)
            alpha, beta, k, mu, Z_x_scaled = self._forward_backward(node_potential, edge_potential)
            # Mengembalikan fungsi normalisasi Z(x) ke skala asli dari logsumexp 
            Z_x = Z_x_scaled + np.sum(node_shift) + (N - 1) * edge_shift
            node_marginals, edge_marginals = self._marginal_probabilities(alpha, beta, node_potential, edge_potential)
        
            # Rumus Empiris: sum t=1^T sum k lambda k fk(yt-1, yt, x, t)
            seq_score = 0.0
            for t in range(N):
                y_t = y_seq[t]
                for feat, val in x_seq[t].items():
                    if feat in self.feature_to_idx:
                        feat_id = self.feature_to_idx[feat]
                        seq_score += W_node[feat_id, y_t] * val
                        # Nilai observasi empiris untuk gradien Node
                        grad_node[feat_id, y_t] -= val
                        
                if t > 0:
                    y_prev = y_seq[t-1]
                    seq_score += W_trans[y_prev, y_t]
                    # Nilai observasi empiris untuk gradien Edge
                    grad_trans[y_prev, y_t] -= 1.0
            
            for t in range(N):
                # Menghitung nilai gradien ke-k untuk fungsi fitur node (Gkx).
                for feat, val in x_seq[t].items():
                    if feat in self.feature_to_idx:
                        feat_id = self.feature_to_idx[feat]
                        grad_node[feat_id, :] += node_marginals[t, :] * val
                        
            for t in range(N - 1):
                # Menghitung nilai gradien ke-k' untuk fungsi fitur edge (Gk'x).
                grad_trans += edge_marginals[t]

            # Rumus Log-Likelihood: Skor Empiris - Normalisasi Z(x)
            log_likelihood += seq_score - Z_x
 
        sigma = self.l2_reg
        # Penalti untuk mencegah overfitting sigma / 2 * sigma lambda^2
        reg_loss = (sigma / 2.0) * np.sum(weights ** 2)
        
        # Menerapkan penalti regularisasi L2 pada gradien: Gk + sigma lambda k
        grad_node += sigma * W_node
        grad_trans += sigma * W_trans
        
        # Mengubah Log-Likelihood menjadi Negative Log-Likelihood (karena L-BFGS-B mencari nilai minimum)
        total_loss = -log_likelihood + reg_loss
        total_grad = np.concatenate([grad_node.flatten(), grad_trans.flatten()])
        
        
        self.iter_count += 1
        if self.iter_count % 10 == 0:
            print(f"Iterasi ke-{self.iter_count} | NLL (Loss): {total_loss:.4f}")
        
        return total_loss, total_grad

    def _viterbi_decoding(self, node_potential, edge_potential):
        N = node_potential.shape[0]
        Y = self.num_labels
        
        # V menyimpan viterbi forward pass (alpha t^max)
        V = np.zeros((N, Y))
        # Menyimpan jejak index buat backtracking
        ptr = np.zeros((N, Y), dtype=int)
        
        log_node = np.log(np.clip(node_potential, 1e-100, None))
        log_edge = np.log(np.clip(edge_potential, 1e-100, None))
        
        # Inisialisasi nilai Viterbi forward pass pada urutan pertama (t=1)
        # Rumus: alpha1^max[y_1] = log(phi 1(y1))
        V[0] = log_node[0]
        
        for t in range(1, N):
            # Menghitung nilai Viterbi forward pass maksimum pada urutan t >= 2 hingga T
            # Rumus: alphat^max [yt] = max yt-1 (alpha t-1^max[yt-1] + log psi + log phit)
            for y in range(Y):
                seq_probs = V[t-1] + log_edge[:, y] + log_node[t, y]
                V[t, y] = np.max(seq_probs) # Mencari probabilitas terbesar
                ptr[t, y] = np.argmax(seq_probs) # Menyimpan jalur asal dari probabilitas terbesar
                
        y_t_star = np.zeros(N, dtype=int)
        
        # Melakukan Viterbi backtracking untuk menentukan label akhir yang paling optimal (yt^*)
        # Rumus: yt^* = argmaxyt (alphat^max[y_t])
        y_t_star[N-1] = np.argmax(V[N-1])
        for t in range(N-2, -1, -1):
            y_t_star[t] = ptr[t+1, y_t_star[t+1]]
            
        return y_t_star

    def fit(self, X, y):
        self.iter_count = 0
        self.feature_to_idx = {}
        self.label_to_idx = {}
        
        for seq_y in y:
            for label in seq_y:
                if label not in self.label_to_idx:
                    self.label_to_idx[label] = len(self.label_to_idx)
                    
        proc_X = self._preprocess_X(X)
        for seq_x in proc_X:
            for features in seq_x:
                for feat in features.keys():
                    if feat not in self.feature_to_idx:
                        self.feature_to_idx[feat] = len(self.feature_to_idx)
                        
        self.idx_to_label = {v: k for k, v in self.label_to_idx.items()}
        self.num_labels = len(self.label_to_idx)
        self.num_features = len(self.feature_to_idx)
        
        y_idx = [[self.label_to_idx[label] for label in seq] for seq in y]
        
        initial_weights = np.zeros(self.num_features * self.num_labels + self.num_labels * self.num_labels)
        
        res = minimize(
            fun=self.gradient,
            x0=initial_weights,
            args=(proc_X, y_idx),
            method='L-BFGS-B',
            jac=True,
            options={'maxiter': self.max_iter, 'disp': True}
        )
        self.weights = res.x
        return self
        
    def predict(self, X):
        if self.weights is None:
            raise ValueError("Model has not been trained yet.")
        
        W_node = self.weights[:self.num_features * self.num_labels].reshape((self.num_features, self.num_labels))
        W_trans = self.weights[self.num_features * self.num_labels:].reshape((self.num_labels, self.num_labels))
        
        proc_X = self._preprocess_X(X)
        y_pred = []
        for x_seq in proc_X:
            node_potential, edge_potential, _, _ = self._get_potentials(x_seq, W_node, W_trans)
            y_t_star = self._viterbi_decoding(node_potential, edge_potential)
            y_pred.append([self.idx_to_label[idx] for idx in y_t_star])
        return y_pred


_SPAN_LEADING_NOISE: set[str] = {
    "reach", "enter", "access", "go", "get", "find", "unlock", "open",
    "explore", "travel", "visit", "see", "do", "make", "take", "heading",
    "near", "in", "at", "by", "from", "toward", "towards", "inside",
    "outside", "around", "through", "across", "into", "onto", "upon",
    "beside", "behind", "beyond", "between", "beneath", "under", "over",
}


def _strip_leading_noise(span: str) -> str:
    tokens = span.split()
    while tokens and tokens[0].lower() in _SPAN_LEADING_NOISE:
        tokens = tokens[1:]
    return " ".join(tokens).strip()


def extract_crf_spans(tokens: list[str], predicted_tags: list[str]) -> list[str]:
    spans = []
    current_span = []
    for token, tag in zip(tokens, predicted_tags):
        if tag == "B-LOC":
            if current_span:
                spans.append(" ".join(current_span))
            current_span = [token]
        elif tag == "I-LOC":
            if current_span:
                current_span.append(token)
            else:
                current_span = [token]
        else:
            if current_span:
                spans.append(" ".join(current_span))
                current_span = []

    if current_span:
        spans.append(" ".join(current_span))

    deduplicated_spans = []
    for span in spans:
        span = _strip_leading_noise(span)
        normalized_span = normalize_name(span)
        if normalized_span and normalized_span not in deduplicated_spans:
            deduplicated_spans.append(normalized_span)

    return deduplicated_spans


def extract_exact_gazetteer_mentions(tokens: list[str], gazetteer_names: set[str], max_window: int = 8) -> list[str]:
    normalized_tokens = [normalize_name(token) for token in tokens]
    exact_mentions = []
    index = 0

    while index < len(normalized_tokens):
        best_match = None
        best_end = index
        upper_bound = min(len(normalized_tokens), index + max_window)

        for end in range(upper_bound, index, -1):
            candidate_tokens = [token for token in normalized_tokens[index:end] if token]
            candidate = " ".join(candidate_tokens)
            if candidate in gazetteer_names:
                best_match = candidate
                best_end = end
                break

        if best_match is not None:
            if best_match not in exact_mentions:
                exact_mentions.append(best_match)
            index = best_end
        else:
            index += 1

    return exact_mentions

MIN_FUZZY_TOKEN_LENGTH = 4

def edit_distance(left: str, right: str) -> int:
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)
    previous_row = list(range(len(right) + 1))
    for left_index, left_char in enumerate(left, start=1):
        current_row = [left_index]
        for right_index, right_char in enumerate(right, start=1):
            insert_cost = current_row[right_index - 1] + 1
            delete_cost = previous_row[right_index] + 1
            replace_cost = previous_row[right_index - 1] + (left_char != right_char)
            current_row.append(min(insert_cost, delete_cost, replace_cost))
        previous_row = current_row
    return previous_row[-1]

def get_max_edit_distance(token: str) -> int:
    if len(token) <= 3:
        return 1
    if len(token) <= 9:
        return 2
    return 2

def get_common_prefix_length(left: str, right: str) -> int:
    shared = 0 
    for left_char, right_char in zip(left, right):
        if left_char != right_char:
            break
        shared += 1
    return shared

def find_best_token_correction(token: str, vocabulary: set[str]) -> dict[str, object] | None:
    normalized_token = normalize_token(token)
    if len(normalized_token) < MIN_FUZZY_TOKEN_LENGTH:
        return None
    best_match = None
    best_distance = None
    best_prefix = -1
    for candidate in vocabulary:
        if abs(len(candidate) - len(normalized_token)) > get_max_edit_distance(normalized_token):
            continue
        distance = edit_distance(normalized_token, candidate)
        if distance > get_max_edit_distance(normalized_token):
            continue
        prefix = get_common_prefix_length(normalized_token, candidate)
        if (
            best_match is None
            or distance < best_distance
            or (distance == best_distance and prefix > best_prefix)
            or (distance == best_distance and prefix == best_prefix and len(candidate) < len(best_match))
        ):
            best_match = candidate
            best_distance = distance
            best_prefix = prefix
    if best_match is None or best_match == normalized_token:
        return None
    return {
        "original": normalized_token,
        "corrected": best_match,
        "distance": best_distance,
        "reason": f"Corrected '{normalized_token}' -> '{best_match}' (edit distance {best_distance}).",
    }

def apply_fuzzy_token_corrections(raw_span: str, gazetteer_tokens: set[str]) -> tuple[str, list[dict[str, object]]]:
    normalized = normalize_name(raw_span)
    span_tokens = [normalize_token(t) for t in normalized.split() if normalize_token(t)]
    corrected_tokens = []
    corrections = []
    for token in span_tokens:
        correction = find_best_token_correction(token, gazetteer_tokens)
        if correction is not None:
            corrected_tokens.append(correction["corrected"])
            corrections.append(correction)
        else:
            corrected_tokens.append(token)
    corrected_span = " ".join(corrected_tokens)
    return corrected_span, corrections

import re as _re

def _expand_abbreviations(span: str) -> str:
    return _re.sub(r'\b(mt|st|dr|ft)\b(?!\.)', r'\1.', span)


def resolve_span_to_canonical(raw_span: str, gazetteer_names: set[str], gazetteer_tokens: set[str]) -> dict[str, object]:
    normalized_span = normalize_name(raw_span)

    core_span = _strip_leading_noise(normalized_span)
    if not core_span:
        core_span = normalized_span

    core_tokens = core_span.split()
    for length in range(len(core_tokens), 0, -1):
        candidate = " ".join(core_tokens[:length])
        expanded = _expand_abbreviations(candidate)
        for c in ([expanded, candidate] if expanded != candidate else [candidate]):
            # 1. Exact match
            if c in gazetteer_names:
                return {
                    "raw_span": normalized_span,
                    "resolved_name": c,
                    "method": "exact",
                    "fuzzy_corrections": [],
                }
            # 2. Alias match
            if c in ALIAS_MAP:
                return {
                    "raw_span": normalized_span,
                    "resolved_name": normalize_name(ALIAS_MAP[c]),
                    "method": "alias",
                    "fuzzy_corrections": [],
                }

    corrected_span, fuzzy_corrections = apply_fuzzy_token_corrections(core_span, gazetteer_tokens)
    if corrected_span and corrected_span != core_span and fuzzy_corrections:
        corrected_expanded = _expand_abbreviations(corrected_span)
        for c in ([corrected_expanded, corrected_span] if corrected_expanded != corrected_span else [corrected_span]):
            if c in gazetteer_names:
                return {
                    "raw_span": normalized_span,
                    "resolved_name": c,
                    "method": "fuzzy",
                    "fuzzy_corrections": fuzzy_corrections,
                }
            if c in ALIAS_MAP:
                return {
                    "raw_span": normalized_span,
                    "resolved_name": normalize_name(ALIAS_MAP[c]),
                    "method": "fuzzy",
                    "fuzzy_corrections": fuzzy_corrections,
                }

    return {
        "raw_span": normalized_span,
        "resolved_name": core_span,
        "method": "raw",
        "fuzzy_corrections": [],
    }

def resolve_query_locations(raw_text: str, model: LinearChainCRF, gazetteer_names: set[str], gazetteer_tokens: set[str]) -> dict[str, object]:
    tokens = tokenize_locations(raw_text)
    if not tokens:
        return {
            "query": raw_text,
            "tokens": [],
            "crf_tags": [],
            "crf_spans": [],
            "exact_matches": [],
            "alias_matches": [],
            "entities": [],
            "resolved_names": [],
        }

    features = sent2features(tokens, gazetteer_names, gazetteer_tokens)
    predicted_tags = model.predict([features])[0]
    crf_tags = list(zip(tokens, predicted_tags))

    crf_spans = extract_crf_spans(tokens, predicted_tags)
    exact_matches = extract_exact_gazetteer_mentions(tokens, gazetteer_names)

    normalized_tokens = [normalize_name(t) for t in tokens]
    all_alias_candidates: list[str] = []
    for start in range(len(normalized_tokens)):
        current_tokens = []
        for end in range(start, min(len(normalized_tokens), start + 4)):
            token = normalized_tokens[end]
            if not token:
                continue
            current_tokens.append(token)
            candidate = " ".join(current_tokens)
            if candidate in ALIAS_MAP:
                alias_resolved = normalize_name(ALIAS_MAP[candidate])
                if candidate not in gazetteer_names or alias_resolved == candidate:
                    if candidate not in all_alias_candidates:
                        all_alias_candidates.append(candidate)

    alias_matches = [
        c for c in all_alias_candidates
        if not any(longer != c and longer.startswith(c + " ") for longer in all_alias_candidates)
    ]

    candidate_entities: list[dict] = []

    for match_name in exact_matches:
        candidate_entities.append({
            "raw_span": match_name,
            "resolved_name": match_name,
            "method": "exact",
            "fuzzy_corrections": [],
        })

    for alias_span in alias_matches:
        resolved_name = normalize_name(ALIAS_MAP[alias_span])
        candidate_entities.append({
            "raw_span": alias_span,
            "resolved_name": resolved_name,
            "method": "alias",
            "fuzzy_corrections": [],
        })

    for span in crf_spans:
        normalized_span = normalize_name(span)
        if not normalized_span:
            continue
        entity = resolve_span_to_canonical(normalized_span, gazetteer_names, gazetteer_tokens)
        candidate_entities.append(entity)

    candidate_entities.sort(key=lambda e: len(e["resolved_name"]), reverse=True)

    entities: list[dict] = []
    seen_resolved: set[str] = set()
    seen_tokens: set[str] = set()   

    for entity in candidate_entities:
        rname = entity["resolved_name"]
        if rname in seen_resolved:
            continue
        rname_tokens = set(rname.split())
        if rname_tokens and rname_tokens <= seen_tokens:
            continue
        entities.append(entity)
        seen_resolved.add(rname)
        seen_tokens.update(rname_tokens)

    def _span_position(entity: dict) -> int:
        span_toks = entity["raw_span"].split()
        n = len(span_toks)
        for idx in range(len(normalized_tokens) - n + 1):
            if normalized_tokens[idx:idx + n] == span_toks:
                return idx
        span_toks = entity["resolved_name"].split()
        n = len(span_toks)
        for idx in range(len(normalized_tokens) - n + 1):
            if normalized_tokens[idx:idx + n] == span_toks:
                return idx
        return len(normalized_tokens)

    entities.sort(key=_span_position)

    resolved_names = [e["resolved_name"] for e in entities]

    return {
        "query": raw_text,
        "tokens": tokens,
        "crf_tags": crf_tags,
        "crf_spans": crf_spans,
        "exact_matches": exact_matches,
        "alias_matches": alias_matches,
        "entities": entities,
        "resolved_names": resolved_names,
    }


def extract_locations(raw_text: str, model: LinearChainCRF, gazetteer_names: set[str], gazetteer_tokens: set[str]) -> list[str]:
    return resolve_query_locations(raw_text, model, gazetteer_names, gazetteer_tokens)["resolved_names"]


# Load model and gazetteer paths
BASE_DIR = Path('../').resolve()
GAZETTEER_PATH = BASE_DIR / 'genshin_areas.json'
MODEL_PATH = BASE_DIR / 'outputs' / 'genshin_location_crf.pkl'

print(f"Loading Gazetteer from {GAZETTEER_PATH}")
gazetteer_names, gazetteer_tokens = load_gazetteer(str(GAZETTEER_PATH))

print(f"Loading Model from {MODEL_PATH}")
import __main__
__main__.LinearChainCRF = LinearChainCRF
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
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port)
