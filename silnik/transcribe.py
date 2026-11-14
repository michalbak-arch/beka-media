import sys, json
from faster_whisper import WhisperModel
model_dir, audio, out = sys.argv[1], sys.argv[2], sys.argv[3]
m = WhisperModel(model_dir, device="cpu", compute_type="int8")
import numpy as np
audio_arr = np.fromfile(audio, dtype=np.float32)
segs, info = m.transcribe(audio_arr, language="pl", word_timestamps=True, beam_size=5)
words = []
for s in segs:
    for w in s.words:
        words.append([w.word.strip(), round(w.start, 3), round(w.end, 3)])
json.dump(words, open(out, "w"), ensure_ascii=False, indent=0)
print(len(words), "words")
