import pytest
from app.errors import AppError
from app.files import validate_file


def test_pdf_signature():
    ext, mime = validate_file('deck.pdf', b'%PDF-1.7\nbody', 1000)
    assert ext == 'pdf' and mime == 'application/pdf'


def test_reject_signature_mismatch():
    with pytest.raises(AppError) as e:
        validate_file('fake.pdf', b'not a pdf', 1000)
    assert e.value.code == 'FILE_SIGNATURE_MISMATCH'


def test_reject_large_file():
    with pytest.raises(AppError) as e:
        validate_file('note.txt', b'a' * 20, 10)
    assert e.value.status == 413


def test_accept_utf8_text():
    ext, mime = validate_file('note.txt', 'Привет'.encode(), 1000)
    assert (ext, mime) == ('txt', 'text/plain')
