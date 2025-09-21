#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PDF診断ツール - 生成AIの指示書に基づくPDF構造チェック
"""

import fitz
import sys
import json
from pathlib import Path
from typing import Dict, List, Any

def diagnose_pdf(pdf_path: str) -> Dict[str, Any]:
    """
    PDFファイルの詳細診断を実行

    Args:
        pdf_path: 診断対象PDFファイルのパス

    Returns:
        診断結果の辞書
    """
    results = {
        "file_info": {},
        "structure_check": {},
        "font_info": [],
        "image_info": [],
        "issues": [],
        "severity": "info"
    }

    try:
        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            results["issues"].append({
                "type": "file_not_found",
                "severity": "critical",
                "message": f"ファイルが見つかりません: {pdf_path}"
            })
            results["severity"] = "critical"
            return results

        # ファイル基本情報
        results["file_info"] = {
            "path": str(pdf_file),
            "size_bytes": pdf_file.stat().st_size,
            "size_mb": round(pdf_file.stat().st_size / 1024 / 1024, 2)
        }

        # PDF構造チェック
        with fitz.open(pdf_path) as doc:
            # PyMuPDFバージョン互換性対応
            try:
                pdf_version = doc.pdf_version() if hasattr(doc, 'pdf_version') else "unknown"
            except:
                pdf_version = "unknown"

            try:
                needs_password = doc.needs_pass if hasattr(doc, 'needs_pass') else False
            except:
                needs_password = False

            results["structure_check"] = {
                "page_count": len(doc),
                "is_encrypted": doc.is_encrypted,
                "needs_password": needs_password,
                "pdf_version": pdf_version,
                "metadata": doc.metadata
            }

            # フォント情報チェック
            for page_num in range(len(doc)):
                page = doc[page_num]
                font_list = page.get_fonts(full=True)

                for font_info in font_list:
                    font_data = {
                        "page": page_num + 1,
                        "xref": font_info[0],
                        "name": font_info[1],
                        "type": font_info[2],
                        "encoding": font_info[3],
                        "embedded": bool(font_info[5])
                    }
                    results["font_info"].append(font_data)

                    # 日本語フォントの埋め込みチェック
                    if not font_data["embedded"] and any(jp_name in font_data["name"] for jp_name in ["MS", "Meiryo", "ヒラギノ", "游", "Yu"]):
                        results["issues"].append({
                            "type": "japanese_font_not_embedded",
                            "severity": "high",
                            "message": f"日本語フォント '{font_data['name']}' が埋め込まれていません (ページ {page_num + 1})",
                            "page": page_num + 1,
                            "font_name": font_data["name"]
                        })
                        if results["severity"] == "info":
                            results["severity"] = "high"

                # 画像情報チェック
                image_list = page.get_images(full=True)
                for img_info in image_list:
                    try:
                        pix = fitz.Pixmap(doc, img_info[0])
                        image_data = {
                            "page": page_num + 1,
                            "xref": img_info[0],
                            "width": pix.width,
                            "height": pix.height,
                            "colorspace": pix.colorspace.name if pix.colorspace else "unknown",
                            "size_mb": round(pix.size / 1024 / 1024, 2)
                        }
                        results["image_info"].append(image_data)

                        # 巨大画像チェック
                        if image_data["size_mb"] > 10:  # 10MB以上
                            results["issues"].append({
                                "type": "large_image",
                                "severity": "medium",
                                "message": f"大きな画像が検出されました: {image_data['size_mb']}MB (ページ {page_num + 1})",
                                "page": page_num + 1,
                                "size_mb": image_data["size_mb"]
                            })
                            if results["severity"] in ["info"]:
                                results["severity"] = "medium"

                        pix = None  # メモリ解放
                    except Exception as e:
                        results["issues"].append({
                            "type": "image_processing_error",
                            "severity": "low",
                            "message": f"画像処理エラー (ページ {page_num + 1}): {str(e)}",
                            "page": page_num + 1
                        })

            # PDF構造の整合性チェック
            try:
                # PyMuPDFによる基本的な構造チェック
                try:
                    xref_count = doc.xref_length() if hasattr(doc, 'xref_length') else len(doc)
                except:
                    xref_count = len(doc)

                results["structure_check"]["xref_count"] = xref_count

                # オブジェクト数のチェック
                if xref_count > 10000:
                    results["issues"].append({
                        "type": "large_xref_table",
                        "severity": "medium",
                        "message": f"xrefテーブルが大きすぎます: {xref_count}オブジェクト"
                    })
                    if results["severity"] == "info":
                        results["severity"] = "medium"

            except Exception as e:
                results["issues"].append({
                    "type": "structure_check_error",
                    "severity": "high",
                    "message": f"PDF構造チェックエラー: {str(e)}"
                })
                if results["severity"] == "info":
                    results["severity"] = "high"

    except Exception as e:
        results["issues"].append({
            "type": "general_error",
            "severity": "critical",
            "message": f"診断中にエラーが発生: {str(e)}"
        })
        results["severity"] = "critical"

    return results

def generate_recommendations(diagnosis: Dict[str, Any]) -> List[str]:
    """診断結果に基づく推奨事項を生成"""
    recommendations = []

    # 重要度別の推奨事項
    critical_issues = [issue for issue in diagnosis["issues"] if issue["severity"] == "critical"]
    high_issues = [issue for issue in diagnosis["issues"] if issue["severity"] == "high"]

    if critical_issues:
        recommendations.append("[CRITICAL] PDFファイルに重大な問題があります。ファイルを再生成してください。")

    if high_issues:
        font_issues = [issue for issue in high_issues if issue["type"] == "japanese_font_not_embedded"]
        if font_issues:
            recommendations.append("[HIGH] 日本語フォントが埋め込まれていません。ReportLabでフォントを明示的に登録・埋め込みしてください。")

    # ファイルサイズチェック
    if diagnosis["file_info"].get("size_mb", 0) > 50:
        recommendations.append("[MEDIUM] ファイルサイズが大きすぎます（50MB以上）。画像圧縮を検討してください。")

    if not diagnosis["issues"]:
        recommendations.append("[OK] PDF構造に問題は検出されませんでした。")

    return recommendations

def main():
    if len(sys.argv) != 2:
        print("使用方法: python pdf_diagnosis.py <PDFファイルパス>")
        sys.exit(1)

    pdf_path = sys.argv[1]
    print(f"PDF診断開始: {pdf_path}")
    print("=" * 60)

    # 診断実行
    diagnosis = diagnose_pdf(pdf_path)

    # 結果表示
    print("[FILE INFO] ファイル情報:")
    print(f"   パス: {diagnosis['file_info'].get('path', 'N/A')}")
    print(f"   サイズ: {diagnosis['file_info'].get('size_mb', 0):.2f} MB")
    print()

    print("[STRUCTURE] PDF構造:")
    structure = diagnosis["structure_check"]
    print(f"   ページ数: {structure.get('page_count', 'N/A')}")
    print(f"   PDFバージョン: {structure.get('pdf_version', 'N/A')}")
    print(f"   暗号化: {'あり' if structure.get('is_encrypted', False) else 'なし'}")
    print(f"   xrefオブジェクト数: {structure.get('xref_count', 'N/A')}")
    print()

    print(f"[FONTS] フォント情報: ({len(diagnosis['font_info'])}個)")
    for font in diagnosis["font_info"][:5]:  # 最初の5個のみ表示
        embed_status = "[OK]埋め込み済み" if font["embedded"] else "[NG]未埋め込み"
        print(f"   {font['name']} ({font['type']}) - {embed_status}")
    if len(diagnosis["font_info"]) > 5:
        print(f"   ... 他 {len(diagnosis['font_info']) - 5}個")
    print()

    print(f"[IMAGES] 画像情報: ({len(diagnosis['image_info'])}個)")
    for img in diagnosis["image_info"][:3]:  # 最初の3個のみ表示
        print(f"   {img['width']}x{img['height']} - {img['size_mb']:.2f}MB")
    if len(diagnosis["image_info"]) > 3:
        print(f"   ... 他 {len(diagnosis['image_info']) - 3}個")
    print()

    # 問題点表示
    print(f"[ISSUES] 検出された問題: ({len(diagnosis['issues'])}件)")
    if diagnosis["issues"]:
        for issue in diagnosis["issues"]:
            severity_map = {"critical": "[CRITICAL]", "high": "[HIGH]", "medium": "[MEDIUM]", "low": "[LOW]"}
            prefix = severity_map.get(issue["severity"], "[UNKNOWN]")
            print(f"   {prefix} {issue['message']}")
    else:
        print("   [OK] 問題は検出されませんでした")
    print()

    # 推奨事項
    recommendations = generate_recommendations(diagnosis)
    print("[RECOMMENDATIONS] 推奨事項:")
    for rec in recommendations:
        print(f"   {rec}")
    print()

    print(f"[RESULT] 総合評価: {diagnosis['severity'].upper()}")
    print("=" * 60)

    # JSON出力（詳細ログ用）
    json_output = json.dumps(diagnosis, ensure_ascii=False, indent=2)
    json_file = Path(pdf_path).with_suffix('.diagnosis.json')
    with open(json_file, 'w', encoding='utf-8') as f:
        f.write(json_output)
    print(f"詳細ログを保存: {json_file}")

if __name__ == "__main__":
    main()