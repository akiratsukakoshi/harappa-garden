import os

def is_valid_extension(filename: str) -> bool:
    """
    サポートされているファイル拡張子かチェックする
    """
    valid_extensions = ['.pdf', '.jpg', '.jpeg', '.png', '.webp']
    return os.path.splitext(filename)[1].lower() in valid_extensions

def get_file_info(filepath: str) -> dict:
    return {
        "filename": os.path.basename(filepath),
        "size": os.path.getsize(filepath),
        "path": filepath
    }
