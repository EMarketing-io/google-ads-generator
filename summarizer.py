import time
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Standard Libraries
splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)


# Function to summarize text using the provided language model
def summarize_text(llm, text, title):
    
    # Split the text into manageable chunks
    print(f"\n🔍 Summarizing: {title}")
    chunks = splitter.split_text(text)
    chunk_summaries = []

    # Iterate through each chunk and summarize it
    total_chunks = len(chunks)
    total_start = time.time()

    # Print the total number of chunks
    for i, chunk in enumerate(chunks, start=1):
        start_time = time.time()
        print(f"  📦 Chunk {i}/{total_chunks} | {len(chunk)} chars")

        # Prepare the prompt for summarization
        prompt = f"""
You are a Google Ads strategist. Summarize this part of the document titled '{title}' into 150 words or fewer.

CONTENT:
{chunk}
"""
        # Call the language model to summarize the chunk
        try:
            summary = llm.predict(prompt)
            chunk_summaries.append(summary)
            print(f"     ✅ Done in {round(time.time() - start_time, 2)}s")
        except Exception as e:
            print(f"     ❌ Error in chunk {i}: {e}")
        time.sleep(0.5)

    # Combine all chunk summaries into a final summary
    final_start = time.time()
    print(f"\n🧠 Combining {len(chunk_summaries)} summaries...")
    
    # Prepare the final prompt for summarization
    final_prompt = f"""
You are a Google Ads strategist. Summarize the following summaries of the document titled '{title}' into 400 words or fewer.

CONTENT:
{"\n\n".join(chunk_summaries)}
"""
    # Call the language model to summarize the final prompt
    try:
        combined = llm.predict(final_prompt)
        print(f"     ✅ Final summary complete in {round(time.time() - final_start, 2)}s")
    except Exception as e:
        print(f"     ❌ Error in final summary: {e}")
        combined = ""

    print(f"✅ {title} summarization done in {round(time.time() - total_start, 2)} seconds\n")
    return combined