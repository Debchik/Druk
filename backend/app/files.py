from pathlib import Path
from .errors import AppError

ALLOWED = {"pdf", "ppt", "pptx", "doc", "docx", "xls", "xlsx", "txt", "csv", "png", "jpg", "jpeg", "webp"}
MIME_BY_EXT = {
    "pdf": "application/pdf", "ppt": "application/vnd.ms-powerpoint", "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "doc": "application/msword", "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "xls": "application/vnd.ms-excel", "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "txt": "text/plain", "csv": "text/csv", "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webp": "image/webp",
}


def validate_file(filename: str, data: bytes, max_bytes: int) -> tuple[str, str]:
    ext = Path(filename).suffix.lower().lstrip(".")
    if ext not in ALLOWED:
        raise AppError(422, "FILE_TYPE_NOT_ALLOWED", "Этот тип файла не поддерживается")
    if len(data) > max_bytes:
        raise AppError(413, "FILE_TOO_LARGE", "Файл превышает допустимый размер")
    if not data:
        raise AppError(422, "EMPTY_FILE", "Пустой файл нельзя загрузить")
    ok = True
    if ext == "pdf": ok = data.startswith(b"%PDF-")
    elif ext == "png": ok = data.startswith(b"\x89PNG\r\n\x1a\n")
    elif ext in {"jpg", "jpeg"}: ok = data.startswith(b"\xff\xd8\xff")
    elif ext == "webp": ok = len(data) > 12 and data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    elif ext in {"docx", "xlsx", "pptx"}: ok = data.startswith(b"PK\x03\x04")
    elif ext in {"doc", "xls", "ppt"}: ok = data.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")
    elif ext in {"txt", "csv"}:
        ok = b"\x00" not in data[:4096]
        if ok:
            try: data.decode("utf-8")
            except UnicodeDecodeError: ok = False
    if not ok:
        raise AppError(422, "FILE_SIGNATURE_MISMATCH", "Содержимое файла не соответствует его расширению")
    return ext, MIME_BY_EXT[ext]
