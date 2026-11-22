/* Render the Release 3 evidence summary to Word with docx-js. Called by scripts/build_release3_docx.py, which parses
 * docs/release-3/README.md into a JSON spec and installs the npm package `docx` into a scratch folder:
 *
 *   node scripts/build_release3_docx.cjs --spec <spec.json> --out <file.docx> --modules <folder with node_modules/docx>
 *
 * Layout: A4, 2.5 cm side margins (16 cm text width), Calibri 10.5 pt body, navy headings, tables with a shaded
 * header row and DXA widths on the table and on every cell, centred figures with numbered captions, page numbers.
 */
"use strict";
const fs = require("fs");
const path = require("path");
const { createRequire } = require("module");

function option(name) {
  const i = process.argv.indexOf(`--${name}`);
  if (i < 0 || i + 1 >= process.argv.length) throw new Error(`missing --${name}`);
  return process.argv[i + 1];
}

const spec = JSON.parse(fs.readFileSync(option("spec"), "utf8"));
const out = option("out");
const docx = createRequire(path.join(path.resolve(option("modules")), "package.json"))("docx");
const {
  AlignmentType, BorderStyle, Document, ExternalHyperlink, Footer, HeadingLevel, ImageRun, LevelFormat, Packer,
  PageNumber, Paragraph, ShadingType, Table, TableCell, TableLayoutType, TableRow, TextRun, VerticalAlign, WidthType,
} = docx;

const FONT = "Calibri";
const MONO = "Consolas";
const COLOR = { ink: "1A1A1A", muted: "4D4B47", accent: "1F3B73", rule: "C3C8D2", headFill: "E4EAF3", noteFill: "F1F4F9", link: "1F5FBF", code: "2E2C29" };
const SIZE = { body: 21, table: 18, caption: 18, code: 19, footer: 16 }; // half-points
const PX_PER_CM = 96 / 2.54; // ImageRun sizes are given in pixels at 96 dpi
const TEXT_W = spec.textWidth;

function runs(list, opts = {}) {
  return list.map((r) => {
    const props = {
      text: r.text,
      bold: Boolean(r.bold || opts.bold) || undefined,
      italics: Boolean(r.italic || opts.italic) || undefined,
      font: r.code ? MONO : opts.font,
      size: r.code ? (opts.size ? opts.size - 1 : SIZE.code) : opts.size,
      color: r.code && !opts.color ? COLOR.code : opts.color,
    };
    if (r.link) return new ExternalHyperlink({ link: r.link, children: [new TextRun({ ...props, color: COLOR.link, underline: {} })] });
    return new TextRun(props);
  });
}

const NONE = { style: BorderStyle.NONE, size: 0, color: "FFFFFF" };
const line = (size, color) => ({ style: BorderStyle.SINGLE, size, color });
const ALIGN = { left: AlignmentType.LEFT, right: AlignmentType.RIGHT, center: AlignmentType.CENTER };

function table(b) {
  const widths = b.widths;
  const cell = (content, i, kind) => new TableCell({
    width: { size: widths[i], type: WidthType.DXA },
    margins: { top: 45, bottom: 45, left: 85, right: 85 },
    verticalAlign: VerticalAlign.CENTER,
    shading: kind === "head" ? { type: ShadingType.CLEAR, color: "auto", fill: COLOR.headFill } : undefined,
    borders: {
      top: kind === "head" ? line(8, COLOR.accent) : NONE,
      bottom: kind === "head" ? line(6, COLOR.accent) : kind === "last" ? line(8, COLOR.accent) : line(2, COLOR.rule),
      left: NONE,
      right: NONE,
    },
    children: [new Paragraph({
      alignment: ALIGN[b.align[i]] || AlignmentType.LEFT,
      spacing: { before: 0, after: 0, line: 240 },
      children: runs(content, { size: SIZE.table, bold: kind === "head", color: kind === "head" ? COLOR.accent : undefined }),
    })],
  });
  const rows = [new TableRow({ tableHeader: true, cantSplit: true, children: b.header.map((c, i) => cell(c, i, "head")) })];
  b.rows.forEach((r, k) => rows.push(new TableRow({
    cantSplit: true,
    children: r.map((c, i) => cell(c, i, k === b.rows.length - 1 ? "last" : "body")),
  })));
  return new Table({
    width: { size: TEXT_W, type: WidthType.DXA },
    columnWidths: widths,
    layout: TableLayoutType.FIXED,
    borders: { top: NONE, bottom: NONE, left: NONE, right: NONE, insideHorizontal: NONE, insideVertical: NONE },
    rows,
  });
}

function figure(b) {
  return [
    new Paragraph({
      alignment: AlignmentType.CENTER,
      keepNext: true,
      keepLines: true,
      spacing: { before: 200, after: 80 },
      children: [new ImageRun({
        type: "png",
        data: fs.readFileSync(b.path),
        transformation: { width: Math.round(b.widthCm * PX_PER_CM), height: Math.round(b.heightCm * PX_PER_CM) },
        altText: { title: `Figure ${b.number}`, description: b.alt, name: `figure-${b.number}` },
      })],
    }),
    new Paragraph({
      alignment: AlignmentType.CENTER,
      keepLines: true,
      spacing: { before: 0, after: 220 },
      children: [new TextRun({ text: `Figure ${b.number}. `, bold: true, size: SIZE.caption, color: COLOR.accent }),
        ...runs(b.caption, { size: SIZE.caption, color: COLOR.muted })],
    }),
  ];
}

const children = [];
let tableBefore = false;
for (const b of spec.blocks) {
  const gap = tableBefore ? { before: 140 } : {}; // air between a table and the paragraph that follows it
  tableBefore = false;
  switch (b.type) {
    case "title":
      children.push(new Paragraph({ heading: HeadingLevel.TITLE, children: runs(b.runs) }));
      break;
    case "subtitle":
      children.push(new Paragraph({
        spacing: { before: 0, after: 200 },
        border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: COLOR.accent, space: 6 } },
        children: runs(b.runs, { italic: true, size: 19, color: COLOR.muted }),
      }));
      break;
    case "h1":
      children.push(new Paragraph({ heading: HeadingLevel.HEADING_1, children: runs(b.runs) }));
      break;
    case "h2":
      children.push(new Paragraph({ heading: HeadingLevel.HEADING_2, children: runs(b.runs) }));
      break;
    case "paragraph":
      children.push(new Paragraph({ keepNext: b.keepNext || undefined, spacing: { ...gap }, children: runs(b.runs) }));
      break;
    case "note":
      children.push(new Paragraph({
        spacing: { before: 60, after: 180 },
        shading: { type: ShadingType.CLEAR, color: "auto", fill: COLOR.noteFill },
        border: { left: { style: BorderStyle.SINGLE, size: 18, color: COLOR.accent, space: 8 } },
        indent: { left: 170, right: 60 },
        children: runs(b.runs, { size: 20 }),
      }));
      break;
    case "bullets":
      b.items.forEach((item) => children.push(new Paragraph({ numbering: { reference: "bullets", level: 0 }, spacing: { after: 60 }, children: runs(item) })));
      break;
    case "table":
      children.push(table(b));
      tableBefore = true;
      break;
    case "figure":
      children.push(...figure(b));
      break;
    default:
      throw new Error(`unknown block type ${b.type}`);
  }
}

const doc = new Document({
  creator: "scripts/build_release3_docx.py",
  title: spec.title,
  subject: "Release 3 evidence summary",
  description: "Generated from docs/release-3/README.md",
  styles: {
    default: {
      document: { run: { font: FONT, size: SIZE.body, color: COLOR.ink }, paragraph: { spacing: { after: 110, line: 264 } } },
      title: { run: { font: FONT, size: 36, bold: true, color: COLOR.accent }, paragraph: { spacing: { before: 0, after: 80 }, keepNext: true } },
      heading1: { run: { font: FONT, size: 26, bold: true, color: COLOR.accent }, paragraph: { spacing: { before: 280, after: 100 }, keepNext: true, keepLines: true } },
      heading2: { run: { font: FONT, size: 22, bold: true, color: COLOR.accent }, paragraph: { spacing: { before: 200, after: 80 }, keepNext: true, keepLines: true } },
    },
  },
  numbering: {
    config: [{
      reference: "bullets",
      levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 360, hanging: 240 } } } }],
    }],
  },
  sections: [{
    properties: {
      page: {
        size: { width: 11906, height: 16838 },
        margin: { top: 1247, right: 1418, bottom: 1247, left: 1418, header: 709, footer: 567 },
      },
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [new TextRun({ children: [`${spec.footer}  ·  page `, PageNumber.CURRENT, " of ", PageNumber.TOTAL_PAGES], size: SIZE.footer, color: COLOR.muted })],
        })],
      }),
    },
    children,
  }],
});

Packer.toBuffer(doc).then((buffer) => {
  fs.writeFileSync(out, buffer);
}).catch((err) => {
  console.error(err);
  process.exit(1);
});
