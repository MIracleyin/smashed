import pickle
import unittest

from necessary import necessary

from smashed.mappers import (
    TokenizerMapper,
    TruncateNFieldsMapper,
    UnpackingMapper,
)
from smashed.mappers.debug import MockMapper

with necessary(("datasets", "dill")):
    import dill
    from datasets.arrow_dataset import Dataset
    from datasets.fingerprint import Hasher

with necessary("transformers"):
    from transformers import AutoTokenizer


class TestPickling(unittest.TestCase):
    def test_pickle(self):
        """Test if caching works"""

        # this should not fail
        m = MockMapper(1) >> MockMapper(1)
        m2 = pickle.loads(pickle.dumps(m))
        self.assertEqual(m, m2)

        # the pickled pipeline should yield same results
        dt = [{"a": 1, "b": 2}]
        out1 = m.map(dt)
        out2 = m2.map(dt)
        self.assertEqual(out1, out2)

        # this should not fail if class is picklable
        hasher = Hasher()
        hasher.update(m.transform)
        hasher.hexdigest()

    def test_dill(self):
        """Test if caching works"""

        # this should not fail
        m = MockMapper(1) >> MockMapper(1)
        m2 = dill.loads(dill.dumps(m))
        self.assertEqual(m, m2)

        # the dilled pipeline should yield same results
        dt = [{"a": 1, "b": 2}]
        out1 = m.map(dt)
        out2 = m2.map(dt)
        self.assertEqual(out1, out2)

        # this should not fail if class is dillable
        hasher = Hasher()
        hasher.update(m.transform)
        hasher.hexdigest()

    def test_unpacking_fingerprint(self):
        """Test if fingerprinting works"""
        mp = (
            UnpackingMapper(
                fields_to_unpack=["a", "b"], ignored_behavior="drop"
            )
            >> MockMapper(1)
            >> MockMapper(1)
        )

        dataset = Dataset.from_dict({"a": [[1, 2, 3]], "b": [[4, 5, 6]]})

        hashes = set()
        for _ in range(100):
            processed_dataset = mp.map(dataset)
            hashes.add(processed_dataset._fingerprint)

        self.assertEqual(len(hashes), 1)

    def test_tokenizer_fingerprint(self):
        dataset = Dataset.from_dict(
            {"a": ["hello world", "my name is john doe"]}
        )

        mp = TokenizerMapper(
            tokenizer=AutoTokenizer.from_pretrained("bert-base-uncased"),
            input_field="a",
        )

        hashes = set()
        for _ in range(100):
            processed_dataset = mp.map(dataset)
            hashes.add(processed_dataset._fingerprint)

        self.assertEqual(len(hashes), 1)

    def test_truncate_fingerprint(self):
        mp = TruncateNFieldsMapper(fields_to_truncate=["a", "b"], max_length=2)

        dataset = Dataset.from_dict({"a": [[1, 2, 3]], "b": [[4, 5, 6]]})

        hashes = set()
        for _ in range(100):
            processed_dataset = mp.map(dataset)
            hashes.add(processed_dataset._fingerprint)

        self.assertEqual(len(hashes), 1)
