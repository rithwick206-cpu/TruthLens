# TruthLens Test Voice Samples

These voice audio files are pre-formatted (16 kHz mono WAV) ready to be tested directly inside the TruthLens UI at http://localhost:3000.

| File Name | Audio Profile | Recommended Viral Claim Text | Expected Detection Result |
| :--- | :--- | :--- | :--- |
| `1_authentic_speech_sample.wav` | Human Vocal Tract Resonances (Natural F0, F1, F2 Formants) | *"Standard field team status report on quarterly operational targets."* | **Low Manipulation Indicator (Authentic)** |
| `2_deepfake_synthetic_clone.wav` | Neural Cloned Voice (Vocoder harmonic artifacts, phase shifts) | *"BREAKING: Leaked emergency decree from governor ordering public transit shutdown."* | **High Manipulation Indicator (Deepfake Voice ~99.9%)** |
| `3_spliced_discontinuity_voice.wav` | Digital Splice / Acoustic Cut (Mid-clip frequency boundary discontinuity) | *"Executive testimony regarding forensic financial audit results."* | **Acoustic Discontinuity / Segment Anomaly Flagged** |
| `4_press_speech_sample.wav` | Live Press Address (Acoustic room reverberation) | *"Official press spokesperson delivering introductory conference address."* | **Consistent Acoustic Profile** |
| `5_suspect_voicenote_sample.wav` | Encrypted Chat Voice Note (Bandpass compressed) | *"Private voice memo discussing logistics schedule."* | **Heuristic Analysis with Codec Limitation Disclaimer** |

### Cross-Modal Contradiction Test Scenario
To test **Gemini 2.5 Flash's Cross-Modal Contradiction Detector**:
1. Upload `1_authentic_speech_sample.wav` or `4_press_speech_sample.wav`.
2. In the Claim Text area, paste a completely fabricated claim:
   > *"URGENT: Executive admits to $50M embezzlement and announces immediate liquidation of company assets!"*
3. TruthLens will transcribe the audio, detect the semantic mismatch, and flag:
   - **Cross-Modal Status**: `CONTRADICTORY` / `UNSUPPORTED`
   - **Contradiction Alert**: Specific explanation of why the viral claim falsifies the actual spoken audio.
