# File: src/my_framework/evaluation/harness.py

from typing import List, Dict, Any, Callable
from ..core.runnables import Runnable

class EvaluationHarness:
    """A class to run evaluations on a given runnable against a dataset."""

    def __init__(
        self,
        runnable_to_test: Runnable,
        evaluator: Callable, # The metric function, e.g., evaluate_faithfulness
        dataset: List[Dict[str, Any]]
    ):
        """
        Args:
            runnable_to_test: The chain or agent to be evaluated.
            evaluator: The function that computes the evaluation metric.
            dataset: A list of dictionaries, where each dict is a test case.
        """
        self.runnable_to_test = runnable_to_test
        self.evaluator = evaluator
        self.dataset = dataset

    def run(self):
        """Runs the evaluation and prints the results."""
        total_score = 0
        total_items = len(self.dataset)
        
        print(f"Starting evaluation with {total_items} test cases...")
        
        for i, item in enumerate(self.dataset):
            print(f"\n--- Running Test Case {i+1}/{total_items} ---")
            
            # Get the predicted output from the runnable
            inputs = item['inputs']
            predicted_output = self.runnable_to_test.invoke(inputs)
            
            print(f"Input: {inputs}")
            print(f"Predicted Output: {predicted_output}")

            # Prepare args for the evaluator function
            eval_args = {
                **item['eval_args'],
                'answer': predicted_output # Pass the runnable's output as the answer
            }
            
            # Calculate the score
            score = self.evaluator(**eval_args)
            total_score += score
            
            print(f"Score: {score}")

        average_score = total_score / total_items if total_items > 0 else 0
        print("\n--- Evaluation Complete ---")
        print(f"Average Score: {average_score:.2f}")
        return {"average_score": average_score}