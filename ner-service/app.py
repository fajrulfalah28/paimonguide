from flask import Flask, request, jsonify
import json
import pickle
import re
import random
import nltk
from pathlib import Path
import os

app = Flask(__name__)

# Try to download NLTK data on startup
try:
    nltk.data.find('taggers/averaged_perceptron_tagger_eng')
except LookupError:
    try:
        nltk.download('averaged_perceptron_tagger_eng', quiet=True)
    except Exception:
        nltk.download('averaged_perceptron_tagger', quiet=True)

LABELS = ['O', 'B-LOC', 'I-LOC']

LOCATION_CONNECTORS = {'of', 'de', 'al', 'al-', 'the'}

ALIAS_MAP = {'mondo': 'mondstadt', 'mond': 'mondstadt', 'mondstat': 'mondstadt', 'dragon spine': 'dragonspine', 'stormterror': "stormterror's lair", 'dvalin lair': "stormterror's lair", "dvalin's lair": "stormterror's lair", 'chasm': 'the chasm', 'chasm underground': 'the chasm: underground mines', 'underground mines': 'the chasm: underground mines', 'chasm maw': "the chasm's maw", 'liyue city': 'liyue harbor', 'chenyu': 'chenyu vale: upper vale', 'enka': 'enkanomiya', 'watatsumi': 'watatsumi island', 'narukami': 'narukami island', 'seirai': 'seirai island', 'yashiori': 'yashiori island', 'tsurumi': 'tsurumi island', 'narukami shrine': 'grand narukami shrine (subarea)', 'grand narukami shrine': 'grand narukami shrine (subarea)', 'sumeru desert': 'hypostyle desert', 'hadramaveth': 'desert of hadramaveth', 'king deshret': 'the mausoleum of king deshret', 'mausoleum': 'the mausoleum of king deshret', 'pyramid': 'the mausoleum of king deshret', 'farakhkert': 'realm of farakhkert', 'oasis': 'vourukasha oasis', 'vanarana': 'vanarana (subarea)', 'old vanarana': 'lost nursery', 'fri': 'fontaine research institute of kinetic energy engineering region', 'research institute': 'fontaine research institute of kinetic energy engineering region', 'kinetic institute': 'fontaine research institute of kinetic energy engineering region', 'meropide': 'fortress of meropide', 'prison': 'fortress of meropide', 'remuria': 'sea of bygone eras', 'bygone eras': 'sea of bygone eras', 'court of fontaine': 'court of fontaine region', 'stadium': 'stadium of the sacred flame', 'scions': '"scions of the canopy"', 'canopy': '"scions of the canopy"', 'echoes': '"children of echoes"', 'springs': '"people of the springs"', 'night wind': '"masters of the night-wind"', 'flower feather': '"flower-feather clan"', 'collective': '"collective of plenty"', 'night kingdom': 'night kingdom', 'nod krai': 'nod-krai', 'nodkrai': 'nod-krai', 'kuuvahki': 'kuuvahki experimental design bureau', 'design bureau': 'kuuvahki experimental design bureau', 'research institute nod krai': 'special territory research institute', 'special territory': 'special territory research institute'}

_ABBREV_RE = re.compile('^[A-Z][a-z]{0,3}\\.$')

def normalize_name(name: str) -> str:
    name = name.lower().strip()
    if name.startswith('"') and name.endswith('"'):
        name = name[1:-1]
    name = re.sub(r"\s*\([^)]*\)\s*$", "", name)
    return name.strip()

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

def load_gazetteer(json_path: str) -> tuple[set[str], set[str]]:
    with open(json_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    names = flatten_gazetteer(data)
    for expansion in ALIAS_MAP.values():
        names.add(normalize_name(expansion))

    return names, build_token_set(names)

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

def ensure_pos_tagger() -> None:
    try:
        nltk.data.find("taggers/averaged_perceptron_tagger_eng")
    except LookupError:
        try:
            nltk.download("averaged_perceptron_tagger_eng", quiet=True)
        except Exception:
            nltk.download("averaged_perceptron_tagger", quiet=True)

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
        "word.isdigit()": word.isdigit(),
        "word.prefix2": normalized[:2],
        "word.prefix3": normalized[:3],
        "word.suffix2": normalized[-2:],
        "word.suffix3": normalized[-3:],
        "postag": postag,
        "postag[:2]": postag[:2],
        "is_sentence_start": index == 0,
        "is_sentence_end": index == len(sentence) - 1,
        "is_location_connector": normalized in LOCATION_CONNECTORS,
        "is_in_genshin_map": is_fuzzy or in_full_name,
        "gazetteer_word_overlap": is_fuzzy,
        "gazetteer_phrase_overlap": in_sentence_gazetteer or is_fuzzy,
    }

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
            "-1:is_connector": prev_norm in LOCATION_CONNECTORS,
            "-1:gazetteer_word_overlap": prev_norm in gazetteer_tokens or is_fuzzy_gazetteer_token(prev_norm, gazetteer_tokens)
        })
    else:
        features["BOS"] = True

    if index < len(sentence) - 1:
        next_word = sentence[index + 1]
        next_norm = normalize_token(next_word)
        features.update({
            "+1:postag": pos_tags[index + 1],
            "+1:postag[:2]": pos_tags[index + 1][:2],
            "+1:is_connector": next_norm in LOCATION_CONNECTORS,
            "+1:gazetteer_word_overlap": next_norm in gazetteer_tokens or is_fuzzy_gazetteer_token(next_norm, gazetteer_tokens)
        })
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

RESOLVER_STOPWORDS = {'the', 'in', 'of', 'to', 'and', 'a', 'an', 'on', 'at', 'for', 'near', 'through'}

NON_LOCATION_QUERY_WORDS = {'about', 'access', 'also', 'boat', 'bro', 'can', 'cant', "can't", 'carry', 'difference', 'do', 'does', "doesn't", "don't", 'done', 'enter', 'explore', 'exploring', 'fast', 'find', 'fly', 'get', 'go', 'goes', 'going', 'guide', 'hard', 'harder', 'hate', 'help', 'how', 'inside', 'is', "isn't", 'it', "it's", 'journey', 'just', 'know', 'make', 'man', 'need', 'pls', 'please', 'quest', 'reach', 'route', 'run', 'someone', 'take', 'teleport', 'tf', 'than', 'that', 'there', 'tp', 'travel', 'traveling', 'trip', 'unlock', 'visit', 'visiting', 'walk', 'want', 'way', 'went', 'what', 'where', "won't"}

GENERIC_GAZETTEER_TOKENS = {'bay', 'camp', 'camps', 'canyon', 'cave', 'city', 'cliff', 'coast', 'east', 'falls', 'forest', 'gate', 'hill', 'hills', 'inn', 'island', 'lake', 'mountain', 'mountains', 'mount', 'north', 'peak', 'plain', 'plains', 'port', 'river', 'ruins', 'site', 'south', 'strait', 'valley', 'village', 'west', 'sea', 'shrine', 'shrines', 'harbor', 'mine', 'mines', 'gorge', 'domain', 'realm', 'desert', 'institute', 'prison', 'fortress'}

OVERLAP_MIN_SCORE = 0.5

FUZZY_OVERLAP_MIN_SCORE = 0.45

RAW_RESOLVED_NAME_FLOOR = 0.5

AMBIGUITY_MARGIN = 0.1

MAX_RESOLVER_CANDIDATES = 5

ALIAS_CONFIDENCE = 0.98

FUZZY_CONFIDENCE_PENALTY = 0.08

MIN_FUZZY_TOKEN_LENGTH = 4

def tokenise_for_overlap(text: str) -> list[str]:
    normalized_text = normalize_name(text)
    rough_tokens = re.split(r"[\s:\-]+", normalized_text)
    cleaned_tokens = []
    for token in rough_tokens:
        cleaned = normalize_token(token)
        if cleaned and cleaned not in RESOLVER_STOPWORDS and cleaned not in NON_LOCATION_QUERY_WORDS:
            cleaned_tokens.append(cleaned)
    return cleaned_tokens

def explain_candidate_reason(overlap_count: int, overlap_ratio: float, overlap_tokens: list[str], method: str) -> str:
    if method == "alias":
        return "Matched curated alias entry."
    if method == "exact":
        return "Matched exact canonical gazetteer phrase."
    if overlap_count == 0:
        return "No meaningful token overlap."
    return f"Matched {overlap_count} token(s): {overlap_tokens} with overlap ratio {overlap_ratio:.3f}."

def score_overlap_candidate(raw_span: str, candidate_name: str) -> dict[str, object]:
    raw_tokens = set(tokenise_for_overlap(raw_span))
    candidate_tokens = set(tokenise_for_overlap(candidate_name))
    overlap_tokens = sorted(raw_tokens & candidate_tokens)
    overlap_count = len(overlap_tokens)
    overlap_ratio = overlap_count / len(raw_tokens) if raw_tokens else 0.0

    return {
        "name": candidate_name,
        "score": round(overlap_ratio, 3),
        "overlap_count": overlap_count,
        "overlap_ratio": round(overlap_ratio, 3),
        "overlap_tokens": overlap_tokens,
        "candidate_token_count": len(candidate_tokens),
        "reason": explain_candidate_reason(overlap_count, overlap_ratio, overlap_tokens, "overlap"),
    }

def rank_overlap_candidates(raw_span: str, gazetteer_names: set[str], max_candidates: int = MAX_RESOLVER_CANDIDATES) -> list[dict[str, object]]:
    scored_candidates = []
    for candidate_name in gazetteer_names:
        candidate_score = score_overlap_candidate(raw_span, candidate_name)
        if candidate_score["overlap_count"] > 0:
            scored_candidates.append(candidate_score)

    scored_candidates.sort(
        key=lambda item: (
            item["overlap_count"],
            item["overlap_ratio"],
            -item["candidate_token_count"],
            -len(item["name"]),
        ),
        reverse=True,
    )
    return scored_candidates[:max_candidates]

def build_exact_entity(match_name: str) -> dict[str, object]:
    return {
        "raw_span": match_name,
        "resolved_name": match_name,
        "method": "exact",
        "confidence": 1.0,
        "ambiguous": False,
        "candidates": [{"name": match_name, "score": 1.0, "reason": explain_candidate_reason(0, 1.0, [], "exact")}],
        "fuzzy_corrections": [],
    }

def build_alias_entity(raw_span: str, resolved_name: str) -> dict[str, object]:
    return {
        "raw_span": raw_span,
        "resolved_name": resolved_name,
        "method": "alias",
        "confidence": ALIAS_CONFIDENCE,
        "ambiguous": False,
        "candidates": [{"name": resolved_name, "score": ALIAS_CONFIDENCE, "reason": explain_candidate_reason(0, ALIAS_CONFIDENCE, [], "alias")}],
        "fuzzy_corrections": [],
    }

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

_FUZZY_CACHE = {}

_FUZZY_CACHE = {}

def find_best_token_correction(token: str, vocabulary: set[str]) -> dict[str, object] | None:
    normalized_token = normalize_token(token)
    if len(normalized_token) < MIN_FUZZY_TOKEN_LENGTH or normalized_token in RESOLVER_STOPWORDS:
        return None
    if normalized_token in _FUZZY_CACHE:
        return _FUZZY_CACHE[normalized_token]
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
    _FUZZY_CACHE[normalized_token] = {
        "original": normalized_token,
        "corrected": best_match,
        "distance": best_distance,
        "reason": f"Corrected '{normalized_token}' -> '{best_match}' (edit distance {best_distance}).",
    }
    return _FUZZY_CACHE[normalized_token]

def apply_fuzzy_token_corrections(raw_span: str, gazetteer_tokens: set[str]) -> tuple[str, list[dict[str, object]]]:
    span_tokens = tokenise_for_overlap(raw_span)
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

def generate_alias_ngrams(tokens: list[str], max_n: int=4) -> list[str]:
    normalized_tokens = [normalize_name(token) for token in tokens]
    alias_ngrams = []
    for start in range(len(normalized_tokens)):
        current_tokens = []
        for end in range(start, min(len(normalized_tokens), start + max_n)):
            token = normalized_tokens[end]
            if not token:
                continue
            current_tokens.append(token)
            candidate = ' '.join(current_tokens)
            if candidate and candidate not in alias_ngrams:
                alias_ngrams.append(candidate)
    return alias_ngrams

def detect_alias_matches(tokens: list[str], gazetteer_names: set[str]) -> list[dict[str, object]]:
    all_candidates: list[str] = []
    for alias_candidate in generate_alias_ngrams(tokens):
        if alias_candidate not in ALIAS_MAP:
            continue
        alias_resolved_name = normalize_name(ALIAS_MAP[alias_candidate])
        if alias_candidate in gazetteer_names and alias_resolved_name != alias_candidate:
            continue
        all_candidates.append(alias_candidate)

    filtered_candidates = [
        c for c in all_candidates
        if not any(longer != c and longer.startswith(c + ' ') for longer in all_candidates)
    ]

    alias_entities = []
    for alias_candidate in filtered_candidates:
        alias_resolved_name = normalize_name(ALIAS_MAP[alias_candidate])
        alias_entity = build_alias_entity(alias_candidate, alias_resolved_name)
        overlap_candidates = rank_overlap_candidates(alias_candidate, gazetteer_names)
        if len(tokenise_for_overlap(alias_candidate)) == 1 and len(overlap_candidates) > 1 and (abs(overlap_candidates[0]['score'] - overlap_candidates[1]['score']) <= AMBIGUITY_MARGIN):
            alias_entity['ambiguous'] = True
            alias_entity['candidates'] = overlap_candidates
        alias_entities.append(alias_entity)
    return alias_entities


def build_overlap_entity(raw_span: str, overlap_candidates: list[dict[str, object]], method: str, confidence: float, ambiguous: bool, fuzzy_corrections: list[dict[str, object]] | None = None) -> dict[str, object]:
    return {
        "raw_span": normalize_name(raw_span),
        "resolved_name": overlap_candidates[0]["name"],
        "method": method,
        "confidence": round(confidence, 3),
        "ambiguous": ambiguous,
        "candidates": overlap_candidates,
        "fuzzy_corrections": fuzzy_corrections or [],
    }

def resolve_span_to_canonical(raw_span: str, gazetteer_names: set[str], gazetteer_tokens: set[str]) -> dict[str, object]:
    normalized_span = normalize_name(raw_span)

    # 1. Exact match
    if normalized_span in gazetteer_names:
        return build_exact_entity(normalized_span)

    # 2. Alias match
    if normalized_span in ALIAS_MAP:
        alias_entity = build_alias_entity(normalized_span, normalize_name(ALIAS_MAP[normalized_span]))
        overlap_candidates = rank_overlap_candidates(normalized_span, gazetteer_names)
        if (
            len(tokenise_for_overlap(normalized_span)) == 1
            and len(overlap_candidates) > 1
            and abs(overlap_candidates[0]["score"] - overlap_candidates[1]["score"]) <= AMBIGUITY_MARGIN
        ):
            alias_entity["ambiguous"] = True
            alias_entity["candidates"] = overlap_candidates
        return alias_entity

    # 3. Overlap match
    overlap_candidates = rank_overlap_candidates(normalized_span, gazetteer_names)
    if overlap_candidates:
        top_candidate = overlap_candidates[0]
        confidence = top_candidate["score"]
        ambiguous = (
            len(overlap_candidates) > 1
            and abs(top_candidate["score"] - overlap_candidates[1]["score"]) <= AMBIGUITY_MARGIN
        )
        non_generic_overlap = [t for t in top_candidate["overlap_tokens"] if t not in GENERIC_GAZETTEER_TOKENS]
        has_meaningful_overlap = bool(non_generic_overlap) or len(tokenise_for_overlap(normalized_span)) == 1
        if confidence >= OVERLAP_MIN_SCORE and has_meaningful_overlap:
            return build_overlap_entity(normalized_span, overlap_candidates, "overlap", confidence, ambiguous)

    # 4. Fuzzy correction
    corrected_span, fuzzy_corrections = apply_fuzzy_token_corrections(normalized_span, gazetteer_tokens)
    if corrected_span and corrected_span != normalized_span and fuzzy_corrections:
        # 4a. Check alias
        if corrected_span in ALIAS_MAP:
            alias_entity = build_alias_entity(normalized_span, normalize_name(ALIAS_MAP[corrected_span]))
            alias_entity["method"] = "fuzzy_overlap"
            alias_entity["confidence"] = round(ALIAS_CONFIDENCE - FUZZY_CONFIDENCE_PENALTY, 3)
            alias_entity["fuzzy_corrections"] = fuzzy_corrections
            alias_entity["candidates"] = [{
                "name": alias_entity["resolved_name"],
                "score": alias_entity["confidence"],
                "reason": "Resolved after fuzzy correction + alias lookup.",
            }]
            return alias_entity
        # 4b. Overlap
        fuzzy_candidates = rank_overlap_candidates(corrected_span, gazetteer_names)
        if fuzzy_candidates:
            top_candidate = fuzzy_candidates[0]
            confidence = max(top_candidate["score"] - FUZZY_CONFIDENCE_PENALTY, 0.0)
            ambiguous = (
                len(fuzzy_candidates) > 1
                and abs(top_candidate["score"] - fuzzy_candidates[1]["score"]) <= AMBIGUITY_MARGIN
            )
            if confidence >= FUZZY_OVERLAP_MIN_SCORE and bool(top_candidate["overlap_tokens"]):
                return build_overlap_entity(normalized_span, fuzzy_candidates, "fuzzy_overlap", confidence, ambiguous, fuzzy_corrections)

    # 5. Raw 
    final_candidates = overlap_candidates if overlap_candidates else []
    return {
        "raw_span": normalized_span,
        "resolved_name": normalized_span,
        "method": "raw",
        "confidence": round(final_candidates[0]["score"], 3) if final_candidates else 0.0,
        "ambiguous": False,
        "candidates": final_candidates,
        "fuzzy_corrections": fuzzy_corrections if "fuzzy_corrections" in dir() else [],
    }

def choose_preferred_entity(left: dict[str, object], right: dict[str, object]) -> dict[str, object]:
    priority = {"exact": 5, "alias": 4, "overlap": 3, "fuzzy_overlap": 2, "raw": 1}
    left_priority = priority[left["method"]]
    right_priority = priority[right["method"]]
    if left_priority != right_priority:
        return left if left_priority > right_priority else right
    if left["confidence"] != right["confidence"]:
        return left if left["confidence"] > right["confidence"] else right
    left_length = len(tokenise_for_overlap(left["resolved_name"]))
    right_length = len(tokenise_for_overlap(right["resolved_name"]))
    if left_length != right_length:
        return left if left_length > right_length else right
    return left

def is_stronger_entity(left: dict[str, object], right: dict[str, object]) -> bool:
    return choose_preferred_entity(left, right) is left

def prune_dominated_entities(entities: list[dict[str, object]]) -> list[dict[str, object]]:
    pruned_entities = []
    for index, entity in enumerate(entities):
        if entity["ambiguous"] or entity["method"] == "exact":
            pruned_entities.append(entity)
            continue

        entity_tokens = set(tokenise_for_overlap(entity["resolved_name"]))
        dominated = False
        for other_index, other in enumerate(entities):
            if index == other_index or other["method"] == "raw":
                continue
            other_tokens = set(tokenise_for_overlap(other["resolved_name"]))
            if entity_tokens and entity_tokens < other_tokens and is_stronger_entity(other, entity):
                dominated = True
                break

        if not dominated:
            pruned_entities.append(entity)
    return pruned_entities

def merge_resolved_entities(entities: list[dict[str, object]]) -> list[dict[str, object]]:
    merged_by_surface = {}
    for entity in entities:
        surface_key = normalize_name(entity["raw_span"])
        existing = merged_by_surface.get(surface_key)
        if existing is None:
            merged_by_surface[surface_key] = entity
        else:
            merged_by_surface[surface_key] = choose_preferred_entity(existing, entity)

    merged_by_name = {}
    for entity in merged_by_surface.values():
        resolved_key = entity["resolved_name"]
        existing = merged_by_name.get(resolved_key)
        if existing is None:
            merged_by_name[resolved_key] = entity
        else:
            merged_by_name[resolved_key] = choose_preferred_entity(existing, entity)

    merged_entities = list(merged_by_name.values())
    return prune_dominated_entities(merged_entities)

def should_include_resolved_name(entity: dict[str, object], entities: list[dict[str, object]]) -> bool:
    if entity["method"] != "raw":
        return True
    if entity["confidence"] < RAW_RESOLVED_NAME_FLOOR:
        return False

    raw_tokens = set(tokenise_for_overlap(entity["raw_span"]))
    for other in entities:
        if other is entity or other["method"] == "raw":
            continue
        other_tokens = set(tokenise_for_overlap(other["resolved_name"]))
        if raw_tokens and raw_tokens <= other_tokens and other["confidence"] >= entity["confidence"]:
            return False
    return True

def resolve_query_locations(raw_text: str, model, gazetteer_names: set[str], gazetteer_tokens: set[str]) -> dict[str, object]:
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
    alias_entities = detect_alias_matches(tokens, gazetteer_names)
    alias_matches = [entity["raw_span"] for entity in alias_entities]

    entities = [build_exact_entity(match_name) for match_name in exact_matches]
    entities.extend(alias_entities)

    processed_spans = set(exact_matches + alias_matches)
    for alias_span in alias_matches:
        for tok in normalize_name(alias_span).split():
            processed_spans.add(tok)

    crf_spans_sorted = sorted(crf_spans, key=lambda s: len(tokenise_for_overlap(normalize_name(s))), reverse=True)
    for span in crf_spans_sorted:
        normalized_span = normalize_name(span)
        if not normalized_span or normalized_span in processed_spans:
            continue
        span_toks = tokenise_for_overlap(normalized_span)
        entity = resolve_span_to_canonical(normalized_span, gazetteer_names, gazetteer_tokens)
        entities.append(entity)
        if entity["method"] != "raw" or entity["confidence"] >= RAW_RESOLVED_NAME_FLOOR:
            processed_spans.add(normalized_span)
            for tok in span_toks:
                processed_spans.add(tok)

    merged_entities = merge_resolved_entities(entities)
    resolved_names = [
        entity["resolved_name"]
        for entity in merged_entities
        if should_include_resolved_name(entity, merged_entities)
    ]

    return {
        "query": raw_text,
        "tokens": tokens,
        "crf_tags": crf_tags,
        "crf_spans": crf_spans,
        "exact_matches": exact_matches,
        "alias_matches": alias_matches,
        "entities": merged_entities,
        "resolved_names": resolved_names,
    }

def extract_locations(raw_text: str, model, gazetteer_names: set[str], gazetteer_tokens: set[str]) -> list[str]:
    return resolve_query_locations(raw_text, model, gazetteer_names, gazetteer_tokens)['resolved_names']

def print_query_resolution(query_text: str, title: str) -> None:
    resolution = resolve_query_locations(query_text, crf_model, gazetteer_names, gazetteer_tokens)
    print(f'\\n{title} before inference:', resolution['query'])
    print(f'{title} after tokenization:', resolution['tokens'])
    print(f'{title} CRF tags:', resolution['crf_tags'])
    print(f'{title} exact gazetteer matches:', resolution['exact_matches'])
    print(f'{title} alias matches:', resolution['alias_matches'])
    print(f'{title} CRF spans:', resolution['crf_spans'])
    print(f'{title} structured entities:')
    for entity in resolution['entities']:
        print(entity)
        if entity['fuzzy_corrections']:
            print('  fuzzy corrections:', entity['fuzzy_corrections'])
        print('  overlap candidates + scores:', entity['candidates'])
    print(f'{title} extracted locations:', resolution['resolved_names'])


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
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port)