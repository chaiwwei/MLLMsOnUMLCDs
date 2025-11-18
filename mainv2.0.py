import json
import re
import argparse
import sys
from collections import defaultdict
from typing import Tuple, Dict, Any, List

def normalize_multiplicity(mult: str) -> str:
    """Normalize multiplicity strings (e.g., '0..*' -> '*', '1..1' -> '1')"""
    if not mult:
        return "1..1"
    mult = mult.strip()
    if mult == "1":
        return "1..1"
    if mult in ("*", "..*"):
        return "0..*"
    if mult == "1..":          # Non-standard: treat as "1..*"
        return "1..*"

    return mult

def parse_attribute(attr: str) -> Tuple[str, str, str, str]:
    attr = attr.strip()
    vis = '+'
    if attr.startswith(('+', '-', '#', '~')):
        vis = attr[0]
        attr = attr[1:].strip()
    
    mult = '1'
    if '[' in attr and attr.endswith(']'):
        idx = attr.rfind('[')
        mult_part = attr[idx+1:-1]
        mult = normalize_multiplicity(mult_part)
        attr = attr[:idx].strip()
    
    if ':' in attr:
        name, typ = attr.split(':', 1)
        name = name.strip()
        typ = typ.strip()
    else:
        name = attr
        typ = ''
    return vis, name, typ, mult

def parse_operation(op: str) -> Tuple[str, str, Tuple[Tuple[str, str], ...], str]:
    op = op.strip()
    vis = '+'
    if op.startswith(('+', '-', '#', '~')):
        vis = op[0]
        op = op[1:].strip()
    
    ret_type = 'void'
    if ':' in op and op.count('(') == op.count(')'):
        last_colon = op.rfind(':')
        last_paren = op.rfind(')')
        if last_colon > last_paren:
            ret_type = op[last_colon+1:].strip()
            op = op[:last_colon].strip()
    
    if '(' not in op:
        return vis, op, (), ret_type

    if ')' not in op:
        return vis, op, (), ret_type

    name_part, rest = op.split('(', 1)
    name = name_part.strip()
    params_str = rest.split(')', 1)[0]

    params_list = []
    if params_str.strip():
        for param in params_str.split(','):
            param = param.strip()
            if not param:
                continue
            if ':' in param:
                p_name, p_type = param.split(':', 1)
                params_list.append((p_name.strip(), p_type.strip()))
            else:
                params_list.append((param, ''))
    
    return vis, name, tuple(params_list), ret_type

def parse_association(assoc: Dict[str, str]) -> Tuple[Tuple[str, str], str, str]:
    src = assoc['source']
    tgt = assoc['target']
    mult_src = normalize_multiplicity(assoc.get('multiplicity_source', ''))
    mult_tgt = normalize_multiplicity(assoc.get('multiplicity_target', ''))
    key = (src, tgt)
    if assoc.get('direction') == 'bidirectional':
        if src > tgt:
            key = (tgt, src)
  
    return key, mult_tgt, mult_src

def describe_relationship(rel_type: str, key) -> str:
    """Convert a relationship tuple into a human-readable description."""
    try:
        if rel_type == "association":
            classes, m1, m2 = key
            return f"{classes[0]} [{m1}] — {classes[1]} [{m2}] (association)"
        elif rel_type in ("composition", "aggregation"):
            whole, part, mw, mp = key
            sym = "◆" if rel_type == "composition" else "◇"
            return f"{whole} [{mw}] {sym}—— {part} [{mp}] ({rel_type})"
        elif rel_type == "dependency":
            dep, sup = key
            return f"{dep} ⟶ {sup} (dependency)"
        elif rel_type == "inheritance":
            parent, child = key
            return f"{child} ──|> {parent} (inheritance)"
        elif rel_type == "realization":
            interface, impl = key
            return f"{impl} ╌╌|> {interface} (realization)"
        else:
            return str(key)
    except Exception:
        return f"<malformed {rel_type}: {key}>"

def load_json_file(filepath: str) -> Dict[Any, Any]:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: File not found: {filepath}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Error: Invalid JSON in {filepath}: {e}", file=sys.stderr)
        sys.exit(1)

def save_json_file(data: Dict, filepath: str):
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"❌ Error writing output file {filepath}: {e}", file=sys.stderr)
        sys.exit(1)

def compute_metrics(true_data: Dict, pred_data: Dict) -> Dict:
    true_elements = {}
    pred_elements = {}

    # --- Process classes ---
    for cls in true_data.get("classes", []):
        name = cls["name"]
        attrs = {parse_attribute(a) for a in cls.get("attributes", [])}
        ops = {parse_operation(o) for o in cls.get("operations", [])}
        true_elements[name] = {"type": "class", "attrs": attrs, "ops": ops}

    for cls in pred_data.get("classes", []):
        name = cls["name"]
        attrs = {parse_attribute(a) for a in cls.get("attributes", [])}
        ops = {parse_operation(o) for o in cls.get("operations", [])}
        pred_elements[name] = {"type": "class", "attrs": attrs, "ops": ops}

    # --- Process enumerations (as classes) ---
    for enum in true_data.get("enumerations", []):
        name = enum["name"]
        literals = {('+', lit, '', '1') for lit in enum.get("literals", [])}
        true_elements[name] = {"type": "enum", "attrs": literals, "ops": set()}

    for enum in pred_data.get("enumerations", []):
        name = enum["name"]
        literals = {('+', lit, '', '1') for lit in enum.get("literals", [])}
        pred_elements[name] = {"type": "enum", "attrs": literals, "ops": set()}

    # --- Match classes/enums by name + content ---
    matched_classes = set()
    for name in true_elements:
        if name in pred_elements:
            t = true_elements[name]
            p = pred_elements[name]
            if t["attrs"] == p["attrs"] and t["ops"] == p["ops"]:
                matched_classes.add(name)

    # --- Process relationships with error resilience ---
    true_rels = defaultdict(set)
    pred_rels = defaultdict(set)
    rel_types = ["association", "composition", "aggregation", "dependency", "inheritance", "realization"]

    def process_relationships(rel_list, rel_type):
        result = set()
        for idx, rel in enumerate(rel_list):
            try:
                if rel_type == "association":
                    src = rel.get('source')
                    tgt = rel.get('target')
                    if src is None or tgt is None:
                        print(f"⚠️  Skipping malformed association (missing source/target): {rel}", file=sys.stderr)
                        continue
                    key = parse_association(rel)
                    result.add(key)
                elif rel_type in ["composition", "aggregation"]:
                    whole = rel.get('whole')
                    part = rel.get('part')
                    if whole is None or part is None:
                        print(f"⚠️  Skipping malformed {rel_type} (missing 'whole' or 'part'): {rel}", file=sys.stderr)
                        continue
                    key = (
                        whole,
                        part,
                        normalize_multiplicity(rel.get('multiplicity_whole', '1')),
                        normalize_multiplicity(rel.get('multiplicity_part', '1'))
                    )
                    result.add(key)
                elif rel_type == "dependency":
                    dep = rel.get('dependent')
                    sup = rel.get('supplier')
                    if dep is None or sup is None:
                        print(f"⚠️  Skipping malformed dependency: {rel}", file=sys.stderr)
                        continue
                    result.add((dep, sup))
                elif rel_type == "inheritance":
                    parent = rel.get('parent')
                    child = rel.get('child')
                    if parent is None or child is None:
                        print(f"⚠️  Skipping malformed inheritance: {rel}", file=sys.stderr)
                        continue
                    result.add((parent, child))
                elif rel_type == "realization":
                    interface = rel.get('interface')
                    impl = rel.get('implementation')
                    if interface is None or impl is None:
                        print(f"⚠️  Skipping malformed realization: {rel}", file=sys.stderr)
                        continue
                    result.add((interface, impl))
            except Exception as e:
                print(f"⚠️  Error parsing {rel_type} #{idx}: {e} — Skipping: {rel}", file=sys.stderr)
                continue
        return result

    for rt in rel_types:
        true_list = true_data.get("relationships", {}).get(rt, [])
        pred_list = pred_data.get("relationships", {}).get(rt, [])
        true_rels[rt] = process_relationships(true_list, rt)
        pred_rels[rt] = process_relationships(pred_list, rt)

    # --- Metric calculation helper ---
    def calc_prf(true_n, pred_n, match_n):
        p = match_n / pred_n if pred_n > 0 else 0.0
        r = match_n / true_n if true_n > 0 else 0.0
        f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0.0
        return {"precision": round(p, 4), "recall": round(r, 4), "f1": round(f1, 4)}

    # --- Counts ---
    true_c, pred_c, match_c = len(true_elements), len(pred_elements), len(matched_classes)
    true_r = sum(len(v) for v in true_rels.values())
    pred_r = sum(len(v) for v in pred_rels.values())
    match_r = sum(len(true_rels[t] & pred_rels[t]) for t in rel_types)

    # --- Detailed output ---
    detailed = {
        "class_matching": {
            "matched": sorted(matched_classes),
            "mismatched_in_ground_truth": sorted(set(true_elements.keys()) - matched_classes),
            "extra_in_prediction": sorted(set(pred_elements.keys()) - matched_classes),
        },
        "relationship_matching": {}
    }

    for rt in rel_types:
        gt_set = true_rels[rt]
        pred_set = pred_rels[rt]
        matched_set = gt_set & pred_set
        missing_set = gt_set - pred_set
        extra_set = pred_set - gt_set

        def format_item(item):
            return {
                "raw": list(item) if isinstance(item, tuple) else item,
                "description": describe_relationship(rt, item)
            }

        matched_list = []
        for item in sorted(matched_set, key=lambda x: str(x)):
            f = format_item(item)
            matched_list.append({
                "ground_truth": f,
                "prediction": f  # identical in exact matching
            })

        detailed["relationship_matching"][rt] = {
            "matched": matched_list,
            "missing_in_prediction": [format_item(item) for item in sorted(missing_set, key=lambda x: str(x))],
            "extra_in_prediction": [format_item(item) for item in sorted(extra_set, key=lambda x: str(x))]
        }

    return {
        "class_metrics": calc_prf(true_c, pred_c, match_c),
        "relationship_metrics": calc_prf(true_r, pred_r, match_r),
        "overall_metrics": calc_prf(true_c + true_r, pred_c + pred_r, match_c + match_r),
        "counts": {
            "true_classes_and_enums": true_c,
            "predicted_classes_and_enums": pred_c,
            "matched_classes_and_enums": match_c,
            "true_relationships": true_r,
            "predicted_relationships": pred_r,
            "matched_relationships": match_r,
        },
        "detailed": detailed
    }

def main():
    parser = argparse.ArgumentParser(
        description="Evaluate class diagram prediction against ground truth.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("-g", "--ground-truth", required=True,
                        help="Path to ground truth JSON file")
    parser.add_argument("-p", "--prediction", required=True,
                        help="Path to prediction JSON file")
    parser.add_argument("-o", "--output", required=True,
                        help="Path to output JSON file for results")

    args = parser.parse_args()

    gt_data = load_json_file(args.ground_truth)
    pred_data = load_json_file(args.prediction)
    results = compute_metrics(gt_data, pred_data)
    save_json_file(results, args.output)

    cm = results['class_metrics']
    rm = results['relationship_metrics']
    om = results['overall_metrics']
    print(f"✅ Evaluation complete. Results saved to: {args.output}")
    print(f"\n📊 Summary:")
    print(f"  Classes/Enums → P: {cm['precision']}, R: {cm['recall']}, F1: {cm['f1']}")
    print(f"  Relationships → P: {rm['precision']}, R: {rm['recall']}, F1: {rm['f1']}")
    print(f"  Overall       → P: {om['precision']}, R: {om['recall']}, F1: {om['f1']}")

if __name__ == "__main__":
    main()