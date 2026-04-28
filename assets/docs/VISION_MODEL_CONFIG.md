# Vision Model Configuration

DeepTutor now supports separate model configuration for vision/image recognition tasks. This allows you to use a different (typically more capable) model for image analysis while using a more cost-effective model for text-only tasks.

## Configuration

### Environment Variables

Set the `LLM_VISION_MODEL` environment variable to specify a separate model for vision tasks:

```bash
# Main model for text generation
export LLM_MODEL=gpt-4o-mini

# Separate model for vision/image analysis
export LLM_VISION_MODEL=gpt-4o

# Other required settings
export LLM_HOST=https://api.openai.com/v1
export LLM_API_KEY=sk-xxx
export LLM_BINDING=openai
```

If `LLM_VISION_MODEL` is not set, the system will automatically fall back to using `LLM_MODEL` for vision tasks.

### Programmatic Configuration

You can also configure the vision model programmatically:

```python
from deeptutor.services.llm.config import LLMConfig

# Create config with separate vision model
config = LLMConfig(
    model="gpt-4o-mini",
    vision_model="gpt-4o",
    api_key="sk-xxx",
    base_url="https://api.openai.com/v1"
)

# Get effective vision model
vision_model = config.get_vision_model()  # Returns "gpt-4o"

# If vision_model is not set, it returns the main model
config2 = LLMConfig(model="gpt-4o-mini", api_key="sk-xxx", base_url="...")
vision_model2 = config2.get_vision_model()  # Returns "gpt-4o-mini"
```

## Components Using Vision Models

The following components will automatically use the configured vision model:

### 1. VisionSolverAgent (GeoGebra Analysis)

Used for analyzing math problem images and generating GeoGebra visualizations:

```python
from deeptutor.agents.vision_solver import VisionSolverAgent

# Agent will automatically use config.get_vision_model()
agent = VisionSolverAgent(
    api_key=llm_config.api_key,
    base_url=llm_config.base_url,
)

# Or explicitly specify a different vision model
agent = VisionSolverAgent(
    api_key=llm_config.api_key,
    base_url=llm_config.base_url,
    vision_model="custom-vision-model"
)
```

### 2. EPUBImageAnalyzer

Used for analyzing images in EPUB documents:

```python
from deeptutor.utils.epub_image_analyzer import EPUBImageAnalyzer

# Analyzer will automatically use config.get_vision_model()
analyzer = EPUBImageAnalyzer()

# Or explicitly specify a vision model
analyzer = EPUBImageAnalyzer(vision_model="gpt-4o")
```

### 3. GeoGebra Analysis Tool

The `geogebra_analysis` built-in tool automatically uses the configured vision model through the VisionSolverAgent.

## Common Use Cases

### Cost Optimization

Use a smaller, cheaper model for text tasks and a larger model only for vision:

```bash
export LLM_MODEL=gpt-4o-mini              # Cheap for text
export LLM_VISION_MODEL=gpt-4o            # More capable for vision
```

### Performance Optimization

Use different providers for different tasks:

```bash
export LLM_MODEL=deepseek-chat            # Fast for text
export LLM_VISION_MODEL=gpt-4o            # Better vision capabilities
```

### Testing

Use different model versions for testing:

```bash
export LLM_MODEL=gpt-4o-mini
export LLM_VISION_MODEL=gpt-4o-mini-2024-07-18  # Specific version for vision
```

## Supported Models

Any vision-capable model supported by your LLM provider can be used. Common options include:

- OpenAI: `gpt-4o`, `gpt-4o-mini`, `gpt-4-turbo`, `gpt-4-vision-preview`
- Anthropic: `claude-3-opus`, `claude-3-sonnet`, `claude-3-haiku`
- Google: `gemini-pro-vision`
- Local: Vision-capable models via Ollama (e.g., `llava`, `bakllava`)

## Migration Guide

### For Existing Users

No changes are required! If you don't set `LLM_VISION_MODEL`, the system will continue to use your `LLM_MODEL` for all tasks, maintaining backward compatibility.

### For New Deployments

To take advantage of separate vision model configuration:

1. Add `LLM_VISION_MODEL` to your `.env` file
2. Restart your DeepTutor service
3. The new configuration will be automatically picked up

## Troubleshooting

### Vision model not being used

Check that:
1. `LLM_VISION_MODEL` is set in your environment
2. The specified model supports vision capabilities
3. You've restarted the service after configuration changes

### Different model capabilities

Some models have different vision capabilities. If you encounter issues:
- Ensure the vision model actually supports multimodal input
- Check provider documentation for model capabilities
- Review logs for capability warnings

## API Reference

### LLMConfig

```python
class LLMConfig:
    vision_model: str | None = None  # Separate model for vision tasks

    def get_vision_model(self) -> str:
        """Return the vision model, falling back to main model if not specified."""
        return self.vision_model or self.model
```

### Environment Variables

- `LLM_MODEL`: Main model for text generation (required)
- `LLM_VISION_MODEL`: Model for vision/image tasks (optional, defaults to LLM_MODEL)
- `LLM_HOST`: API endpoint URL (required)
- `LLM_API_KEY`: API authentication key (required)
- `LLM_BINDING`: Provider binding (default: `openai`)

## Examples

See the test suite for more examples:
- `tests/services/llm/test_config_module.py` - Configuration tests
- `tests/core/test_builtin_tools.py` - Tool integration tests
