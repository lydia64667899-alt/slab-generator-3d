from __future__ import annotations

import hashlib

import py3Dmol
import streamlit as st
import streamlit.components.v1 as components

from pymatgen.core import Lattice, Structure
from pymatgen.core.surface import SlabGenerator
from pymatgen.io.cif import CifWriter
from pymatgen.io.vasp import Poscar


st.set_page_config(
    page_title="Slab Generator 3D",
    page_icon="🧱",
    layout="wide",
)

st.title("🧱 Slab Generator：晶面切割與 3D 視覺化")
st.caption("Python + Streamlit + pymatgen + py3Dmol")


if "slab_cache_key" not in st.session_state:
    st.session_state.slab_cache_key = None

if "generated_slabs" not in st.session_state:
    st.session_state.generated_slabs = None

if "generation_error" not in st.session_state:
    st.session_state.generation_error = None


def load_structure(file_bytes: bytes, filename: str) -> Structure:
    """從上傳內容讀取 CIF 或 POSCAR/VASP。"""
    text = file_bytes.decode("utf-8-sig", errors="replace")
    lower_name = filename.lower()

    formats = ("cif", "poscar") if lower_name.endswith(".cif") else ("poscar", "cif")
    errors: list[str] = []

    for fmt in formats:
        try:
            structure = Structure.from_str(text, fmt=fmt)
            if len(structure) == 0:
                raise ValueError("結構中沒有原子。")
            return structure
        except Exception as exc:
            errors.append(f"{fmt}: {exc}")

    raise ValueError(
        "檔案無法解析為 CIF 或 POSCAR。\n\n" + "\n".join(errors)
    )


def make_builtin_copper() -> Structure:
    """建立面心立方 Cu 範例結構。"""
    return Structure.from_spacegroup(
        "Fm-3m",
        Lattice.cubic(3.615),
        ["Cu"],
        [[0, 0, 0]],
    )


def structure_to_cif(structure: Structure) -> str:
    """將 Structure 轉成 CIF 字串。"""
    return str(CifWriter(structure))


def structure_to_poscar(structure: Structure) -> str:
    """將 Structure 轉成標準 VASP POSCAR 字串。"""
    return Poscar(structure).get_str()


def render_3d(
    structure: Structure,
    style_name: str,
    show_unit_cell: bool,
    dark_background: bool,
) -> None:
    """使用 py3Dmol 顯示可旋轉的 3D 結構。"""
    cif_text = structure_to_cif(structure)

    viewer = py3Dmol.view(width="100%", height=560)
    viewer.addModel(cif_text, "cif")
    viewer.setBackgroundColor("#181818" if dark_background else "white")

    if style_name == "Ball and Stick":
        viewer.setStyle(
            {},
            {
                "stick": {
                    "radius": 0.14,
                    "colorscheme": "Jmol",
                },
                "sphere": {
                    "scale": 0.28,
                    "colorscheme": "Jmol",
                },
            },
        )
    elif style_name == "Spacefill":
        viewer.setStyle(
            {},
            {
                "sphere": {
                    "scale": 0.55,
                    "colorscheme": "Jmol",
                }
            },
        )
    else:
        viewer.setStyle(
            {},
            {
                "stick": {
                    "radius": 0.18,
                    "colorscheme": "Jmol",
                }
            },
        )

    if show_unit_cell:
        viewer.addUnitCell()

    viewer.zoomTo()
    viewer.render()

    components.html(
        viewer.write_html(),
        height=580,
        scrolling=False,
    )


def make_cache_key(
    source_key: str,
    miller: tuple[int, int, int],
    slab_thickness: float,
    vacuum_thickness: float,
    center_slab: bool,
    primitive: bool,
) -> tuple:
    return (
        source_key,
        miller,
        round(float(slab_thickness), 4),
        round(float(vacuum_thickness), 4),
        bool(center_slab),
        bool(primitive),
    )


with st.sidebar:
    st.header("📁 1. 載入晶體結構")

    input_mode = st.radio(
        "選擇輸入方式",
        ["上傳 CIF / POSCAR", "內建 Cu 範例"],
    )

    bulk_structure = None
    source_key = None
    source_name = None

    if input_mode == "上傳 CIF / POSCAR":
        uploaded_file = st.file_uploader(
            "上傳晶體結構檔案",
            type=["cif", "vasp", "poscar"],
            help="支援 .cif、.vasp、.poscar。",
        )

        if uploaded_file is not None:
            raw_bytes = uploaded_file.getvalue()
            source_key = hashlib.sha256(raw_bytes).hexdigest()
            source_name = uploaded_file.name

            try:
                bulk_structure = load_structure(
                    raw_bytes,
                    uploaded_file.name,
                )
                st.success(f"成功載入：{uploaded_file.name}")
            except Exception as exc:
                st.error("讀取檔案失敗")
                st.code(str(exc), language="text")
    else:
        bulk_structure = make_builtin_copper()
        source_key = "builtin-cu-fcc-3.615"
        source_name = "Cu_builtin"
        st.success("已載入內建 Cu 範例")

    st.divider()
    st.header("✂️ 2. Miller Index（密勒指數）")

    h_col, k_col, l_col = st.columns(3)

    h = int(
        h_col.number_input(
            "h",
            min_value=-9,
            max_value=9,
            value=1,
            step=1,
        )
    )
    k = int(
        k_col.number_input(
            "k",
            min_value=-9,
            max_value=9,
            value=1,
            step=1,
        )
    )
    l = int(
        l_col.number_input(
            "l",
            min_value=-9,
            max_value=9,
            value=1,
            step=1,
        )
    )

    miller_index = (h, k, l)

    st.divider()
    st.header("📐 3. Slab 幾何參數")

    slab_thickness = st.slider(
        "Slab 最小厚度（Å）",
        min_value=5.0,
        max_value=30.0,
        value=15.0,
        step=0.5,
    )

    vacuum_thickness = st.slider(
        "Vacuum 真空層厚度（Å）",
        min_value=5.0,
        max_value=30.0,
        value=15.0,
        step=0.5,
    )

    center_slab = st.checkbox(
        "將 Slab 置中於晶胞內",
        value=True,
    )

    primitive = st.checkbox(
        "使用 primitive cell",
        value=True,
    )

    st.divider()
    st.header("🔮 4. 3D 顯示設定")

    sc_a_col, sc_b_col, sc_c_col = st.columns(3)

    super_a = int(
        sc_a_col.number_input(
            "A 倍",
            min_value=1,
            max_value=6,
            value=2,
            step=1,
        )
    )
    super_b = int(
        sc_b_col.number_input(
            "B 倍",
            min_value=1,
            max_value=6,
            value=2,
            step=1,
        )
    )
    super_c = int(
        sc_c_col.number_input(
            "C 倍",
            min_value=1,
            max_value=3,
            value=1,
            step=1,
        )
    )

    style_name = st.selectbox(
        "3D 顯示樣式",
        ["Ball and Stick", "Spacefill", "Stick"],
    )

    show_unit_cell = st.checkbox(
        "顯示 Unit Cell",
        value=True,
    )

    dark_background = st.checkbox(
        "深色背景",
        value=True,
    )

    generate_disabled = (
        bulk_structure is None
        or miller_index == (0, 0, 0)
    )

    generate_button = st.button(
        "🚀 產生 Slab",
        type="primary",
        use_container_width=True,
        disabled=generate_disabled,
    )


if bulk_structure is None:
    st.info("請先從左側上傳 CIF / POSCAR，或選擇內建 Cu 範例。")
    st.stop()

if miller_index == (0, 0, 0):
    st.error("Miller Index 不可以是 (0, 0, 0)。")
    st.stop()


st.subheader("📊 原始 Bulk 結構資訊")

bulk_a, bulk_b, bulk_c = bulk_structure.lattice.abc
bulk_alpha, bulk_beta, bulk_gamma = bulk_structure.lattice.angles

metric1, metric2, metric3, metric4 = st.columns(4)

metric1.metric(
    "化學式",
    bulk_structure.composition.reduced_formula,
)
metric2.metric(
    "原子數",
    len(bulk_structure),
)
metric3.metric(
    "體積",
    f"{bulk_structure.volume:.3f} Å³",
)
metric4.metric(
    "密度",
    f"{bulk_structure.density:.3f} g/cm³",
)

with st.expander("查看 Bulk 晶格參數"):
    st.code(
        (
            f"a = {bulk_a:.6f} Å\n"
            f"b = {bulk_b:.6f} Å\n"
            f"c = {bulk_c:.6f} Å\n"
            f"α = {bulk_alpha:.6f}°\n"
            f"β = {bulk_beta:.6f}°\n"
            f"γ = {bulk_gamma:.6f}°"
        ),
        language="text",
    )


current_cache_key = make_cache_key(
    source_key=source_key,
    miller=miller_index,
    slab_thickness=slab_thickness,
    vacuum_thickness=vacuum_thickness,
    center_slab=center_slab,
    primitive=primitive,
)

if generate_button:
    st.session_state.generation_error = None

    try:
        with st.spinner("正在建立 Slab 並搜尋 termination..."):
            generator = SlabGenerator(
                initial_structure=bulk_structure,
                miller_index=miller_index,
                min_slab_size=float(slab_thickness),
                min_vacuum_size=float(vacuum_thickness),
                lll_reduce=False,
                center_slab=bool(center_slab),
                primitive=bool(primitive),
                in_unit_planes=False,
            )

            slabs = generator.get_slabs()

            if not slabs:
                raise ValueError("沒有找到可用的 Slab termination。")

            st.session_state.generated_slabs = slabs
            st.session_state.slab_cache_key = current_cache_key

    except Exception as exc:
        st.session_state.generated_slabs = None
        st.session_state.slab_cache_key = None
        st.session_state.generation_error = str(exc)


if st.session_state.generation_error:
    st.error("Slab 建構失敗")
    st.code(
        st.session_state.generation_error,
        language="text",
    )


slabs_are_current = (
    st.session_state.generated_slabs is not None
    and st.session_state.slab_cache_key == current_cache_key
)

if (
    st.session_state.generated_slabs is not None
    and st.session_state.slab_cache_key != current_cache_key
):
    st.warning("左側參數已變更，請重新按「產生 Slab」。")


if not slabs_are_current:
    st.subheader("🔍 Bulk 3D 預覽")

    render_3d(
        structure=bulk_structure,
        style_name=style_name,
        show_unit_cell=show_unit_cell,
        dark_background=dark_background,
    )

    st.info("設定左側參數後，按下「產生 Slab」。")
    st.stop()


generated_slabs = st.session_state.generated_slabs

with st.sidebar:
    st.divider()
    st.header("🏆 5. Termination 表面終端")

    termination_index = st.selectbox(
        "選擇 termination",
        options=list(range(len(generated_slabs))),
        format_func=lambda index: (
            f"Termination {index + 1} "
            f"(shift={float(getattr(generated_slabs[index], 'shift', 0.0)):.4f})"
        ),
    )


final_slab = generated_slabs[termination_index].copy()
final_slab.make_supercell([super_a, super_b, super_c])
final_structure = final_slab.get_sorted_structure()


try:
    cif_out = structure_to_cif(final_structure)
    poscar_out = structure_to_poscar(final_structure)
except Exception as exc:
    st.error("Slab 已生成，但建立 CIF / POSCAR 輸出時失敗。")
    st.code(str(exc), language="text")
    st.stop()


st.divider()
st.subheader("🔬 Slab 計算結果")

slab_a, slab_b, slab_c = final_structure.lattice.abc
slab_alpha, slab_beta, slab_gamma = final_structure.lattice.angles

result1, result2, result3, result4 = st.columns(4)

result1.metric(
    "Miller Index",
    f"({h} {k} {l})",
)
result2.metric(
    "Termination",
    termination_index + 1,
)
result3.metric(
    "Supercell 原子數",
    len(final_structure),
)
result4.metric(
    "晶胞 c 長度",
    f"{slab_c:.3f} Å",
)


viewer_col, export_col = st.columns([2.1, 1])


with viewer_col:
    st.subheader("🧊 可旋轉 3D 結構")

    render_3d(
        structure=final_structure,
        style_name=style_name,
        show_unit_cell=show_unit_cell,
        dark_background=dark_background,
    )

    st.info(
        "滑鼠左鍵旋轉、滾輪縮放；"
        "右鍵或中鍵拖曳可平移。"
    )


with export_col:
    st.subheader("💾 匯出模擬結構檔")

    formula_name = (
        final_structure.composition.reduced_formula
        .replace(" ", "")
    )

    file_base_name = (
        f"Slab_{formula_name}_{h}{k}{l}"
        f"_T{termination_index + 1}"
    )

    st.write(
        f"**化學式：** "
        f"`{final_structure.composition.reduced_formula}`"
    )
    st.write(
        f"**Miller Index：** `({h} {k} {l})`"
    )
    st.write(
        f"**Supercell：** "
        f"`{super_a} × {super_b} × {super_c}`"
    )

    st.code(
        (
            f"a = {slab_a:.6f} Å\n"
            f"b = {slab_b:.6f} Å\n"
            f"c = {slab_c:.6f} Å\n"
            f"α = {slab_alpha:.6f}°\n"
            f"β = {slab_beta:.6f}°\n"
            f"γ = {slab_gamma:.6f}°"
        ),
        language="text",
    )

    st.download_button(
        label="📥 下載 VASP POSCAR",
        data=poscar_out,
        file_name=f"POSCAR_{file_base_name}",
        mime="text/plain",
        type="primary",
        use_container_width=True,
    )

    st.download_button(
        label="📥 下載 VESTA CIF",
        data=cif_out,
        file_name=f"{file_base_name}.cif",
        mime="chemical/x-cif",
        use_container_width=True,
    )


poscar_tab, cif_tab = st.tabs(
    ["預覽 POSCAR", "預覽 CIF"]
)

with poscar_tab:
    st.code(poscar_out, language="text")

with cif_tab:
    st.code(cif_out, language="text")
