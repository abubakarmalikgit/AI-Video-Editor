import sys, subprocess, shutil, json, importlib, os

ROOT = os.path.dirname(os.path.abspath(__file__))
os.environ["PATH"] = os.path.join(ROOT, "tools", "ffmpeg", "bin") + os.pathsep + os.environ["PATH"]
critical_fail = False
report = {}

def tag(ok, critical=True):
    return "[ OK ]" if ok else ("[FAIL]" if critical else "[WARN]")

def check(name, ok, detail="", critical=True):
    global critical_fail
    print(f"{tag(ok, critical)} {name} {detail}")
    if not ok and critical:
        critical_fail = True

def run(cmd, timeout=60):
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout + r.stderr
    except Exception as e:
        return 1, str(e)

v = sys.version_info
check("Python", (3, 10) <= v[:2] <= (3, 12), f"{v.major}.{v.minor}.{v.micro}")

for mod, pip_name in {"webview": "pywebview", "faster_whisper": "faster-whisper", "psutil": "psutil"}.items():
    try:
        importlib.import_module(mod)
        check(f"Package {pip_name}", True)
    except Exception as e:
        check(f"Package {pip_name}", False, str(e)[:80])

ff, fp = shutil.which("ffmpeg"), shutil.which("ffprobe")
check("ffmpeg", bool(ff), ff or "not found")
check("ffprobe", bool(fp), fp or "not found")

try:
    import winreg
    found = False
    guid = r"Software\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}"
    for hive, sub in [(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node" + guid[8:]),
                      (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE" + guid[8:]),
                      (winreg.HKEY_CURRENT_USER, guid)]:
        try:
            winreg.CloseKey(winreg.OpenKey(hive, sub)); found = True; break
        except OSError:
            pass
    check("Edge WebView2", found, "" if found else "missing (the app window may not open)", critical=False)
except Exception:
    pass

encoder = "libx264"
if ff:
    for enc in ["h264_nvenc", "h264_qsv", "h264_amf"]:
        code, _ = run([ff, "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=256x256:d=0.2",
                       "-c:v", enc, "-f", "null", "-"])
        if code == 0:
            encoder = enc
            break
    print(f"[ OK ] Video encoder: {encoder}" + (" (CPU, no working GPU encoder found)" if encoder == "libx264" else ""))
report["video_encoder"] = encoder

cuda = False
try:
    import ctranslate2
    cuda = ctranslate2.get_cuda_device_count() > 0
except Exception:
    pass
print(f"{tag(True)} Whisper device: {'GPU (CUDA)' if cuda else 'CPU'}")

ram = 8
try:
    import psutil
    ram = psutil.virtual_memory().total / 1024**3
    free = shutil.disk_usage(ROOT).free / 1024**3
    check("RAM", ram >= 7, f"{ram:.1f} GB", critical=False)
    check("Free disk space", free >= 10, f"{free:.1f} GB", critical=False)
except Exception:
    pass

report["whisper_device"] = "cuda" if cuda else "cpu"
report["whisper_compute_type"] = "float16" if cuda else "int8"
report["whisper_model"] = "medium" if cuda else ("small" if ram >= 12 else "base")
print(f"{tag(True)} Whisper model: {report['whisper_model']} ({report['whisper_compute_type']})")

with open(os.path.join(ROOT, "system_report.json"), "w") as f:
    json.dump(report, f, indent=2)

print()
print("RESULT:", "PROBLEMS FOUND" if critical_fail else "ALL CRITICAL CHECKS PASSED")
sys.exit(1 if critical_fail else 0)
