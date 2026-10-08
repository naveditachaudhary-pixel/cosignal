import os
from PIL import Image, ImageDraw, ImageFont

def generate_gif(output_path="docs/demo.gif"):
    # 2x Super-sampling scale factor for ultra-crisp Retina text and smooth curves
    S = 2
    canvas_w, canvas_h = 920 * S, 540 * S
    final_w, final_h = 920, 540

    # Load high quality Mac system fonts with proportional sizing for 2x scale
    try:
        font_title = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16 * S)
        font_bold = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 15 * S)
        font_header = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 17 * S)
        font_main = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 14 * S)
        font_sm = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 12 * S)
        font_xs = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 10 * S)
        font_mono = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 13 * S)
        font_amount = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 26 * S)
    except Exception:
        font_title = font_bold = font_header = font_main = font_sm = font_xs = font_mono = font_amount = ImageFont.load_default()

    # Color Palette (Modern Slate & Dark Theme)
    bg_dark = (13, 17, 23)            # #0d1117 Main Canvas
    card_bg = (22, 27, 34)            # #161b22 Panel Card
    panel_bg = (30, 35, 45)           # #1e232d Inner Box
    code_bg = (16, 20, 27)            # #10141b Code Block
    border_subtle = (48, 54, 61)      # #30363d Border
    
    text_white = (240, 246, 252)
    text_muted = (139, 148, 158)
    text_subtle = (100, 116, 139)
    
    brand_blue = (56, 189, 248)       # #38bdf8 Electric Sky Blue
    warning_amber = (245, 158, 11)   # #f59e0b Caution Amber
    success_green = (16, 185, 129)    # #10b981 Emerald Green
    purple_accent = (168, 85, 247)    # #a855f7 Royal Purple
    slack_bg = (34, 18, 38)           # Slack alert container
    slack_border = (112, 45, 120)

    def draw_rounded_rect(draw, box, radius, fill=None, outline=None, width=1):
        x1, y1, x2, y2 = [int(v) for v in box]
        draw.rounded_rectangle((x1, y1, x2, y2), radius=int(radius), fill=fill, outline=outline, width=int(width))

    def draw_badge(draw, box, text, font, bg, fg, border=None):
        draw_rounded_rect(draw, box, (box[3]-box[1])//2, fill=bg, outline=border or fg, width=1*S)
        tw = draw.textlength(text, font=font)
        cx = (box[0] + box[2]) / 2 - tw / 2
        cy = (box[1] + box[3]) / 2 - (font.size / 2)
        draw.text((cx, cy), text, font=font, fill=fg)

    def draw_window_header(draw, active_step=1):
        # Top App Frame Header
        draw_rounded_rect(draw, (16 * S, 16 * S, canvas_w - 16 * S, 64 * S), 10 * S, fill=(22, 27, 34), outline=border_subtle, width=1 * S)
        
        # Mac OS Window Control Buttons
        draw.ellipse((32 * S, 34 * S, 44 * S, 46 * S), fill=(255, 95, 86))   # Red close
        draw.ellipse((50 * S, 34 * S, 62 * S, 46 * S), fill=(255, 189, 46))  # Yellow min
        draw.ellipse((68 * S, 34 * S, 80 * S, 46 * S), fill=(39, 201, 63))   # Green max
        
        # App Title
        draw.text((96 * S, 29 * S), "Cosignal", font=font_header, fill=text_white)
        draw.text((176 * S, 33 * S), "— Dual-Control Financial Guardrails for AI Agents", font=font_sm, fill=text_muted)
        
        # Stepper Progress Bar (4 Steps)
        steps = [
            ("1. Trigger", brand_blue),
            ("2. Policy Check", warning_amber),
            ("3. Human Gate", purple_accent),
            ("4. Audited", success_green)
        ]
        
        start_x = canvas_w - 450 * S
        pill_w = 100 * S
        pill_gap = 105 * S
        
        for idx, (label, color) in enumerate(steps, 1):
            x = start_x + (idx - 1) * pill_gap
            y = 27 * S
            is_current = (idx == active_step)
            is_past = (idx < active_step)
            
            fill_col = color if is_current else ((40, 48, 60) if is_past else (26, 31, 40))
            txt_col = text_white if (is_current or is_past) else text_subtle
            out_col = color if is_current else (border_subtle if not is_past else color)
            
            draw_rounded_rect(draw, (x, y, x + pill_w, y + 26 * S), 13 * S, fill=fill_col, outline=out_col, width=1 * S)
            
            tw = draw.textlength(label, font=font_xs)
            tx = x + (pill_w - tw) / 2
            draw.text((tx, y + 5 * S), label, font=font_xs, fill=txt_col)

    def draw_agent_panel(draw, phase):
        # Left Panel Box
        left_box = (16 * S, 76 * S, 450 * S, canvas_h - 16 * S)
        outline_col = success_green if phase == 4 else (warning_amber if phase in (2, 3) else border_subtle)
        draw_rounded_rect(draw, left_box, 12 * S, fill=card_bg, outline=outline_col, width=1.5 * S)
        
        # Panel Title & Metadata
        draw_badge(draw, (32 * S, 90 * S, 80 * S, 110 * S), "AI", font_xs, (16, 40, 60), brand_blue)
        draw.text((88 * S, 92 * S), "Agent: invoice-processor-01", font=font_bold, fill=text_white)
        
        # Status Badge top-right of left panel
        if phase == 1:
            badge_bg, badge_txt, status_label = (30, 58, 90), brand_blue, "RUNNING"
        elif phase in (2, 3):
            badge_bg, badge_txt, status_label = (60, 40, 15), warning_amber, "PAUSED (HELD)"
        else:
            badge_bg, badge_txt, status_label = (15, 60, 40), success_green, "RESUMED & PASSED"
            
        draw_badge(draw, (310 * S, 90 * S, 434 * S, 112 * S), status_label, font_xs, badge_bg, badge_txt)

        draw.text((32 * S, 120 * S), "Task: Automated Vendor Disbursement (Acme Supplies)", font=font_sm, fill=text_muted)
        
        # IDE / Code Block Container
        code_box = (32 * S, 144 * S, 434 * S, 380 * S)
        draw_rounded_rect(draw, code_box, 8 * S, fill=code_bg, outline=(35, 42, 54), width=1 * S)
        
        # Code Tab Header
        draw_rounded_rect(draw, (32 * S, 144 * S, 434 * S, 172 * S), 8 * S, fill=(24, 30, 40))
        draw.text((44 * S, 151 * S), "agent_payout.py", font=font_xs, fill=brand_blue)
        draw.text((350 * S, 151 * S), "Python 3.11", font=font_xs, fill=text_subtle)
        
        # Code Lines with Line Numbers & Syntax Highlighting
        lines = [
            ("01", "import cosignal", text_subtle, brand_blue),
            ("02", "", text_subtle, text_white),
            ("03", "# Execute high-value disbursement", text_subtle, text_subtle),
            ("04", "decision = cosignal.check(", text_subtle, text_white),
            ("05", '    action="vendor_disbursement",', text_subtle, brand_blue),
            ("06", '    amount=15000.00,  # USD', text_subtle, warning_amber),
            ("07", '    vendor="Acme Supplies Inc"', text_subtle, text_white),
            ("08", ")", text_subtle, text_white),
        ]
        
        line_y = 182 * S
        for num, text, num_col, code_col in lines:
            draw.text((44 * S, line_y), num, font=font_mono, fill=num_col)
            draw.text((75 * S, line_y), text, font=font_mono, fill=code_col)
            line_y += 22 * S

        # Agent Runtime Output Box below Code
        status_box = (32 * S, 396 * S, 434 * S, 508 * S)
        if phase == 1:
            draw_rounded_rect(draw, status_box, 8 * S, fill=(20, 32, 48), outline=brand_blue, width=1 * S)
            draw.text((46 * S, 412 * S), "EXECUTION: cosignal.check() invoked", font=font_bold, fill=brand_blue)
            draw.text((46 * S, 436 * S), "Requesting policy decision for $15,000.00 USD...", font=font_sm, fill=text_white)
            draw.text((46 * S, 462 * S), "Evaluating policy rules asynchronously...", font=font_sm, fill=text_muted)
            draw_rounded_rect(draw, (46 * S, 485 * S, 220 * S, 498 * S), 6 * S, fill=(30, 50, 75))
            draw.text((54 * S, 486 * S), "SDK Wait: Active (300s)", font=font_xs, fill=brand_blue)
        elif phase in (2, 3):
            draw_rounded_rect(draw, status_box, 8 * S, fill=(45, 28, 12), outline=warning_amber, width=1.5 * S)
            draw.text((46 * S, 412 * S), "POLICY GATE INTERCEPTED", font=font_bold, fill=warning_amber)
            draw.text((46 * S, 436 * S), 'Reason: "Exceeds $10,000 threshold"', font=font_sm, fill=text_white)
            draw.text((46 * S, 462 * S), "Agent execution synchronously PAUSED.", font=font_sm, fill=warning_amber)
            draw_rounded_rect(draw, (46 * S, 485 * S, 260 * S, 498 * S), 6 * S, fill=(65, 38, 15))
            draw.text((54 * S, 486 * S), "Awaiting Human Approval via Slack/UI", font=font_xs, fill=warning_amber)
        else: # Phase 4
            draw_rounded_rect(draw, status_box, 8 * S, fill=(14, 45, 30), outline=success_green, width=1.5 * S)
            draw.text((46 * S, 412 * S), "DECISION ALLOWED (APPROVED)", font=font_bold, fill=success_green)
            draw.text((46 * S, 436 * S), 'Authorizer: alex@company.com (Finance Lead)', font=font_sm, fill=text_white)
            draw.text((46 * S, 462 * S), "Payment $15,000.00 dispatched to vendor!", font=font_sm, fill=success_green)
            draw_rounded_rect(draw, (46 * S, 485 * S, 260 * S, 498 * S), 6 * S, fill=(20, 65, 42))
            draw.text((54 * S, 486 * S), "Auth Token: #cos_98421 (Verified)", font=font_xs, fill=success_green)

    def draw_right_panel(draw, phase, button_state="normal", cursor_pos=None):
        right_box = (470 * S, 76 * S, canvas_w - 16 * S, canvas_h - 16 * S)
        outline_col = success_green if phase == 4 else (warning_amber if phase in (2, 3) else border_subtle)
        draw_rounded_rect(draw, right_box, 12 * S, fill=card_bg, outline=outline_col, width=1.5 * S)
        
        # Panel Title
        draw_badge(draw, (486 * S, 90 * S, 550 * S, 110 * S), "ENGINE", font_xs, (40, 30, 60), purple_accent)
        draw.text((558 * S, 92 * S), "Cosignal Policy Engine", font=font_bold, fill=text_white)
        draw.text((486 * S, 118 * S), "Real-time evaluation & Human-in-the-loop governance", font=font_sm, fill=text_muted)
        
        # Policy Rule Card (Always visible at top of right panel)
        rule_box = (486 * S, 144 * S, canvas_w - 32 * S, 226 * S)
        draw_rounded_rect(draw, rule_box, 8 * S, fill=panel_bg, outline=(45, 52, 66), width=1 * S)
        
        draw_rounded_rect(draw, (498 * S, 154 * S, 640 * S, 174 * S), 4 * S, fill=(38, 46, 62))
        draw.text((506 * S, 156 * S), "RULE #high-value-payout", font=font_xs, fill=brand_blue)
        
        draw.text((498 * S, 182 * S), "IF amount > $10,000.00 USD", font=font_bold, fill=text_white)
        draw.text((498 * S, 204 * S), "ACTION: Require Dual-Control Human Approval", font=font_sm, fill=warning_amber if phase >= 2 else text_muted)

        if phase == 1:
            # Phase 1: Evaluating rule animation
            eval_box = (486 * S, 240 * S, canvas_w - 32 * S, 508 * S)
            draw_rounded_rect(draw, eval_box, 8 * S, fill=code_bg, outline=border_subtle)
            draw.text((550 * S, 340 * S), "Inspecting active policy rules...", font=font_main, fill=brand_blue)
            draw.text((530 * S, 370 * S), "Matching payload parameters against guardrails", font=font_sm, fill=text_muted)
            
        elif phase in (2, 3):
            # Phase 2 & 3: Slack Toast + Approval Card
            # 1. Slack Alert Toast
            slack_box = (486 * S, 240 * S, canvas_w - 32 * S, 316 * S)
            draw_rounded_rect(draw, slack_box, 8 * S, fill=slack_bg, outline=slack_border, width=1 * S)
            
            draw_badge(draw, (500 * S, 250 * S, 555 * S, 268 * S), "SLACK", font_xs, (60, 20, 65), (240, 180, 250))
            draw.text((563 * S, 252 * S), "Notification (#finance-approvals)", font=font_bold, fill=(235, 170, 245))
            draw.text((canvas_w - 95 * S, 254 * S), "Just now", font=font_xs, fill=text_subtle)
            draw.text((500 * S, 278 * S), "Approval Required: $15,000.00 requested by invoice-processor-01", font=font_sm, fill=text_white)
            draw.text((500 * S, 296 * S), "Vendor: Acme Supplies Inc. • Policy: #high-value-payout", font=font_xs, fill=text_muted)
            
            # 2. Dual Control Approval Card
            card_box = (486 * S, 328 * S, canvas_w - 32 * S, 508 * S)
            card_border = brand_blue if button_state == "hover" else (success_green if button_state == "pressed" else warning_amber)
            draw_rounded_rect(draw, card_box, 8 * S, fill=panel_bg, outline=card_border, width=1.5 * S)
            
            draw.text((500 * S, 340 * S), "PENDING APPROVAL REQUEST #req-84920", font=font_bold, fill=warning_amber)
            draw.text((500 * S, 365 * S), "Vendor: Acme Supplies Inc.", font=font_main, fill=text_muted)
            draw.text((500 * S, 388 * S), "$15,000.00", font=font_amount, fill=warning_amber)
            draw.text((680 * S, 396 * S), "USD", font=font_bold, fill=text_subtle)
            
            draw.text((500 * S, 426 * S), "Reviewer: Alex Rivera (Finance Lead)", font=font_sm, fill=brand_blue)
            
            # Action Buttons: Approve & Reject
            btn_app_box = (500 * S, 454 * S, 660 * S, 494 * S)
            btn_rej_box = (674 * S, 454 * S, 780 * S, 494 * S)
            
            if button_state == "hover":
                app_fill, app_out = (20, 190, 130), text_white
            elif button_state == "pressed":
                app_fill, app_out = (10, 130, 85), success_green
            else:
                app_fill, app_out = success_green, success_green
                
            draw_rounded_rect(draw, btn_app_box, 6 * S, fill=app_fill, outline=app_out, width=2 * S if button_state != "normal" else 1 * S)
            draw.text((545 * S, 465 * S), "Approve", font=font_bold, fill=text_white)
            
            draw_rounded_rect(draw, btn_rej_box, 6 * S, fill=(40, 45, 55), outline=(70, 80, 95), width=1 * S)
            draw.text((702 * S, 465 * S), "Reject", font=font_bold, fill=text_muted)

        else: # Phase 4: Immutable Audit Trail Log
            audit_box = (486 * S, 240 * S, canvas_w - 32 * S, 508 * S)
            draw_rounded_rect(draw, audit_box, 8 * S, fill=code_bg, outline=success_green, width=1.5 * S)
            
            draw.text((502 * S, 254 * S), "IMMUTABLE AUDIT TRAIL LOG", font=font_bold, fill=success_green)
            draw_badge(draw, (canvas_w - 132 * S, 248 * S, canvas_w - 48 * S, 268 * S), "VERIFIED", font_xs, (15, 60, 40), success_green)
            
            logs = [
                ("EVENT_ID:", "#evt-9842104928"),
                ("TIMESTAMP:", "2026-10-08T15:42:04Z"),
                ("AGENT:", "invoice-processor-01"),
                ("ACTION:", "vendor_disbursement ($15,000.00)"),
                ("POLICY:", "high-value-payout (PASSED)"),
                ("DECISION:", "APPROVED BY HUMAN"),
                ("APPROVER:", "alex@company.com (Alex Rivera)"),
                ("HASH:", "sha256:8f9a2b1c4e7d90a1..."),
            ]
            
            ly = 284 * S
            for k, v in logs:
                draw.text((502 * S, ly), k, font=font_mono, fill=text_subtle)
                col = success_green if "APPROVED" in v or "PASSED" in v else (brand_blue if "@" in v else text_white)
                draw.text((610 * S, ly), v, font=font_mono, fill=col)
                ly += 22 * S
                
            draw_rounded_rect(draw, (502 * S, 468 * S, canvas_w - 48 * S, 496 * S), 5 * S, fill=(16, 50, 32), outline=success_green)
            draw.text((520 * S, 474 * S), "Cryptographic audit entry saved to immutable storage", font=font_xs, fill=success_green)

        # Draw Cursor if present
        if cursor_pos:
            cx, cy = cursor_pos
            cx, cy = int(cx * S), int(cy * S)
            cursor_points = [(cx, cy), (cx, cy + 22 * S), (cx + 6 * S, cy + 16 * S), (cx + 14 * S, cy + 22 * S), (cx + 18 * S, cy + 18 * S), (cx + 10 * S, cy + 13 * S), (cx + 18 * S, cy + 13 * S)]
            draw.polygon(cursor_points, fill=text_white, outline=(0, 0, 0))

    # Frame Generation Sequence
    raw_frames = []
    frame_durations = []

    # Phase 1: Request Initiated (4 frames)
    for i in range(4):
        img = Image.new("RGB", (canvas_w, canvas_h), bg_dark)
        draw = ImageDraw.Draw(img)
        draw_window_header(draw, active_step=1)
        draw_agent_panel(draw, phase=1)
        draw_right_panel(draw, phase=1)
        raw_frames.append(img)
        frame_durations.append(800)

    # Phase 2: Intercepted & Slack Alert (4 frames)
    for i in range(4):
        img = Image.new("RGB", (canvas_w, canvas_h), bg_dark)
        draw = ImageDraw.Draw(img)
        draw_window_header(draw, active_step=2)
        draw_agent_panel(draw, phase=2)
        draw_right_panel(draw, phase=2, button_state="normal")
        raw_frames.append(img)
        frame_durations.append(700)

    # Phase 3: Cursor approaches & clicks Approve (8 frames)
    start_cx, start_cy = 760, 490
    target_cx, target_cy = 580, 474

    for i in range(8):
        t = i / 7.0
        t_eased = 3 * t * t - 2 * t * t * t
        cur_x = start_cx + (target_cx - start_cx) * t_eased
        cur_y = start_cy + (target_cy - start_cy) * t_eased

        b_state = "normal" if i < 5 else ("hover" if i < 7 else "pressed")
        img = Image.new("RGB", (canvas_w, canvas_h), bg_dark)
        draw = ImageDraw.Draw(img)
        draw_window_header(draw, active_step=3)
        draw_agent_panel(draw, phase=3)
        draw_right_panel(draw, phase=3, button_state=b_state, cursor_pos=(cur_x, cur_y))
        raw_frames.append(img)
        frame_durations.append(220 if i < 5 else 450)

    # Phase 4: Approved! Execution Resumed & Audit Recorded (8 frames)
    for i in range(8):
        img = Image.new("RGB", (canvas_w, canvas_h), bg_dark)
        draw = ImageDraw.Draw(img)
        draw_window_header(draw, active_step=4)
        draw_agent_panel(draw, phase=4)
        draw_right_panel(draw, phase=4)
        raw_frames.append(img)
        frame_durations.append(900 if i < 7 else 2800)

    # Downsample frames from 2x canvas resolution to final GIF resolution using Lanczos anti-aliasing
    final_frames = []
    print(f"Processing {len(raw_frames)} frames with 2x supersampling...")
    for idx, f in enumerate(raw_frames):
        resized = f.resize((final_w, final_h), Image.Resampling.LANCZOS)
        final_frames.append(resized)

    # Save output as animated GIF with disposal=2 to prevent frame stacking
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    final_frames[0].save(
        output_path,
        save_all=True,
        append_images=final_frames[1:],
        duration=frame_durations,
        loop=0,
        disposal=2
    )
    print(f"✨ Ultra High-Quality GIF successfully created at {output_path} ({final_w}x{final_h})")

if __name__ == "__main__":
    generate_gif()
