#!/usr/bin/env python3
"""
河北省新冠中医诊疗方案 - 本体推理引擎
基于 JSON-LD 本体的智能查询与推理工具

用法:
  python3 ontology_query.py diagnosis <症状1> <症状2> ...     # 辨证推理
  python3 ontology_query.py formula <证型名>                   # 方剂查询
  python3 ontology_query.py herb <方剂名>                      # 组方查询
  python3 ontology_query.py acupoint <阶段名>                  # 穴位查询
  python3 ontology_query.py cross-herb <药名>                  # 跨方剂药物分析
  python3 ontology_query.py prevention <人群>                  # 预防方案
  python3 ontology_query.py graph <证型名>                     # 知识图谱可视化
  python3 ontology_query.py ontology-info                      # 本体元数据
"""

import json
import sys
import os
from pathlib import Path
from collections import defaultdict

SCRIPT_DIR = Path(__file__).parent
ONTOLOGY_DIR = SCRIPT_DIR.parent / "ontology"
INSTANCES_FILE = ONTOLOGY_DIR / "instances.jsonld"

NS = "https://tcm-covid19-hebei.openclaw.ai/ontology#"

def load_ontology():
    """加载本体实例数据"""
    with open(INSTANCES_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    graph = {}
    for item in data.get("@graph", []):
        gid = item.get("@id", "").replace(NS, "")
        if gid:
            graph[gid] = item
    return graph

def resolve_id(graph, label_or_id):
    """通过标签或ID查找实体"""
    clean = label_or_id.strip()
    if clean.startswith("tcm:"):
        clean = clean[4:]
    if clean in graph:
        return clean
    for eid, entity in graph.items():
        lbl = entity.get("rdfs:label", "")
        if isinstance(lbl, str) and (clean in lbl or lbl in clean):
            return eid
    return None

def get_label(graph, entity_id):
    """获取实体标签"""
    eid = entity_id.replace(NS, "") if NS in entity_id else entity_id
    entity = graph.get(eid, {})
    return entity.get("rdfs:label", eid)

def get_syndromes_by_phase(graph, phase_id):
    """按阶段获取所有证型"""
    results = []
    for eid, entity in graph.items():
        if entity.get("@type") == f"{NS}Syndrome" or entity.get("@type") == "tcm:Syndrome":
            phase = entity.get("tcm:hasPhase", "")
            if isinstance(phase, str):
                phase = phase.replace(NS, "")
            if phase == phase_id:
                results.append(eid)
    return results

def get_symptoms_of_syndrome(graph, syndrome_id):
    """获取证型的所有症状"""
    entity = graph.get(syndrome_id, {})
    symptoms = entity.get("tcm:hasSymptom", [])
    if isinstance(symptoms, str):
        symptoms = [symptoms]
    labels = []
    for s in symptoms:
        sid = s.replace(NS, "") if NS in s else s
        labels.append(get_label(graph, sid))
    # 补充舌象脉象
    tongue = entity.get("tcm:hasTongue", "")
    pulse = entity.get("tcm:hasPulse", "")
    if tongue:
        labels.append(f"[舌]{tongue}")
    if pulse:
        labels.append(f"[脉]{pulse}")
    return labels

def get_formula_of_syndrome(graph, syndrome_id):
    """获取证型推荐方剂"""
    entity = graph.get(syndrome_id, {})
    formulas = entity.get("tcm:recommendedFormula", [])
    if isinstance(formulas, str):
        formulas = [formulas]
    results = []
    for f in formulas:
        fid = f.replace(NS, "") if NS in f else f
        fentity = graph.get(fid, {})
        results.append({
            "id": fid,
            "label": get_label(graph, fid),
            "type": fentity.get("@type", "").replace(NS, "").replace("tcm:", ""),
            "composition": fentity.get("tcm:hasComposition", []),
            "administration": fentity.get("tcm:hasAdministration", ""),
            "frequency": fentity.get("tcm:hasFrequency", ""),
            "note": fentity.get("tcm:hasNote", "")
        })
    return results

def get_acupoints_of_syndrome(graph, syndrome_id):
    """获取证型推荐穴位"""
    entity = graph.get(syndrome_id, {})
    points = entity.get("tcm:hasAcupoint", [])
    if isinstance(points, str):
        points = [points]
    results = []
    for p in points:
        pid = p.replace(NS, "") if NS in p else p
        pentity = graph.get(pid, {})
        meridian = pentity.get("tcm:belongs_toMeridian", "")
        if isinstance(meridian, str):
            meridian = meridian.replace(NS, "")
        results.append({
            "label": get_label(graph, pid),
            "meridian": get_label(graph, meridian) if meridian else ""
        })
    return results

# ==================== 核心推理功能 ====================

def diagnose(graph, symptom_labels):
    """
    辨证推理：根据症状匹配证型
    使用加权匹配算法：
    - 核心症状（舌象、脉象）权重 2.0
    - 普通症状权重 1.0
    - 按匹配度排序
    """
    normalized_input = [s.strip().lower() for s in symptom_labels]

    results = []
    for eid, entity in graph.items():
        if entity.get("@type") not in [f"{NS}Syndrome", "tcm:Syndrome"]:
            continue

        syndrome_symptoms = get_symptoms_of_syndrome(graph, eid)
        syndrome_name = get_label(graph, eid)
        phase = entity.get("tcm:hasPhase", "")
        if isinstance(phase, str):
            phase = phase.replace(NS, "")
        phase_name = get_label(graph, phase)

        matched = []
        total_weight = 0
        match_weight = 0

        for sym in syndrome_symptoms:
            is_special = sym.startswith("[舌]") or sym.startswith("[脉]")
            weight = 2.0 if is_special else 1.0
            total_weight += weight

            sym_lower = sym.lower()
            for user_sym in normalized_input:
                if user_sym in sym_lower or sym_lower in user_sym:
                    matched.append(sym)
                    match_weight += weight
                    break

        if matched:
            score = match_weight / total_weight if total_weight > 0 else 0
            results.append({
                "syndrome": syndrome_name,
                "syndrome_id": eid,
                "phase": phase_name,
                "score": round(score, 3),
                "matched_symptoms": matched,
                "all_symptoms": syndrome_symptoms,
                "match_ratio": f"{len(matched)}/{len(syndrome_symptoms)}"
            })

    results.sort(key=lambda x: x["score"], reverse=True)
    return results

def build_knowledge_graph(graph, syndrome_id):
    """
    构建单个证型的知识图谱（关系网络）
    返回以证型为中心的所有关联实体
    """
    entity = graph.get(syndrome_id, {})
    name = get_label(graph, syndrome_id)

    kg = {
        "center": name,
        "type": "Syndrome",
        "connections": []
    }

    # 阶段
    phase = entity.get("tcm:hasPhase", "")
    if isinstance(phase, str):
        phase = phase.replace(NS, "")
    if phase:
        kg["connections"].append({
            "relation": "所属阶段",
            "target": get_label(graph, phase),
            "target_type": "Phase"
        })

    # 症状
    symptoms = entity.get("tcm:hasSymptom", [])
    if isinstance(symptoms, str):
        symptoms = [symptoms]
    for s in symptoms:
        sid = s.replace(NS, "") if NS in s else s
        kg["connections"].append({
            "relation": "表现症状",
            "target": get_label(graph, sid),
            "target_type": "Symptom"
        })

    # 舌象脉象
    tongue = entity.get("tcm:hasTongue", "")
    pulse = entity.get("tcm:hasPulse", "")
    if tongue:
        kg["connections"].append({"relation": "舌象", "target": tongue, "target_type": "TongueSign"})
    if pulse:
        kg["connections"].append({"relation": "脉象", "target": pulse, "target_type": "PulseSign"})

    # 方剂
    formulas = entity.get("tcm:recommendedFormula", [])
    if isinstance(formulas, str):
        formulas = [formulas]
    for f in formulas:
        fid = f.replace(NS, "") if NS in f else f
        fentity = graph.get(fid, {})
        fnode = {
            "relation": "推荐方剂",
            "target": get_label(graph, fid),
            "target_type": fentity.get("@type", "").replace(NS, "").replace("tcm:", ""),
            "children": []
        }
        # 药物组成
        comp = fentity.get("tcm:hasComposition", [])
        for herb in comp:
            if isinstance(herb, dict):
                fnode["children"].append({
                    "relation": "组成药物",
                    "target": f"{herb.get('tcm:herb', '')} {herb.get('tcm:dosage', '')}",
                    "target_type": "Herb"
                })
        kg["connections"].append(fnode)

    # 穴位
    points = entity.get("tcm:hasAcupoint", [])
    if isinstance(points, str):
        points = [points]
    for p in points:
        pid = p.replace(NS, "") if NS in p else p
        pentity = graph.get(pid, {})
        meridian = pentity.get("tcm:belongs_toMeridian", "")
        if isinstance(meridian, str):
            meridian = meridian.replace(NS, "")
        kg["connections"].append({
            "relation": "推荐穴位",
            "target": get_label(graph, pid),
            "target_type": "Acupoint",
            "meridian": get_label(graph, meridian) if meridian else ""
        })

    return kg

def cross_herb_analysis(graph, herb_name):
    """分析某味中药在不同方剂中的使用情况"""
    results = []
    for eid, entity in graph.items():
        if entity.get("@type") not in [f"{NS}Decoction", "tcm:Decoction"]:
            continue
        comp = entity.get("tcm:hasComposition", [])
        for h in comp:
            if isinstance(h, dict) and herb_name in h.get("tcm:herb", ""):
                formula_name = get_label(graph, eid)
                dosage = h.get("tcm:dosage", "")
                treats = entity.get("tcm:treatsSyndrome", [])
                if isinstance(treats, str):
                    treats = [treats]
                syndrome_names = []
                for t in treats:
                    tid = t.replace(NS, "") if NS in t else t
                    syndrome_names.append(get_label(graph, tid))
                results.append({
                    "formula": formula_name,
                    "dosage": dosage,
                    "treats_syndromes": syndrome_names
                })
    return results

def get_prevention(graph, population):
    """获取预防方案"""
    prevention_formulas = []
    for eid, entity in graph.items():
        if entity.get("tcm:isPreventionFormula") is True:
            prevention_formulas.append({
                "id": eid,
                "label": get_label(graph, eid),
                "note": entity.get("tcm:hasNote", "")
            })

    # 基于人群筛选
    population_map = {
        "密接": "密接人群",
        "普通": "普通成人",
        "老年": "老年体虚",
        "儿童": "儿童"
    }
    matched_key = None
    for k, v in population_map.items():
        if k in population:
            matched_key = v
            break

    return {
        "population": matched_key or population,
        "formulas": prevention_formulas
    }

# ==================== 格式化输出 ====================

def format_diagnosis(results):
    """格式化辨证结果"""
    if not results:
        return "❌ 未找到匹配的证型，请检查症状描述。"

    lines = ["🔍 辨证推理结果（按匹配度排序）\n"]
    for i, r in enumerate(results[:5], 1):
        bar = "█" * int(r["score"] * 10) + "░" * (10 - int(r["score"] * 10))
        lines.append(f"{'🥇🥈🥉'[min(i-1,2)] if i<=3 else '  '} {i}. 【{r['syndrome']}】")
        lines.append(f"     阶段: {r['phase']}")
        lines.append(f"     匹配: {r['match_ratio']} 症状 | 得分: {bar} {r['score']:.1%}")
        lines.append(f"     已匹配: {', '.join(r['matched_symptoms'])}")

        # 推荐方剂
        formulas = get_formula_of_syndrome(graph_global, r['syndrome_id'])
        if formulas:
            f_names = [f["label"] for f in formulas]
            lines.append(f"     💊 推荐方剂: {', '.join(f_names)}")
        lines.append("")

    return "\n".join(lines)

def format_knowledge_graph(kg):
    """格式化知识图谱"""
    lines = [f"🕸️ 知识图谱: {kg['center']}\n"]
    lines.append(f"   ┌─ 类型: {kg['type']}\n")

    for conn in kg["connections"]:
        rtype = conn.get("target_type", "")
        rel = conn.get("relation", "")
        target = conn.get("target", "")

        icon = {
            "Phase": "📅", "Symptom": "🩺", "TongueSign": "👅", "PulseSign": "💓",
            "Decoction": "🍵", "PatentMedicine": "💊", "Herb": "🌿",
            "Acupoint": "📍", "Meridian": "🌊"
        }.get(rtype, "•")

        if conn.get("children"):
            lines.append(f"   ├─ {icon} {rel}: {target}")
            for child in conn["children"]:
                lines.append(f"   │    └─ 🌿 {child['target']}")
        else:
            meridian = conn.get("meridian", "")
            extra = f" ({meridian})" if meridian else ""
            lines.append(f"   ├─ {icon} {rel}: {target}{extra}")

    return "\n".join(lines)

def format_formula(formulas):
    """格式化方剂信息"""
    if not formulas:
        return "❌ 未找到相关方剂。"
    lines = []
    for f in formulas:
        lines.append(f"💊 {f['label']} ({f['type']})")
        if f['composition']:
            lines.append("   组成:")
            for h in f['composition']:
                if isinstance(h, dict):
                    lines.append(f"   • {h.get('tcm:herb','')} {h.get('tcm:dosage','')}")
        if f['administration']:
            lines.append(f"   服法: {f['administration']}")
        if f['frequency']:
            lines.append(f"   疗程: {f['frequency']}")
        if f['note']:
            lines.append(f"   备注: {f['note']}")
        lines.append("")
    return "\n".join(lines)

def format_acupoints(points):
    """格式化穴位信息"""
    if not points:
        return "❌ 未找到相关穴位。"
    by_meridian = defaultdict(list)
    for p in points:
        mer = p.get("meridian", "其他")
        by_meridian[mer].append(p["label"])

    lines = ["📍 推荐穴位:\n"]
    for mer, pts in by_meridian.items():
        lines.append(f"   🌊 {mer}: {', '.join(pts)}")
    return "\n".join(lines)

def format_cross_herb(results, herb_name):
    """格式化跨方剂药物分析"""
    if not results:
        return f"❌ 未在任何方剂中找到「{herb_name}」。"
    lines = [f"🌿 「{herb_name}」跨方剂分析（共 {len(results)} 个方剂使用）\n"]
    for r in results:
        syndromes = ", ".join(r["treats_syndromes"])
        lines.append(f"   🍵 {r['formula']}")
        lines.append(f"      用量: {r['dosage']}")
        lines.append(f"      主治证型: {syndromes}")
        lines.append("")
    return "\n".join(lines)

def ontology_info(graph):
    """本体元数据统计"""
    type_counts = defaultdict(int)
    for eid, entity in graph.items():
        t = entity.get("@type", "").replace(NS, "").replace("tcm:", "")
        type_counts[t] += 1

    lines = ["📊 本体元数据\n"]
    lines.append(f"   命名空间: {NS}")
    lines.append(f"   实体总数: {len(graph)}\n")
    lines.append("   类分布:")
    for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
        lines.append(f"   • {t}: {c}")
    return "\n".join(lines)

# ==================== 主入口 ====================

graph_global = None

def main():
    global graph_global
    graph_global = load_ontology()

    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = sys.argv[1].lower()

    if cmd == "diagnosis" and len(sys.argv) >= 3:
        symptoms = sys.argv[2:]
        results = diagnose(graph_global, symptoms)
        print(format_diagnosis(results))

    elif cmd == "formula" and len(sys.argv) >= 3:
        name = " ".join(sys.argv[2:])
        sid = resolve_id(graph_global, name)
        if sid:
            formulas = get_formula_of_syndrome(graph_global, sid)
            print(format_formula(formulas))
        else:
            print(f"❌ 未找到证型「{name}」")

    elif cmd == "herb" and len(sys.argv) >= 3:
        name = " ".join(sys.argv[2:])
        fid = resolve_id(graph_global, name)
        if fid:
            entity = graph_global[fid]
            comp = entity.get("tcm:hasComposition", [])
            print(f"🍵 {get_label(graph_global, fid)} 组成:")
            for h in comp:
                if isinstance(h, dict):
                    print(f"   • {h.get('tcm:herb','')} {h.get('tcm:dosage','')}")
        else:
            print(f"❌ 未找到方剂「{name}」")

    elif cmd == "acupoint" and len(sys.argv) >= 3:
        name = " ".join(sys.argv[2:])
        phase_id = resolve_id(graph_global, name)
        if phase_id:
            syndromes = get_syndromes_by_phase(graph_global, phase_id)
            all_points = []
            for sid in syndromes:
                all_points.extend(get_acupoints_of_syndrome(graph_global, sid))
            # 去重
            seen = set()
            unique = []
            for p in all_points:
                if p["label"] not in seen:
                    seen.add(p["label"])
                    unique.append(p)
            print(format_acupoints(unique))
        else:
            print(f"❌ 未找到阶段「{name}」")

    elif cmd == "cross-herb" and len(sys.argv) >= 3:
        name = " ".join(sys.argv[2:])
        results = cross_herb_analysis(graph_global, name)
        print(format_cross_herb(results, name))

    elif cmd == "prevention" and len(sys.argv) >= 3:
        pop = " ".join(sys.argv[2:])
        result = get_prevention(graph_global, pop)
        print(f"🛡️ 预防方案 - {result['population']}人群")
        print(f"   详见: references/treatment-detail.md 预防章节")

    elif cmd == "graph" and len(sys.argv) >= 3:
        name = " ".join(sys.argv[2:])
        sid = resolve_id(graph_global, name)
        if sid:
            kg = build_knowledge_graph(graph_global, sid)
            print(format_knowledge_graph(kg))
        else:
            print(f"❌ 未找到证型「{name}」")

    elif cmd == "ontology-info":
        print(ontology_info(graph_global))

    else:
        print(__doc__)

if __name__ == "__main__":
    main()
