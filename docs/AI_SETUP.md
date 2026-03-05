# AI Analysis Feature - Setup Guide

## Overview

Fortune Lab now includes AI-powered analysis using Ollama with LLaMA 3.1 8B model. This feature provides intelligent interpretation of lottery statistics, pattern analysis, and AI-recommended number combinations.

## Prerequisites

1. **Ollama** installed on your system
2. **LLaMA 3.1 8B model** (or another compatible model)

## Installation Steps

### 1. Install Ollama

#### Linux
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

#### macOS
```bash
brew install ollama
```

#### Windows
Download from: https://ollama.com/download/windows

### 2. Start Ollama Service

```bash
ollama serve
```

Leave this running in a terminal window.

### 3. Pull the LLaMA Model

In a new terminal:
```bash
ollama pull llama3.1:8b
```

This will download the ~4.7GB model. It may take a few minutes depending on your internet connection.

### 4. Verify Installation

Run the test script:
```bash
uv run python test_ollama.py
```

You should see:
```
✅ Ollama is ready! AI features are available.
```

## Configuration

Edit your `.env` file or set environment variables:

```env
# AI Configuration
OLLAMA_ENABLED=True
OLLAMA_MODEL=llama3.1:8b
OLLAMA_HOST=http://localhost:11434
OLLAMA_TIMEOUT=120
```

### Configuration Options

- **OLLAMA_ENABLED**: Enable/disable AI features (default: `True`)
- **OLLAMA_MODEL**: Model to use (default: `llama3.1:8b`)
- **OLLAMA_HOST**: Ollama server URL (default: `http://localhost:11434`)
- **OLLAMA_TIMEOUT**: Request timeout in seconds (default: `120`)

## Using Other Models

You can use different Ollama models:

```bash
# Pull a different model
ollama pull llama3.2:3b    # Smaller, faster
ollama pull mistral:7b     # Alternative model
ollama pull llama3.1:70b   # Larger, more capable (requires more RAM)
```

Update your `.env`:
```env
OLLAMA_MODEL=mistral:7b
```

## Using the AI Analysis Feature

### From the Web Interface

1. **Scrape lottery data** (if not already done)
2. **Generate analysis** for a result file
3. Click the **"Analysis History"** button
4. Click **"Analyze with AI"** button (🧠icon)
5. Wait for AI to process (may take 30-60 seconds)
6. View the AI-generated insights and recommendations

### Via API

```bash
curl -X POST http://localhost:5000/api/ai-analyze \
  -H "Content-Type: application/json" \
  -d '{"filename": "analysis_result_Ultra_Lotto_6-58_20260115_20260116_070044.json"}'
```

### Check Ollama Status

```bash
curl http://localhost:5000/api/ollama-status
```

## What the AI Provides

1. **Executive Summary** - Key insights from statistical analysis
2. **Statistical Interpretation** - Pattern analysis and trends
3. **AI-Recommended Top 5 Combinations** - Data-driven number predictions
4. **Detailed Reasoning** - Explanation for each recommendation
5. **Responsible Gaming Disclaimer** - Reminder about randomness

## Troubleshooting

### Ollama Not Running

**Error**: "Ollama is not running"

**Solution**:
```bash
ollama serve
```

### Model Not Available

**Error**: "Model 'llama3.1:8b' is not available"

**Solution**:
```bash
ollama pull llama3.1:8b
```

### Timeout Errors

**Error**: "AI analysis failed" with timeout

**Solution**: Increase timeout in `.env`:
```env
OLLAMA_TIMEOUT=180  # 3 minutes
```

### Connection Refused

**Error**: "Connection refused to http://localhost:11434"

**Solution**: 
1. Check if Ollama is running: `ps aux | grep ollama`
2. Try restarting: `ollama serve`
3. Check if port 11434 is available: `lsof -i :11434`

### Out of Memory

**Error**: Model loading fails or system freezes

**Solution**:
- Use a smaller model: `ollama pull llama3.2:3b`
- Close other applications
- Ensure you have at least 8GB RAM for 8B models

### Slow Performance

**Tips**:
- Use GPU acceleration (CUDA/Metal) if available
- Use smaller models for faster responses
- Increase available RAM
- Close unnecessary applications

## Performance Notes

### Model Sizes and Requirements

| Model | Size | RAM Required | Speed | Quality |
|-------|------|--------------|-------|---------|
| llama3.2:3b | ~2GB | 4GB | Fast | Good |
| llama3.1:8b | ~4.7GB | 8GB | Medium | Excellent |
| mistral:7b | ~4.1GB | 8GB | Medium | Excellent |
| llama3.1:70b | ~40GB | 64GB | Slow | Outstanding |

### Response Times

- **Small models (3B)**: 10-20 seconds
- **Medium models (7-8B)**: 30-60 seconds
- **Large models (70B)**: 2-5 minutes

## Security Considerations

- Ollama runs **locally** - no data sent to external servers
- All analysis happens on your machine
- No API keys or cloud services required
- Complete privacy and data control

## Advanced Usage

### Custom Prompts

Edit `app/modules/ai_analyzer.py` to customize the analysis prompt:

```python
def _build_analysis_prompt(self, ...):
    prompt = f"""
    # Your custom prompt here
    ...
    """
    return prompt
```

### Temperature and Parameters

Modify the `ollama.chat()` call in `ai_analyzer.py`:

```python
response = ollama.chat(
    model=self.model,
    messages=[...],
    options={
        'temperature': 0.7,    # 0.0-1.0 (lower = more focused)
        'top_p': 0.9,          # Nucleus sampling
        'num_predict': 2000,   # Max tokens
    }
)
```

## Disabling AI Features

To disable AI features without uninstalling:

```env
OLLAMA_ENABLED=False
```

Or remove the ollama package:

```bash
uv remove ollama
```

## Resources

- **Ollama Documentation**: https://ollama.com/
- **Available Models**: https://ollama.com/library
- **API Reference**: https://github.com/ollama/ollama/blob/main/docs/api.md

## Support

If you encounter issues:

1. Check this guide's troubleshooting section
2. Verify Ollama is running: `ollama list`
3. Test with: `uv run python test_ollama.py`
4. Check logs in console for detailed error messages

---

**Note**: AI predictions are based on statistical patterns but lottery draws are inherently random. Use AI analysis for educational and entertainment purposes only. Always gamble responsibly.
