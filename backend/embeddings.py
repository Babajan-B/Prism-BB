"""
Embedding and vision helpers using the new google-genai SDK.

New Gemini Embedding Model Capabilities (gemini-embedding-2-preview):
  - Supports up to 6 images per request (PNG/JPEG)
  - Supports up to 8192 text tokens
  - Supports videos up to 128 seconds (MP4/MOV/H264/H265/AV1/VP9)
  - Supports audio up to 80 seconds (MP3/WAV)
  - Supports PDFs up to 6 pages

Approach:
  - Images are auto-resized to fit API limits
  - Batch processing (up to 6 items per API call)
  - Failed items are silently skipped
  - All embeddings share the same 3072-dim space

References:
  https://ai.google.dev/gemini-api/docs/embeddings
"""

import os
import io
from PIL import Image

from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

MULTIMODAL_EMBEDDING_MODEL = "gemini-embedding-2-preview"  # Public preview
VISION_MODEL = "gemini-2.0-flash-lite"
# Matryoshka Representation Learning: supports flexible output dimensions
# 3072 (default, best quality), 1536, 768 also available for storage/performance trade-off
EMBEDDING_DIM = 3072
MAX_IMAGE_SIZE = (2048, 2048)  # Max dimensions for resizing
# Gemini Embedding limits per file type (from official docs):
# - Images: each image counts toward 8192 token limit, max 6 images per request
# - PDFs: max 6 pages
# - Videos: max 128 seconds
# - Audio: max 80 seconds  
# - Text: max 8192 tokens
MAX_FILE_SIZE_MB = 20  # General file size safety limit
BATCH_SIZE = 6  # Max items per request

_client: genai.Client | None = None


def _get_client() -> genai.Client:
    """Lazily create and cache a Gemini client."""
    global _client
    if _client is None:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY not found. Make sure it is set in the .env file."
            )
        _client = genai.Client(api_key=api_key)
    return _client


def setup_gemini():
    """Warm up the Gemini client (called once on startup)."""
    _get_client()


def _mime_type(file_path: str) -> str:
    """Infer MIME type from file extension for all supported media types."""
    ext = os.path.splitext(file_path)[-1].lower()
    mime_types = {
        # Images
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".bmp": "image/bmp",
        # Videos
        ".mp4": "video/mp4",
        ".mov": "video/quicktime",
        ".avi": "video/x-msvideo",
        ".mkv": "video/x-matroska",
        ".webm": "video/webm",
        # Audio
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".ogg": "audio/ogg",
        ".m4a": "audio/mp4",
        ".flac": "audio/flac",
        ".aac": "audio/aac",
        # Documents
        ".pdf": "application/pdf",
        ".txt": "text/plain",
        ".md": "text/plain",
        ".json": "text/plain",
        ".csv": "text/plain",
    }
    return mime_types.get(ext, "application/octet-stream")


def _media_type(file_path: str) -> str:
    """Categorize file into media type."""
    ext = os.path.splitext(file_path)[-1].lower()
    images = [".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp"]
    videos = [".mp4", ".mov", ".avi", ".mkv", ".webm"]
    audio = [".mp3", ".wav", ".ogg", ".m4a", ".flac", ".aac"]
    text = [".txt", ".md", ".json", ".csv"]
    
    if ext in images:
        return "image"
    elif ext in videos:
        return "video"
    elif ext in audio:
        return "audio"
    elif ext == ".pdf":
        return "pdf"
    elif ext in text:
        return "text"
    return "unknown"


def _resize_image(image_path: str) -> bytes:
    """
    Resize image to fit within Gemini limits.
    Returns resized image bytes.
    """
    try:
        with Image.open(image_path) as img:
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # Resize if too large
            if img.size[0] > MAX_IMAGE_SIZE[0] or img.size[1] > MAX_IMAGE_SIZE[1]:
                img.thumbnail(MAX_IMAGE_SIZE, Image.Resampling.LANCZOS)
            
            # Save to bytes with quality adjustment
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=85, optimize=True)
            output.seek(0)
            
            return output.getvalue()
    except Exception:
        # Fallback: return original file
        with open(image_path, 'rb') as f:
            return f.read()


# ── Unified media embedding ─────────────────────────────────────────────────

def _prepare_content(file_path: str) -> types.Part | str | None:
    """
    Prepare content for embedding based on file type.
    Returns a Part for binary files, string for text files, or None on failure.
    """
    media_type = _media_type(file_path)
    mime = _mime_type(file_path)
    
    try:
        if media_type == "text":
            # Read text files directly as string content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                return f.read()[:8192]  # Limit to 8192 tokens
        
        elif media_type == "image":
            # Resize images before sending
            return types.Part.from_bytes(
                data=_resize_image(file_path),
                mime_type="image/jpeg"
            )
        
        elif media_type == "pdf":
            # Gemini API handles PDFs up to 6 pages natively
            file_size = os.path.getsize(file_path)
            print(f"[PDF] Processing {file_path}, size: {file_size / 1024:.1f}KB")
            
            if file_size > 20 * 1024 * 1024:
                print(f"[PDF] Too large: {file_size / 1024 / 1024:.1f}MB > 20MB")
                return None
            
            with open(file_path, 'rb') as f:
                pdf_bytes = f.read()
            
            print(f"[PDF] Sending {len(pdf_bytes)} bytes to API (max 6 pages)")
            return types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")
        
        else:
            # Binary files: video, audio
            file_size = os.path.getsize(file_path)
            
            # Check file size (API has undocumented limits, stay conservative)
            if file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
                print(f"[FILE] Too large: {file_path} ({file_size / 1024 / 1024:.1f}MB > {MAX_FILE_SIZE_MB}MB)")
                return None
            
            with open(file_path, 'rb') as f:
                return types.Part.from_bytes(
                    data=f.read(),
                    mime_type=mime
                )
    except Exception as e:
        print(f"Failed to prepare {file_path}: {e}")
        return None


def generate_media_embedding_batch(file_paths: list[str]) -> list[list[float] | None]:
    """
    Embed multiple media files (images, videos, audio, PDFs, text) using batching.
    Returns a list of embeddings, with None for failed files.
    """
    if not file_paths:
        return []
    
    client = _get_client()
    embeddings = []
    
    print(f"[EMBED] Processing {len(file_paths)} files in batches of {BATCH_SIZE}")
    
    # Process ONE file at a time to isolate failures
    for file_path in file_paths:
        try:
            print(f"[EMBED] Processing: {os.path.basename(file_path)}")
            content = _prepare_content(file_path)
            
            if content is None:
                print(f"[EMBED]   -> Preparation failed")
                embeddings.append(None)
                continue
            
            # Call API for single item
            print(f"[EMBED]   -> Calling API...")
            result = client.models.embed_content(
                model=MULTIMODAL_EMBEDDING_MODEL,
                contents=[content],  # List with single item
            )
            
            if result.embeddings and len(result.embeddings) > 0:
                embeddings.append(result.embeddings[0].values)
                print(f"[EMBED]   -> Success")
            else:
                print(f"[EMBED]   -> No embedding returned")
                embeddings.append(None)
                
        except Exception as e:
            print(f"[EMBED]   -> API Error: {e}")
            import traceback
            traceback.print_exc()
            embeddings.append(None)
    
    print(f"[EMBED] Total: {len(embeddings)} files, {sum(1 for e in embeddings if e is not None)} successful")
    return embeddings


def generate_image_embedding_batch(image_paths: list[str]) -> list[list[float] | None]:
    """Legacy wrapper for image batch embedding."""
    return generate_media_embedding_batch(image_paths)


def generate_image_embedding(file_path: str) -> list[float] | None:
    """Embed a single file. Returns None on failure."""
    results = generate_media_embedding_batch([file_path])
    return results[0] if results else None


def generate_query_embedding(query: str) -> list[float]:
    """Embed a text query."""
    client = _get_client()
    result = client.models.embed_content(
        model=MULTIMODAL_EMBEDDING_MODEL,
        contents=query,
    )
    return result.embeddings[0].values


# ── Caption generation for all media types ─────────────────────────────────

def generate_media_caption(file_path: str) -> str:
    """
    Generate a caption for any media type.
    Returns empty string on failure.
    """
    media_type = _media_type(file_path)
    
    try:
        client = _get_client()
        
        if media_type == "text":
            # For text files, return first 200 chars as "caption"
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(500)
                return content[:200] + "..." if len(content) > 200 else content
        
        elif media_type == "image":
            image_bytes = _resize_image(file_path)
            response = client.models.generate_content(
                model=VISION_MODEL,
                contents=[
                    types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
                    types.Part.from_text(text="Describe this image concisely in 1-2 sentences."),
                ],
            )
            return response.text.strip()
        
        elif media_type == "video":
            # For videos, sample frames would be ideal, but we'll use a generic prompt
            with open(file_path, 'rb') as f:
                video_bytes = f.read()
            response = client.models.generate_content(
                model=VISION_MODEL,
                contents=[
                    types.Part.from_bytes(data=video_bytes, mime_type=_mime_type(file_path)),
                    types.Part.from_text(text="Describe what happens in this video concisely in 1-2 sentences."),
                ],
            )
            return response.text.strip()
        
        elif media_type == "audio":
            with open(file_path, 'rb') as f:
                audio_bytes = f.read()
            response = client.models.generate_content(
                model=VISION_MODEL,
                contents=[
                    types.Part.from_bytes(data=audio_bytes, mime_type=_mime_type(file_path)),
                    types.Part.from_text(text="Describe this audio concisely in 1-2 sentences."),
                ],
            )
            return response.text.strip()
        
        elif media_type == "pdf":
            # Send PDF directly to API (handles up to 6 pages)
            with open(file_path, 'rb') as f:
                pdf_bytes = f.read()
            
            response = client.models.generate_content(
                model=VISION_MODEL,
                contents=[
                    types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf"),
                    types.Part.from_text(text="Summarize this document concisely in 1-2 sentences."),
                ],
            )
            return response.text.strip()
        
        return ""
    except Exception:
        return ""


# ── Legacy wrappers ─────────────────────────────────

def generate_image_caption(image_path: str) -> str:
    """Legacy wrapper for image caption."""
    return generate_media_caption(image_path)
