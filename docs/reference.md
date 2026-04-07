# TTS Converter — Quick Reference

## Voice profiles

| Profile key   | Language | Gender | Model                  | Notes                        |
|---------------|----------|--------|------------------------|------------------------------|
| `zh_female`   | Chinese  | Female | fastspeech2_aishell3   | Default; clean, clear        |
| `zh_female_2` | Chinese  | Female | fastspeech2_aishell3   | Slightly different tone      |
| `zh_male`     | Chinese  | Male   | fastspeech2_aishell3   | spk_id 100                   |
| `zh_male_2`   | Chinese  | Male   | fastspeech2_aishell3   | spk_id 110, slightly deeper  |
| `en_female`   | English  | Female | fastspeech2_ljspeech   | Best English quality         |
| `en_male`     | English  | Male   | fastspeech2_vctk       | VCTK spk 0                   |
| `en_male_2`   | English  | Male   | fastspeech2_vctk       | VCTK spk 1, slightly different |

Aliases: `default` = `zh_female` | `female` = `zh_female` | `male` = `zh_male`

---

## Common commands

```bash
# Auto-detect language & voice (works for both zh and en files)
python main.py --file doc.txt --output out.wav

# Explicit English female voice
python main.py --file doc.txt --output out.wav --profile en_female

# Chinese male voice
python main.py --file doc.txt --output out.wav --profile zh_male

# Your original command, now parallel:
python main.py --file "/path/to/Zohar_...txt" --output ./zohar_1.wav --profile zh_female

# Control parallelism (default is auto: usually 3–4 on Mac)
python main.py --file doc.txt --output out.wav --profile en_female --workers 4

# Add 300 ms silence between chunks (sounds more natural for narration)
python main.py --file doc.txt --output out.wav --profile en_female --silence-ms 300

# Larger chunks = fewer API calls (faster but may clip long sentences)
python main.py --file doc.txt --output out.wav --chunk-size 300

# List all profiles
python main.py --list-profiles

# Test a profile
python main.py --test --profile en_male

# Test every profile
python main.py --test-all
```

---

## Tuning tips for speed on Mac

| Setting       | Recommendation                                                  |
|---------------|-----------------------------------------------------------------|
| `--workers`   | 3–4 on M-series; 2 on older Intel (PaddleSpeech is CPU-heavy)  |
| `--chunk-size`| 200–300; larger = fewer round-trips but harder text for model   |
| `--silence-ms`| 0 for speed; 200–400 for more natural narration pauses          |

## Finding a better male English voice

VCTK has 109 speakers. Try spk_ids 0–10 to find one you like.
You can add more profiles directly in `src/tts_engine.py` under `VOICE_PROFILES`:

```python
"en_male_3": {
    "lang": "en",
    "am": "fastspeech2_vctk",
    "voc": "hifigan_vctk",
    "spk_id": 5,          # experiment with 0-108
    "description": "English male VCTK spk 5",
},
```