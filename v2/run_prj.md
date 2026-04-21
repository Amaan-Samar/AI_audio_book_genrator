# List available voice profiles
python main.py --list-profiles

# Convert document with male voice
python main.py --file "document.txt" --output "male_audio.wav" --profile male

# Convert document with female voice  
python main.py --file "document.txt" --output "female_audio.wav" --profile female

# Convert with specific female voice
python main.py --file "C:\Users\Amaan\Documents\github_projects\tts_project\data\subtitles\chinese_text.txt" --output "epstine.wav" --profile female

# Test all voices
python main.py --test-all

# Quick direct test
python test_voices.py



conda activate tools/venv 
----------------------

# Process an entire directory tree
python main.py --dir '/Users/Farmdar/Documents/github/tts_project/pdf_txt_extractor/output_text/' --subtitles srt vtt --profile en_male_3

# All existing modes still work exactly as before
python main.py --file doc.txt --output out.wav --subtitles srt
python main.py --text "你好世界"