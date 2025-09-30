import logging
from transformers import pipeline, AutoTokenizer

class ITCriticalFilter:

    def __init__(self):

        self._tokenizer = AutoTokenizer.from_pretrained("tasksource/ModernBERT-base-nli")
        self._tokenizer.model_max_length = 2048 # max_position_embeddings in model's config

        self.classifier = pipeline("zero-shot-classification", 
                                   model="tasksource/ModernBERT-base-nli", 
                                   tokenizer=self._tokenizer,
                                   device = 'cpu',
                                   )
        
        self._labels = ['IT-critical', 'Not-IT-critical']
        
    def calculate_relevance(self, text: str) -> tuple[bool, float]:
        """
        Calculate relevance score for IT management news.
        """

        output = self.classifier(text, self._labels)
        labels, scores = output['labels'], output['scores']
        critical_idx = labels.index(self._labels[0])
        is_critical = (scores[critical_idx] > 0.5)

        # print('OUTPUT: ', output)
        # print()

        return is_critical, scores[0]