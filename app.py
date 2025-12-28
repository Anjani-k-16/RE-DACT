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
import platform
import shutil

fake = Faker()

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

def extract_text_from_image(file):
    system = platform.system()

    if system == "Windows":
        pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
    else:
        if shutil.which("tesseract"):
            pytesseract.pytesseract.tesseract_cmd = shutil.which("tesseract")
        else:
            st.error("⚠️ Tesseract OCR is not available in this environment.")
            return ""

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


st.set_page_config(page_title="RE-DACT", layout="centered")

st.markdown("""
<div style="text-align:center;padding:28px;border-radius:18px;
background:linear-gradient(120deg,#4f46e5,#7c3aed);color:white;">
<h1>RE-DACT</h1>
<p>Secure Redaction & Anonymization Tool</p>
</div>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("### Redaction Controls")
    level = st.slider("Redaction Level", 1, 4, 2)

uploaded_file = st.file_uploader(
    "Upload File",
    type=["txt", "xlsx", "pdf", "png", "jpg", "jpeg"]
)

if uploaded_file:
    file_name = uploaded_file.name.lower()

    if file_name.endswith(".xlsx"):
        df = pd.read_excel(uploaded_file)
        TEXT_COL = "PII_Found"
        df["REDACTED_TEXT"] = df[TEXT_COL].astype(str).apply(
            lambda x: redact_text(x, detect_entities(x), level)
        )
        out = io.BytesIO()
        df.to_excel(out, index=False)
        st.download_button("Download Redacted Excel", out.getvalue(),
                           file_name="REDACT_Output.xlsx")

    elif file_name.endswith(".txt"):
        text = uploaded_file.read().decode("utf-8")

    elif file_name.endswith(".pdf"):
        text = extract_text_from_pdf(uploaded_file)

    elif file_name.endswith((".png", ".jpg", ".jpeg")):
        text = extract_text_from_image(uploaded_file)

    if not file_name.endswith(".xlsx"):
        st.subheader("Original Text")
        st.write(text)

        entities = detect_entities(text)
        redacted = redact_text(text, entities, level)

        st.subheader("Redacted Text")
        st.write(redacted)

        pdf_buffer = generate_pdf(redacted)
        st.download_button("Download Redacted Text as PDF",
                           pdf_buffer, file_name="REDACT_Output.pdf",
                           mime="application/pdf")


