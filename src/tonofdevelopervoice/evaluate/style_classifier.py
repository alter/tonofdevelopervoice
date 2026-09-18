# style_classifier.py
from dataclasses import dataclass

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split


@dataclass(frozen=True)
class StyleClassifierResult:
    held_out_accuracy: float


class StyleClassifier:
    def __init__(self) -> None:
        self._vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4))
        self._model = LogisticRegression(max_iter=1000)
        self._fitted = False

    def fit(
        self,
        authentic_texts: list[str],
        synthetic_texts: list[str],
        test_size: float = 0.2,
        seed: int = 42,
    ) -> StyleClassifierResult:
        texts = authentic_texts + synthetic_texts
        labels = [1] * len(authentic_texts) + [0] * len(synthetic_texts)

        x_train, x_test, y_train, y_test = train_test_split(
            texts, labels, test_size=test_size, random_state=seed, stratify=labels
        )

        x_train_vec = self._vectorizer.fit_transform(x_train)
        self._model.fit(x_train_vec, y_train)
        self._fitted = True

        x_test_vec = self._vectorizer.transform(x_test)
        accuracy = float(self._model.score(x_test_vec, y_test))
        return StyleClassifierResult(held_out_accuracy=accuracy)

    def score(self, text: str) -> float:
        if not self._fitted:
            raise RuntimeError("StyleClassifier must be fit before scoring")
        vec = self._vectorizer.transform([text])
        proba = self._model.predict_proba(vec)[0]
        classes = list(self._model.classes_)
        return float(proba[classes.index(1)])
