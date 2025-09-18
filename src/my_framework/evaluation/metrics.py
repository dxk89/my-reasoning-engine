# File: src/my_framework/evaluation/metrics.py

from ..models.base import BaseChatModel
from ..core.schemas import HumanMessage, SystemMessage

def evaluate_faithfulness(query: str, context: str, answer: str, evaluator_llm: BaseChatModel) -> float:
    """
    Uses an 'LLM-as-a-judge' to evaluate if the answer is grounded in the context.
    Returns 1.0 for faithful, 0.0 for not faithful.
    """
    prompt = [
        SystemMessage(
            content="You are a meticulous evaluator. Your task is to determine if the "
                    "'Answer' is fully supported by the provided 'Context'. "
                    "Respond with only 'yes' or 'no'."
        ),
        HumanMessage(
            content=f"Query: {query}\n\n"
                    f"Context: {context}\n\n"
                    f"Answer: {answer}\n\n"
                    "Is the Answer fully supported by the Context? (yes/no)"
        )
    ]
    
    response = evaluator_llm.invoke(prompt)
    decision = response.content.strip().lower()
    
    return 1.0 if decision == "yes" else 0.0