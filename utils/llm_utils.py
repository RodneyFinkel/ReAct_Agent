import logging
from langchain_groq import ChatGroq


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("LLM-Monitor")



def get_resilient_llm(model_name="llama-3.3-70b-versatile", temperature=0):
    primary = ChatGroq(model_name=model_name, temperature=temperature)
    fallback = ChatGroq(model_name="meta-llama/llama-4-scout-17b-16e-instruct", temperature=temperature)
    
    def log_and_retry(model, name):
        try:
            return model
        except Exception as e:
            logger.error(f"❌ Error in {name}: {str(e)}")
            raise e

    # Note: .with_fallbacks is convenient but hides the individual model errors.
    # To track this, we monitor the primary specifically.
    return primary.with_fallbacks([fallback])



