import streamlit as st
import pandas as pd
import re
from faker import Faker
import pdfplumber
from PIL import Image
import pytesseract
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

fake = Faker()


# ---------- ENTITY DETECTION ----------
def detect_entities(text):
    entities = []

    for e in re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text):
        entities.append((e, "EMAIL"))

    for p in re.findall(r"\b[0-9]{10}\b", text):
        entities.append((p, "PHONE"))

    for n in re.findall(r"\b[A-Z][a-z]+\s[A-Z][a-z]+\b", text):
        entities.append((n, "PERSON"))

    for org in re.findall(
        r"\b[A-Z][A-Za-z]+\s(?:Ltd|Pvt|Corporation|Corp|Technologies|Systems|Solutions|Tech|Company)\b",
        text,
    ):
        entities.append((org, "ORG"))

    for city in re.findall(r"\b[A-Z][a-z]{3,}\b", text):
        entities.append((city, "GPE"))

    return entities


# ---------- REDACTION ENGINE ----------
def redact_text(text, entities, level=2):
    redacted_text = text

    for value, label in entities:

        if level == 1:
            rep = "*" * len(value)

        elif level == 2:
            rep = f"[{label}]"

        elif level == 3:
            rep = f"<{label}_REDACTED>"

        elif level == 4:
            if label == "PERSON":
                rep = fake.name()
            elif label == "ORG":
                rep = fake.company()
            elif label == "GPE":
                rep = fake.city()
            elif label == "EMAIL":
                rep = fake.email()
            elif label == "PHONE":
                rep = fake.phone_number()
            else:
                rep = fake.word()
        else:
            rep = "[REDACTED]"

        redacted_text = redacted_text.replace(value, rep)

    return redacted_text


# ---------- TEXT EXTRACTORS ----------
def extract_text_from_image(file):
    image = Image.open(file)
    return pytesseract.image_to_string(image)


def extract_text_from_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text


# ---------- PDF EXPORT ----------
def generate_pdf(text):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    y = height - 60
    for line in text.split("\n"):
        if y <= 40:
            pdf.showPage()
            y = height - 60
        pdf.drawString(50, y, line[:90])
        y -= 18

    pdf.save()
    buffer.seek(0)
    return buffer


# ---------- UI HEADER ----------
st.set_page_config(page_title="RE-DACT", layout="centered")

st.markdown("""
    <div style="
        text-align:center;
        padding:28px 12px;
        border-radius:18px;
        background: linear-gradient(120deg, #4f46e5, #7c3aed);
        color:white;
        margin-bottom:10px;">
        <h1 style="font-weight:900; letter-spacing:1px; margin-bottom:6px;">
            RE-DACT
        </h1>
    </div>
""", unsafe_allow_html=True)


# ---------- CAPABILITY TAGS ----------
st.markdown("""
<div style="display:flex; gap:10px; flex-wrap:wrap; justify-content:center;">
<div style="padding:8px 12px; border-radius:12px;background:#eef2ff; border:1px solid #c7d2fe;"> Detects & Redacts Sensitive PII</div>
<div style="padding:8px 12px; border-radius:12px;background:#ecfeff; border:1px solid #bae6fd;"> Supports Text / PDF / Images / Excel</div>
<div style="padding:8px 12px; border-radius:12px;background:#f0fdf4; border:1px solid #bbf7d0;"> Multiple Redaction Modes</div>
</div><br>
""", unsafe_allow_html=True)


# ---------- SIDEBAR ----------
with st.sidebar:
    st.markdown("### 🔧 Redaction Controls")

    level = st.slider(
        "Redaction Level",
        1, 4, 2,
        help="Choose how aggressively data is anonymized"
    )

    st.markdown("""
    <div style="padding:10px; border-radius:10px;
                background:#eef2ff; border:1px solid #c7d2fe;">
    <b>Levels Guide</b><br><br>
    <b>1 — Mask</b> → *****<br>
    <b>2 — Token Replace</b> → [EMAIL]<br>
    <b>3 — Light Anonymization</b> → &lt;PERSON_REDACTED&gt;<br>
    <b>4 — Synthetic Replacement</b> → Fake but realistic values
    </div>
    """, unsafe_allow_html=True)


# ---------- UPLOAD CARD ----------
st.markdown("""
<div style='margin-top:5px; padding:16px;
            border-radius:14px; background:#f8fafc;
            border:1px solid #e5e7eb'>
    <h4 style='margin-bottom:6px;'> Start Redaction</h4>
    <p style='color:#555'>
        Upload your document to extract text and apply secure anonymization.
    </p>
</div>
""", unsafe_allow_html=True)


# ---------- FILE INPUT ----------
uploaded_file = st.file_uploader(
    "Upload File",
    type=["txt", "xlsx", "pdf", "png", "jpg", "jpeg"]
)


# ---------- PROCESSING ----------
if uploaded_file:
    file_name = uploaded_file.name.lower()

    # Excel
    if file_name.endswith(".xlsx"):
        df = pd.read_excel(uploaded_file)
        TEXT_COL = "PII_Found"

        st.subheader("Input Preview")
        st.dataframe(df.head())

        df["REDACTED_TEXT"] = df[TEXT_COL].astype(str).apply(
            lambda x: redact_text(x, detect_entities(x), level)
        )

        st.subheader("Redacted Output")
        st.dataframe(df[["PII_Found", "REDACTED_TEXT"]].head())

        out = io.BytesIO()
        df.to_excel(out, index=False)

        st.download_button(
            "Download Redacted Excel",
            out.getvalue(),
            file_name="REDACT_Output.xlsx"
        )

    # Text
    elif file_name.endswith(".txt"):
        text = uploaded_file.read().decode("utf-8")

    # PDF
    elif file_name.endswith(".pdf"):
        text = extract_text_from_pdf(uploaded_file)

    # Image (OCR)
    elif file_name.endswith((".png", ".jpg", ".jpeg")):
        text = extract_text_from_image(uploaded_file)

    # ---------- REDACT NON-EXCEL ----------
    if not file_name.endswith(".xlsx"):

        st.subheader("Original Text")
        st.write(text)

        entities = detect_entities(text)
        redacted = redact_text(text, entities, level)

        st.subheader("Redacted Text")
        st.write(redacted)

        pdf_buffer = generate_pdf(redacted)

        st.download_button(
            "Download Redacted Text as PDF",
            pdf_buffer,
            file_name="REDACT_Output.pdf",
            mime="application/pdf"
        )




