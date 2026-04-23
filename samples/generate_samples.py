"""
Generates sample test files for the Careficient pipeline.
Run once: python samples/generate_samples.py
Produces:
  samples/sample_visit.wav        — home health nurse visit audio (TTS)
  samples/sample_clinical_note.png — scanned clinical note image (Pillow)
"""

import os
import sys
import textwrap
from pathlib import Path

HERE = Path(__file__).parent


# ---------------------------------------------------------------------------
# WAV — realistic home health nursing visit transcript
# ---------------------------------------------------------------------------

TRANSCRIPT = (
    "This is a home health nursing visit for patient John Smith, date of birth March 15, 1948. "
    "Today's visit date is April 23, 2026. "
    "The patient is complaining of shortness of breath and mild ankle swelling for the past three days. "
    "Vital signs: blood pressure 148 over 92, heart rate 88, respiratory rate 20, "
    "oxygen saturation 94 percent on room air, temperature 98.6 degrees Fahrenheit, weight 196 pounds. "
    "Current medications: Lasix 40 milligrams once daily by mouth, Lisinopril 10 milligrams once daily by mouth, "
    "Carvedilol 12.5 milligrams twice daily by mouth, aspirin 81 milligrams once daily. "
    "Assessment: Congestive heart failure exacerbation with fluid retention. "
    "Hypertension, blood pressure elevated today but patient reports missed dose yesterday. "
    "Plan: Reinforce medication compliance. "
    "Monitor weight daily. "
    "Return to clinic if weight increases more than 2 pounds in 24 hours or shortness of breath worsens. "
    "Next nursing visit scheduled in 48 hours."
)


def generate_wav():
    try:
        import pyttsx3
    except ImportError:
        print("pyttsx3 not installed — skipping WAV generation")
        return

    out = HERE / "sample_visit.wav"
    engine = pyttsx3.init()
    engine.setProperty("rate", 155)   # words per minute — natural nurse pace
    engine.setProperty("volume", 0.95)

    # Use David (male) for variety
    voices = engine.getProperty("voices")
    for v in voices:
        if "david" in v.name.lower():
            engine.setProperty("voice", v.id)
            break

    engine.save_to_file(TRANSCRIPT, str(out))
    engine.runAndWait()
    print(f"Generated: {out}  ({out.stat().st_size // 1024} KB)")


# ---------------------------------------------------------------------------
# PNG — hand-filled clinical note
# ---------------------------------------------------------------------------

NOTE_TEXT = """\
CAREFICIENT HOME HEALTH SERVICES
────────────────────────────────────────────────────────────
NURSING VISIT NOTE
────────────────────────────────────────────────────────────
Patient:       John Smith                   DOB: 03/15/1948
Visit Date:    04/23/2026                   MR#: CHF-00124
Clinician:     R. Patel, RN                 NPI: 1234567890

CHIEF COMPLAINT
  Patient complains of shortness of breath and ankle swelling x 3 days.

VITAL SIGNS
  BP:    148/92 mmHg          HR:   88 bpm
  RR:    20 /min              SpO2: 94% (room air)
  Temp:  98.6 °F              Wt:   196 lbs

CURRENT MEDICATIONS
  Lasix (furosemide) 40 mg     PO  once daily
  Lisinopril          10 mg     PO  once daily
  Carvedilol          12.5 mg   PO  twice daily
  Aspirin             81 mg     PO  once daily

ASSESSMENT / DIAGNOSES
  1. Congestive Heart Failure (CHF) — Acute exacerbation      ICD-10: I50.9
  2. Hypertension — Moderate, elevated today (missed dose)    ICD-10: I10
  3. Peripheral Edema — Mild bilateral ankle edema            ICD-10: R60.0

PLAN
  • Reinforce medication adherence; patient missed Lasix yesterday.
  • Daily weight monitoring — notify MD if +2 lbs in 24 hours.
  • Low-sodium diet counseling provided.
  • Follow-up nursing visit in 48 hours.
  • Return to ED if dyspnea worsens or SpO2 < 90%.

────────────────────────────────────────────────────────────
Clinician Signature: ____________________  Date: 04/23/2026
"""


def generate_png():
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        print("Pillow not installed — skipping PNG generation")
        return

    # A4 at 150 dpi → 1240 × 1754 px  (readable by Tesseract at 300 dpi equivalent)
    W, H = 1240, 1754
    img = Image.new("RGB", (W, H), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    # Try to load a monospace font; fall back to default
    font = None
    font_paths = [
        "C:/Windows/Fonts/cour.ttf",       # Courier New
        "C:/Windows/Fonts/consola.ttf",    # Consolas
        "C:/Windows/Fonts/lucon.ttf",      # Lucida Console
    ]
    for fp in font_paths:
        if os.path.exists(fp):
            try:
                font = ImageFont.truetype(fp, size=22)
                break
            except Exception:
                continue

    if font is None:
        font = ImageFont.load_default()

    margin_x, margin_y = 60, 60
    line_height = 30
    y = margin_y

    for line in NOTE_TEXT.splitlines():
        draw.text((margin_x, y), line, fill=(20, 20, 20), font=font)
        y += line_height

    out = HERE / "sample_clinical_note.png"
    img.save(str(out), dpi=(150, 150))
    print(f"Generated: {out}  ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    print("Generating sample files …")
    generate_wav()
    generate_png()
    print("Done.")
