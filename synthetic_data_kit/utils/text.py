# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.
# Text processing utilities
import re
import json
from typing import List, Dict, Any

def split_into_chunks(text: str, chunk_size: int = 4000, overlap: int = 200) -> List[str]:
    """Split text into chunks with optional overlap"""
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        if len(current_chunk) + len(para) > chunk_size and current_chunk:
            chunks.append(current_chunk)
            # Keep some overlap for context
            sentences = current_chunk.split('. ')
            if len(sentences) > 3:
                current_chunk = '. '.join(sentences[-3:]) + "\n\n" + para
            else:
                current_chunk = para
        else:
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para
    
    if current_chunk:
        chunks.append(current_chunk)
    
    return chunks

def extract_json_from_text(text: str) -> Dict[str, Any]:
    """Extract JSON from text that might contain markdown or other content"""
    text = text.strip()
    
    # Try to parse as complete JSON
    if text.startswith('{') and text.endswith('}') or text.startswith('[') and text.endswith(']'):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
    
    # Look for JSON within Markdown code blocks
    json_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
    match = re.search(json_pattern, text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass
    
    # Try a more aggressive pattern
    json_pattern = r'\{[\s\S]*\}|\[[\s\S]*\]'
    match = re.search(json_pattern, text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    
    raise ValueError("Could not extract valid JSON from the response")

def clean_extracted_text(text: str) -> str:
    """Clean extracted text by removing control characters and normalizing whitespace
    
    Args:
        text: Raw extracted text
        
    Returns:
        Cleaned text
    """
    if not text:
        return text

    # Remove form feed characters (page breaks) - these are very common in PDFs
    text = text.replace("\x0c", "")

    # Remove other common control characters but preserve newlines and tabs
    control_chars = [
        "\x00", "\x01", "\x02", "\x03", "\x04", "\x05", "\x06", "\x07", 
        "\x08", "\x0b", "\x0e", "\x0f", "\x10", "\x11", "\x12", "\x13", 
        "\x14", "\x15", "\x16", "\x17", "\x18", "\x19", "\x1a", "\x1b", 
        "\x1c", "\x1d", "\x1e", "\x1f", "\x7f",
    ]
    for char in control_chars:
        text = text.replace(char, "")

    # Normalize whitespace - replace multiple consecutive whitespace with single space
    text = re.sub(r"[ \t]+", " ", text)  # Only normalize spaces and tabs, not newlines
    
    # Remove leading/trailing whitespace from each line while preserving line breaks
    lines = text.split("\n")
    lines = [line.strip() for line in lines]

    # Remove empty lines but keep paragraph breaks (max 1 consecutive newline)
    cleaned_lines = []
    consecutive_empty = 0
    for line in lines:
        if line:
            cleaned_lines.append(line)
            consecutive_empty = 0
        else:
            consecutive_empty += 1
            if consecutive_empty <= 1:  # Keep single empty lines for paragraph breaks
                cleaned_lines.append(line)

    text = "\n".join(cleaned_lines)

    # Final cleanup: remove excessive newlines at start/end
    text = text.strip()

    return text