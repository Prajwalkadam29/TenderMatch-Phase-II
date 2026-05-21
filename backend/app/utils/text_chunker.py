from typing import List

def chunk_text(text: str, chunk_size: int = 2000, overlap: int = 200) -> List[str]:
    """
    Split a long text into overlapping chunks, respecting word/sentence boundaries.
    """
    if not text:
        return []
        
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    text_len = len(text)
    
    while start < text_len:
        end = min(start + chunk_size, text_len)
        
        if end < text_len:
            # Try to snap the end to a logical boundary
            window_start = max(start, end - min(200, chunk_size // 2))
            window = text[window_start:end]
            
            # Find best boundary
            for sep in ["\n\n", "\n", ". ", " "]:
                idx = window.rfind(sep)
                if idx != -1:
                    end = window_start + idx + len(sep)
                    break

        # Do not produce empty chunks
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        if end >= text_len:
            break
            
        # Calculate next start
        start = max(0, end - overlap)
        if start > 0:
            window_end = min(text_len, start + min(100, overlap // 2))
            window = text[start:window_end]
            for sep in ["\n\n", "\n", ". ", " "]:
                idx = window.find(sep)
                if idx != -1:
                    start = start + idx + len(sep)
                    break
                    
    return chunks
