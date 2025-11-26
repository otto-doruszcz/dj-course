from tokenizers import Tokenizer
from tokenizers.models import BPE
from tokenizers.trainers import BpeTrainer
from tokenizers.pre_tokenizers import Whitespace
from corpora import get_corpus_file

tokenizer_configs = [
    {
        "corpus_source": "WOLNELEKTURY",
        "file_pattern": "pan-tadeusz-*.txt",
        "output_file": "tokenizers/pan-tadeusz-tokenizer.json"
    },
    {
        "corpus_source": "WOLNELEKTURY",
        "file_pattern": "*.txt",
        "output_file": "tokenizers/tokenizer-wolnelektury.json"
    },
    {
        "corpus_source": "NKJP",
        "file_pattern": "*.txt",
        "output_file": "tokenizers/tokenizer-nkjp.json"
    },
    {
        "corpus_source": "ALL",
        "file_pattern": "*.txt",
        "output_file": "tokenizers/tokenizer-all-corpora.json"
    },
    # Add more configs as needed
    # {
    #     "corpus_source": "OTHER_SOURCE",
    #     "file_pattern": "other_file.txt",
    #     "output_file": "tokenizers/other_tokenizer.json"
    # }
]
for config in tokenizer_configs:
    FILES = [str(f) for f in get_corpus_file(config["corpus_source"], config["file_pattern"])]
    tokenizer = Tokenizer(BPE(unk_token="[UNK]"))
    tokenizer.pre_tokenizer = Whitespace()
    trainer = BpeTrainer(
        special_tokens=["[UNK]", "[CLS]", "[SEP]", "[PAD]", "[MASK]"],
        vocab_size=32000,
        min_frequency=2
    )
    tokenizer.train(FILES, trainer=trainer)
    tokenizer.save(config["output_file"])

for txt in [
    "Litwo! Ojczyzno moja! ty jesteś jak zdrowie.",
    "Jakże mi wesoło!",
    "Jeśli wolisz mieć pełną kontrolę nad tym, które listy są łączone (a to jest bezpieczniejsze, gdy słownik może zawierać inne klucze), po prostu prześlij listę list do spłaszczenia.",
]:
    encoded = tokenizer.encode(txt)
    print("Zakodowany tekst:", encoded.tokens)
    print("ID tokenów:", encoded.ids)
