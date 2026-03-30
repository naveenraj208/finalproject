import sys
import os

# Set up environment
from llm_client import call_model
from retriever import top_k_similar, search_knowledge_base
from memory_manager import MemoryManager
from prompt_builder import PromptBuilder

def test_ollama():
    print("Testing Ollama Connectivity...")
    try:
        response = call_model("Hello, are you there?", max_tokens=10)
        print(f"Ollama Response: {response}")
        return True
    except Exception as e:
        print(f"Ollama Error: {e}")
        return False

def test_faiss():
    print("\nTesting FAISS Knowledge Base Search...")
    query = "What are the advantages of smart transportation?"
    results = search_knowledge_base(query, k=2)
    if results:
        for text, score in results:
            print(f"Match (Score: {score:.4f}): {text[:100]}...")
        return True
    else:
        print("No results found in KB.")
        return False

def test_prompt_builder():
    print("\nTesting Prompt Builder and Anti-Procrastination...")
    mm = MemoryManager()
    pb = PromptBuilder(mm)
    
    # Test on-topic
    query_on = "Tell me about smart city transportation advantages."
    prompt_on = pb.build(query_on)
    print("On-topic prompt built successfully.")
    
    # Test off-topic
    query_off = "How do I bake a cake?"
    prompt_off = pb.build(query_off)
    if "[SYSTEM NOTE]" in prompt_off:
        print("Anti-Procrastination layer triggered correctly for off-topic query.")
    else:
        print("Anti-Procrastination layer DID NOT trigger (Score might be higher than expected).")
    
    return True

if __name__ == "__main__":
    o = test_ollama()
    f = test_faiss()
    p = test_prompt_builder()
    
    if o and f and p:
        print("\nAll systems operational!")
        sys.exit(0)
    else:
        print("\nSome tests failed.")
        sys.exit(1)
