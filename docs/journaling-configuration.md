# Journaling Agent Configuration

The journaling agent supports configurable settings through environment variables. These settings allow you to customize when and how summarization is applied to journal entries.

## Configuration Options

### Word Count Threshold
- **Environment Variable**: `JOURNALING_WORD_COUNT_THRESHOLD`
- **Default**: `150`
- **Range**: `10-1000`
- **Description**: Minimum word count to trigger automatic summarization

### Summary Ratio
- **Environment Variable**: `JOURNALING_SUMMARY_RATIO`
- **Default**: `0.2` (20%)
- **Range**: `0.0-1.0`
- **Description**: Maximum ratio of summary length to original text

### Enable Summarization
- **Environment Variable**: `JOURNALING_ENABLE_SUMMARIZATION`
- **Default**: `true`
- **Description**: Enable or disable automatic summarization for long entries

### Minimum Words for Summarization
- **Environment Variable**: `JOURNALING_SUMMARY_MIN_WORDS`
- **Default**: `20`
- **Range**: `5-100`
- **Description**: Minimum words required before summarization can be attempted

### Maximum Summary Attempts
- **Environment Variable**: `JOURNALING_MAX_SUMMARY_ATTEMPTS`
- **Default**: `3`
- **Range**: `1-10`
- **Description**: Maximum attempts for AI summarization before giving up

## Example Configuration

Create or update your `.env` file:

```bash
# Journaling Agent Configuration
JOURNALING_WORD_COUNT_THRESHOLD=200
JOURNALING_SUMMARY_RATIO=0.15
JOURNALING_ENABLE_SUMMARIZATION=true
JOURNALING_SUMMARY_MIN_WORDS=30
JOURNALING_MAX_SUMMARY_ATTEMPTS=2
```

## Usage

The configuration is automatically loaded when the application starts. All functions will use these settings by default, but individual functions also accept optional parameters to override the defaults when needed.

### Programmatic Override Examples

```python
# Use settings defaults
result = exceeds_word_limit(text)

# Override with custom limit
result = exceeds_word_limit(text, word_limit=100)

# Use settings defaults
summary = generate_summary(text)

# Override with custom ratio
summary = generate_summary(text, max_summary_ratio=0.1)
```

## Validation

All configuration values are validated at startup:
- Word count thresholds must be between 10 and 1000
- Summary ratios must be greater than 0.0 and at most 1.0
- Minimum words must be between 5 and 100
- Maximum attempts must be between 1 and 10

Invalid values will raise a `ValidationError` during application startup.
