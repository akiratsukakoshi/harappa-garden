import os
import json
import google.generativeai as genai
from modules.utils import setup_logger

class PDFAnalyzer:
    def __init__(self):
        self.logger = setup_logger("PDFAnalyzer")
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            # Use Gemini 2.0 Flash
            self.model = genai.GenerativeModel('gemini-2.0-flash')
        else:
            self.logger.warning("GEMINI_API_KEY not found in environment variables.")
            self.model = None

    def analyze(self, file_path, section_candidates=None):
        """
        ファイル（画像/PDF）を読み込み、Geminiで解析してJSONを返す。
        section_candidates: list of section names strings
        """
        if not self.model:
            self.logger.error("Gemini model not initialized.")
            # Return dummy data for development if key is missing
            return self._get_dummy_data()

        try:
            self.logger.info(f"Uploading file {file_path} to Gemini...")
            myfile = genai.upload_file(file_path)
            
            section_prompt = ""
            if section_candidates:
                candidates_str = ", ".join(section_candidates)
                section_prompt = f"- section_name: 取引内容から最も適切な部門を推定してください。候補: [{candidates_str}]。不明な場合は null"

            prompt = f"""
            この請求書/レシート画像を解析し、以下の情報をJSON形式で抽出してください。
            日付は YYYY-MM-DD 形式にしてください。
            金額は数値のみ（通貨記号なし）にしてください。
            支払先(payee)は、請求書の発行元（サービス提供者）です。「HARAPPA株式会社」や「HARAPPA」は請求先（自社）なので、**絶対に**支払先にしないでください。
            
            【重要】金額の整合性について:
            1. **document_total**: 請求書/レシートの**税込請求総額（Grand Total）**を必ず正確に抽出してください。これが検算の基準になります。
            2. **items**: 明細行をリストで抽出してください。
                - 明細の金額(amount)は、可能な限り**税込**で抽出してください。
                - もし明細が税抜で記載されており、最後にまとめて消費税が加算されている場合は、**税抜のまま**抽出しても構いません（後でシステムが補正します）。
            
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
            
            self.logger.info("Generating content...")
            result = self.model.generate_content([myfile, prompt])
            
            # Clean up response text if it contains markdown code blocks
            text = result.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            
            data = json.loads(text.strip())
            
            # Normalize data structure: Ensure 'items' exists
            if 'items' not in data or not data['items']:
                # If no items found, create one from top level
                # Use document_total as amount if available, else standard amount
                total = data.get("document_total", data.get("amount", 0))
                data['items'] = [{
                    "description": data.get("description", ""),
                    "amount": total,
                    "section_name": data.get("section_name")
                }]
                
            # Ensure document_total exists
            if 'document_total' not in data:
                 # Fallback to sum of items or top level amount
                 items_sum = sum(item.get('amount', 0) for item in data['items'])
                 data['document_total'] = data.get('amount', items_sum)
            
            return data

        except Exception as e:
            self.logger.error(f"Error during analysis: {e}")
            return None

    def _get_dummy_data(self):
        self.logger.info("Returning dummy data.")
        return {
            "date": "2025-12-14",
            "amount": 12345,
            "payee": "Amazon Dummy",
            "invoice_number": "T1234567890123",
            "description": "Dummy transaction for testing"
        }
