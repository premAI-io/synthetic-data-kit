# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the terms described in the LICENSE file in
# the root directory of this source tree.
# HTML Parsers

import os
import requests
from typing import Dict, Any, List
from urllib.parse import urlparse, urljoin
import logging

logger = logging.getLogger(__name__)

class HTMLParser:
    """Parser for HTML files and web pages with iframe content extraction"""
    
    def __init__(self, extract_iframe_content: bool = True, max_iframe_depth: int = 3):
        """Initialize the HTML parser
        
        Args:
            extract_iframe_content: Whether to extract content from iframes
            max_iframe_depth: Maximum recursion depth for nested iframes
        """
        self.extract_iframe_content = extract_iframe_content
        self.max_iframe_depth = max_iframe_depth
        self._processed_urls = set()  # Prevent infinite loops
    
    def parse(self, file_path: str) -> str:
        """Parse an HTML file or URL into plain text
        
        Args:
            file_path: Path to the HTML file or URL
            
        Returns:
            Extracted text from the HTML including iframe content
        """
        # Clear processed URLs for new parsing session
        self._processed_urls.clear()
        
        return self._parse_html_content(file_path, depth=0)
    
    def _parse_html_content(self, file_path: str, depth: int = 0) -> str:
        """Internal method to parse HTML content with iframe support
        
        Args:
            file_path: Path to HTML file or URL
            depth: Current recursion depth for iframe processing
            
        Returns:
            Extracted text content
        """
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            raise ImportError("beautifulsoup4 is required for HTML parsing. Install it with: pip install beautifulsoup4")
        
        # Prevent infinite loops and excessive recursion
        if depth > self.max_iframe_depth:
            logger.warning(f"Maximum iframe depth ({self.max_iframe_depth}) reached, skipping: {file_path}")
            return ""
            
        if file_path in self._processed_urls:
            logger.info(f"Already processed URL, skipping to prevent loops: {file_path}")
            return ""
            
        self._processed_urls.add(file_path)
        
        # Get HTML content
        try:
            if file_path.startswith(('http://', 'https://')):
                # It's a URL, fetch content
                response = requests.get(file_path, timeout=10)
                response.raise_for_status()
                html_content = response.text
                base_url = file_path
            else:
                # It's a local file, read it
                with open(file_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                base_url = f"file://{os.path.dirname(os.path.abspath(file_path))}"
        except Exception as e:
            logger.error(f"Error fetching content from {file_path}: {str(e)}")
            return ""
        
        # Parse HTML and extract text
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Process iframes before removing them
        iframe_texts = []
        if self.extract_iframe_content and depth < self.max_iframe_depth:
            iframe_texts = self._extract_iframe_content(soup, base_url, depth)
        
        # Remove script and style elements
        for script in soup(['script', 'style']):
            script.extract()
            
        # Remove iframe elements now that we've processed them
        for iframe in soup.find_all('iframe'):
            iframe.extract()
        
        # Get text from main document
        text = soup.get_text()
        
        # Break into lines and remove leading and trailing space
        lines = (line.strip() for line in text.splitlines())
        # Break multi-headlines into a line each
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        # Drop blank lines
        main_text = '\n'.join(chunk for chunk in chunks if chunk)
        
        # Combine main text with iframe content
        all_texts = [main_text] + iframe_texts
        combined_text = '\n\n'.join(filter(None, all_texts))
        
        return combined_text
    
    def _extract_iframe_content(self, soup, base_url: str, depth: int) -> List[str]:
        """Extract content from all iframes in the document
        
        Args:
            soup: BeautifulSoup object of the current document
            base_url: Base URL for resolving relative iframe URLs
            depth: Current recursion depth
            
        Returns:
            List of extracted text from iframes
        """
        iframe_texts = []
        iframes = soup.find_all('iframe')
        
        logger.info(f"Found {len(iframes)} iframe(s) at depth {depth}")
        
        for i, iframe in enumerate(iframes):
            src = iframe.get('src')
            if not src:
                logger.info(f"Iframe {i+1} has no src attribute, skipping")
                continue
            
            # Resolve relative URLs
            if src.startswith(('http://', 'https://')):
                iframe_url = src
            elif src.startswith('//'):
                # Protocol-relative URL
                protocol = 'https:' if base_url.startswith('https:') else 'http:'
                iframe_url = protocol + src
            elif src.startswith('/'):
                # Absolute path
                parsed_base = urlparse(base_url)
                iframe_url = f"{parsed_base.scheme}://{parsed_base.netloc}{src}"
            else:
                # Relative path
                if base_url.startswith('file://'):
                    # For local files, handle path resolution differently
                    base_dir = base_url[7:]  # Remove 'file://' prefix
                    iframe_path = os.path.join(base_dir, src)
                    iframe_url = iframe_path
                else:
                    iframe_url = urljoin(base_url, src)
            
            logger.info(f"Processing iframe {i+1}: {iframe_url}")
            
            # Skip certain types of iframes that typically don't contain useful text
            skip_patterns = [
                'googletagmanager.com',
                'google-analytics.com',
                'facebook.com/tr',
                'doubleclick.net',
                'ads.',
                'advertising.',
                'analytics.',
                'tracking.',
                '.jpg', '.jpeg', '.png', '.gif', '.svg',  # Image files
                'about:blank'
            ]
            
            if any(pattern in iframe_url.lower() for pattern in skip_patterns):
                logger.info(f"Skipping iframe with likely non-text content: {iframe_url}")
                continue
            
            try:
                # Recursively parse iframe content
                iframe_text = self._parse_html_content(iframe_url, depth + 1)
                if iframe_text.strip():
                    iframe_texts.append(f"{iframe_url}]\n{iframe_text}")
                    logger.info(f"Successfully extracted {len(iframe_text)} characters from iframe {i+1}")
                else:
                    logger.info(f"No text content found in iframe {i+1}")
            except Exception as e:
                logger.error(f"Error processing iframe {i+1} ({iframe_url}): {str(e)}")
                continue
        
        return iframe_texts
    
    def save(self, content: str, output_path: str) -> None: 
        """Save the extracted text to a file
        
        Args:
            content: Extracted text content
            output_path: Path to save the text
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)