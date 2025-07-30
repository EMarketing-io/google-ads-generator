from langchain.prompts import PromptTemplate


def answer_question(llm, question, documents):
    for source, content in documents.items():
        if not content.strip():
            continue

        prompt = PromptTemplate(
            input_variables=["context", "question"],
            template="""
You are a helpful assistant. Use the context below to answer the question.

CONTEXT:
{context}

QUESTION:
{question}

If the answer is not found in the context, say: "I don’t know based on the given document."
""",
        )

        response = llm.predict(prompt.format(context=content, question=question)).strip()

        if response.lower() not in [
            "i don't know",
            "i do not know",
            "i’m not sure",
            "i don’t know based on the given document.",
            "i cannot answer that",
        ]:
            return response, source

    return "❌ I couldn’t find the answer in any of the documents.", "None"
