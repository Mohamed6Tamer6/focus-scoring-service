from fpdf import FPDF
from datetime import datetime

class FocusReportPDF(FPDF):
    def header(self):
        self.set_fill_color(30, 33, 48)  
        self.rect(0, 0, 210, 40, 'F')
        
        self.set_text_color(255, 255, 255)
        self.set_font('helvetica', 'B', 24)
        self.cell(0, 25, 'AI Focus Tracker', 0, 1, 'C')
        
        self.set_font('helvetica', '', 12)
        self.set_text_color(200, 200, 200)
        self.cell(0, -5, 'Session Analysis Report', 0, 1, 'C')
        self.ln(20)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Generated on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} | Page {self.page_no()}', 0, 0, 'C')

    def chapter_title(self, label):
        self.set_font('helvetica', 'B', 14)
        self.set_fill_color(240, 240, 240)
        self.set_text_color(30, 33, 48)
        self.cell(0, 10, f"  {label}", 0, 1, 'L', fill=True)
        self.ln(4)

    def metric_box(self, label, value, x, y, w, h, color=(76, 175, 80)):
        self.set_draw_color(*color)
        self.set_line_width(1)
        self.rect(x, y, w, h)
        
        self.set_xy(x, y + 2)
        self.set_font('helvetica', '', 10)
        self.set_text_color(100, 100, 100)
        self.cell(w, 5, label, 0, 1, 'C')
        
        self.set_xy(x, y + 8)
        self.set_font('helvetica', 'B', 14)
        self.set_text_color(*color)
        self.cell(w, 10, value, 0, 1, 'C')

def generate_pdf_report(report_data):
    pdf = FocusReportPDF()
    pdf.add_page()
    
    # 1. Summary Section
    pdf.chapter_title("Session Overview")
    
    total_session_duration = report_data['total_time']
    focus_time = report_data['focus_time']
    unfocus_time = report_data['unfocus_time']
    absence_time = report_data['absence_time']
    
    # Calculate focus rate while present
    present_time = total_session_duration - absence_time
    focus_rate = (focus_time / max(present_time, 0.1)) * 100
    focus_rate = min(focus_rate, 100.0)
    
    # Draw Metric Boxes - 5 boxes
    pdf.metric_box("Total Session", f"{total_session_duration:.1f}s", 10, 65, 36, 20, (33, 150, 243))
    pdf.metric_box("Focus Time", f"{focus_time:.1f}s", 50, 65, 36, 20, (76, 175, 80))
    pdf.metric_box("Unfocus", f"{unfocus_time:.1f}s", 90, 65, 36, 20, (255, 82, 82))
    pdf.metric_box("Absence", f"{absence_time:.1f}s", 130, 65, 36, 20, (255, 193, 7))
    pdf.metric_box("Blinks", str(report_data['total_blinks']), 170, 65, 30, 20, (156, 39, 176))
    
    pdf.ln(25)
    
    # 2. Rating Section
    if focus_rate >= 85:
        rating, color = "EXCELLENT", (76, 175, 80)
    elif focus_rate >= 70:
        rating, color = "GOOD", (139, 195, 74)
    elif focus_rate >= 50:
        rating, color = "FAIR", (255, 193, 7)
    else:
        rating, color = "POOR", (244, 67, 54)
        
    pdf.set_fill_color(*color)
    pdf.rect(10, 95, 190, 15, 'F')
    pdf.set_xy(10, 95)
    pdf.set_font('helvetica', 'B', 16)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(190, 15, f"OVERALL RATING: {rating} (Focus: {focus_rate:.1f}%)", 0, 1, 'C')
    
    pdf.ln(10)
    
    # 3. Detailed Tables
    if report_data['unfocused_periods']:
        pdf.chapter_title("Detailed Unfocus Events")
        
        # Table Header
        pdf.set_font('helvetica', 'B', 11)
        pdf.set_fill_color(220, 220, 220)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(15, 10, "#", 1, 0, 'C', fill=True)
        pdf.cell(60, 10, "Start Time", 1, 0, 'C', fill=True)
        pdf.cell(60, 10, "End Time", 1, 0, 'C', fill=True)
        pdf.cell(55, 10, "Duration (sec)", 1, 1, 'C', fill=True)
        
        pdf.set_font('helvetica', '', 10)
        for i, p in enumerate(report_data['unfocused_periods'], 1):
            pdf.cell(15, 8, str(i), 1, 0, 'C')
            pdf.cell(60, 8, p['start'].strftime('%H:%M:%S'), 1, 0, 'C')
            pdf.cell(60, 8, p['end'].strftime('%H:%M:%S'), 1, 0, 'C')
            pdf.cell(55, 8, f"{p['duration']:.1f}s", 1, 1, 'C')
        pdf.ln(10)

    if report_data['absence_periods']:
        pdf.chapter_title("Detailed Absence Events")
        
        # Table Header
        pdf.set_font('helvetica', 'B', 11)
        pdf.set_fill_color(220, 220, 220)
        pdf.set_text_color(0, 0, 0)
        pdf.cell(15, 10, "#", 1, 0, 'C', fill=True)
        pdf.cell(60, 10, "Start Time", 1, 0, 'C', fill=True)
        pdf.cell(60, 10, "End Time", 1, 0, 'C', fill=True)
        pdf.cell(55, 10, "Duration (sec)", 1, 1, 'C', fill=True)
        
        pdf.set_font('helvetica', '', 10)
        for i, p in enumerate(report_data['absence_periods'], 1):
            pdf.cell(15, 8, str(i), 1, 0, 'C')
            pdf.cell(60, 8, p['start'].strftime('%H:%M:%S'), 1, 0, 'C')
            pdf.cell(60, 8, p['end'].strftime('%H:%M:%S'), 1, 0, 'C')
            pdf.cell(55, 8, f"{p['duration']:.1f}s", 1, 1, 'C')

    return bytes(pdf.output())
