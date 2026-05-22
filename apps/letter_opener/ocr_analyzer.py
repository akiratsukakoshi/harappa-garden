import os
import json
import uuid
import datetime
import google.generativeai as genai
from modules.utils import setup_logger

class TaskAnalyzer:
    def __init__(self):
        self.logger = setup_logger("TaskAnalyzer_LetterOpener")
        self.api_key = os.getenv("GEMINI_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash')
        else:
            self.logger.warning("GEMINI_API_KEY not found in environment variables.")
            self.model = None

    def analyze(self, file_path):
        """
        ファイル（画像/PDF）を読み込み、Geminiで解析してタスク情報のJSONを返す。
        """
        if not self.model:
            self.logger.error("Gemini model not initialized.")
            return self._get_dummy_data()

        try:
            self.logger.info(f"Uploading file {file_path} to Gemini...")
            myfile = genai.upload_file(file_path)
            
            today_str = datetime.datetime.now().strftime("%Y/%m/%d")

            prompt = f"""
            この書類（郵便物・ハガキ・封筒など）の画像を解析し、どのような対応が必要か読み解き、以下の情報をJSON形式で抽出してください。
            
            前提:
            本日は {today_str} です。
            
            抽出項目:
            - task_type: タスク種類。必ず以下のいずれかに分類してください: ["支払い", "手続き", "書類提出", "連絡", "確認", "その他"]
            - task_content: 具体的タスク内容 (string)。簡潔に「〇〇の支払いを行う」「〇〇へ連絡する」など。
            - deadline: 締切日 (string, YYYY/MM/DD形式)。書類に記載がなければ "未定" とすること。記載がある場合は読み取ってYYYY/MM/DD形式にすること。
            - summary: 書類の概要 (string)。差出人や主な主旨の1文。
            
            出力はJSONのみにしてください。Markdownのコードブロックは不要です。
            """
            
            self.logger.info("Generating content...")
            result = self.model.generate_content([myfile, prompt])
            
            text = result.text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            
            data = json.loads(text.strip())
            
            # タスク番号を自動付与
            data["task_id"] = f"LTR-{uuid.uuid4().hex[:4].upper()}"
            
            return data

        except Exception as e:
            self.logger.error(f"Error during analysis: {e}")
            return None

    def _get_dummy_data(self):
        self.logger.info("Returning dummy data.")
        return {
            "task_id": f"LTR-{uuid.uuid4().hex[:4].upper()}",
            "task_type": "手続き",
            "task_content": "ダミーの手続きタスク",
            "deadline": "2026/04/30",
            "summary": "ダミー書類の解析結果です。"
        }
