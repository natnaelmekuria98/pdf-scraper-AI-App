import streamlit as st
import pandas as pd
from PyPDF2 import PdfReader
import re
import tempfile
import io
import locale
import spacy
import xlsxwriter

# Load the English language model from spaCy
nlp = spacy.load("en_core_web_sm")

def extract_pdf_contents(pdf_file):
    pdf_text = ""
    with open(pdf_file, "rb") as file:
        pdf_reader = PdfReader(file)
        for page in pdf_reader.pages:
            pdf_text += page.extract_text()
    return pdf_text

def clean_text(text):
    cleaned_text = re.sub(r"[^\w\s$.,-]", "", text)  # Allow decimal point, comma, and hyphen in amounts
    cleaned_text = re.sub(r"\s+", " ", cleaned_text)
    return cleaned_text.strip()

def extract_value(pattern, text):
    matches = re.findall(pattern, text)
    return matches

def clean_value(value):
    return value.lower().strip() if value else "Not Available"

def format_number(number):
    try:
        number = locale.atof(number)
        formatted_number = locale.format_string("%0.2f", number, grouping=True)
        return formatted_number
    except ValueError:
        return number

def extract_person_names(text):
    doc = nlp(text)
    person_names = [ent.text for ent in doc.ents if ent.label_ == "PERSON"]
    return person_names

def extract_life_assured_name(pdf_text):
    person_names = extract_person_names(pdf_text)
    return person_names[0] if person_names else "Not Available"

def extract_insurance_company(pdf_text):
    insurance_companies = ["Asteron", "Asteron life", "Chubb Life", "Partner Life", "AIA New Zealand", "AIA", "Accuro", "Fidelity Life", "Southern Cross"]  # Replace with a list of known insurance companies
    for company in insurance_companies:
        if company.lower() in pdf_text.lower():
            return company
    return "Not Available"

def create_table(pdf_text, assured_name):
    amount_dollars = extract_value(r"\$\d+(?:,\d+)*(?:\.\d+)?", pdf_text)  # Modified pattern to capture numbers with comma separators
    amount_dollars = [clean_value(amount) for amount in amount_dollars]
    amount_dollars = [format_number(amount) for amount in amount_dollars]

    insurance_company = extract_insurance_company(pdf_text)

    rows = [
        ["Assured Name", "Benefit Type", "Level", "Monthly Premium", "Insurer"],
        [assured_name, "Life Cover", amount_dollars[0] if len(amount_dollars) > 0 else "", amount_dollars[1] if len(amount_dollars) > 1 else "", insurance_company],
        [assured_name, "Standalone Total & Permanent Disablement", amount_dollars[2] if len(amount_dollars) > 2 else "", amount_dollars[3] if len(amount_dollars) > 3 else "", insurance_company],
        [assured_name, "Income Protection", amount_dollars[4] if len(amount_dollars) > 4 else "", amount_dollars[5] if len(amount_dollars) > 5 else "", insurance_company],
        ["", "Total Premiums", "", "", insurance_company],
    ]

    return rows

def main():
    st.title("AI PDF Extractor App")

    uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])
    if uploaded_file is not None:
        st.write("Uploaded PDF File:", uploaded_file.name)

        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(uploaded_file.read())

        pdf_contents = extract_pdf_contents(temp_file.name)
        st.write("Extracted Text:")
        st.write(pdf_contents)

        cleaned_text = clean_text(pdf_contents)

        assured_name = extract_life_assured_name(cleaned_text)

        rows = create_table(cleaned_text, assured_name)
        st.write("Table:")
        st.table(rows)

        # Convert table data to a DataFrame
        df = pd.DataFrame(rows[1:], columns=rows[0])

        # Remove columns Premium Effective Date and Policy Anniversary Date
        # df = df.drop(columns=["Premium Effective Date", "Policy Anniversary Date"], errors="ignore")

        # Download as Excel file
        excel_buffer = io.BytesIO()
        excel_writer = pd.ExcelWriter(excel_buffer, engine="xlsxwriter")
        df.to_excel(excel_writer, index=False, sheet_name="Sheet1")
        excel_writer.save()
        excel_buffer.seek(0)
        st.download_button(
            label="Download as Excel",
            data=excel_buffer,
            file_name="extracted_table.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

if __name__ == "__main__":
    # Set locale to format numbers with comma separators
    locale.setlocale(locale.LC_ALL, "")

    main()
