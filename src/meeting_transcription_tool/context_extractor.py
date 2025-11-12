"""
Smart context extraction from filenames and metadata.

Extracts meeting context, participant names, dates, and times from file information.
"""
from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Optional, Tuple
from pathlib import Path


def extract_context_from_filename(filename: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract meeting context and participant names from filename.
    
    Args:
        filename: Name of the audio file
    
    Returns:
        Tuple of (context_description, participant_names)
        
    Examples:
        "Ian Laiks 1on1 10-30 12-10.m4a" -> ("1-on-1 meeting", "Ian Laiks")
        "Team Standup 2024-01-15.m4a" -> ("Team standup meeting", None)
        "Sarah John Interview 03-20.m4a" -> ("Interview", "Sarah, John")
    """
    # Remove extension
    name = Path(filename).stem
    
    # Common meeting type patterns
    meeting_types = {
        r'1on1|1-on-1|one-on-one': '1-on-1 meeting',
        r'interview': 'Interview',
        r'standup|stand-up|daily': 'Daily standup meeting',
        r'review|retrospective|retro': 'Review meeting',
        r'planning|sprint planning': 'Planning meeting',
        r'demo|demonstration': 'Demo meeting',
        r'sync|synch': 'Sync meeting',
        r'kickoff|kick-off': 'Kickoff meeting',
        r'townhall|town hall|all-hands': 'All-hands meeting',
        r'call|conference': 'Conference call',
    }
    
    context = None
    for pattern, description in meeting_types.items():
        if re.search(pattern, name, re.IGNORECASE):
            context = description
            break
    
    # Extract names - improved pattern matching
    # Look for capitalized words that are likely names
    # Pattern: First letter capital, rest lowercase, 2+ characters, not common terms
    words = re.findall(r'\b[A-Z][a-z]{2,}\b', name)
    
    # Extended exclude terms
    exclude_terms = {
        'Meeting', 'Call', 'Interview', 'Demo', 'Sync', 'Team', 'Review', 'Daily', 'Sprint',
        'Performance', 'Quarterly', 'Annual', 'Weekly', 'Monthly', 'Final', 'Proof', 'Audio',
        'Transcript', 'Recording', 'Session', 'Standup', 'Planning', 'Retro', 'Kickoff',
        'Townhall', 'Conference', 'Discussion', 'Presentation', 'Workshop', 'Training',
        'January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
        'September', 'October', 'November', 'December', 'Monday', 'Tuesday', 'Wednesday',
        'Thursday', 'Friday', 'Saturday', 'Sunday', 'Q1', 'Q2', 'Q3', 'Q4', '2024', '2025'
    }
    
    # Also exclude time patterns and common words
    names = []
    for w in words:
        w_lower = w.lower()
        # Skip if it's an excluded term, a number, or too short
        if (w not in exclude_terms and 
            w_lower not in exclude_terms and
            not re.match(r'^\d', w) and
            len(w) >= 2 and
            w_lower not in ['am', 'pm', 'on', 'at', 'the', 'and', 'with', 'for', 'from']):
            names.append(w)
    
    participant_names = None
    if names:
        # Take first 4 names (in case of multiple participants)
        participant_names = ', '.join(names[:4])
    
    # Build context description
    if context and participant_names:
        context = f"{context} with {participant_names}"
    elif context:
        context = context
    elif participant_names:
        context = f"Meeting with {participant_names}"
    
    return context, participant_names


def extract_date_from_filename(filename: str) -> Optional[datetime]:
    """
    Extract date from filename.
    
    Supports formats:
    - YYYY-MM-DD
    - MM-DD-YYYY
    - MM-DD
    - YYYYMMDD
    """
    name = Path(filename).stem
    
    # Try various date patterns
    patterns = [
        (r'(\d{4})-(\d{2})-(\d{2})', '%Y-%m-%d'),  # 2024-01-15
        (r'(\d{2})-(\d{2})-(\d{4})', '%m-%d-%Y'),  # 01-15-2024
        (r'(\d{4})(\d{2})(\d{2})', '%Y%m%d'),      # 20240115
        (r'(\d{2})-(\d{2})', '%m-%d'),             # 01-15 (current year assumed)
    ]
    
    for pattern, fmt in patterns:
        match = re.search(pattern, name)
        if match:
            try:
                date_str = '-'.join(match.groups())
                date_obj = datetime.strptime(date_str, fmt)
                # If only month-day, add current year
                if fmt == '%m-%d':
                    date_obj = date_obj.replace(year=datetime.now().year)
                return date_obj
            except ValueError:
                continue
    
    return None


def extract_time_from_filename(filename: str) -> Optional[str]:
    """
    Extract time from filename.
    
    Supports formats:
    - HH-MM (24-hour)
    - HH-MM-AM/PM
    """
    name = Path(filename).stem
    
    # Time patterns
    patterns = [
        r'(\d{1,2})-(\d{2})\s*(am|pm)',  # 12-30 PM
        r'(\d{1,2})-(\d{2})',            # 14-30
    ]
    
    for pattern in patterns:
        match = re.search(pattern, name, re.IGNORECASE)
        if match:
            groups = match.groups()
            hour = int(groups[0])
            minute = int(groups[1])
            
            if len(groups) > 2 and groups[2]:  # AM/PM format
                period = groups[2].lower()
                if period == 'pm' and hour < 12:
                    hour += 12
                elif period == 'am' and hour == 12:
                    hour = 0
            
            return f"{hour:02d}:{minute:02d}"
    
    return None


def get_file_creation_date(file_path: str) -> Optional[datetime]:
    """Get file creation date from metadata."""
    try:
        stat = os.stat(file_path)
        # Use creation time on Windows, modified time on Unix
        timestamp = stat.st_ctime if hasattr(stat, 'st_ctime') else stat.st_mtime
        return datetime.fromtimestamp(timestamp)
    except Exception:
        return None


def extract_full_context(file_path: str) -> str:
    """
    Extract complete context from filename and metadata.
    
    Returns a comprehensive context string suitable for AI speaker identification.
    """
    filename = os.path.basename(file_path)
    
    # Extract from filename
    context, names = extract_context_from_filename(filename)
    file_date = extract_date_from_filename(filename)
    file_time = extract_time_from_filename(filename)
    
    # Fallback to file metadata if no date in filename
    if not file_date:
        file_date = get_file_creation_date(file_path)
    
    # Build comprehensive context
    context_parts = []
    
    if context:
        context_parts.append(context)
    
    if file_date:
        date_str = file_date.strftime("%B %d, %Y")
        context_parts.append(f"recorded on {date_str}")
    
    if file_time:
        context_parts.append(f"at {file_time}")
    
    if not context_parts:
        return "Meeting or conversation"
    
    return ", ".join(context_parts)


def format_context_for_display(file_path: str) -> str:
    """Format extracted context for console display."""
    context = extract_full_context(file_path)
    _, names = extract_context_from_filename(os.path.basename(file_path))
    
    lines = [f"[Context] {context}"]
    if names:
        lines.append(f"[Participants] {names}")
    
    return "\n".join(lines)

