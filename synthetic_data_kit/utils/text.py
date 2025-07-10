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
    
    # Fallback: split chunks that are still too long using sentence boundaries
    final_chunks = []
    for chunk in chunks:
        if len(chunk) <= chunk_size:
            final_chunks.append(chunk)
        else:
            sub_chunks = _split_long_chunk_by_sentences(chunk, chunk_size, overlap)
            final_chunks.extend(sub_chunks)
    
    return final_chunks


def _split_long_chunk_by_sentences(chunk: str, chunk_size: int, overlap: int) -> List[str]:
    """Split a long chunk by finding closest sentence boundaries to chunk_size"""
    sentences = chunk.split('. ')
    
    # If no sentence separators found, fall back to word boundaries
    if len(sentences) == 1:
        return _split_by_words(chunk, chunk_size, overlap)
    
    chunks = []
    current_text = ""
    
    i = 0
    while i < len(sentences):
        sentence = sentences[i]
        # Restore the period (except potentially for the last sentence)
        if i < len(sentences) - 1:
            sentence_with_period = sentence + '. '
        else:
            sentence_with_period = sentence
        
        # Check if adding this sentence would exceed chunk_size
        if len(current_text) + len(sentence_with_period) > chunk_size and current_text:
            # Save current chunk
            chunks.append(current_text.strip())
            
            # Start new chunk with overlap
            overlap_text = _get_sentence_overlap(current_text, overlap)
            current_text = overlap_text + sentence_with_period
        else:
            current_text += sentence_with_period
        
        i += 1
    
    # Add the remaining text as the last chunk
    if current_text.strip():
        chunks.append(current_text.strip())
    
    return chunks


def _split_by_words(text: str, chunk_size: int, overlap: int) -> List[str]:
    """Split text by words when no sentence separators are available"""
    words = text.split()
    chunks = []
    current_text = ""
    
    i = 0
    while i < len(words):
        word = words[i]
        word_with_space = word + (' ' if i < len(words) - 1 else '')
        
        # Check if adding this word would exceed chunk_size
        if len(current_text) + len(word_with_space) > chunk_size and current_text:
            # Save current chunk
            chunks.append(current_text.strip())
            
            # Start new chunk with overlap
            overlap_text = _get_word_overlap(current_text, overlap)
            current_text = overlap_text + word_with_space
        else:
            current_text += word_with_space
        
        i += 1
    
    # Add the remaining text as the last chunk
    if current_text.strip():
        chunks.append(current_text.strip())
    
    return chunks


def _get_sentence_overlap(text: str, target_overlap: int) -> str:
    """Get overlap text from the end of a chunk using sentence boundaries"""
    if len(text) <= target_overlap:
        return text
    
    sentences = text.split('. ')
    if len(sentences) <= 1:
        # No sentence boundaries, use character overlap
        return text[-target_overlap:] + ' '
    
    # Build overlap from the end
    overlap_sentences = []
    current_length = 0
    
    for i in range(len(sentences) - 1, -1, -1):
        sentence = sentences[i]
        if i < len(sentences) - 1:
            sentence_with_period = sentence + '. '
        else:
            sentence_with_period = sentence
        
        if current_length + len(sentence_with_period) <= target_overlap:
            overlap_sentences.insert(0, sentence_with_period)
            current_length += len(sentence_with_period)
        else:
            break
    
    return ''.join(overlap_sentences) if overlap_sentences else text[-target_overlap:] + ' '


def _get_word_overlap(text: str, target_overlap: int) -> str:
    """Get overlap text from the end of a chunk using word boundaries"""
    if len(text) <= target_overlap:
        return text
    
    words = text.split()
    overlap_words = []
    current_length = 0
    
    for word in reversed(words):
        word_with_space = word + ' '
        if current_length + len(word_with_space) <= target_overlap:
            overlap_words.insert(0, word_with_space)
            current_length += len(word_with_space)
        else:
            break
    
    return ''.join(overlap_words) if overlap_words else text[-target_overlap:] + ' '

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