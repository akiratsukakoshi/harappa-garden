"""pdf_analyzer — 請求書 PDF/画像の Gemini 解析(HMC apps/invoice_processor/pdf_analyzer.py 移植)。

Garden 化の差分:
- 退役済みの旧 SDK `google.generativeai` + `gemini-2.0-flash`(404)を
  新 SDK `google.genai` + env 指定モデル(既定 gemini-2.5-flash)に更新
  (S37 expense-processor / S40 genai 移行と同じ判断)
- ファイルは inline bytes で渡す(請求書サイズなら十分。upload_file API 不要)
- 429 リトライを追加(expense-processor と同パターン)
- プロンプト・正規化ロジック(items 補完 / document_total 補完)は HMC と同一
"""
import json
import os
import time

from google import genai
from google.genai import types as genai_types

from .utils import setup_logger

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

_MIME_TYPES = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


class PDFAnalyzer:
    def __init__(self):
        self.logger = setup_logger("PDFAnalyzer")
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            self.client = genai.Client(api_key=self.api_key)
        else:
            self.logger.warning("GEMINI_API_KEY not found in environment variables.")
            self.client = None

    def analyze(self, file_path, section_candidates=None):
        """ファイル(画像/PDF)を Gemini で解析して JSON dict を返す。失敗は None。"""
        if not self.client:
            self.logger.error("Gemini client not initialized.")
            return None

        ext = os.path.splitext(file_path)[1].lower()
        mime_type = _MIME_TYPES.get(ext)
        if not mime_type:
            self.logger.error(f"Unsupported extension for analysis: {file_path}")
            return None

        section_prompt = ""
        if section_candidates:
            candidates_str = ", ".join(section_candidates)
            section_prompt = f"- section_name: 取引内容から最も適切な部門を推定してください。候補: [{candidates_str}]。不明な場合は null"

        prompt = f"""
        この請求書/レシート画像を解析し、以下の情報をJSON形式で抽出してください。
        日付は YYYY-MM-DD 形式にしてください。
        金額は数値のみ(通貨記号なし)にしてください。
        支払先(payee)は、請求書の発行元(サービス提供者)です。「HARAPPA株式会社」や「HARAPPA」は請求先(自社)なので、**絶対に**支払先にしないでください。

        【重要】金額の整合性について:
        1. **document_total**: 請求書/レシートの**税込請求総額(Grand Total)**を必ず正確に抽出してください。これが検算の基準になります。
        2. **items**: 明細行をリストで抽出してください。
            - 明細の金額(amount)は、可能な限り**税込**で抽出してください。
            - もし明細が税抜で記載されており、最後にまとめて消費税が加算されている場合は、**税抜のまま**抽出しても構いません(後でシステムが補正します)。

        必要なフィールド:
        - date: 取引日 (string, YYYY-MM-DD)
        - document_total: 請求総額(税込) (int)
        - payee: 支払先/発行元 (string, HARAPPA以外)
        - invoice_number: インボイス登録番号 (string, T+13桁の数字, なければ null)
        - description: 全体の要約 (string)
        {section_prompt}
        - items: 明細行のリスト
            - description: 明細の内容 (string)
            - amount: 金額 (int)
            - section_name: 明細ごとの部門 (あれば。なければトップレベルと同じかnull)

        出力はJSONのみにしてください。Markdownのコードブロックは不要です。
        """

        try:
            with open(file_path, "rb") as f:
                file_bytes = f.read()

            response = None
            max_retries = 3
            base_wait = 2
            for attempt in range(max_retries):
                try:
                    response = self.client.models.generate_content(
                        model=GEMINI_MODEL,
                        contents=[
                            genai_types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
                            prompt,
                        ],
                    )
                    break
                except Exception as e:
                    if "429" in str(e) and attempt < max_retries - 1:
                        wait_time = base_wait * (2 ** attempt)
                        self.logger.warning(f"AI rate limit hit. Retrying in {wait_time}s...")
                        time.sleep(wait_time)
                    else:
                        raise
            if not response:
                return None

            text = response.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            data = json.loads(text.strip())

            # items が無ければトップレベルから 1 行補完(HMC と同一)
            if "items" not in data or not data["items"]:
                total = data.get("document_total", data.get("amount", 0))
                data["items"] = [{
                    "description": data.get("description", ""),
                    "amount": total,
                    "section_name": data.get("section_name"),
                }]
            if "document_total" not in data:
                items_sum = sum(item.get("amount", 0) or 0 for item in data["items"])
                data["document_total"] = data.get("amount", items_sum)
            return data

        except Exception as e:
            self.logger.error(f"Error during analysis of {os.path.basename(file_path)}: {e}")
            return None
