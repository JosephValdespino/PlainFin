import streamlit as st
import PyPDF2
from openai import OpenAI
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO

# Load API key from Streamlit secrets
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.title("PlainFin: Finance Document Explainer")
st.write("Upload a financial filing (10-K, 10-Q, earnings report) and get a summary that explains not just **what** happened, but also **why**.")

# Upload PDF
uploaded_file = st.file_uploader("Upload a PDF", type="pdf")

def extract_text(pdf_file):
    """Extract text from uploaded PDF using PyPDF2"""
    reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in reader.pages:
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

def build_pdf(report_text):
    """Generate a PDF from text using reportlab"""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    text_object = c.beginText(40, height - 50)
    text_object.setFont("Helvetica", 11)

    for line in report_text.splitlines():
        if line.strip().startswith("# "):   # Big Title
            text_object.setFont("Helvetica-Bold", 16)
            text_object.textLine(line.replace("# ", ""))
            text_object.setFont("Helvetica", 11)
            text_object.moveCursor(0, 10)
        elif line.strip().startswith("## "):  # Subheader
            text_object.setFont("Helvetica-Bold", 14)
            text_object.textLine(line.replace("## ", ""))
            text_object.setFont("Helvetica", 11)
            text_object.moveCursor(0, 6)
        elif line.strip().startswith("### "):  # Section header
            text_object.setFont("Helvetica-Bold", 12)
            text_object.textLine(line.replace("### ", ""))
            text_object.setFont("Helvetica", 11)
        else:
            text_object.textLine(line)

        # Auto new page if reaching bottom
        if text_object.getY() < 50:
            c.drawText(text_object)
            c.showPage()
            text_object = c.beginText(40, height - 50)
            text_object.setFont("Helvetica", 11)

    c.drawText(text_object)
    c.save()
    buffer.seek(0)
    return buffer

if uploaded_file:
    with st.spinner("Reading document..."):
        raw_text = extract_text(uploaded_file)

    st.success("✅ Document uploaded. Now generating explanation...")

    # Chunk text
    chunks = chunk_text(raw_text, 2000)

    summaries = []
    for i, chunk in enumerate(chunks[:3]):  # limit to 3 chunks for now
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a finance tutor who explains both facts and reasoning in bullet-point format."
                },
                {
                    "role": "user",
                    "content": f"Summarize this section of a financial filing in BULLET POINTS. For each bullet, explain BOTH:\n- What happened (fact)\n- Why it happened (drivers, logic, concepts).\n\nText:\n{chunk}"
                }
            ],
            temperature=0.5,
            max_tokens=500
        )
        summaries.append(response.choices[0].message.content)

    st.subheader("📊 Fact + Why Explanation (Per Section)")
    for i, summary in enumerate(summaries):
        with st.expander(f"Section {i+1}"):
            st.markdown(summary)

    # Executive summary across all chunks
    with st.spinner("Creating executive summary..."):
        joined_summaries = "\n\n".join(summaries)
        final_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "You are a finance tutor who writes clear, structured executive summaries in bullet-point format."
                },
                {
                    "role": "user",
                    "content": f"Here are section summaries from a financial filing:\n{joined_summaries}\n\nWrite a concise EXECUTIVE SUMMARY in BULLET POINTS that highlights:\n- Key facts (what happened)\n- Main drivers/reasons (why it happened)\nKeep it clear and professional."
                }
            ],
            temperature=0.5,
            max_tokens=600
        )
        executive_summary = final_response.choices[0].message.content

    st.subheader("📌 Executive Summary")
    st.markdown(executive_summary)

    # Build full report (Markdown styled)
    full_report = "# 📊 PlainFin Report\n\n"
    full_report += "This report summarizes a financial filing, structured into per-section insights and a high-level executive summary.\n\n"

    full_report += "## 📖 Per-Section Summaries\n\n"
    for i, summary in enumerate(summaries):
        full_report += f"### Section {i+1}\n{summary}\n\n"

    full_report += "## 📌 Executive Summary\n\n"
    full_report += executive_summary

    # Download as Markdown
    st.download_button(
        label="⬇️ Download Full Report (Markdown)",
        data=full_report,
        file_name="plainfin_report.md",
        mime="text/markdown"
    )

    # Download as PDF
    pdf_buffer = build_pdf(full_report)
    st.download_button(
        label="⬇️ Download Full Report (PDF)",
        data=pdf_buffer,
        file_name="plainfin_report.pdf",
        mime="application/pdf"
    )
