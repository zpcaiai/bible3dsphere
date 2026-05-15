import json
import math
from pathlib import Path

JSON_FILE = Path("emotion_sphere_layout.json")

def fibonacci_sphere(samples=1):
    points = []
    if samples <= 1:
        return [(0, 1, 0)]
    
    phi = math.pi * (3. - math.sqrt(5.))  # golden angle in radians

    for i in range(samples):
        y = 1 - (i / float(samples - 1)) * 2  # y goes from 1 to -1
        radius = math.sqrt(1 - y * y)  # radius at y

        theta = phi * i  # golden angle increment

        x = math.cos(theta) * radius
        z = math.sin(theta) * radius

        points.append((x, y, z))

    return points

def main():
    if not JSON_FILE.exists():
        print("Layout file not found")
        return
    
    data = json.loads(JSON_FILE.read_text(encoding='utf-8'))
    count = len(data)
    print(f"Distributing {count} items uniformly...")

    points = fibonacci_sphere(count)

    for i, item in enumerate(data):
        x, y, z = points[i]
        item["x"] = float(x)
        item["y"] = float(y)
        item["z"] = float(z)

    JSON_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"Updated {count} items with uniform Fibonacci distribution.")

if __name__ == "__main__":
    main()
