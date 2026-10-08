"""Generate SANZO-owned demo inputs. This script never parses documents."""

from __future__ import annotations

import argparse
from html import escape
import json
import os
from pathlib import Path
import shutil
import subprocess

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

ROOT = Path(__file__).resolve().parents[1]
BUNDLED = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies"


def spreadsheet(mode: str, output: Path, research: Path | None = None) -> None:
    modules = BUNDLED / "node/node_modules"
    link = ROOT / "scripts/node_modules"
    if not link.exists():
        link.symlink_to(modules, target_is_directory=True)
    node = os.environ.get("ARTIFACT_NODE") or str(BUNDLED / "node/bin/node")
    if not Path(node).exists():
        node = shutil.which("node") or "node"
    args = [node, str(ROOT / "scripts/generate_workbook.mjs"), mode, str(output)]
    if research:
        args.append(str(research))
    subprocess.run(args, check=True)


def smoke(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    target = output / "minimal.pdf"
    pdf = canvas.Canvas(str(target), pagesize=A4)
    pdf.setTitle("SANZO SDK smoke test")
    pdf.setFont("Helvetica-Bold", 18)
    pdf.drawString(54, 780, "SANZO SDK smoke test")
    pdf.setFont("Helvetica", 12)
    pdf.drawString(54, 744, "This is a native-text PDF created by SANZO for SDK testing.")
    pdf.drawString(54, 714, "Property: SANZO smoke fixture")
    pdf.drawString(54, 690, "Price JPY: 12345678")
    pdf.drawString(54, 666, "This fixture is not a real property and must not be published.")
    pdf.save()
    spreadsheet("smoke", output)
    print(f"Generated: {target}")
    print(f"Generated: {output / 'minimal.xlsx'}")


def business_pdf(target: Path, title: str, subtitle: str, rows: list[tuple[str, object]], notes: list[str]) -> None:
    """Create native-text PDF with explicit key:value source records."""
    font = "NotoSansJP"
    pdfmetrics.registerFont(TTFont(font, str(ROOT / "assets/fonts/NotoSansJP-Regular.ttf")))
    title_style = ParagraphStyle("Title", fontName=font, fontSize=22, leading=30, textColor=colors.HexColor("#183F35"), spaceAfter=12, wordWrap="CJK")
    subtitle_style = ParagraphStyle("Subtitle", fontName=font, fontSize=10, leading=16, textColor=colors.HexColor("#627469"), spaceAfter=16, wordWrap="CJK")
    row_style = ParagraphStyle("Row", fontName=font, fontSize=10, leading=17, spaceAfter=8, wordWrap="CJK")
    note_style = ParagraphStyle("Note", fontName=font, fontSize=9, leading=15, textColor=colors.HexColor("#4B5B53"), spaceAfter=7, wordWrap="CJK")
    source_style = ParagraphStyle("Source", fontName=font, fontSize=8, leading=12, spaceAfter=6, textColor=colors.HexColor("#52655A"), wordWrap="CJK")

    def footer(pdf: canvas.Canvas, doc: SimpleDocTemplate) -> None:
        pdf.setStrokeColor(colors.HexColor("#CFD9CF"))
        pdf.line(42, 38, A4[0] - 42, 38)
        pdf.setFont(font, 8)
        pdf.setFillColor(colors.HexColor("#627469"))
        pdf.drawString(42, 24, "公開情報を基にSANZOがデモ用に再構成")
        pdf.drawRightString(A4[0] - 42, 24, str(doc.page))

    doc = SimpleDocTemplate(str(target), pagesize=A4, rightMargin=42, leftMargin=42, topMargin=42, bottomMargin=52, title=title, author="SANZO")
    story = [Paragraph(escape(title), title_style), Paragraph(escape(subtitle), subtitle_style)]
    for key, value in rows:
        if value is None:
            continue
        style = source_style if key.startswith("source_") else row_style
        story.append(Paragraph(escape(f"{key}: {value}"), style))
    if notes:
        story.append(Spacer(1, 12))
        story.append(Paragraph("確認事項", subtitle_style))
        for note in notes:
            story.append(Paragraph(escape(note), note_style))
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


def business(output: Path, research: Path) -> None:
    data = json.loads(research.read_text(encoding="utf-8"))
    p = data["property"]
    if p["lot"] != "No.15":
        raise ValueError("This document set is restricted to verified No.15 facts.")
    output.mkdir(parents=True, exist_ok=True)
    sources = {s["id"]: s for s in data["sources"]}

    def source_rows(source_id: str) -> list[tuple[str, object]]:
        src = sources[source_id]
        return [(key, src.get(key)) for key in ("source_name", "source_url", "checked_at", "effective_date", "valid_until")]

    property_rows = [(key, p.get(key)) for key in ("property_name", "lot", "price", "address", "station", "land_area", "building_area", "completion_date")]
    property_rows.insert(3, ("price_basis", p["price_basis"]))
    property_rows.extend([
        ("area_unit", "m²"),
        ("layout", f"{p['layout']}（No.15公式平面図から分類）"),
        ("layout_details", "1階LDK 16.8帖。2階主寝室7.2帖、洋室4.8帖が2室。"),
        ("parking_notes", p["parking_notes"]),
        ("scope_notes", "駅距離920～950m・最長徒歩12分は販売中4戸の掲載範囲。No.15単独の徒歩分数は未確認。"),
    ])
    property_rows.extend(source_rows("property_top"))
    property_rows.extend([(key, sources["property_overview"][key]) for key in ("source_name", "source_url")])
    property_rows.append(("source_url", sources["property_no15_plan"]["source_url"]))
    business_pdf(output / "物件概要_demo.pdf", "物件概要", p["property_name"], property_rows, [
        "価格・面積・完成年月はNo.15の公開情報です。価格は76,900,000円（土地建物・税込）。",
        p["layout_basis"],
        "情報登録日2026-10-02、有効期限2026-10-15。実演前に販売状況を再確認してください。期限後は現行の確定情報として使用しません。",
    ])

    equipment_rows = [("property_name", p["property_name"]), ("lot", p["lot"])]
    for item in data["equipment"]:
        details = [str(item[k]) for k in ("maker", "product", "location", "notes") if item.get(k)]
        if "capacity_kw" in item:
            details.append(f"{item['capacity_kw']:.1f}kW")
        if "quantity" in item:
            details.append(f"{item['quantity']}台")
        description = item["name"] + (f"（{'。'.join(details)}）" if details else "")
        equipment_rows.append(("equipment", description))
    equipment_rows.extend(source_rows("property_top"))
    equipment_rows.append(("scope_notes", "すべて公式ページでNo.15に掲載された設備。性能保証や未掲載の仕様を補完しません。"))
    business_pdf(output / "設備仕様_demo.pdf", "設備仕様", p["property_name"], equipment_rows, ["蓄電システムの公式表記「4.9kW」を記録しています。kWhへの訂正・換算は行っていません。", "第三者の写真・図面は使用していません。設備の詳細条件は担当スタッフにご確認ください。"])

    nearby_rows = [("property_name", p["property_name"]), ("lot", p["lot"]), ("station", p["station"]), ("scope_notes", data["nearby_metadata"]["display_required_notes"])]
    nearby_rows.append(("surroundings", "八千代中央駅：920～950m、最長徒歩12分（販売中4戸の範囲／最長値）"))
    for item in data["nearby"]:
        lo, hi = item["distance_m_range"]
        nearby_rows.append(("surroundings", f"{item['name']}：{lo}～{hi}m、最長徒歩{item['walking_minutes_max']}分（販売中4戸の範囲／最長値）"))
    nearby_rows.extend(source_rows("property_nearby"))
    nearby_rows.extend([("effective_date", "2026-10-02（物件概要の登録日。周辺ページ固有の更新日は未記載）"), ("valid_until", p["valid_until"])])
    business_pdf(output / "周辺環境_demo.pdf", "周辺環境", p["property_name"], nearby_rows, ["No.15単独の距離・徒歩分数は未確認です。範囲の端点をNo.15に割り当てていません。", "公式周辺写真の撮影年月2025年8月は情報登録日ではありません。この資料に写真は転載していません。", "徒歩所要時間は公式掲載値です。経路や歩行速度等により変わります。"])

    spreadsheet("business", output, research)
    print("Generated three business PDFs and 住宅ローン_demo.xlsx from verified research.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--research", type=Path, help="Verified public_data.json to generate business files")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.smoke:
        smoke(args.output or ROOT / "demo_documents/smoke")
    elif args.research:
        business(args.output or ROOT / "demo_documents", args.research)
    else:
        parser.error("Use --smoke or --research research/public_data.json")


if __name__ == "__main__":
    main()
