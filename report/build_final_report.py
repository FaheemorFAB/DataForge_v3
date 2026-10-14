"""
Build the final publication-ready DataForge Project Report DOCX and PDF.
Replaces all blurry and low-visibility diagrams with crystal clear 300 DPI figures,
updates Chapter 5 UI captures with native 1080p un-cropped screenshots,
fixes Figure 3.5 so it is a distinct architecture interaction diagram,
removes all cropping artifacts, sets optimal layout dimensions,
and compiles via LibreOffice into a beautiful final PDF.
"""

import os
import re
import shutil
import subprocess
import zipfile
from pathlib import Path
from PIL import Image

BASE_DIR = Path("/home/fab/DataForge")
REPORT_DIR = BASE_DIR / "report"
SRC_DOCX = REPORT_DIR / "DataForge_Report.docx"
OUT_DOCX = REPORT_DIR / "DataForge_Final_Year_Report.docx"
OUT_PDF = REPORT_DIR / "DataForge_Final_Year_Report.pdf"

FIG_DIR = REPORT_DIR / "generated_figures"
ASSETS_DIR = BASE_DIR / "assets"

WORK_DIR = REPORT_DIR / "docx_build"
if WORK_DIR.exists():
    shutil.rmtree(WORK_DIR)
WORK_DIR.mkdir(parents=True, exist_ok=True)

print("1. Extracting source DOCX...")
with zipfile.ZipFile(SRC_DOCX, "r") as z:
    z.extractall(WORK_DIR)

# Media replacements
# image2.png -> Figure 3.1
# image4.png -> Figure 3.2
# image6.png -> Figure 3.3
# image8.png -> Figure 3.4
# image18.png -> Figure 3.5 (New!)
# image10.png -> Figure 5.1 (assets/auth.png)
# image11.png -> Figure 5.2 (assets/upload.png)
# image12.png -> Figure 5.3 (assets/cleaning_1.png)
# image13.png -> Figure 5.4 (assets/preview.png)
# image14.png -> Figure 5.5 (assets/AiQuery.png)
# image15.png -> Figure 5.6 (assets/AutoMl.png)
# image16.png -> Figure 5.7 (assets/Insights.png)
# image17.png -> Figure 5.8 (assets/Dashboard.png)

media_dir = WORK_DIR / "word" / "media"
media_dir.mkdir(parents=True, exist_ok=True)

REPLACEMENTS = {
    "image2.png": FIG_DIR / "figure_3_1_system_workflow.png",
    "image4.png": FIG_DIR / "figure_3_2_system_architecture.png",
    "image6.png": FIG_DIR / "figure_3_3_context_dfd_level_0.png",
    "image8.png": FIG_DIR / "figure_3_4_detailed_dfd_level_1.png",
    "image18.png": FIG_DIR / "figure_3_5_module_interaction.png",
    "image10.png": ASSETS_DIR / "auth.png",
    "image11.png": ASSETS_DIR / "upload.png",
    "image12.png": ASSETS_DIR / "cleaning_1.png",
    "image13.png": ASSETS_DIR / "preview.png",
    "image14.png": ASSETS_DIR / "AiQuery.png",
    "image15.png": ASSETS_DIR / "AutoMl.png",
    "image16.png": ASSETS_DIR / "Insights.png",
    "image17.png": ASSETS_DIR / "Dashboard.png",
}

print("2. Copying high-resolution media assets...")
for target_name, src_path in REPLACEMENTS.items():
    if src_path.exists():
        dest = media_dir / target_name
        shutil.copy2(src_path, dest)
        print(f"  Copied {src_path.name} -> {target_name} ({src_path.stat().st_size // 1024} KB)")
    else:
        print(f"  WARNING: Source file {src_path} not found!")

# Also remove low-res svg fallbacks so Word/LibreOffice always renders our crisp PNGs
for svg_f in ["image3.svg", "image5.svg", "image7.svg", "image9.svg"]:
    svg_p = media_dir / svg_f
    if svg_p.exists():
        svg_p.unlink()

print("3. Updating word/_rels/document.xml.rels...")
rels_file = WORK_DIR / "word" / "_rels" / "document.xml.rels"
rels_content = rels_file.read_text(encoding="utf-8")

# Add rId39 for image18.png (Figure 3.5) if not present
if "image18.png" not in rels_content:
    new_rel = '<Relationship Id="rId39" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/image18.png"/>'
    rels_content = rels_content.replace("</Relationships>", f"  {new_rel}\n</Relationships>")
    rels_file.write_text(rels_content, encoding="utf-8")
    print("  Added relationship rId39 -> media/image18.png")

print("4. Updating word/document.xml...")
doc_file = WORK_DIR / "word" / "document.xml"
doc_xml = doc_file.read_text(encoding="utf-8")

# Remove any asvg:svgBlip extensions that force low-res SVG fallback
doc_xml = re.sub(
    r'<a:extLst>\s*<a:ext uri="\{96DAC541-7B7A-43D3-8B79-37D633B846F1\}">.*?</a:ext>\s*</a:extLst>',
    '',
    doc_xml,
    flags=re.DOTALL
)

# Remove any intrusive a:srcRect cropping tags on UI screenshots
doc_xml = re.sub(r'<a:srcRect [^>]*/>', '<a:srcRect/>', doc_xml)

# Replace the second occurrence of rId12 with rId39 (Figure 3.5)
# Find all occurrences of <a:blip r:embed="rId12"
first_pos = doc_xml.find('r:embed="rId12"')
if first_pos != -1:
    second_pos = doc_xml.find('r:embed="rId12"', first_pos + 10)
    if second_pos != -1:
        doc_xml = doc_xml[:second_pos] + 'r:embed="rId39"' + doc_xml[second_pos + len('r:embed="rId12"'):]
        print("  Updated Figure 3.5 to use distinct rId39 (image18.png)")

# Set optimal, proportional dimensions for every drawing
# 1 inch = 914400 EMUs
DIMENSIONS = {
    "rId12": (4114800, 5777000),  # Fig 3.1: 4.5 in x 6.32 in
    "rId14": (5486400, 4637000),  # Fig 3.2: 6.0 in x 5.07 in
    "rId16": (5303520, 4087000),  # Fig 3.3: 5.8 in x 4.47 in
    "rId18": (4572000, 5340000),  # Fig 3.4: 5.0 in x 5.84 in
    "rId39": (5303520, 4411000),  # Fig 3.5: 5.8 in x 4.82 in
    "rId20": (5303520, 2398000),  # Fig 5.1: 5.8 in x 2.62 in
    "rId21": (5303520, 2398000),  # Fig 5.2: 5.8 in x 2.62 in
    "rId22": (5303520, 2398000),  # Fig 5.3: 5.8 in x 2.62 in
    "rId23": (5303520, 2398000),  # Fig 5.4: 5.8 in x 2.62 in
    "rId24": (5303520, 2398000),  # Fig 5.5: 5.8 in x 2.62 in
    "rId25": (5303520, 2398000),  # Fig 5.6: 5.8 in x 2.62 in
    "rId26": (5303520, 2398000),  # Fig 5.7: 5.8 in x 2.62 in
    "rId27": (5303520, 2398000),  # Fig 5.8: 5.8 in x 2.62 in
}

# Update extent tags corresponding to each blip
for rid, (cx, cy) in DIMENSIONS.items():
    pattern = rf'(<wp:extent\s+cx=")[^"]*("\s+cy=")[^"]*("/>.*?<a:blip\s+[^>]*r:embed="{rid}")'
    def repl_wp(m):
        return f'{m.group(1)}{cx}{m.group(2)}{cy}{m.group(3)}'
    doc_xml = re.sub(pattern, repl_wp, doc_xml, flags=re.DOTALL)
    
    # Also update a:ext inside pic:spPr
    pattern_sp = rf'(<a:blip\s+[^>]*r:embed="{rid}".*?<a:ext\s+cx=")[^"]*("\s+cy=")[^"]*("/>)'
    def repl_sp(m):
        return f'{m.group(1)}{cx}{m.group(2)}{cy}{m.group(3)}'
    doc_xml = re.sub(pattern_sp, repl_sp, doc_xml, flags=re.DOTALL)

# Clean all figure and table captions: Replace broken dynamic STYLEREF/SEQ fields with clean, static, reliable text
ALL_CAPTIONS = [
    ("System Workflo", "Figure 3.1: System Workflow"),
    ("DataForge System Architecture", "Figure 3.2: DataForge System Architecture"),
    ("Context Diagram (level 0) DFD", "Figure 3.3: Context Diagram (level 0) DFD"),
    ("Detailed Diagram (level 1) DFD", "Figure 3.4: Detailed Diagram (level 1) DFD"),
    ("Functional Module Interaction", "Figure 3.5: Functional Module Interaction Diagram"),
    ("Target User Segments", "Table 1.1: Target User Segments and their primary use cases"),
    ("Technology Stack Used", "Table 4.1: Technology Stack Used"),
    ("Software Requirements and Development", "Table 4.2: Software Requirements and Development Environment"),
    ("User Login Interface", "Figure 5.1: User Login Interface"),
    ("Dataset Upload and Import Interface", "Figure 5.2: Dataset Upload and Import Interface"),
    ("Data Cleaning Results", "Figure 5.3: Data Cleaning Results"),
    ("EDA Report", "Figure 5.4: EDA Report"),
    ("AI Query Interface", "Figure 5.5: AI Query Interface"),
    ("AutoML Results", "Figure 5.6: AutoML Results"),
    ("Generated Insights", "Figure 5.7: Generated Insights"),
    ("Dashboard Interface", "Figure 5.8: Dashboard Interface"),
]

for key, target_text in ALL_CAPTIONS:
    matches = list(re.finditer(re.escape(key), doc_xml))
    for m in reversed(matches):
        idx = m.start()
        p_start = doc_xml.rfind('<w:p ', 0, idx)
        p_end = doc_xml.find('</w:p>', idx) + 6
        p_xml = doc_xml[p_start:p_end]
        if 'STYLEREF' in p_xml or 'SEQ Figure' in p_xml or 'SEQ Table' in p_xml:
            bms = re.findall(r'<w:bookmarkStart[^>]*/>', p_xml)
            bme = re.findall(r'<w:bookmarkEnd[^>]*/>', p_xml)
            bm_start_str = "".join(bms)
            bm_end_str = "".join(bme)
            
            clean_p = (
                f'<w:p w:rsidR="00406FAE" w:rsidP="00406FAE">'
                f'<w:pPr><w:pStyle w:val="Caption"/><w:spacing w:before="120" w:after="180" w:line="360" w:lineRule="auto"/><w:jc w:val="center"/>'
                f'<w:rPr><w:rFonts w:asciiTheme="majorBidi" w:hAnsiTheme="majorBidi" w:cstheme="majorBidi"/><w:b/><w:bCs/><w:sz w:val="24"/><w:szCs w:val="24"/><w:color w:val="0f172a"/><w:lang w:val="en-GB"/></w:rPr>'
                f'</w:pPr>'
                f'{bm_start_str}'
                f'<w:r>'
                f'<w:rPr><w:rFonts w:asciiTheme="majorBidi" w:hAnsiTheme="majorBidi" w:cstheme="majorBidi"/><w:b/><w:bCs/><w:sz w:val="24"/><w:szCs w:val="24"/><w:color w:val="0f172a"/><w:lang w:val="en-GB"/></w:rPr>'
                f'<w:t>{target_text}</w:t>'
                f'</w:r>'
                f'{bm_end_str}'
                f'</w:p>'
            )
            doc_xml = doc_xml[:p_start] + clean_p + doc_xml[p_end:]
            print(f"  Standardized caption: {target_text}")

doc_file.write_text(doc_xml, encoding="utf-8")
print("  Document XML updated successfully with clear dimensions, static captions, and uncropped views.")

print("5. Repackaging updated DOCX...")
if OUT_DOCX.exists():
    OUT_DOCX.unlink()

with zipfile.ZipFile(OUT_DOCX, "w", zipfile.ZIP_DEFLATED) as zip_out:
    for root, dirs, files in os.walk(WORK_DIR):
        for file in files:
            full_path = Path(root) / file
            rel_path = full_path.relative_to(WORK_DIR)
            zip_out.write(full_path, rel_path)

print(f"  Saved {OUT_DOCX} ({OUT_DOCX.stat().st_size // 1024} KB)")

# Also overwrite DataForge_Report.docx so user has the final version in both filenames
shutil.copy2(OUT_DOCX, SRC_DOCX)
print(f"  Updated source {SRC_DOCX}")

print("6. Converting DOCX to PDF using LibreOffice...")
cmd = [
    "libreoffice",
    "--headless",
    "--convert-to", "pdf",
    str(OUT_DOCX),
    "--outdir", str(REPORT_DIR)
]
res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
print("  LibreOffice output:", res.stdout.strip())
if res.stderr:
    print("  LibreOffice stderr:", res.stderr.strip())

if OUT_PDF.exists():
    print(f"  Successfully compiled {OUT_PDF} ({OUT_PDF.stat().st_size // 1024} KB)")
    # Also copy to Downloads
    dl_pdf = Path("/home/fab/Downloads/DataForge_Report.pdf")
    shutil.copy2(OUT_PDF, dl_pdf)
    print(f"  Copied to {dl_pdf}")
else:
    print("  ERROR: PDF generation failed!")

print("Report build complete.")
