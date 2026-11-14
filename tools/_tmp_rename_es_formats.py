# -*- coding: utf-8 -*-
from pathlib import Path

APP = Path(r"D:\AIAD\apps\sgenaxis-desktop\ui\app.js")
t = APP.read_text(encoding="utf-8")

repls = [
    (
        "儲存場景套件到目前專案 scene/（default.sg＋.sgml＋.sgui）",
        "儲存場景套件到目前專案 scene/（default.es＋.esml＋.esui）",
    ),
    (
        "儲存場景 XML 到目前專案 scene/default.sgs",
        "儲存場景 XML 到目前專案 scene/default.ess",
    ),
    (
        "自目前專案 scene/default.sgs 載入",
        "自目前專案 scene/default.ess 載入",
    ),
    (
        """  /**
   * 場景打包 .sgb（bin）：預設專案檔名
   * - default.sg（工項 JSON）
   * - default.sgml（架構圖 XML）
   * - default.sgui（UI 設計 JSON）
   */
  const SGB_MAGIC = "SGB1";
  const SGB_ENTRY_WORK = "default.sg";
  const SGB_ENTRY_ARCH = "default.sgml";
  const SGB_ENTRY_DESIGN = "default.sgui";
  const SGB_DEFAULT_NAME = "default.sgb";
  /** 專案內場景相對路徑（僅限 scene/；經 scene_save／scene_load）。 */
  const SCENE_SGS_REL = "scene/default.sgs";
  const SCENE_SG_REL = "scene/default.sg";
  const SCENE_SGML_REL = "scene/default.sgml";
  const SCENE_SGUI_REL = "scene/default.sgui";
""",
        """  /**
   * 場景打包 .sgb（bin）：預設專案檔名（EluSlot）
   * - default.es（工項 JSON）
   * - default.esml（架構圖 XML）
   * - default.esui（UI 設計 JSON）
   */
  const SGB_MAGIC = "SGB1";
  const SGB_ENTRY_WORK = "default.es";
  const SGB_ENTRY_ARCH = "default.esml";
  const SGB_ENTRY_DESIGN = "default.esui";
  const SGB_DEFAULT_NAME = "default.sgb";
  /** 專案內場景相對路徑（僅限 scene/；經 scene_save／scene_load）。 */
  const SCENE_SGS_REL = "scene/default.ess";
  const SCENE_SG_REL = "scene/default.es";
  const SCENE_SGML_REL = "scene/default.esml";
  const SCENE_SGUI_REL = "scene/default.esui";
""",
    ),
    ('format: "sgenaxis.sg",', 'format: "eluslot.es",'),
    ('copy.format = "sgenaxis.sgui";', 'copy.format = "eluslot.esui";'),
    (
        "'<?xml version=\"1.0\"?><sgenaxisArch/>'",
        "'<?xml version=\"1.0\"?><eluslotArch/>'",
    ),
    (
        'doc.format !== "sgenaxis.sg" && !doc.board',
        'doc.format !== "eluslot.es" && doc.format !== "sgenaxis.sg" && !doc.board',
    ),
    (
        'throw new Error("invalid default.sg");',
        'throw new Error("invalid default.es");',
    ),
    (
        'throw new Error("invalid default.sgui");',
        'throw new Error("invalid default.esui");',
    ),
    (
        "/* 內部仍走 DesignDoc；format 可為 sgenaxis.sgui 或 sgenaxis.design */",
        "/* 內部仍走 DesignDoc；format 可為 eluslot.esui／sgenaxis.sgui／sgenaxis.design */",
    ),
    (
        'if (!arch) throw new Error("default.sgml parse failed");',
        'if (!arch) throw new Error("default.esml parse failed");',
    ),
    (
        """    const workText =
      map[SGB_ENTRY_WORK] || map["work.sg"] || map["project.sg"];
    const archText =
      map[SGB_ENTRY_ARCH] || map["arch.sgml"] || map["architecture.sgml"];
    const designText =
      map[SGB_ENTRY_DESIGN] || map["design.sgui"] || map["ui.sgui"];
    if (!workText || !archText || !designText) {
      throw new Error(
        "SGB missing default.sg／default.sgml／default.sgui"
      );
    }
""",
        """    const workText =
      map[SGB_ENTRY_WORK] ||
      map["default.sg"] ||
      map["work.es"] ||
      map["work.sg"] ||
      map["project.sg"];
    const archText =
      map[SGB_ENTRY_ARCH] ||
      map["default.sgml"] ||
      map["arch.esml"] ||
      map["arch.sgml"] ||
      map["architecture.sgml"];
    const designText =
      map[SGB_ENTRY_DESIGN] ||
      map["default.sgui"] ||
      map["design.esui"] ||
      map["design.sgui"] ||
      map["ui.sgui"];
    if (!workText || !archText || !designText) {
      throw new Error(
        "SGB missing default.es／default.esml／default.esui"
      );
    }
""",
    ),
    (
        """  /**
   * 場景 XML .sgs：專案內場景單一 XML（對照 .sgb 三件套）
   * - work（工項／board）
   * - architecture（sgenaxisArch）
   * - design（UI 設計節點）
   */
  const SGS_DEFAULT_NAME = "default.sgs";
""",
        """  /**
   * 場景 XML .ess：專案內場景單一 XML（對照 .es＋.esml＋.esui 套件）
   * - work（工項／board）
   * - architecture（eluslotArch）
   * - design（UI 設計節點）
   */
  const SGS_DEFAULT_NAME = "default.ess";
""",
    ),
]

n = 0
for a, b in repls:
    c = t.count(a)
    if c == 0:
        print("MISS:", a[:70].replace("\n", " "))
    else:
        t = t.replace(a, b)
        n += 1
        if c > 1:
            print("MULTI", c, a[:50].replace("\n", " "))

# Scene XML writer / reader format strings
t2 = t
pairs = [
    (
        '<sgenaxisScene format="sgenaxis.sgs" formatVersion="1" encoding="xml">\\n',
        '<eluslotScene format="eluslot.ess" formatVersion="1" encoding="xml">\\n',
    ),
    (
        'archAttr("sgbCompat", "default.sg+default.sgml+default.sgui")',
        'archAttr("sgbCompat", "default.es+default.esml+default.esui")',
    ),
    (
        'xml += \'  <work format="sgenaxis.sg" encoding="xml">\\n\';',
        'xml += \'  <work format="eluslot.es" encoding="xml">\\n\';',
    ),
    (
        'xml += \'  <design format="sgenaxis.sgui" encoding="xml">\\n\';',
        'xml += \'  <design format="eluslot.esui" encoding="xml">\\n\';',
    ),
    ("</sgenaxisScene>\\n", "</eluslotScene>\\n"),
    (
        'format: "sgenaxis.sgui",',
        'format: "eluslot.esui",',
    ),
    (
        'if (!scene) throw new Error("invalid .sgs（需 sgenaxisScene XML）");',
        'if (!scene) throw new Error("invalid .ess（需 eluslotScene XML）");',
    ),
    ('toast("已載入專案場景 .sgs");', 'toast("已載入專案場景 .ess");'),
    ('toast("儲存 .sgs 失敗：" + String(err));', 'toast("儲存 .ess 失敗：" + String(err));'),
    (
        'toast("開啟專案 .sgs 失敗：" + String(err));',
        'toast("開啟專案 .ess 失敗：" + String(err));',
    ),
    (
        'const ARCH_XML_DEFAULT_NAME = "default.sgml";',
        'const ARCH_XML_DEFAULT_NAME = "default.esml";',
    ),
    ('format: "sgenaxis.arch",', 'format: "eluslot.esml",'),
    (
        "escapeXml(d.format || \"sgenaxis.arch\")",
        "escapeXml(d.format || \"eluslot.esml\")",
    ),
    (
        'doc.format = archXmlAttr(root, "format", "sgenaxis.arch");',
        'doc.format = archXmlAttr(root, "format", "eluslot.esml");',
    ),
    (
        'toast("拒絕：無法解析架構 XML（需 <sgenaxisArch>）");',
        'toast("拒絕：無法解析架構 XML（需 <eluslotArch>）");',
    ),
]
for a, b in pairs:
    if a not in t2:
        print("MISS2:", a[:80])
    else:
        t2 = t2.replace(a, b)
        n += 1

APP.write_text(t2, encoding="utf-8")
print("done replacements ~", n)
# sanity
for needle in [
    "scene/default.ess",
    "eluslot.ess",
    "default.es",
    "default.esml",
    "default.esui",
    "eluslotArch",
    "eluslotScene",
]:
    print(needle, t2.count(needle))
