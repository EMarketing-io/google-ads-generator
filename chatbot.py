from langchain.prompts import PromptTemplate


def answer_question(llm, question, documents):
    prompt = PromptTemplate(
        input_variables=["context", "question"],
        template="""
You are a helpful, knowledgeable assistant supporting a Google Ads strategist.

Answer the user's question based ONLY on the content provided in the context below.
This content was taken from client materials (website, offers, questionnaire, or transcript).

✅ Be concise, clear, and professional.
✅ Focus only on factual, verifiable details found in the content.
❌ Do NOT make up answers. If the answer isn’t in the context, say:

"I'm sorry, I couldn’t find that information in the provided documents."

---

CONTEXT:
{context}

QUESTION:
{question}

ANSWER:
""",
    )

    # Loop through documents to find the best source
    for source, content in documents.items():
        if not content.strip():
            continue  # skip if empty

        # Fill prompt and ask LLM
        response = llm.predict(
            prompt.format(context=content, question=question)
        ).strip()

        # Return if not a generic fallback response
        if response.lower() not in [
            "i don't know",
            "i do not know",
            "i’m not sure",
            "i cannot answer that",
            "i'm sorry, i couldn’t find that information in the provided documents.",
        ]:
            return response, source

    return (
        "I'm sorry, I couldn’t find that information in the provided documents.",
        "None",
    )
