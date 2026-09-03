# 河北省新冠中医诊疗方案（第七版）- OpenClaw Ontology Skill

基于**本体论（Ontology）**的中医知识库，内置 OWL 本体和 Python 推理引擎。

## 核心特性

### 🧠 本体驱动的知识表示
- **OWL 本体**定义了完整的中医领域概念模型（类、属性、公理）
- **JSON-LD** 格式的结构化实例数据，可被机器推理和查询
- 实体关系网络：疾病→阶段→证型→症状/方剂→药物/穴位→经络

### 🔍 智能辨证推理
根据患者症状自动匹配证型，使用加权算法：
- 舌象/脉象权重 2.0（核心辨证依据）
- 普通症状权重 1.0
- 输出 Top 5 匹配结果及推荐方剂

### 🕸️ 知识图谱可视化
以任意证型为中心展开完整关系网络：
```
症状 → 证型 → 方剂 → 药物组成
              ↓
           穴位 → 经络
```

### 🌿 跨方剂药物分析
分析某味中药在所有方剂中的用量差异和主治证型。

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

## 本体统计

| 类型 | 数量 | 说明 |
|------|------|------|
| Syndrome | 16 | 轻型2 + 中型3 + 重型2 + 危重型1 + 恢复期8 |
| Decoction | 17 | 含清肺排毒汤（通用方） |
| Symptom | 47 | 含舌象、脉象 |
| Acupoint | 22 | 跨 9 条经络 |
| ExternalTherapy | 9 | 针刺/艾灸/推拿/耳穴/刮痧/拔罐/功法 |
| **总计** | **136** | |

## 使用方式

### 命令行推理引擎

```bash
# 辨证推理：输入症状，自动匹配证型
python3 scripts/ontology_query.py diagnosis 发热 咽痛 苔黄

# 知识图谱：展开证型完整关系网络
python3 scripts/ontology_query.py graph 浊毒闭肺证

# 方剂查询
python3 scripts/ontology_query.py formula 浊毒化热证

# 跨方剂药物分析
python3 scripts/ontology_query.py cross-herb 藿香

# 穴位查询
python3 scripts/ontology_query.py acupoint 重型

# 本体元数据
python3 scripts/ontology_query.py ontology-info
```

### OpenClaw 内使用

安装后，在对话中直接描述患者症状，AI 会自动调用推理引擎进行辨证论治。

## 目录结构

```
tcm-covid19-hebei/
├── SKILL.md                        # 技能主文件
├── ontology/
│   ├── schema.ttl                  # OWL 本体模式（Turtle 格式）
│   └── instances.jsonld            # 实例数据（JSON-LD 格式，136个实体）
├── scripts/
│   └── ontology_query.py           # Python 推理引擎
├── references/
│   └── treatment-detail.md         # 详细处方与外治法
├── README.md
└── LICENSE
```

## 安装

```bash
# OpenClaw 安装
openclaw skills install tcm-covid19-hebei.skill

# 或直接复制
cp -r tcm-covid19-hebei ~/.openclaw/skills/
```

## 技术栈

- **本体语言**: OWL 2 / RDF (Turtle) + JSON-LD
- **推理引擎**: Python 3 (加权匹配算法)
- **知识表示**: 面向对象的中医领域本体

## 免责声明

本技能内容来源于河北省中医药管理局公开发布的诊疗方案，仅供中医学习与参考。实际用药请务必在执业中医师指导下进行。

## 来源

- [河北省中医药管理局](http://hbzyywx.hebwst.gov.cn/)
- 原文：[关于印发河北省新型冠状病毒感染中医药诊疗方案（试行第七版）的通知](https://mp.weixin.qq.com/s/W5CEefgW1PDNcx09OtYGkw)

## License

MIT
