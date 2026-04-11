# Real Model vs Non-AI Mock Application Visual Pack

This pack combines real model performance charts and architecture flowcharts comparing the production AI system with a non-AI mock app flow.

## Graphs (Real Model)

### 1) Production Metrics Overview
![Real model metrics](visuals/real_model_metrics.png)

Source: `models/metrics.json`

### 2) Model Family Tradeoff (F1 vs ROC-AUC)
![Model family tradeoff](visuals/model_family_tradeoff.png)

Source: `models/model_comparison.csv`

### 3) Production Confusion Matrix
![Production confusion matrix](visuals/production_confusion_matrix.png)

Source: `models/metrics.json`

### 4) Top Delay Drivers (Feature Importance)
![Top delay drivers](visuals/top_delay_drivers.png)

Source: `models/metrics.json` -> `top_30_features`

## Infographic

### AI vs Non-AI Capability Infographic
![AI vs non-AI infographic](visuals/ai_vs_non_ai_infographic.png)

Notes:
- AI scores include real model-backed performance dimensions plus product capability dimensions.
- Non-AI mock values are qualitative reference values for product communication.

## Flowcharts

### A) Real AI Model Pipeline
```mermaid
flowchart LR
    A[Trip Input\nsource, destination, cargo, weather, traffic] --> B[Feature Engineering\n24 features]
    B --> C[Production LightGBM\nInference]
    C --> D[Delay Probability + Risk]
    D --> E[Route Scoring\nprimary + alternatives]
    E --> F[Reroute Recommendation\nconfidence + urgency]
    F --> G[Dashboard + Alerts + Tracking]
```

### B) Non-AI Mock Application Pipeline
```mermaid
flowchart LR
    A[User Inputs Form Data] --> B[Static Rules / Fixed Weights]
    B --> C[Predefined Route Cards]
    C --> D[Deterministic ETA + Delay Label]
    D --> E[UI Rendering Only]
```

### C) Side-by-Side Decision Logic
```mermaid
flowchart TD
    subgraph Real_AI
        R1[Realtime features] --> R2[ML probability]
        R2 --> R3[Alternative route ranking]
        R3 --> R4[Adaptive reroute]
    end

    subgraph Non_AI_Mock
        M1[Manual fields] --> M2[Hardcoded thresholds]
        M2 --> M3[Single fixed output pattern]
        M3 --> M4[No learning or adaptation]
    end
```

## Regenerate Visuals

Run:

```powershell
Set-Location c:/Users/Bruger/embedded-tms-ai
C:/Users/Bruger/AppData/Local/Programs/Python/Python314/python.exe scripts/generate_model_visuals.py
```
