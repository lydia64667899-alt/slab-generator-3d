from pymatgen.core import Structure
from pymatgen.core.surface import SlabGenerator

# ==========================================
# 讀取 Bulk POSCAR
# ==========================================

print("=" * 45)
print("         Slab Generator")
print("=" * 45)

try:
    structure = Structure.from_file("POSCAR")
    print("✓ 成功讀取 POSCAR")
except Exception as e:
    print("✗ 無法讀取 POSCAR")
    print(e)
    exit()

# ==========================================
# 輸入 Miller Index
# ==========================================

print("\n請輸入 Miller Index")

h = int(input("h = "))
k = int(input("k = "))
l = int(input("l = "))

if h == 0 and k == 0 and l == 0:
    print("Miller Index 不可以是 (0,0,0)")
    exit()

miller = (h, k, l)

# ==========================================
# Slab 厚度
# ==========================================

slab_size = float(input("\n請輸入 Slab 厚度 (Å)："))

# ==========================================
# Vacuum 厚度
# ==========================================

vacuum_size = float(input("請輸入 Vacuum 厚度 (Å)："))

# ==========================================
# 建立 Slab Generator
# ==========================================

generator = SlabGenerator(
    initial_structure=structure,
    miller_index=miller,
    min_slab_size=slab_size,
    min_vacuum_size=vacuum_size,
    center_slab=True
)

slabs = generator.get_slabs()

if len(slabs) == 0:
    print("找不到符合條件的 Slab")
    exit()

print(f"\n找到 {len(slabs)} 個 Slab")

# ==========================================
# 第一個 Slab
# ==========================================

slab = slabs[0]

# ==========================================
# 檔名
# ==========================================

filename = f"POSCAR_{h}{k}{l}"

# ==========================================
# 輸出 POSCAR
# ==========================================

slab.to(fmt="poscar", filename=filename)

# ==========================================
# 顯示資訊
# ==========================================

print("\n" + "=" * 45)
print("Slab 建立成功！")
print("=" * 45)

print(f"Miller Index  : {miller}")
print(f"Slab 厚度     : {slab_size} Å")
print(f"Vacuum 厚度   : {vacuum_size} Å")
print(f"原子數        : {len(slab)}")
print(f"輸出檔案      : {filename}")

print("=" * 45)
generate_slab(
    bulk_file,
    h,
    k,
    l,
    thickness,
    vacuum
)