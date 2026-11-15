import os, urllib.request

BASE = "https://cdn.jsdelivr.net/fontsource/fonts/"
FONTS = {
    "inter-400.woff2": "inter@latest/latin-400-normal.woff2",
    "inter-500.woff2": "inter@latest/latin-500-normal.woff2",
    "inter-600.woff2": "inter@latest/latin-600-normal.woff2",
    "sora-600.woff2": "sora@latest/latin-600-normal.woff2",
    "sora-700.woff2": "sora@latest/latin-700-normal.woff2",
    "jbmono-400.woff2": "jetbrains-mono@latest/latin-400-normal.woff2",
}
folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web", "fonts")
os.makedirs(folder, exist_ok=True)
for name, path in FONTS.items():
    dest = os.path.join(folder, name)
    if os.path.exists(dest) and os.path.getsize(dest) > 1000:
        continue
    try:
        urllib.request.urlretrieve(BASE + path, dest)
        print(f"     font downloaded: {name}")
    except Exception as e:
        print(f"     [WARN] could not download {name} ({e}). The app will use system fonts instead.")
