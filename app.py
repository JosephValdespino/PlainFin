import streamlit as st
from openai import OpenAI

# Load API key from Streamlit secrets
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

st.title("📘 PlainFin: Learn Finance Smarter")
st.write("Ask me any finance question — I'll explain not just *what* it is, but also *why* it works that way.")

# User input
user_question = st.text_input("💬 Enter your finance question:")

if user_question:
    with st.spinner("Thinking..."):
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a patient finance tutor. Explain concepts clearly, step by step, with both the definition and the logic behind it."},
                {"role": "user", "content": user_question}
            ]
        )

        answer = response.choices[0].message.content
        st.markdown(f"### ✨ Answer:\n{answer}")
