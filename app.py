import streamlit as st
import PyPDF2
from openai import OpenAI
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO

# Initialize OpenAI client
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.title("📊 PlainFin: Finance Document Copilot")
st.write(
    "Upload a financial filing (10-K, 10-Q, earnings report) and get:\n"
    "- Per-section summaries with facts + reasons\n"
    "- Executive summary\n"
    "- Key metrics (revenue, margins, debt, etc.)\n"
    "- Plain English explanations of financial jargon\n"
    "- Custom Q&A about the filing (with or without outside knowledge)"
)

# ----------------------------
# PDF Extraction
# ----------------------------
uploaded_file = st.file_uploader("📂 Upload a PDF", type="pdf")

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

# ----------------------------
# Main Processing
# ----------------------------
if uploaded_file:
    with st.spinner("📖 Reading document..."):
        raw_text = extract_text(uploaded_file)

    st.success("✅ Document uploaded. Now generating insights...")

    # --- Per-section summaries ---
    chunks = chunk_text(raw_text, 2000)
    summaries = []
    for i, chunk in enumerate(chunks[:3]):  # limit to 3 chunks
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a finance tutor who explains both facts and reasoning in bullet-point format. No bold/italics."},
                {"role": "user", "content": f"Summarize this section of a financial filing in BULLET POINTS. For each bullet, explain BOTH:\n- What happened (fact)\n- Why it happened (drivers, logic, concepts).\n\nText:\n{chunk}"}
            ],
            temperature=0.5,
            max_tokens=500
        )
        summaries.append(response.choices[0].message.content)

    st.subheader("📊 Per-Section Summaries")
    for i, summary in enumerate(summaries):
        with st.expander(f"Section {i+1}"):
            st.markdown(summary)

    # --- Executive summary ---
    with st.spinner("📝 Creating executive summary..."):
        joined_summaries = "\n\n".join(summaries)
        final_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a finance tutor who writes clear, structured executive summaries in bullet-point format. No bold/italics."},
                {"role": "user", "content": f"Here are section summaries from a financial filing:\n{joined_summaries}\n\nWrite a concise EXECUTIVE SUMMARY in BULLET POINTS that highlights:\n- Key facts (what happened)\n- Main drivers/reasons (why it happened)\nKeep it clear and professional."}
            ],
            temperature=0.5,
            max_tokens=600
        )
        executive_summary = final_response.choices[0].message.content

    st.subheader("📌 Executive Summary")
    st.markdown(executive_summary)

    # --- Key Metrics Extraction ---
    st.subheader("📈 Key Metrics")
    metric_prompt = f"""
    Extract and highlight the most important financial metrics from this filing. 
    Focus on:
    - Revenue growth (YoY, QoQ if available)
    - Profitability (gross margin, operating margin, net income)
    - Debt levels and leverage
    - Cash flow highlights
    - Guidance (if mentioned)

    Return them as bullet points with both the number (fact) and its implication (why it matters).
    Text:\n{raw_text[:8000]}
    """
    metric_response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": "You are a financial analyst."},
                  {"role": "user", "content": metric_prompt}],
        temperature=0.4,
        max_tokens=600
    )
    st.markdown(metric_response.choices[0].message.content)

    # --- Explain Jargon ---
    st.subheader("🗂️ Explain Financial Jargon")
    jargon_term = st.text_input("Enter a financial term you'd like explained:")
    if jargon_term:
        jargon_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a finance tutor who explains concepts in plain English with examples. No bold/italics."},
                {"role": "user", "content": f"Explain the term '{jargon_term}' in simple language with a real-world analogy. No bold/italics."}
            ],
            temperature=0.5,
            max_tokens=300
        )
        st.info(jargon_response.choices[0].message.content)

    # --- Q&A ---
    st.subheader("❓ Ask Questions About the Filing")
    user_question = st.text_input("Ask a question (e.g., 'What are Tesla’s main risks this year?')")
    qa_mode = st.radio("Answer Mode:", ["Document Only", "Document + Outside Knowledge"], horizontal=True)

    if user_question:
        if qa_mode == "Document Only":
            qa_prompt = f"Use ONLY the content of this financial filing to answer:\n{user_question}\n\nFiling text:\n{raw_text[:12000]}"
        else:
            qa_prompt = f"Use BOTH the financial filing and your own financial knowledge to answer:\n{user_question}\n\nFiling text:\n{raw_text[:12000]}"

        qa_response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a senior equity research analyst. Always explain both the fact (what) and the reasoning (why). No bold/italics."},
                {"role": "user", "content": qa_prompt}
            ],
            temperature=0.5,
            max_tokens=600
        )
        st.success(qa_response.choices[0].message.content)

    # --- Build Full Report (Markdown + PDF) ---
    full_report = "# 📊 PlainFin Report\n\n"
    full_report += "## 📖 Per-Section Summaries\n\n"
    for i, summary in enumerate(summaries):
        full_report += f"### Section {i+1}\n{summary}\n\n"
    full_report += "## 📌 Executive Summary\n\n" + executive_summary + "\n\n"

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
