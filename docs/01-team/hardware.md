# Hardware

Each member: fill in RAM / VRAM / storage. Specs marked `(assumption)` are typical for the model, not checked.

## Laptops
| Member | Laptop | CPU / GPU | ML backend | Notes |
|---|---|---|---|---|
| Bhavyam | Lenovo LOQ | NVIDIA RTX 2050 (4 GB VRAM, assumption) | CUDA (PyTorch, TF) | Small-model training, fine-tuning with small batches |
| Abhijay | HP Omen | NVIDIA RTX 3050 (4–6 GB VRAM, assumption) | CUDA (PyTorch, TF) | Strongest GPU on the team → main training machine |
| Gunagye | Lenovo Yoga | Intel Core Ultra 7 155H, Intel Arc iGPU, NPU | CPU, Intel XPU / OpenVINO | Good for inference, data processing, backend/frontend |
| Shefali | MacBook Air M4 | Apple M4 (unified memory) | MPS (PyTorch), Core ML / MLX | Fanless: long training runs throttle; good for inference, iOS builds |

RAM: Bhavyam _?_ · Abhijay _?_ · Gunagye _?_ · Shefali _?_

## Phones / tablets
| Member | Devices | Useful for |
|---|---|---|
| Shefali | iPhone, iPad | iOS testing, on-device (Core ML) demos, larger-screen demo |
| Gunagye | iPhone | iOS testing |
| Bhavyam | Android phone | Android testing, `adb` |
| Abhijay | Android phone | Android testing, `adb` |

## What this means for the split (draft)
- **Training / heavy ML:** Abhijay (RTX 3050), then Bhavyam (RTX 2050). Both CUDA, so one shared training script runs on both.
- **Data prep, backend, integration:** Gunagye (many CPU cores, Arc for inference).
- **Frontend / iOS / demo polish:** Shefali (M4, only Mac → only one who can build iOS apps).
- **Cross-platform test:** 2 iOS + 2 Android phones + 1 iPad.
- 4–6 GB VRAM caps us at small models or quantised/LoRA fine-tuning; plan for that or use free cloud GPUs (Colab/Kaggle).

Final split lives in `../06-plan/work-split.md`.
