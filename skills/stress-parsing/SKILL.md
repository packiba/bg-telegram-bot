# Skill: stress-parsing

## Overview

Use this skill when working with Bulgarian stress accent placement via the rechnik.chitanka.info dictionary parser. Covers parsing logic, fallback strategies, and Unicode handling.

## When to Use

- Modifying `utils/stress.py`
- Debugging stress mark placement issues
- Updating parser for dictionary structure changes
- Adding new stress-related functionality

## Dictionary API

### Endpoint
```
GET https://rechnik.chitanka.info/w/{word}
```

### Response
HTML page with word forms and stress marks.

### Parsing Strategy

#### Primary Method
Find stressed word forms:
```python
soup.find_all('span', id=lambda x: x and x.startswith('name-stressed_'))
```

#### Fallback Method
Find any Cyrillic tokens with combining diacritical marks:
```python
import re
cyrillic_with_stress = re.findall(r'[а-яА-ЯёЁ\u0300\u0301]+', html_text)
```

#### Lemmatization Fallback
If direct lookup fails:
1. Find "производна форма" (derived form) link on page
2. Extract base form URL from `<a href="/w/...">`
3. Fetch base form page
4. Extract stressed vowel position
5. Map stress to original word by vowel index

## Core Algorithm

### add_stress_to_text(text, force_bulgarian=False)

```
1. If not force_bulgarian:
   - Check for LANG:BG marker (case-insensitive, anywhere)
   - If not found: return text unchanged
   - Strip LANG:BG/LANG:RU markers

2. Tokenize text into: words, punctuation, whitespace

3. For each word:
   - If ≤1 vowel: return as-is
   - Lookup stress via dictionary
   - Apply stress mark if found
   - Preserve original casing

4. Reassemble and return
```

### Word-Level Stress Lookup

```
_lookup_word_stress(word):
1. Normalize: strip existing accents
2. If ≤1 vowel: return word
3. Try direct lookup:
   - Fetch chitanka page
   - Parse stressed forms
   - Return first match
4. If direct fails, try lemmatization:
   - Find base form link
   - Fetch base form page
   - Extract stressed vowel index
   - Map to original word
5. If all fails: return word unchanged
```

## Unicode Handling

### Stress Marks
- Combining grave accent: `\u0300` (U+0300)
- Combining acute accent: `\u0301` (U+0301)
- Applied to vowel characters

### Bulgarian Vowels
```
а е и о у ъ ю я
А Е И О У Ъ Ю Я
```

### Key Functions

#### strip_accents(str)
```python
def strip_accents(s: str) -> str:
    return s.normalize('NFD').replace('\u0300', '').replace('\u0301', '').normalize('NFC')
```

#### vowel_positions(word)
```python
def vowel_positions(word: str) -> list[int]:
    # Returns indices of vowels in word
    # Accounts for combining characters
```

#### stressed_vowel_index(stressed_word)
```python
def stressed_vowel_index(word: str) -> int:
    # Returns which vowel (0-based) has stress mark
    # Returns -1 if no stress found
```

#### apply_stress(word, vowel_index)
```python
def apply_stress(word: str, index: int) -> str:
    # Inserts \u0300 after the vowel at given index
    # Preserves casing
```

## Caching Strategy

### Word-Level Cache
```python
@functools.lru_cache(maxsize=5000)
def _lookup_word_stress(word: str) -> str:
    ...
```

### Cache Behavior
- Cache key: lowercase normalized word
- Cache hit: instant return
- Cache miss: HTTP request + parse
- Cache size: 5000 words (~99% hit rate for typical usage)
- No invalidation needed (dictionary is static)

## Error Handling

### HTTP Errors
- 404: Word not in dictionary → return word unchanged
- 500: Server error → return word unchanged
- Timeout (10s): → return word unchanged
- Connection error: → return word unchanged

### Parsing Errors
- HTML structure changed: → fallback to regex method
- No stressed forms found: → try lemmatization
- Lemmatization fails: → return word unchanged

### Logging
```python
logger.warning(f"Stress lookup failed for '{word}': {error}")
```

## Testing

### Test Cases
```python
# Direct lookup
"болгарский" → "български" (with stress)
"река" → "река̀" or "ре́ка"

# Lemmatization
"реки" → lookup "река" → map stress

# Already stressed
"ре́ка" → strip → lookup → reapply

# No stress needed
"в" → "в" (consonant only)
"и" → "и" (single vowel)

# Mixed case
"България" → "България̀" (preserve capital)

# Punctuation
"Здравей!" → "Здраве́й!" (preserve punctuation)
```

### Validation
```bash
# Test against known words
python -c "from utils.stress import add_stress_to_text; print(add_stress_to_text('болгарский текст', force_bulgarian=True))"
```

## Maintenance

### Dictionary Structure Changes
If rechnik.chitanka.info changes HTML structure:
1. Update primary parsing selector
2. Verify fallback still works
3. Test against sample words
4. Update this skill documentation

### Performance
- Monitor cache hit rate
- Consider Redis cache if >1000 concurrent users
- Batch requests for long texts (future optimization)

## Reference

- Dictionary: https://rechnik.chitanka.info
- Unicode combining characters: https://unicode.org/charts/PDF/U0300.pdf
- Bulgarian alphabet: https://en.wikipedia.org/wiki/Bulgarian_alphabet
