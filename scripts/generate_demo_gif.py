import os
from PIL import Image, ImageDraw, ImageFont

def draw_rounded_rect(draw, box, radius, fill=None, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)

def generate_gif(output_path="docs/demo.gif"):
    width, height = 860, 480
    
    # Try loading system font, fallback to default
    try:
        font_large = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 22)
        font_bold = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 16)
        font_main = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 15)
        font_sm = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 13)
        font_mono = ImageFont.truetype("/System/Library/Fonts/Supplemental/Courier New.ttf", 14)
    except Exception:
        font_large = font_bold = font_main = font_sm = font_mono = ImageFont.load_default()

    frames = []

    # Palette
    bg_dark = (11, 14, 20)           # #0b0e14
    card_bg = (24, 29, 42)           # #181d2a
    panel_bg = (19, 23, 34)          # #131722
    border_col = (255, 255, 255, 25) # rgba border
    text_white = (255, 255, 255)
    text_muted = (139, 148, 158)
    text_subtle = (100, 116, 139)
    brand_blue = (56, 189, 248)       # #38bdf8
    warning_amber = (245, 158, 11)   # #f59e0b
    success_green = (16, 185, 129)    # #10b981
    danger_red = (244, 63, 94)        # #f43f5e
    slack_purple = (74, 21, 75)

    def base_frame(title="Cosignal Dual-Control Approval Flow"):
        img = Image.new("RGB", (width, height), bg_dark)
        draw = ImageDraw.Draw(img)
        
        # Header bar
        draw_rounded_rect(draw, (20, 16, width - 20, 60), 8, fill=panel_bg, outline=(40, 48, 64))
        # Window dots
        draw.ellipse((34, 33, 44, 43), fill=(239, 68, 68))
        draw.ellipse((50, 33, 60, 43), fill=(245, 158, 11))
        draw.ellipse((66, 33, 76, 43), fill=(16, 185, 129))
        
        draw.text((95, 27), "Cosignal — Dual-Control Financial Guardrails", font=font_bold, fill=text_white)
        draw.text((width - 180, 29), "● LIVE MONITOR", font=font_sm, fill=success_green)
        
        return img, draw

    # STEP 1: Agent attempts payment (3 frames)
    for i in range(3):
        img, draw = base_frame()
        
        # Left Panel: Agent Code / Execution
        draw_rounded_rect(draw, (20, 75, 420, 415), 10, fill=card_bg, outline=(45, 55, 75))
        draw.text((35, 90), "🤖 AI Agent: invoice-processor-01", font=font_bold, fill=brand_blue)
        draw.text((35, 115), "Action: Execute Vendor Disbursement", font=font_sm, fill=text_muted)
        
        # Code box
        draw_rounded_rect(draw, (35, 140, 405, 330), 6, fill=(13, 17, 23), outline=(35, 42, 58))
        draw.text((45, 150), "# Python Agent SDK Call", font=font_mono, fill=text_subtle)
        draw.text((45, 175), "decision = cosignal.check(", font=font_mono, fill=text_white)
        draw.text((65, 198), 'action="create_payment",', font=font_mono, fill=brand_blue)
        draw.text((65, 221), 'vendor="Acme Supplies",', font=font_mono, fill=text_white)
        draw.text((65, 244), 'amount=15000.00,', font=font_mono, fill=warning_amber)
        draw.text((65, 267), 'wait=300', font=font_mono, fill=text_white)
        draw.text((45, 290), ")", font=font_mono, fill=text_white)
        
        # Progress status
        dots = "." * (i + 1)
        draw_rounded_rect(draw, (35, 350, 405, 395), 6, fill=(26, 32, 44), outline=(45, 55, 75))
        draw.text((50, 363), f"⚡ Agent requesting $15,000.00 check{dots}", font=font_bold, fill=brand_blue)

        # Right Panel: Cosignal Engine (evaluating)
        draw_rounded_rect(draw, (440, 75, width - 20, 415), 10, fill=card_bg, outline=(45, 55, 75))
        draw.text((455, 90), "🛡️ Cosignal Policy Engine", font=font_bold, fill=text_white)
        draw.text((455, 115), "Evaluating active rule set...", font=font_sm, fill=text_muted)
        
        # Rule check card
        draw_rounded_rect(draw, (455, 140, width - 35, 220), 8, fill=panel_bg, outline=(40, 48, 64))
        draw.text((470, 155), "Rule #high-value-payment", font=font_bold, fill=text_white)
        draw.text((470, 180), "Condition: amount > $10,000.00", font=font_sm, fill=text_subtle)
        
        frames.append(img)

    # STEP 2: Policy Blocks Payment & Requests Human Approval (3 frames)
    for i in range(3):
        img, draw = base_frame()
        
        # Left Panel: Agent HELD
        draw_rounded_rect(draw, (20, 75, 420, 415), 10, fill=card_bg, outline=(245, 158, 11))
        draw.text((35, 90), "🤖 AI Agent: invoice-processor-01", font=font_bold, fill=brand_blue)
        draw.text((35, 115), "Status: PAUSED (Awaiting Human)", font=font_sm, fill=warning_amber)
        
        # Code box
        draw_rounded_rect(draw, (35, 140, 405, 330), 6, fill=(13, 17, 23), outline=(35, 42, 58))
        draw.text((45, 150), "# Agent paused synchronously", font=font_mono, fill=text_subtle)
        draw.text((45, 175), "decision = cosignal.check(...)", font=font_mono, fill=text_white)
        draw.text((45, 205), "--> decision.allowed: ", font=font_mono, fill=text_muted)
        draw.text((215, 205), "FALSE (HELD)", font=font_mono, fill=warning_amber)
        draw.text((45, 235), '--> reason: "High value payment"', font=font_mono, fill=warning_amber)
        draw.text((45, 265), "--> waiting for reviewer...", font=font_mono, fill=brand_blue)
        
        # Status Box
        draw_rounded_rect(draw, (35, 345, 405, 398), 6, fill=(45, 30, 10), outline=warning_amber)
        draw.text((50, 360), "🛑 PAYMENT BLOCKED ($15,000)", font=font_bold, fill=warning_amber)
        draw.text((50, 378), "Policy limit $10,000 exceeded", font=font_sm, fill=text_white)

        # Right Panel: Approvals Inbox + Slack Notification
        draw_rounded_rect(draw, (440, 75, width - 20, 415), 10, fill=card_bg, outline=(55, 65, 85))
        draw.text((455, 90), "📥 Approvals Inbox & Alerts", font=font_bold, fill=text_white)
        
        # Slack alert toast
        draw_rounded_rect(draw, (455, 125, width - 35, 195), 8, fill=(40, 20, 45), outline=(120, 40, 130))
        draw.text((470, 135), "🔔 Slack Alert (#finance-approvals)", font=font_bold, fill=(240, 180, 250))
        draw.text((470, 160), "High-Value Payment $15,000 to Acme Supplies", font=font_sm, fill=text_white)
        
        # Approval card waiting
        draw_rounded_rect(draw, (455, 210, width - 35, 395), 8, fill=panel_bg, outline=warning_amber)
        draw.text((470, 225), "PENDING APPROVAL #req-84920", font=font_bold, fill=warning_amber)
        draw.text((470, 255), "Vendor: Acme Supplies", font=font_main, fill=text_white)
        draw.text((470, 280), "Amount: $15,000.00", font=font_large, fill=warning_amber)
        draw.text((470, 312), "Agent: invoice-processor-01", font=font_sm, fill=text_muted)
        
        # Buttons (Approve / Reject)
        draw_rounded_rect(draw, (470, 345, 580, 382), 6, fill=success_green)
        draw.text((492, 356), "Approve", font=font_bold, fill=text_white)
        
        draw_rounded_rect(draw, (595, 345, 690, 382), 6, fill=(40, 45, 55), outline=(80, 90, 110))
        draw.text((620, 356), "Reject", font=font_bold, fill=text_muted)
        
        frames.append(img)

    # STEP 3: Human Clicks Approve (Cursor animation, 3 frames)
    for i in range(3):
        img, draw = base_frame()
        
        # Left Panel: Agent HELD
        draw_rounded_rect(draw, (20, 75, 420, 415), 10, fill=card_bg, outline=(245, 158, 11))
        draw.text((35, 90), "🤖 AI Agent: invoice-processor-01", font=font_bold, fill=brand_blue)
        draw.text((35, 115), "Status: PAUSED (Awaiting Human)", font=font_sm, fill=warning_amber)
        
        draw_rounded_rect(draw, (35, 140, 405, 330), 6, fill=(13, 17, 23), outline=(35, 42, 58))
        draw.text((45, 150), "# Agent paused synchronously", font=font_mono, fill=text_subtle)
        draw.text((45, 175), "decision = cosignal.check(...)", font=font_mono, fill=text_white)
        draw.text((45, 205), "--> decision.allowed: ", font=font_mono, fill=text_muted)
        draw.text((215, 205), "WAITING...", font=font_mono, fill=warning_amber)
        
        draw_rounded_rect(draw, (35, 345, 405, 398), 6, fill=(45, 30, 10), outline=warning_amber)
        draw.text((50, 360), "🛑 PAYMENT BLOCKED ($15,000)", font=font_bold, fill=warning_amber)
        draw.text((50, 378), "Policy limit $10,000 exceeded", font=font_sm, fill=text_white)

        # Right Panel: Approvals Inbox with click on Approve
        draw_rounded_rect(draw, (440, 75, width - 20, 415), 10, fill=card_bg, outline=(55, 65, 85))
        draw.text((455, 90), "📥 Approvals Inbox & Alerts", font=font_bold, fill=text_white)
        
        draw_rounded_rect(draw, (455, 125, width - 35, 195), 8, fill=(40, 20, 45), outline=(120, 40, 130))
        draw.text((470, 135), "🔔 Slack Alert (#finance-approvals)", font=font_bold, fill=(240, 180, 250))
        draw.text((470, 160), "High-Value Payment $15,000 to Acme Supplies", font=font_sm, fill=text_white)
        
        draw_rounded_rect(draw, (455, 210, width - 35, 395), 8, fill=panel_bg, outline=brand_blue)
        draw.text((470, 225), "REVIEWING BY: Alex (Finance Lead)", font=font_bold, fill=brand_blue)
        draw.text((470, 255), "Vendor: Acme Supplies", font=font_main, fill=text_white)
        draw.text((470, 280), "Amount: $15,000.00", font=font_large, fill=warning_amber)
        
        # Click effect on Approve button
        btn_fill = (5, 150, 100) if i == 2 else success_green
        draw_rounded_rect(draw, (470, 345, 580, 382), 6, fill=btn_fill, outline=text_white, width=2)
        draw.text((492, 356), "Approve", font=font_bold, fill=text_white)
        
        draw_rounded_rect(draw, (595, 345, 690, 382), 6, fill=(40, 45, 55), outline=(80, 90, 110))
        draw.text((620, 356), "Reject", font=font_bold, fill=text_muted)
        
        # Cursor icon moving towards/clicking approve button
        cursor_x = 560 - (2 - i) * 30
        cursor_y = 370 - (2 - i) * 15
        draw.polygon([(cursor_x, cursor_y), (cursor_x + 12, cursor_y + 16), (cursor_x + 6, cursor_y + 16), (cursor_x, cursor_y + 22)], fill=text_white)
        
        frames.append(img)

    # STEP 4: Approved! Agent Resumes & Audit Trail Logged (4 frames)
    for i in range(4):
        img, draw = base_frame()
        
        # Left Panel: Agent RESUMED & SUCCESSFUL
        draw_rounded_rect(draw, (20, 75, 420, 415), 10, fill=card_bg, outline=success_green)
        draw.text((35, 90), "🤖 AI Agent: invoice-processor-01", font=font_bold, fill=brand_blue)
        draw.text((35, 115), "Status: RESUMED & COMPLETED", font=font_sm, fill=success_green)
        
        # Code box
        draw_rounded_rect(draw, (35, 140, 405, 330), 6, fill=(13, 17, 23), outline=(35, 42, 58))
        draw.text((45, 150), "# Human approval received", font=font_mono, fill=success_green)
        draw.text((45, 175), "decision = cosignal.check(...)", font=font_mono, fill=text_white)
        draw.text((45, 205), "--> decision.allowed: ", font=font_mono, fill=text_muted)
        draw.text((215, 205), "TRUE (APPROVED)", font=font_mono, fill=success_green)
        draw.text((45, 235), '--> decision.by: "alex@company.com"', font=font_mono, fill=brand_blue)
        draw.text((45, 265), "pay(invoice)  # Dispatched!", font=font_mono, fill=success_green)
        
        # Success status box
        draw_rounded_rect(draw, (35, 345, 405, 398), 6, fill=(10, 45, 30), outline=success_green)
        draw.text((50, 360), "✅ PAYMENT DISPATCHED ($15,000)", font=font_bold, fill=success_green)
        draw.text((50, 378), "Approved by Alex (Dual-Control Verified)", font=font_sm, fill=text_white)

        # Right Panel: Immutable Audit Trail Log
        draw_rounded_rect(draw, (440, 75, width - 20, 415), 10, fill=card_bg, outline=success_green)
        draw.text((455, 90), "📜 Append-Only Audit Trail", font=font_bold, fill=text_white)
        draw.text((455, 115), "Cryptographic Record #84920 Saved", font=font_sm, fill=success_green)
        
        # Audit Log Box
        draw_rounded_rect(draw, (455, 140, width - 35, 395), 8, fill=(13, 17, 23), outline=(35, 42, 58))
        draw.text((470, 155), "TIMESTAMP: 2026-10-08T14:58:12Z", font=font_mono, fill=text_subtle)
        draw.text((470, 180), "ACTION: create_payment", font=font_mono, fill=brand_blue)
        draw.text((470, 205), "PAYEE: Acme Supplies", font=font_mono, fill=text_white)
        draw.text((470, 230), "AMOUNT: $15,000.00 USD", font=font_mono, fill=warning_amber)
        draw.text((470, 255), "POLICY: high-value-payment", font=font_mono, fill=text_muted)
        draw.text((470, 280), "DECISION: APPROVED", font=font_mono, fill=success_green)
        draw.text((470, 305), "REVIEWER: alex@company.com", font=font_mono, fill=brand_blue)
        draw.text((470, 330), "HASH: 8f9a2b1c4e7d...", font=font_mono, fill=text_subtle)
        
        draw_rounded_rect(draw, (470, 360, width - 50, 385), 4, fill=(20, 50, 35))
        draw.text((480, 366), "🔒 Immutable audit record stored in DB", font=font_sm, fill=success_green)
        
        frames.append(img)

    # Save as animated GIF
    durations = [1200, 1200, 1200, 1500, 1500, 1500, 800, 800, 1200, 1800, 1800, 1800, 2500]
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0
    )
    print(f"GIF successfully created at {output_path}")

if __name__ == "__main__":
    generate_gif()
