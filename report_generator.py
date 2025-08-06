import os
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from config import Config

class ReportGenerator:
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        
        # Create output directory if it doesn't exist
        os.makedirs(self.config.REPORT_OUTPUT_DIR, exist_ok=True)
    
    def generate_weekly_report(self, mentions: List[Dict[str, Any]]) -> str:
        """Generate a PDF report for the weekly mentions"""
        # Calculate date range for the report
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=7)
        
        # Create filename with timestamp
        timestamp = end_date.strftime("%Y%m%d_%H%M%S")
        filename = f"twitter_clone_report_{timestamp}.pdf"
        filepath = os.path.join(self.config.REPORT_OUTPUT_DIR, filename)
        
        try:
            # Create PDF document
            doc = SimpleDocTemplate(filepath, pagesize=letter)
            styles = getSampleStyleSheet()
            story = []
            
            # Add title
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=18,
                spaceAfter=30,
                alignment=1  # Center alignment
            )
            story.append(Paragraph("Twitter Clone Monitor Report", title_style))
            
            # Add date range
            date_range = f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
            story.append(Paragraph(f"Report Period: {date_range}", styles['Heading2']))
            story.append(Spacer(1, 0.2 * inch))
            
            # Add summary
            total_mentions = len(mentions)
            handles_mentioned = set(m['handle'] for m in mentions)
            summary = (
                f"<b>Total Mentions:</b> {total_mentions}<br/>"
                f"<b>Handles Mentioned:</b> {', '.join(f'@{h}' for h in handles_mentioned) if handles_mentioned else 'None'}"
            )
            story.append(Paragraph(summary, styles['Normal']))
            story.append(Spacer(1, 0.3 * inch))
            
            # Group mentions by handle
            mentions_by_handle = {}
            for mention in mentions:
                handle = mention['handle']
                if handle not in mentions_by_handle:
                    mentions_by_handle[handle] = []
                mentions_by_handle[handle].append(mention)
            
            # Create a section for each handle
            for handle, handle_mentions in mentions_by_handle.items():
                story.append(Paragraph(f"@{handle} Mentions", styles['Heading3']))
                story.append(Spacer(1, 0.1 * inch))
                
                # Create table for mentions
                data = [["Author", "Date", "Tweet"]]
                for mention in handle_mentions:
                    # Format date
                    date_str = datetime.fromisoformat(mention['timestamp']).strftime('%Y-%m-%d %H:%M')
                    
                    # Truncate tweet text if too long
                    tweet_text = mention['text']
                    if len(tweet_text) > 80:
                        tweet_text = tweet_text[:77] + "..."
                    
                    data.append([
                        f"@{mention['author']}",
                        date_str,
                        tweet_text
                    ])
                
                # Create table and style it
                table = Table(data)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                story.append(table)
                story.append(Spacer(1, 0.3 * inch))
            
            # Build PDF
            doc.build(story)
            self.logger.info(f"Generated report: {filepath}")
            return filepath
        
        except Exception as e:
            self.logger.error(f"Error generating report: {e}")
            raise