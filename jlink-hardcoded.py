import subprocess
import struct
import shutil
import os

JLINK_PATH = r"C:\Program Files\SEGGER\JLink_V812d\JLink.exe"
WORKDIR = r"C:\Users\Admin\Downloads"
DEVICE = "STM32F103CB"
INTERFACE = "SWD"
SPEED = "4000"
SERIAL = '26354/00040000'
KM = 0

def make_jlink_script(uid_hex):
    script_path = os.path.join(WORKDIR, "flash.jlink")
    with open(script_path, "w") as f:
        f.write(f"""device {DEVICE}
if {INTERFACE}
speed {SPEED}
r
loadbin {os.path.join(WORKDIR, "boot.bin").replace("\\", "/")}, 0x08000000
loadbin {os.path.join(WORKDIR, "DRV223.bin").replace("\\", "/")}, 0x08001000
loadbin {os.path.join(WORKDIR, "data_temp.bin").replace("\\", "/")}, 0x0800F800
r
g
q
""")
    return script_path

def get_uid():
    preflash_script = os.path.join(WORKDIR, "preflash.jlink")
    with open(preflash_script, "w") as f:
        f.write(f"""device {DEVICE}
if {INTERFACE}
speed {SPEED}
r
erase
loadbin {os.path.join(WORKDIR, "boot.bin").replace("\\", "/")}, 0x08000000
r
q
""")

    subprocess.run([JLINK_PATH, "-CommanderScript", preflash_script])

    uid_script = os.path.join(WORKDIR, "readuid.jlink")
    with open(uid_script, "w") as f:
        f.write(f"""device {DEVICE}
if {INTERFACE}
speed {SPEED}
r
mem32 0x1FFFF7E8, 3
q
""")

    result = subprocess.run([JLINK_PATH, "-CommanderScript", uid_script], capture_output=True, text=True)

    print(result.stdout)

    uid = []
    for line in result.stdout.splitlines():
        if "1FFFF7E8 =" in line:
            parts = line.split("=")[1].strip().split()
            uid = [int(p, 16) for p in parts]
            break

    if len(uid) != 3:
        raise RuntimeError("Something went wrong, check J-Link output")

    print(f"UID: {uid}")
    return uid


def patch_data(uid):
    src = os.path.join(WORKDIR, "data.bin")
    dst = os.path.join(WORKDIR, "data_temp.bin")
    shutil.copy(src, dst)

    with open(dst, "r+b") as f:
        f.seek(0x20)
        f.write(SERIAL.encode('ascii'))

        f.seek(0x1B4)
        f.write(struct.pack('<I', uid[0]))
        f.seek(0x1B8)
        f.write(struct.pack('<I', uid[1]))
        f.seek(0x1BC)
        f.write(struct.pack('<I', uid[2]))

        f.seek(0x52)
        f.write(struct.pack('<I', KM * 1000))


def flash_all():
    uid = get_uid()
    patch_data(uid)
    script_path = make_jlink_script(uid)
    subprocess.run([JLINK_PATH, "-CommanderScript", script_path])

if __name__ == "__main__":
    flash_all()