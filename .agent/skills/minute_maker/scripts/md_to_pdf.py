#!/usr/bin/env python3
import sys
import os
import logging
import base64
import markdown2
from weasyprint import HTML, CSS

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('weasyprint')
logger.setLevel(logging.INFO)

def md_to_pdf(md_file_path, output_path=None):
    """
    Converts a Markdown file to PDF using markdown2 and weasyprint.
    Embeds font as Base64 to avoid filesystem/fontconfig issues.
    """
    if not os.path.exists(md_file_path):
        print(f"Error: File not found: {md_file_path}")
        sys.exit(1)

    # Determine output path
    if output_path:
        pdf_file_path = output_path
    else:
        base_name = os.path.splitext(md_file_path)[0]
        pdf_file_path = base_name + ".pdf"

    try:
        with open(md_file_path, "r", encoding="utf-8") as f:
            md_content = f.read()

        # Convert Markdown to HTML
        html_content = markdown2.markdown(md_content, extras=['tables', 'fenced-code-blocks', 'break-on-newline'])

        # Font setup - Read and Base64 encode
        font_path = os.path.join(os.getcwd(), "data/minutes_maker/fonts/NotoSansJP-Regular.otf")
        
        if not os.path.exists(font_path):
            logger.error(f"Font file not found at {font_path}")
            sys.exit(1)
            
        with open(font_path, "rb") as font_file:
            font_b64 = base64.b64encode(font_file.read()).decode('utf-8')

        # CSS with Base64 font (OpenType)
        css_style = f"""
        @font-face {{
            font-family: 'Noto Sans CJK JP';
            src: url(data:font/otf;base64,{font_b64}) format('opentype');
            font-weight: normal;
            font-style: normal;
        }}
        @page {{
            size: A4;
            margin: 20mm;
            @bottom-center {{
                content: counter(page);
                font-family: 'Noto Sans CJK JP', sans-serif;
                font-size: 10pt;
            }}
        }}
        body {{
            font-family: 'Noto Sans CJK JP', "Hiragino Kaku Gothic ProN", "Meiryo", sans-serif;
            font-size: 10.5pt;
            line-height: 1.6;
            color: #333;
        }}
        h1 {{
            font-size: 18pt;
            border-bottom: 2px solid #555;
            padding-bottom: 5px;
            margin-bottom: 20px;
            font-family: 'Noto Sans CJK JP', sans-serif;
        }}
        h2 {{
            font-size: 14pt;
            border-left: 5px solid #4CAF50;
            padding-left: 10px;
            margin-top: 30px;
            margin-bottom: 15px;
            background-color: #f9f9f9;
            font-family: 'Noto Sans CJK JP', sans-serif;
        }}
        h3 {{
            font-size: 12pt;
            font-weight: bold;
            margin-top: 20px;
            border-bottom: 1px dotted #ccc;
            font-family: 'Noto Sans CJK JP', sans-serif;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 20px;
            font-size: 9pt;
            font-family: 'Noto Sans CJK JP', sans-serif;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }}
        th {{
            background-color: #f2f2f2;
            font-weight: bold;
        }}
        code {{
            background-color: #f5f5f5;
            padding: 2px 4px;
            border-radius: 3px;
            font-family: "Consolas", "Courier New", monospace;
            font-size: 0.9em;
        }}
        pre {{
            background-color: #f5f5f5;
            padding: 10px;
            border-radius: 5px;
            overflow-x: auto;
        }}
        """

        # Wrap in HTML skeleton
        full_html = f"""
        <!DOCTYPE html>
        <html lang="ja">
        <head>
            <meta charset="UTF-8">
            <title>Meeting Minutes</title>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """

        # Generate PDF
        print(f"Generating PDF: {pdf_file_path}...")
        HTML(string=full_html).write_pdf(pdf_file_path, stylesheets=[CSS(string=css_style)])
        print("Done.")

    except Exception as e:
        logger.error(f"Error converting to PDF: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 md_to_pdf.py <markdown_file> [output_pdf_path]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    md_to_pdf(input_file, output_file)
