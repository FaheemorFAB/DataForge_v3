# DataForge v3 — System Architecture & Engineering Diagrams

This directory contains the formal architectural, operational, and data flow diagrams for **DataForge v3**. All diagrams have been developed through in-depth analysis of the active codebase and engineered to meet academic textbook and technical publication standards.

---

## 📋 Catalog of Developed Figures

| Figure | Title | Mermaid File | Markdown File | Standard |
| :---: | :--- | :---: | :---: | :--- |
| **Figure 3.1** | **System Workflow** | [`figure_3_1_system_workflow.mmd`](figure_3_1_system_workflow.mmd) | [`figure_3_1_system_workflow.md`](figure_3_1_system_workflow.md) | Operational Process Lifecycle |
| **Figure 3.2** | **DataForge System Architecture** | [`figure_3_2_dataforge_system_architecture.mmd`](figure_3_2_dataforge_system_architecture.mmd) | [`figure_3_2_dataforge_system_architecture.md`](figure_3_2_dataforge_system_architecture.md) | Multi-Tiered System Architecture (IEEE 1471) |
| **Figure 3.3** | **Context Diagram (level 0) DFD** | [`figure_3_3_context_diagram_level_0_dfd.mmd`](figure_3_3_context_diagram_level_0_dfd.mmd) | [`figure_3_3_context_diagram_level_0_dfd.md`](figure_3_3_context_diagram_level_0_dfd.md) | Structured Analysis Context Diagram (Yourdon) |
| **Figure 3.4** | **Detailed Diagram (level 1) DFD** | [`figure_3_4_detailed_diagram_level_1_dfd.mmd`](figure_3_4_detailed_diagram_level_1_dfd.mmd) | [`figure_3_4_detailed_diagram_level_1_dfd.md`](figure_3_4_detailed_diagram_level_1_dfd.md) | Functional Subprocess & Store Decomposition |
| **Figure 3.5** | **Functional Module Interaction Diagram** | [`figure_3_5_functional_module_interaction.mmd`](figure_3_5_functional_module_interaction.mmd) | [`figure_3_5_functional_module_interaction.md`](figure_3_5_functional_module_interaction.md) | Subsystem Interface & Contract Flow |

---

## 🎨 Design & Aesthetic Guidelines

### 1. Minimalistic Textbook Black-and-White Palette
Every diagram uses high-contrast monochrome design tokens engineered for crisp rendering on standard printers and high-resolution academic displays:
- **Background Fill**: Pure White (`#ffffff`) for nodes and canvas.
- **Accents & Subgraphs**: Subtle light grayscale tints (`#f0f0f0`, `#f5f5f5`, `#fafafa`) for visual hierarchy without heavy ink coverage.
- **Borders & Connectors**: Solid black (`#000000`, 1.2px to 2.5px stroke width) and clean dashed lines for internal data stores and security boundaries.
- **Typography**: Clean, neutral sans-serif typography (`Helvetica, Arial, sans-serif`) with calibrated font sizes (10px–12px) to maximize legibility.

### 2. A4 Portrait Page Proportions
- Each diagram is structured vertically (`flowchart TD`) with balanced aspect ratios (~1:1.3 to 1:1.4).
- Node labels incorporate intentional line breaks (`<br/>`) to eliminate excessive horizontal sprawl.
- When rendered or printed, each diagram fits comfortably within an **A4 portrait page** (210mm × 297mm) with standard 15mm margins, preserving sharp readability without text truncation or scaling degradation.

---

## 🖨️ Viewing and Printing to PDF

### Option A: Interactive HTML Preview (One-Click Print)
Open [`preview.html`](preview.html) in any modern web browser:
```bash
# Example: Open directly in your browser
google-chrome diagrams/preview.html
# or
xdg-open diagrams/preview.html
```
- The page renders all 5 diagrams dynamically using Mermaid.js with textbook print styles.
- Press **Ctrl + P** (or **Cmd + P** on macOS) and choose **"Save as PDF"**.
- Layout is pre-configured with CSS `@page { size: A4 portrait; margin: 15mm; }` and automatic page breaks between figures.

### Option B: Unified Markdown Document
View [`all_diagrams.md`](all_diagrams.md) in any markdown viewer, IDE preview, GitHub, or Pandoc converter.

### Option C: Standalone Mermaid Files (`.mmd`)
Directly compile individual `.mmd` files using `mermaid-cli` or online at [Mermaid Live Editor](https://mermaid.live).
