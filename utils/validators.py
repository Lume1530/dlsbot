import re
from typing import Optional

def validate_instagram_link(url: str) -> bool:
    """Validate if URL is a valid Instagram reel/post URL"""
    if not url or not isinstance(url, str):
        return False
    
    # Clean up the URL - remove @ symbol and query parameters
    url = url.strip().lstrip('@')
    url = url.split('?')[0]  # Remove query parameters
    
    patterns = [
        r'instagram\.com/(?:[^/]+/)?(?:p|reel|tv)/([A-Za-z0-9_-]+)',
        r'instagram\.com/reel/([A-Za-z0-9_-]+)',
        r'instagram\.com/p/([A-Za-z0-9_-]+)',
        r'instagram\.com/tv/([A-Za-z0-9_-]+)'
    ]
    
    for pattern in patterns:
        if re.search(pattern, url):
            return True
    return False

def extract_shortcode_from_url(url: str) -> Optional[str]:
    """Extract shortcode from Instagram URL"""
    if not url or not isinstance(url, str):
        return None
    
    # Clean up the URL - remove @ symbol and query parameters
    url = url.strip().lstrip('@')
    url = url.split('?')[0]  # Remove query parameters
    
    patterns = [
        r'instagram\.com/(?:[^/]+/)?(?:p|reel|tv)/([A-Za-z0-9_-]+)',
        r'/(?:p|reel|tv)/([A-Za-z0-9_-]+)',
        r'^([A-Za-z0-9_-]+)$'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def validate_email(email: str) -> bool:
    """Validate email format"""
    if not email or not isinstance(email, str):
        return False
    
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email.strip()))

def validate_usdt_address(address: str) -> bool:
    """Validate USDT ERC20 address format"""
    if not address or not isinstance(address, str):
        return False
    
    address = address.strip()
    # Basic Ethereum address validation
    if not address.startswith('0x'):
        return False
    
    if len(address) != 42:
        return False
    
    # Check if all characters after 0x are valid hex
    hex_part = address[2:]
    return all(c in '0123456789abcdefABCDEF' for c in hex_part)

def validate_instagram_handle(handle: str) -> bool:
    """Validate Instagram handle format"""
    if not handle or not isinstance(handle, str):
        return False
    
    handle = handle.strip().lstrip('@')
    # Instagram username rules: 1-30 characters, letters, numbers, periods, underscores
    pattern = r'^[a-zA-Z0-9._]{1,30}$'
    return bool(re.match(pattern, handle))

def validate_upi_address(upi: str) -> bool:
    """Validate UPI address format"""
    if not upi or not isinstance(upi, str):
        return False
    
    upi = upi.strip()
    # Basic UPI validation - should contain @ symbol
    return '@' in upi and len(upi) >= 5