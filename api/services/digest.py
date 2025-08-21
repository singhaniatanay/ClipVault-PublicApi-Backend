"""Digest service for generating email templates and managing digest preferences."""

from typing import List, Dict, Any
from datetime import datetime
import structlog

logger = structlog.get_logger()


def generate_digest_html(user_name: str, clips: List[Dict[str, Any]], digest_type: str) -> str:
    """Generate HTML digest preview.
    
    Args:
        user_name: User's display name
        clips: List of clip dictionaries
        digest_type: Type of digest ('daily', 'weekly', 'monthly')
        
    Returns:
        Generated HTML content
    """
    # Generate clips HTML
    clips_html = ""
    for clip in clips:
        title = clip.get("title", "Untitled")
        description = clip.get("description", "")
        source_url = clip.get("source_url", "")
        thumbnail_url = clip.get("thumbnail_url", "")
        
        clips_html += f"""
        <div class="clip-item" style="margin-bottom: 20px; padding: 15px; border: 1px solid #e0e0e0; border-radius: 8px;">
            <h3 style="margin: 0 0 10px 0; color: #333;">
                <a href="{source_url}" style="color: #007bff; text-decoration: none;">{title}</a>
            </h3>
            {f'<p style="margin: 0 0 10px 0; color: #666; font-size: 14px;">{description}</p>' if description else ''}
            {f'<img src="{thumbnail_url}" alt="Thumbnail" style="max-width: 200px; height: auto; border-radius: 4px;" />' if thumbnail_url else ''}
        </div>
        """
    
    if not clips:
        clips_html = """
        <div style="text-align: center; padding: 40px; color: #666;">
            <p>No clips saved yet. Start saving your favorite content!</p>
        </div>
        """
    
    # Generate the full HTML template
    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>ClipVault {digest_type.title()} Digest</title>
        <style>
            body {{
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f8f9fa;
            }}
            .container {{
                background-color: white;
                padding: 30px;
                border-radius: 12px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            .header {{
                text-align: center;
                margin-bottom: 30px;
                padding-bottom: 20px;
                border-bottom: 2px solid #007bff;
            }}
            .header h1 {{
                color: #007bff;
                margin: 0;
                font-size: 28px;
            }}
            .header p {{
                color: #666;
                margin: 10px 0 0 0;
                font-size: 16px;
            }}
            .clips-section {{
                margin-bottom: 30px;
            }}
            .clips-section h2 {{
                color: #333;
                margin-bottom: 20px;
                font-size: 20px;
            }}
            .clip-item {{
                margin-bottom: 20px;
                padding: 15px;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                transition: box-shadow 0.2s;
            }}
            .clip-item:hover {{
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            }}
            .clip-item h3 {{
                margin: 0 0 10px 0;
                color: #333;
            }}
            .clip-item h3 a {{
                color: #007bff;
                text-decoration: none;
            }}
            .clip-item h3 a:hover {{
                text-decoration: underline;
            }}
            .clip-item p {{
                margin: 0 0 10px 0;
                color: #666;
                font-size: 14px;
            }}
            .clip-item img {{
                max-width: 200px;
                height: auto;
                border-radius: 4px;
            }}
            .footer {{
                text-align: center;
                margin-top: 30px;
                padding-top: 20px;
                border-top: 1px solid #e0e0e0;
                color: #666;
                font-size: 14px;
            }}
            .footer a {{
                color: #007bff;
                text-decoration: none;
            }}
            .footer a:hover {{
                text-decoration: underline;
            }}
            @media (max-width: 600px) {{
                body {{
                    padding: 10px;
                }}
                .container {{
                    padding: 20px;
                }}
                .header h1 {{
                    font-size: 24px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📚 ClipVault Digest</h1>
                <p>Hello {user_name}!</p>
                <p>Here are your latest saved clips from your {digest_type} digest:</p>
            </div>
            
            <div class="clips-section">
                <h2>📌 Your Latest Clips</h2>
                {clips_html}
            </div>
            
            <div class="footer">
                <p>
                    <a href="https://clipvault.com/digest/unsubscribe?user_id=USER_ID">Unsubscribe from digests</a> | 
                    <a href="https://clipvault.com">Visit ClipVault</a>
                </p>
                <p>Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    logger.debug(
        "Digest HTML generated",
        user_name=user_name,
        clip_count=len(clips),
        digest_type=digest_type
    )
    
    return html_template


def get_digest_subject_line(digest_type: str, clip_count: int) -> str:
    """Generate subject line for digest email.
    
    Args:
        digest_type: Type of digest ('daily', 'weekly', 'monthly')
        clip_count: Number of clips in digest
        
    Returns:
        Email subject line
    """
    if digest_type == "daily":
        return f"📚 Your Daily ClipVault Digest ({clip_count} new clips)"
    elif digest_type == "weekly":
        return f"📚 Your Weekly ClipVault Digest ({clip_count} clips this week)"
    else:  # monthly
        return f"📚 Your Monthly ClipVault Digest ({clip_count} clips this month)"


def format_digest_summary(clips: List[Dict[str, Any]]) -> str:
    """Generate a text summary of the digest.
    
    Args:
        clips: List of clip dictionaries
        
    Returns:
        Text summary
    """
    if not clips:
        return "No clips saved in this period."
    
    summary = f"Found {len(clips)} clip(s):\n\n"
    
    for i, clip in enumerate(clips, 1):
        title = clip.get("title", "Untitled")
        source_url = clip.get("source_url", "")
        summary += f"{i}. {title}\n   {source_url}\n\n"
    
    return summary 