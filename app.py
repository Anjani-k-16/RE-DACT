import streamlit as st
import pandas as pd
import re
from faker import Faker

import pdfplumber
from PIL import Image
import pytesseract
import io


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
    pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
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



st.set_page_config(page_title="RE-DACT", layout="centered")

st.markdown(
    """
    <div style='text-align:center; padding-top:6px;'>
        <h1 style='font-weight:900; letter-spacing:1px;'>RE-DACT</h1>
        <p style='color:gray; font-size:15px;'>
            AI-Powered Redaction & Anonymization Tool<br>
            Protect sensitive data across documents, images & records
        </p>
    </div>

    <div style='display:flex; justify-content:center; gap:18px; margin-top:18px; flex-wrap:wrap;'>
        <div style='padding:10px 14px; border-radius:12px; border:1px solid #ddd;'>🔐 Detects PII Automatically</div>
        <div style='padding:10px 14px; border-radius:12px; border:1px solid #ddd;'>🧾 Supports Text / PDF / Images / Excel</div>
        <div style='padding:10px 14px; border-radius:12px; border:1px solid #ddd;'>⚙️ Multiple Redaction Levels</div>
    </div>

    <br>
    <hr>
    """,
    unsafe_allow_html=True
)



with st.sidebar:
    st.header("⚙️ Redaction Controls")
    level = st.slider("Redaction Level", 1, 4, 2)
    st.write("""
**Levels**
1 — Mask  
2 — Token Replace  
3 — Light Anonymization  
4 — Synthetic Replacement
""")



st.markdown(
    """
    <div style='margin-top:25px; padding:16px; border-radius:14px;
                background:#f5f8ff; border:1px solid #d9e2ff;'>
        <h4> Start Redaction</h4>
        <p style='color:#555;'>
            Upload your document or image to extract text and apply secure redaction.
            Scroll below for results.
        </p>
    </div>
    """,
    unsafe_allow_html=True
)



uploaded_file = st.file_uploader(
    "Upload a file (Text / Excel / PDF / Image)",
    type=["txt", "xlsx", "pdf", "png", "jpg", "jpeg"]
)



if uploaded_file:

    file_name = uploaded_file.name.lower()

  
    if file_name.endswith(".xlsx"):
        df = pd.read_excel(uploaded_file)
        TEXT_COL = "PII_Found"

        st.subheader("Input Preview")
        st.dataframe(df.head())

        df["REDACTED_TEXT"] = df[TEXT_COL].astype(str).apply(
            lambda x: redact_text(x, detect_entities(x), level)
        )

        st.subheader("Redacted Output")
        st.dataframe(df[["PII_Found", "REDACTED_TEXT"]])

        out = io.BytesIO()
        df.to_excel(out, index=False)

        st.download_button(
            "Download Redacted Excel",
            out.getvalue(),
            file_name="REDACT_Output.xlsx"
        )

   
    elif file_name.endswith(".txt"):
        text = uploaded_file.read().decode("utf-8")

    
    elif file_name.endswith(".pdf"):
        text = extract_text_from_pdf(uploaded_file)

   
    elif file_name.endswith((".png", ".jpg", ".jpeg")):
        text = extract_text_from_image(uploaded_file)

  
    if not file_name.endswith(".xlsx"):
        st.subheader("📄 Extracted / Original Text")
        st.write(text)

        entities = detect_entities(text)
        redacted = redact_text(text, entities, level)

        st.subheader("Redacted Text")
        st.write(redacted)


