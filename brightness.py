# brightness.py
import os
import glob
import time
import threading
import subprocess

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
BRIGHT_BIN = os.path.join(BASE_PATH, 'anbernic-bright')

MAX_LEVEL = 7
SYSFS_LEVELS = [5, 15, 30, 50, 70, 90, 110, 140]

# ==================== 机型识别接口 ====================
DEVICE_MODEL_FILE = "/mnt/vendor/oem/board.ini"

# 机型字符串 → 亮度后端
# "bin"   : 调用 anbernic-bright（H700 机型）
# "sysfs" : 直接写 /sys/class/backlight/*/brightness（RK3568 机型）
MODEL_BACKEND_MAP = {
    'RGCUBEXX':  'bin',
    'RG34XX':    'bin',
    'RG34XXSP':  'bin',
    'RGSP':      'bin',
    'RG28XX':    'bin',
    'RG35XX+_P': 'bin',
    'RG35XXH':   'bin',
    'RG35XXSP':  'bin',
    'RG40XXH':   'bin',
    'RG40XXV':   'bin',
    'RG35XXPRO': 'bin',
    'RGDS':      'sysfs',
    'RGDSPLUS':  'sysfs'
}


def detect_device_model():
    """读取系统文件，返回机型字符串（大写）。失败返回 None。"""
    try:
        if os.path.exists(DEVICE_MODEL_FILE):
            content = open(DEVICE_MODEL_FILE, 'r', errors='ignore').read().strip()
            # 只取第一行第一段，防止文件里有其它内容
            first_line = content.splitlines()[0].strip()
            # 如果文件内容是 key=value 形式，尝试取值
            if '=' in first_line:
                first_line = first_line.split('=', 1)[1].strip()
            return first_line.upper() if first_line else None
    except Exception as e:
        print(f"[Brightness] detect_device_model failed: {e}")
    return None


# ==================== 控制器 ====================
class BrightnessController:
    def __init__(self):
        self._lock = threading.RLock()
        self._orig = None       # 调暗前的原始等级
        self._restored = True   # True = 当前是亮态
        self._backend = None
        self._model = None

        self._model = detect_device_model()
        self._backend = self._pick_backend()

        print(f"[Brightness] model={self._model}, backend={self._backend}")

    # ---------- 后端选择 ----------
    def _pick_backend(self):
        # 1) 优先按机型映射
        if self._model and self._model in MODEL_BACKEND_MAP:
            preferred = MODEL_BACKEND_MAP[self._model]
            if preferred == 'bin' and not self._bin_available():
                print("[Brightness] bin backend not available, fallback to sysfs")
            elif preferred == 'sysfs' and not self._sysfs_available():
                print("[Brightness] sysfs backend not available, fallback to bin")
            else:
                return preferred

        # 2) 自动探测：有 anbernic-bright 就用它
        if self._bin_available():
            return 'bin'
        if self._sysfs_available():
            return 'sysfs'
        return 'null'

    def _bin_available(self):
        return os.path.isfile(BRIGHT_BIN) and os.access(BRIGHT_BIN, os.X_OK)

    def _sysfs_available(self):
        return bool(glob.glob('/sys/class/backlight/*/brightness'))

    # ---------- 读写 ----------
    def get_level(self):
        with self._lock:
            if self._backend == 'bin':
                try:
                    r = subprocess.run(
                        [BRIGHT_BIN, 'get'],
                        capture_output=True, text=True, timeout=2
                    )
                    return max(0, min(MAX_LEVEL, int(r.stdout.strip())))
                except Exception as e:
                    print(f"[Brightness] bin get failed: {e}")
                    return MAX_LEVEL

            if self._backend == 'sysfs':
                # 上屏优先，读不到再试下屏
                devices = glob.glob('/sys/class/backlight/*/brightness')
                for dev in reversed(devices):
                    try:
                        with open(dev, 'r') as f:
                            cur = int(f.read().strip())
                        return min(
                            range(len(SYSFS_LEVELS)),
                            key=lambda i: abs(SYSFS_LEVELS[i] - cur)
                        )
                    except Exception:
                        continue
                return MAX_LEVEL

            return MAX_LEVEL

    def set_level(self, level):
        level = max(0, min(MAX_LEVEL, int(level)))
        with self._lock:
            if self._backend == 'bin':
                try:
                    subprocess.run(
                        [BRIGHT_BIN, str(level)],
                        capture_output=True, timeout=2
                    )
                except Exception as e:
                    print(f"[Brightness] bin set {level} failed: {e}")

            elif self._backend == 'sysfs':
                for dev in glob.glob('/sys/class/backlight/*/brightness'):
                    try:
                        with open(dev, 'w') as f:
                            f.write(str(SYSFS_LEVELS[level]))
                    except Exception as e:
                        print(f"[Brightness] sysfs write {dev} failed: {e}")

            # null backend 直接忽略

    # ---------- 调暗 / 恢复 ----------
    @property
    def is_restored(self):
        with self._lock:
            return self._restored

    def begin_dim(self):
        """记录当前亮度作为原始亮度，并切换到"暗态"。返回原始等级。"""
        with self._lock:
            orig = self.get_level()
            if orig < 0 or orig > MAX_LEVEL:
                orig = MAX_LEVEL
            self._orig = orig
            self._restored = False
            return orig

    def restore_if_needed(self):
        """如果当前是暗态，恢复原始亮度。返回是否真的恢复了。"""
        with self._lock:
            if self._orig is None or self._restored:
                return False
            self.set_level(self._orig)
            self._restored = True
            print(f"[AutoDim] 恢复亮度等级 {self._orig}")
            return True

    def restore_on_exit(self):
        """退出前无条件恢复（即使已经是亮态也不报错）。"""
        with self._lock:
            if self._orig is not None:
                try:
                    self.set_level(self._orig)
                    print(f"[AutoDim] 退出前恢复亮度 {self._orig}")
                except Exception as e:
                    print(f"[AutoDim] restore on exit failed: {e}")


# 全局单例，供 app.py 直接 import
brightness = BrightnessController()