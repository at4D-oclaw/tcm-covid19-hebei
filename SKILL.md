---
name: tcm-covid19-hebei
description: >
  基于本体论（Ontology）的河北省新型冠状病毒感染中医药诊疗方案（第七版）技能。
  内置 OWL 本体（136个实体、16种证型、17个方剂、47个症状、22个穴位）和 Python 推理引擎，
  支持症状→证型智能辨证、方剂→药物→穴位知识图谱查询、跨方剂药物分析。
  适用场景：(1) 根据患者症状自动辨证推理并推荐方剂；(2) 查询证型-方剂-药物-穴位完整知识图谱；
  (3) 分析某味中药在各方剂中的用量差异；(4) 查询儿童/成人/预防方案；(5) 针灸、推拿、刮痧等外治法。
  来源：河北省中医药管理局。
---

# 河北省新冠中医诊疗方案 - 本体化知识库

## 本体架构

```
Disease ──hasPhase──> Phase ──contains──> Syndrome
                                       │
                        ┌───────────────┼───────────────┐
                        ▼               ▼               ▼
                   hasSymptom    recommendedFormula   hasAcupoint
                        │               │               │
                        ▼               ▼               ▼
                    Symptom    ┌──Decoction──┐     Acupoint
                      │        │             │        │
                 TongueSign    │   composedOf │   belongs_to
                 PulseSign     ▼             ▼     Meridian
                              Herb     PatentMedicine
```

**核心推理路径**: 症状 → 辨证（加权匹配）→ 证型 → 方剂 → 药物组成 + 穴位

## 推理引擎使用

本 skill 内置 Python 推理引擎 `scripts/ontology_query.py`，执行前需加载 `ontology/instances.jsonld`。

### 1. 辨证推理（核心功能）

根据患者症状自动匹配证型，使用加权算法：
- 舌象/脉象权重 **2.0**（核心辨证依据）
- 普通症状权重 **1.0**
- 按匹配得分排序，返回 Top 5

```bash
python3 scripts/ontology_query.py diagnosis <症状1> <症状2> ...
```

示例：
```bash
python3 scripts/ontology_query.py diagnosis 发热 咽痛 苔黄
python3 scripts/ontology_query.py diagnosis 倦怠乏力 纳呆 舌淡体胖苔白
python3 scripts/ontology_query.py diagnosis 呼吸困难 神昏 汗出肢冷
```

### 2. 知识图谱查询

以证型为中心展开完整关系网络（症状→证型→方剂→药物→穴位→经络）：

```bash
python3 scripts/ontology_query.py graph <证型名>
```

### 3. 方剂查询

```bash
python3 scripts/ontology_query.py formula <证型名>    # 查证型对应方剂
python3 scripts/ontology_query.py herb <方剂名>       # 查方剂药物组成
```

### 4. 穴位查询

```bash
python3 scripts/ontology_query.py acupoint <阶段名>   # 按阶段查穴位
```

### 5. 跨方剂药物分析

分析某味中药在所有方剂中的用量与主治证型：

```bash
python3 scripts/ontology_query.py cross-herb <药名>
```

### 6. 本体元数据

```bash
python3 scripts/ontology_query.py ontology-info
```

## 快速辨证流程

当用户提供症状时，按以下步骤操作：

1. **提取关键症状**：从用户描述中提取症状关键词（发热、咳嗽、苔黄、脉浮等）
2. **运行辨证推理**：`python3 scripts/ontology_query.py diagnosis <症状...>`
3. **查看知识图谱**：对最匹配的证型运行 `graph` 命令获取完整信息
4. **综合建议**：结合方剂、穴位、外治法给出完整方案

若用户描述不够精确，追问以下关键信息：
- **寒热**：怕冷还是发热？发热程度？
- **舌象**：舌质颜色？苔的颜色和厚薄？
- **消化**：食欲、大便情况？
- **精神**：疲倦程度？意识状态？

## 本体文件说明

| 文件 | 格式 | 说明 |
|------|------|------|
| `ontology/schema.ttl` | OWL Turtle | 本体模式定义（类、属性、公理） |
| `ontology/instances.jsonld` | JSON-LD | 全部实例数据（136个实体） |
| `scripts/ontology_query.py` | Python | 推理引擎（辨证/图谱/分析） |
| `references/treatment-detail.md` | Markdown | 完整处方与外治法参考文档 |

## 本体统计

- **16 种证型**：轻型2 + 中型3 + 重型2 + 危重型1 + 恢复期8
- **17 个方剂**：含清肺排毒汤（通用方）
- **47 个症状**：含舌象、脉象
- **22 个穴位**：跨 9 条经络
- **9 种外治法**：针刺、艾灸、推拿、耳穴、刮痧、拔罐、八段锦、太极、六字诀

## 详细处方

完整方剂组成、剂量、服法及外治法见 `references/treatment-detail.md`。

## 重要提示

- 本方案仅供参考，实际用药需在中医师指导下进行
- 儿童剂量按年龄调整：1-3岁1/3剂量，3-6岁1/2剂量，6岁以上原方剂量
