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

# -------------------------------------------------
# ENTITY DETECTION
# -------------------------------------------------
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
        text):
        entities.append((org, "ORG"))

    for city in re.findall(r"\b[A-Z][a-z]{3,}\b", text):
        entities.append((city, "GPE"))

    return entities


# -------------------------------------------------
# REDACTION ENGINE
# -------------------------------------------------
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
            if label == "PERSON": rep = fake.name()
            elif label == "ORG": rep = fake.company()
            elif label == "GPE": rep = fake.city()
            elif label == "EMAIL": rep = fake.email()
            elif label == "PHONE": rep = fake.phone_number()
            else: rep = fake.word()

        else:
            rep = "[REDACTED]"

        redacted_text = redacted_text.replace(value, rep)

    return redacted_text


# -------------------------------------------------
# TEXT EXTRACTION
# -------------------------------------------------
def extract_text_from_image(file):
    image = Image.open(file)
    return pytesseract.image_to_string(image)


def extract_text_from_pdf(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            if page.extract_text():
                text += page.extract_text() + "\n"
    return text


# -------------------------------------------------
# PDF EXPORT
# -------------------------------------------------
def generate_pdf(text):
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter
    y = height - 60

    for line in text.split("\n"):
        if y < 40:
            pdf.showPage()
            y = height - 60
        pdf.drawString(50, y, line[:90])
        y -= 18

    pdf.save()
    buffer.seek(0)
    return buffer


# -------------------------------------------------
# UI CONFIG
# -------------------------------------------------
st.set_page_config(page_title="RE-DACT", layout="centered")

# -------------------------------------------------
# HERO SECTION
# -------------------------------------------------
st.markdown("""
<div style="
    text-align:center;
    padding:36px 16px;
    border-radius:22px;
    background: linear-gradient(120deg, #4f46e5, #7c3aed);
    color:white;
    margin-bottom:20px;">
    <h1 style="font-weight:900; letter-spacing:2px; margin-bottom:10px;">
        RE-DACT
    </h1>
    <p style="font-size:16px; max-width:600px; margin:auto;">
        Secure, Gradational Redaction & Anonymization Tool  
        for Text, PDF, Excel & Images
    </p>
</div>
""", unsafe_allow_html=True)

# -------------------------------------------------
# INFO CARDS
# -------------------------------------------------
st.markdown("""
<div style="display:flex; gap:14px; justify-content:center; flex-wrap:wrap;">

<div style="background:#eef2ff; padding:14px 18px; border-radius:14px;">
🔐 Detects Sensitive PII
</div>

<div style="background:#ecfeff; padding:14px 18px; border-radius:14px;">
📄 Supports Multiple File Types
</div>

<div style="background:#f0fdf4; padding:14px 18px; border-radius:14px;">
⚙️ Multi-Level Redaction Control
</div>

</div>
<br><hr>
""", unsafe_allow_html=True)

# -------------------------------------------------
# SIDEBAR CONTROLS
# -------------------------------------------------
with st.sidebar:
    st.markdown("### ⚙️ Redaction Settings")
    level = st.slider("Redaction Level", 1, 4, 2)

    st.info("""
**Level Guide**
1 — Mask  
2 — Token Replace  
3 — Light Anonymization  
4 — Synthetic Data
""")

# -------------------------------------------------
# UPLOAD CARD
# -------------------------------------------------
st.markdown("""
<div style="
    background:#f8fafc;
    padding:18px;
    border-radius:16px;
    border:1px solid #e5e7eb;">
    <h4>🚀 Start Redaction</h4>
    <p style="color:#555;">
        Upload a document to extract text and securely redact sensitive information.
    </p>
</div>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "Upload File",
    type=["txt", "xlsx", "pdf", "png", "jpg", "jpeg"]
)

# -------------------------------------------------
# FILE PROCESSING
# -------------------------------------------------
if uploaded_file:
    file_name = uploaded_file.name.lower()

    if file_name.endswith(".xlsx"):
        df = pd.read_excel(uploaded_file)
        TEXT_COL = "PII_Found"

        st.subheader("📊 Input Preview")
        st.dataframe(df.head())

        df["REDACTED_TEXT"] = df[TEXT_COL].astype(str).apply(
            lambda x: redact_text(x, detect_entities(x), level)
        )

        st.subheader("🔐 Redacted Output")
        st.dataframe(df[["PII_Found", "REDACTED_TEXT"]].head())

        out = io.BytesIO()
        df.to_excel(out, index=False)

        st.download_button("⬇️ Download Redacted Excel",
                           out.getvalue(),
                           file_name="REDACT_Output.xlsx")

    else:
        if file_name.endswith(".txt"):
            text = uploaded_file.read().decode("utf-8")
        elif file_name.endswith(".pdf"):
            text = extract_text_from_pdf(uploaded_file)
        elif file_name.endswith((".png", ".jpg", ".jpeg")):
            text = extract_text_from_image(uploaded_file)

        st.subheader("📄 Original Text")
        st.write(text)

        redacted = redact_text(text, detect_entities(text), level)

        st.subheader("🔐 Redacted Text")
        st.write(redacted)

        pdf_buffer = generate_pdf(redacted)

        st.download_button(
            "⬇️ Download Redacted PDF",
            pdf_buffer,
            file_name="REDACT_Output.pdf",
            mime="application/pdf"
        )
