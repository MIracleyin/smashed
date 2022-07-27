import unittest

import transformers
from smashed.mappers.tokenize import TokenizerMapper, ValidUnicodeMapper
from smashed.interfaces.simple import Dataset, TokenizerMapper, ValidUnicodeMapper

class TestValidUnicodeMapper(unittest.TestCase):
    def test_map(self):
        mapper = ValidUnicodeMapper(
            input_fields=['tokens'],
            unicode_categories=["Cc", "Cf", "Co", "Cs", "Mn", "Zl", "Zp", "Zs"],
            replace_token='[UNK]'
        )
        dataset = Dataset([
            {
                'tokens': ['This', 'example', 'has', 'bad', "\uf02a", "\uf02a\u00ad", "Modalities\uf02a"]
            }
        ])
        new_dataset = mapper.map(dataset)
        self.assertListEqual(new_dataset, [
            {'tokens': ['This', 'example', 'has', 'bad', '[UNK]', '[UNK]', 'Modalities\uf02a']}
        ])


class TestTokenizerMapper(unittest.TestCase):
    def setUp(self):
        self.tokenizer = transformers.AutoTokenizer.from_pretrained(
            'allenai/scibert_scivocab_uncased'
        )

    def test_map(self):
        mapper = TokenizerMapper(
            input_field='text',
            tokenizer=self.tokenizer
        )
        dataset = Dataset([
            {
                'text': [
                    'This is a sentence.',
                    'This is two sentences. Here is the second one.'
                ]
            },
            {
                'text': [
                    'This is a separate instance.',
                    'This',
                    'is',
                    'some',
                    'tokens',
                    '.'
                ]
            }
        ])
        new_dataset = mapper.map(dataset)
        assert len(dataset) == len(new_dataset)     # same num dicts
        assert isinstance(new_dataset[0], dict)     # each element is dict
        assert 'input_ids' in new_dataset[0]        # dict has keys
        assert 'attention_mask' in new_dataset[0]
        assert len(new_dataset[0]['attention_mask']) == len(new_dataset[0]['input_ids'])    # mask same dimension as inputs
        assert self.tokenizer.decode(new_dataset[0]['input_ids'][0]) == '[CLS] this is a sentence. [SEP]'
        assert self.tokenizer.decode(new_dataset[0]['input_ids'][1]) == '[CLS] this is two sentences. here is the second one. [SEP]'

    def test_truncation_max_length(self):
        mapper = TokenizerMapper(
            input_field='text',
            tokenizer=self.tokenizer,
            truncation=True,
            max_length=10,
        )
        dataset = Dataset([
            {
                'text': [
                    'This is an instance that will be truncated because it is longer than ten word pieces.',
                    'This is the subsequent unit in this instance that will be separately truncated.'
                ]
            },
            {
                'text': [
                    'This is the next instance.'
                ]
            }
        ])
        new_dataset = mapper.map(dataset)
        assert len(dataset) == len(new_dataset)     # same num dicts
        assert self.tokenizer.decode(new_dataset[0]['input_ids'][0]) == '[CLS] this is an instance that will be truncated [SEP]'
        assert self.tokenizer.decode(new_dataset[0]['input_ids'][1]) == '[CLS] this is the subsequent unit in this instance [SEP]'
        assert self.tokenizer.decode(new_dataset[1]['input_ids'][0]) == '[CLS] this is the next instance. [SEP]'

    def test_overflow(self):
        mapper = TokenizerMapper(
            input_field='text',
            tokenizer=self.tokenizer,
            truncation=True,
            max_length=10,
            return_overflowing_tokens=True
        )
        dataset = Dataset([
            {
                'text': [
                    'This is an instance that will be truncated because it is longer than ten word pieces.',
                    'This is the subsequent unit in this instance that will be separately truncated.'
                ]
            },
            {
                'text': [
                    'This is the next instance.'
                ]
            }
        ])
        new_dataset = mapper.map(dataset)
        assert len(dataset) == len(new_dataset)     # same num dicts
        assert 'overflow_to_sample_mapping' in new_dataset[0]
        assert self.tokenizer.decode(new_dataset[0]['input_ids'][0]) == '[CLS] this is an instance that will be truncated [SEP]'
        assert self.tokenizer.decode(new_dataset[0]['input_ids'][1]) == '[CLS] because it is longer than ten word pieces [SEP]'
        assert self.tokenizer.decode(new_dataset[0]['input_ids'][2]) == '[CLS]. [SEP]'
        assert self.tokenizer.decode(new_dataset[0]['input_ids'][3]) == '[CLS] this is the subsequent unit in this instance [SEP]'
        assert self.tokenizer.decode(new_dataset[0]['input_ids'][4]) == '[CLS] that will be separately truncated. [SEP]'
        assert self.tokenizer.decode(new_dataset[1]['input_ids'][0]) == '[CLS] this is the next instance. [SEP]'

    def test_char_offsets(self):
        mapper = TokenizerMapper(
            input_field='text',
            tokenizer=self.tokenizer,
            return_offsets_mapping=True
        )
        dataset = Dataset([
            {
                'text': [
                    'This is a Pterodactyl.'
                ]
            }
        ])
        new_dataset = mapper.map(dataset)
        # offsets are start:end char spans into the original text. each wordpiece has its own start/end.
        # special tokens like [cls] and [sep] dont have any offsets (start == end char)
        assert [dataset[0]['text'][0][start:end] for start, end in new_dataset[0]['offset_mapping'][0]] == ['', 'This', 'is', 'a', 'Pt', 'ero', 'da', 'ct', 'yl', '.', '']

    def test_split_into_words(self):
        mapper = TokenizerMapper(
            input_field='text',
            tokenizer=self.tokenizer,
            truncation=True,
            max_length=10,
            return_offsets_mapping=True,
            is_split_into_words=True
        )

        dataset = Dataset([
            {
                'text': [
                    'This is a Pterodactyl.'
                ]
            }
        ])
        new_dataset = mapper.map(dataset)
        # compare this with `test_char_offsets()`. there, we see `offset_mapping` has list elements,
        # but here, it's collapsed into one field
        assert [dataset[0]['text'][0][start:end] for start, end in new_dataset[0]['offset_mapping']] == ['', 'This', 'is', 'a', 'Pt', 'ero', 'da', 'ct', 'yl', '']


        # now try with a larger dataset to test things like truncation and all that
        dataset = Dataset([
            {
                'text': [
                    'This is a sentence.',
                    'This is two sentences. Here is the second one.'
                ]
            },
            {
                'text': [
                    'This is a separate instance.',
                    'This',
                    'is',
                    'some',
                    'tokens',
                    '.'
                ]
            }
        ])
        new_dataset = mapper.map(dataset)
        # when `is_split_into_words=False`, `input_ids` keeps elements in the List[str] separate. that is, tokenizes each separately.
        # when `is_split_into_words=True`, `input_ids` collapses the List[str] into a single str for tokenization.
        # to see difference, compare with the test results from `test_map()`
        assert self.tokenizer.decode(new_dataset[0]['input_ids']) == '[CLS] this is a sentence. this is two [SEP]'
        assert self.tokenizer.decode(new_dataset[1]['input_ids']) == '[CLS] this is a separate instance. this is [SEP]'


        # compare with `test_overflow()`
        # when we set `return_overflowing_tokens=True`, we gain the list elements of `input_ids` again.
        # what happens here is, the list elements are stitched together due to `is_split_into_words=True`,
        # then the overflow logic is applied to create more instances.
        # key difference versus what we see in `test_overflow()` is this no longer adheres to
        # boundaries between List[str] elements within an instance (dict).
        # specifically, the boundary between `...ten word pieces.` and `This is the subsequent...` is gone now.
        mapper = TokenizerMapper(
            input_field='text',
            tokenizer=self.tokenizer,
            truncation=True,
            max_length=10,
            return_offsets_mapping=True,
            is_split_into_words=True,
            return_overflowing_tokens=True
        )
        dataset = Dataset([
            {
                'text': [
                    'This is an instance that will be truncated because it is longer than ten word pieces.',
                    'This is the subsequent unit in this instance that will be separately truncated.'
                ]
            },
            {
                'text': [
                    'This is the next instance.'
                ]
            }
        ])
        new_dataset = mapper.map(dataset)
        assert self.tokenizer.decode(new_dataset[0]['input_ids'][0]) == '[CLS] this is an instance that will be truncated [SEP]'
        assert self.tokenizer.decode(new_dataset[0]['input_ids'][1]) == '[CLS] because it is longer than ten word pieces [SEP]'
        assert self.tokenizer.decode(new_dataset[0]['input_ids'][2]) == '[CLS]. this is the subsequent unit in this [SEP]'
        assert self.tokenizer.decode(new_dataset[0]['input_ids'][3]) == '[CLS] instance that will be separately truncated. [SEP]'
        assert self.tokenizer.decode(new_dataset[1]['input_ids'][0]) == '[CLS] this is the next instance. [SEP]'

    def test_return_words(self):
        mapper = TokenizerMapper(
            input_field='text',
            tokenizer=self.tokenizer,
            truncation=True,
            max_length=10,
            return_offsets_mapping=True,
            is_split_into_words=True,
            return_overflowing_tokens=True,
            return_word_ids=True,
            return_words=True
        )
        dataset = Dataset([
            {
                'text': [
                    'This', 'is', 'a', 'Pterodactyl', 'that', 'will', 'be', 'truncated',
                    'because', 'it', 'is', 'longer', 'than', 'ten', 'word', 'pieces', '.',
                    'This', 'is', 'the', 'subsequent', 'Pterodactyl', 'in', 'this', 'instance',
                    'that', 'will', 'be', 'separately', 'truncated', '.'
                ]
            }
        ])
        new_dataset = mapper.map(dataset)
        assert 'words' in new_dataset
        assert 'word_ids' in new_dataset
        # there are 2 primary functionalities we need to check here
        # first, word pieces are correctly mapped. see how Pterodactyl, which is split into 5 wordpieces, is correctly mapped back to its original word
        # second, despite truncation & returning overflow causing there to be additional new sequences, that we can still map back to
        #  the original word in the sequence. See how tokens in sequence [1] and [2] can still get mapped back to the original word.
        assert new_dataset[0]['words'][0] == [None, 'This', 'is', 'a', 'Pterodactyl', 'Pterodactyl', 'Pterodactyl', 'Pterodactyl', 'Pterodactyl', None]
        assert new_dataset[0]['words'][1] == [None, 'that', 'will', 'be', 'truncated', 'because', 'it', 'is', 'longer', None]
        assert new_dataset[0]['words'][2] == [None, 'than', 'ten', 'word', 'pieces', '.', 'This', 'is', 'the', None]


