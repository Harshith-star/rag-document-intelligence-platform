from app.services.document_processor import chunk_text, clean_text


def test_clean_text_collapses_whitespace():
    assert clean_text("hello   \n\n world  ") == "hello world"


def test_chunk_text_empty():
    assert chunk_text("") == []


def test_chunk_text_basic():
    text = "a" * 2000
    chunks = chunk_text(text, chunk_size=800, overlap=100)
    assert len(chunks) > 1
    assert all(len(c) <= 800 for c in chunks)
    assert chunks[0][-100:] == chunks[1][:100]
