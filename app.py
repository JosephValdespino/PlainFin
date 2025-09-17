import streamlit as st
import openai
import PyPDF2

# Load API key from Streamlit secrets
openai.api_key = st.secrets["OPENAI_API_KEY"]

st.title("PlainFin: Finance Document Explainer")
st.write("Upload a financial filing (10-K, 10-Q, or earnings report) and get a summary that explains not just **what** happened, but also **why** it happened.")

# Upload PDF
uploaded_file = st.file_uploader("Upload a PDF", type="pdf")

def extract_text(pdf_file):
    """Extract text from uploaded PDF"""
    reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text

if uploaded_file:
    with st.spinner("Reading document..."):
        raw_text = extract_text(uploaded_file)

    st.success("Document uploaded. Generating explanations...")

    # Split text into smaller chunks (avoid token limits)
    chunks = [raw_text[i:i+2000] for i in range(0, len(raw_text), 2000)]

    summaries = []
    for chunk in chunks[:3]:  # limit to 3 chunks for MVP
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a finance tutor who explains both facts and reasoning."},
                {"role": "user", "content": f"Summarize this financial text. For each point, explain BOTH:\n1. What happened (fact)\n2. Why it happened (drivers, logic, concept).\n\nText:\n{chunk}"}
            ],
            temperature=0.5,
            max_tokens=500
        )
        summaries.append(response["choices"][0]["message"]["content"])

    st.subheader("📊 Fact + Why Explanations")
    for i, summary in enumerate(summaries):
        st.markdown(f"**Section {i+1}:**")
        st.write(summary)
