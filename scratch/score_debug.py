
from pathlib import Path

def score_file(path):
    data = path.read_bytes()
    # Simple RLE-like score: reward long runs of identical bytes
    score = 0
    prev = None
    for b in data:
        if b == prev:
            score += 1
        prev = b
    return score

print("Scores (higher is more structured):")
for p in sorted(Path('debug_output').glob('*.png')):
    print(f"{p.name}: {score_file(p)}")
