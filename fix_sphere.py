import json, math, copy

PUBLIC = 'emotion-sphere-ui/public/emotion_sphere_layout.json'
ROOT   = 'emotion_sphere_layout.json'
DIST   = 'emotion-sphere-ui/dist/emotion_sphere_layout.json'

ZH_MAP = {
    'desire':'渴望','longing':'思念','reminiscence':'怀念','yearning':'向往',
    'anticipation':'期待','craving':'强烈渴求','joy':'喜乐','happiness':'快乐',
    'pleasure':'愉悦','gladness':'高兴','bliss':'极乐','gratitude':'感恩',
    'thankfulness':'感谢','hope':'盼望','optimism':'乐观','eagerness':'热切',
    'ardor':'热情','fervor':'激情','exuberance':'活力','excitement':'兴奋',
    'exhilaration':'振奋','rapture':'陶醉','fascination':'着迷','infatuation':'迷恋',
    'fondness':'喜爱','affection':'情感','interest':'兴趣','curiosity':'好奇',
    'invigoration':'振作','encouragement':'鼓励','peace':'平静','tranquility':'宁静',
    'serenity':'安详','security':'安全感','relief':'如释重负','lightness':'轻松',
    'comfort':'安慰','enjoyment':'享受','fulfillment':'满足','satisfaction':'满意',
    'loneliness':'孤独','solitude':'独处','isolation':'隔绝','hunger':'渴求',
    'sadness':'悲伤','sorrow':'哀愁','grief':'悲痛','anguish':'极度痛苦',
    'despair':'绝望','hopelessness':'无望','loss':'失落','emptiness':'空虚',
    'regret':'后悔','remorse':'懊悔','self-condemnation':'自责','shame':'羞耻',
    'embarrassment':'尴尬','guilt':'内疚','fear':'恐惧','dread':'畏惧',
    'anxiety':'焦虑','worry':'担忧','nervousness':'紧张','panic':'恐慌',
    'anger':'愤怒','rage':'暴怒','fury':'狂怒','irritation':'烦躁',
    'impatience':'不耐烦','disgust':'厌恶','contempt':'鄙视','jealousy':'嫉妒',
    'envy':'羡慕嫉妒','compassion':'怜悯','sympathy':'同情','empathy':'共情',
    'comprehension':'豁然开朗','forgiveness':'释怀','pardon':'宽恕',
    'ambivalence':'矛盾纠结','confusion':'迷茫','uncertainty':'不确定',
    'doubt':'怀疑','defensiveness':'防御','alienation':'疏离',
}

NEED = set(ZH_MAP.keys())  # 87 emotions

with open(PUBLIC) as f:
    data = json.load(f)

# Step 1: deduplicate — keep first occurrence of each short_en
seen = {}
deduped = []
for node in data:
    k = node['short_en']
    if k not in seen:
        seen[k] = True
        deduped.append(node)

# Step 2: keep only the 87 needed
filtered = [n for n in deduped if n['short_en'] in NEED]

# Step 3: fix zh_labels
for n in filtered:
    n['zh_label'] = ZH_MAP[n['short_en']]

# Step 4: find missing
have = {n['short_en'] for n in filtered}
missing = NEED - have
print('Still missing after filter:', sorted(missing))

# Step 5: generate Fibonacci coords for ALL generated nodes, replacing bad coords
# Collect indices of generated nodes in filtered
gen_indices = [i for i, n in enumerate(filtered) if n.get('layer') == 'generated']
# Also need to add missing nodes — assign them generated slots too
# Total generated slots = len(gen_indices) + len(missing)
# Redistribute all generated nodes + missing with Fibonacci
total_gen = len(gen_indices) + len(missing)
golden = (1 + math.sqrt(5)) / 2

def fib_point(i, total, offset=0):
    theta = math.acos(1 - 2*(i+0.5)/total)
    phi   = 2 * math.pi * i / golden
    x = math.sin(theta) * math.cos(phi)
    y = math.cos(theta)
    z = math.sin(theta) * math.sin(phi)
    return round(x,8), round(y,8), round(z,8)

# Reassign existing generated nodes
for slot, idx in enumerate(gen_indices):
    x, y, z = fib_point(slot, total_gen)
    filtered[idx]['x'] = x
    filtered[idx]['y'] = y
    filtered[idx]['z'] = z

# Add missing nodes
for slot, key in enumerate(sorted(missing), start=len(gen_indices)):
    x, y, z = fib_point(slot, total_gen)
    filtered.append({
        'feature_key': f'generated:{key}',
        'feature_id': key,
        'layer': 'generated',
        'model_id': 'generated',
        'source_keyword': 'emotion',
        'explanation': ZH_MAP[key],
        'x': x, 'y': y, 'z': z,
        'nearest_neighbors': [],
        'zh_label': ZH_MAP[key],
        'short_en': key,
    })

print(f'Final count: {len(filtered)}')
# Verify no duplicates
from collections import Counter
dup = {k:v for k,v in Counter(n['short_en'] for n in filtered).items() if v>1}
print('Remaining duplicates:', dup)

# Check coordinate overlaps
coords = [(round(n['x'],4), round(n['y'],4), round(n['z'],4)) for n in filtered]
coord_dup = {c:v for c,v in Counter(coords).items() if v>1}
print('Coordinate overlaps:', coord_dup)

out = json.dumps(filtered, ensure_ascii=False, indent=2)
for path in [PUBLIC, ROOT, DIST]:
    with open(path, 'w') as f:
        f.write(out)
    print(f'Written: {path}')
print('Done.')
