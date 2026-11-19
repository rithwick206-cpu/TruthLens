# TruthLens: Multimodal Digital Forensics & Deepfake Detection Suite

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-16.4.6-black.svg?style=flat&logo=next.js&logoColor=white)](https://nextjs.org)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.2+-EE4C2C.svg?style=flat&logo=pytorch&logoColor=white)](https://pytorch.org)
[![Accuracy](https://img.shields.io/badge/Model_Accuracy-97.64%25-brightgreen.svg?style=flat)]()
[![ROC-AUC](https://img.shields.io/badge/ROC--AUC-0.9974-blue.svg?style=flat)]()
[![Tests](https://img.shields.io/badge/Pytest-21%2F21_Passed-emerald.svg?style=flat)]()
[![License](https://img.shields.io/badge/License-MIT-purple.svg?style=flat)]()

**TruthLens** is an end-to-end multimodal digital forensics and deepfake detection platform. Engineered for investigative journalists, legal forensic examiners, and threat intelligence units, TruthLens decomposes visual media, video reels, acoustic speech notes, and viral contextual claims to expose digital manipulation with cryptographic traceability and Explainable AI (XAI).

---

## Key Forensic Capabilities

* **Visual Forensics**: Custom-trained EfficientNet-B0 with Grad-CAM neural attention heatmaps, Error Level Analysis (ELA) at 95% JPEG quality, and complete EXIF metadata provenance extraction.
* **Video Reel Forensics**: Dynamic ~1 FPS temporal keyframing, per-second anomaly score curves, and automated audio-video stream demuxing for dual-track analysis.
* **Acoustic & Voice Forensics**: Wav2Vec2 transformer embeddings, vocoder harmonic discontinuity detection, spectral flatness, zero-crossing rate analysis, and Groq Whisper Large-v3 ASR transcription.
* **Cross-Modal Semantic Correlation**: Google Gemini 2.5 Flash cross-examines audio transcripts and visual landmarks against purported viral claims to catch context-swapped disinformation, backed by a deterministic signal correlator fallback.
* **Cryptographic Chain of Custody**: Immediate deterministic SHA-256 evidence hashing at ingestion; untouched preservation in `backend/storage/originals/`.
* **Human Investigator Audit Station**: Four legal forensic determinations with sworn examiner audit notes and instant **Court-Ready PDF Generation** (ReportLab).
* **Power-User Workbench**: Global Command Palette (`⌘K`), keyboard shortcuts (`N`, `M`, `1-3`, `E`), risk filter triage, and 1-click evidentiary brief clipboard export.

---

## Machine Learning Architecture & Benchmarks

TruthLens rejects toy classifiers and black-box overconfidence. Its core image detector was custom-trained from scratch on a balanced multimodal deepfake dataset:

| Metric | Measured Benchmark Value | Evaluation Context |
| :--- | :--- | :--- |
| **Architecture** | Custom EfficientNet-B0 | Squeeze-and-Excitation convolutional backbone |
| **Training Dataset** | **140,002 images** | 70,001 authentic + 70,001 synthetic |
| **Validation Accuracy** | **97.64%** | Evaluated on holdout validation split |
| **ROC-AUC** | **0.9974** | Area under Receiver Operating Characteristic |
| **Platt Temperature Scaling** | **$T = 1.065$** | Calibrates raw logits into statistically honest probabilities |
| **Speech Model** | Wav2Vec2-XLSR | Neural vocoder and audio splice detection |
| **ASR Engine** | Groq Whisper Large-v3 | Sub-second high-accuracy acoustic transcription |

---

## System Architecture

```
                          ┌──────────────────────────────────────┐
                          │   Digital Evidence Ingestion        │
                          │   (Image / Video Reel / Audio / Text)│
                          └──────────────────┬───────────────────┘
                                             │
                       ┌─────────────────────┴─────────────────────┐
                       │  Deterministic SHA-256 Cryptographic Hash │
                       │  Immutable Storage: storage/originals/   │
                       └─────────────────────┬─────────────────────┘
                                             │
      ┌──────────────────────┬───────────────┴───────────────┬──────────────────────┐
      │                      │                               │                      │
┌─────▼──────────────┐ ┌─────▼──────────────┐ ┌──────────────▼────────┐ ┌───────────▼──────────┐
│  Image Forensics   │ │   Video Forensics  │ │   Audio Forensics     │ │  Context / Claim NLP │
├────────────────────┤ ├────────────────────┤ ├───────────────────────┤ ├──────────────────────┤
│ • EfficientNet-B0  │ │ • Keyframing (~1fps)│ │ • Wav2Vec2 Embeddings │ │ • Viral Disinfo Cues │
│ • Grad-CAM Heatmap │ │ • Temporal Spline  │ │ • Vocoder Harmonics   │ │ • Whisper ASR Sync   │
│ • ELA (95% Quality)│ │ • Audio Demuxing   │ │ • Spectral Flatness   │ │ • Sensation Analysis │
└─────┬──────────────┘ └─────┬──────────────┘ └──────────────┬────────┘ └───────────┬──────────┘
      │                      │                               │                      │
      └──────────────────────┼───────────────────────────────┴──────────────────────┘
                             │
            ┌────────────────▼────────────────┐
            │   Cross-Modal Forensic Engine   │
            │   (Gemini 2.5 Flash + Fallback) │
            │   • Coherence & Semantic Check  │
            │   • Ensemble Platt Scaling (T)  │
            └────────────────┬────────────────┘
                             │
            ┌────────────────▼────────────────┐
            │   Human Investigator Station    │
            │   • Sworn Audit Determination   │
            │   • Court-Ready PDF Generator   │
            └─────────────────────────────────┘
```

---

## Technology Stack

| Layer | Technologies Used |
| :--- | :--- |
| **Frontend** | Next.js 16.4.6, React 19, TypeScript, Tailwind CSS v4, Lucide Icons, Canvas API |
| **Backend API** | Python 3.9+, FastAPI, Uvicorn, SQLite3, Pydantic v2 |
| **Machine Learning** | PyTorch, torchvision, HuggingFace Transformers, Torchaudio |
| **Signal Forensics** | OpenCV (`cv2`), Pillow (PIL), Librosa, SoundFile, NumPy, SciPy |
| **AI & LLM** | Google Gemini 2.5 Flash (`google-genai`), Groq Whisper API |
| **Report Generation** | ReportLab PDF Engine (cryptographic stamps, Grad-CAM plates) |
| **Testing** | Pytest, Pytest-AnyIO (21 / 21 automated tests passing) |

---

## Getting Started

### Prerequisites
* Python 3.9, 3.10, or 3.11
* Node.js 18+ and npm
* ffmpeg installed (`brew install ffmpeg` on macOS, `sudo apt install ffmpeg` on Ubuntu)

### 1. Clone the Repository
```bash
git clone https://github.com/your-username/truthlens.git
cd truthlens
```

### 2. Backend Setup
```bash
# Create and activate virtual environment
python3 -m venv backend/venv
source backend/venv/bin/activate

# Install dependencies
pip install -r backend/requirements.txt

# (Optional) Export Gemini API key for cross-modal VQA (fallback runs deterministically without key)
export GEMINI_API_KEY="your-gemini-api-key"

# Launch FastAPI backend server
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
The backend API documentation is accessible at `http://127.0.0.1:8000/docs`.

### 3. Frontend Setup
In a new terminal window:
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:3000` in your browser.

---

## Automated Test Verification

TruthLens maintains a strict automated test suite verifying every layer from SHA-256 ingestion to PDF report generation:

```bash
backend/venv/bin/pytest backend/tests/ -v
```

```text
backend/tests/test_phase1.py::test_health_endpoint PASSED                [  4%]
backend/tests/test_phase1.py::test_ingest_image_and_caption PASSED       [  9%]
backend/tests/test_phase1.py::test_get_case_record PASSED                [ 14%]
backend/tests/test_phase1.py::test_reject_empty_request PASSED           [ 19%]
backend/tests/test_phase1.py::test_case_not_found PASSED                 [ 23%]
backend/tests/test_phase2.py::test_analyze_case_end_to_end PASSED        [ 28%]
backend/tests/test_phase2.py::test_analyze_nonexistent_case PASSED       [ 33%]
backend/tests/test_phase2.py::test_multipart_file_upload_runs_custom_model_and_artifacts PASSED [ 38%]
backend/tests/test_phase3.py::test_analyze_audio_end_to_end PASSED       [ 42%]
backend/tests/test_phase3.py::test_analyze_video_end_to_end PASSED       [ 47%]
backend/tests/test_phase3.py::test_analyze_multimodal_bundle PASSED      [ 52%]
backend/tests/test_phase4.py::test_correlator_deterministic_fallback_without_key PASSED [ 57%]
backend/tests/test_phase4.py::test_correlator_contradictory_signals PASSED [ 61%]
backend/tests/test_phase4.py::test_correlator_mocked_gemini_vqa_mismatch PASSED [ 66%]
backend/tests/test_phase4.py::test_correlator_gemini_error_graceful_fallback PASSED [ 71%]
backend/tests/test_phase4.py::test_analyze_caption_only_case PASSED      [ 76%]
backend/tests/test_phase5.py::test_review_audit_sync PASSED              [ 80%]
backend/tests/test_phase5.py::test_pdf_report_generation PASSED          [ 85%]
backend/tests/test_phase5.py::test_model_metrics_endpoint PASSED         [ 90%]
backend/tests/test_phase5.py::test_demo_samples_and_loaders PASSED       [ 95%]
backend/tests/test_phase5.py::test_unknown_demo_sample_404 PASSED        [100%]
======================= 21 passed in 12.59s =======================
```

---

## Pre-Built Demo Presets

TruthLens includes 7 pre-packaged forensic demonstration cases ready for immediate evaluation:

1. 🟢 **Authentic DSLR Photo**: Clean Canon EOS metadata with reinforcing context.
2. 🔴 **Multimodal Fake**: AI facial composite paired with cloned voice and fake emergency order.
3. 🟡 **Compressed Social Media Photo**: WhatsApp downsampled real photo with stripped EXIF.
4. 🔴 **CEO Voice Clone Scam**: Urgent wire transfer authorization with neural vocoder harmonics.
5. 🟣 **Spliced Audio Testimony**: Stitched court deposition featuring mid-sentence phase jumps.
6. 🔴 **Banking Robocall Scam**: Cellular bandpass (300Hz-3400Hz) automated voice attack.
7. 🟢 **Clean Broadcast Speech**: Pristine studio address with natural vocal formants.

---

## Forensic Integrity & Legal Humility

TruthLens adheres to modern legal standards for digital evidence:
1. **Probabilistic Outputs**: The system outputs calibrated likelihoods rather than claiming binary 100% certainty.
2. **Alternative Explanations**: Automatically notes benign causes of anomalies (e.g. social messaging compression, microphone noise gating, motion blur).
3. **Mandatory Human Sign-Off**: Automated outputs serve as decision-support; reports require a human investigator's sworn audit determination before export.

---

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
