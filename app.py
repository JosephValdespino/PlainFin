import streamlit as st
import pdfplumber
from openai import OpenAI

# Load API key from Streamlit secrets
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.title("PlainFin: Finance Document Explainer")
st.write("Upload a financial filing (10-K, 10-Q, earnings report) and get a summary that explains not just **what** happened, but also **why**.")

# Upload PDF
uploaded_file = st.file_uploader("Upload a PDF", type="pdf")

def extract_text(pdf_file):
    """Extract text from uploaded PDF"""
    text = ""
    with pdfplumber.open(pdf_file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text

def chunk_text(text, chunk_size=2000):
    """Split text into chunks without cutting words"""
    words = text.split()
    chunks, current = [], []
    length = 0
    for word in words:
        if length + len(word) + 1 > chunk_size:
            chunks.append(" ".join(current))
            current, length = [], 0
        current.append(word)
        length += len(word) + 1
    if current:
        chunks.append(" ".join(current))
    return chunks

if uploaded_file:
    with st.spinner("Reading document..."):
        raw_text = extract_text(uploaded_file)

    st.success("✅ Document uploaded. Now generating explanation...")

    chunks = chunk_text(raw_text, 2000)

    summaries = []
    for i, chunk in enumerate(chunks[:3]):  # limit to 3 chunks for now
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a finance tutor who explains both facts and reasoning."},
                {"role": "user", "content": f"Summarize this section of a financial filing. For each point, explain BOTH:\n1. What happened (fact)\n2. Why it happened (logic, drivers, concepts).\n\nText:\n{chunk}"}
            ],
            temperature=0.5,
            max_tokens=500
        )
        summaries.append(response.choices[0].message.content)

    st.subheader("📊 Fact + Why Explanation")
    for i, summary in enumerate(summaries):
        with st.expander(f"Section {i+1}"):
            st.write(summary)
