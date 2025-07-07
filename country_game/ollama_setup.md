# Ollama Setup for Country Game

## Installation Instructions

1. Download and install Ollama for your operating system:
   - Windows: Visit [https://ollama.com/download/windows](https://ollama.com/download/windows)
   - macOS: Visit [https://ollama.com/download/mac](https://ollama.com/download/mac)
   - Linux: Run `curl -fsSL https://ollama.com/install.sh | sh`

2. Verify Ollama is installed correctly by opening a terminal/command prompt and running:
   ```
   ollama --version
   ```

## Adding the Gemma 7B Model

1. Once Ollama is installed, pull the Gemma 7B model by running:
   ```
   ollama pull gemma:7b
   ```

2. Wait for the download to complete. This may take some time depending on your internet connection as the model is several gigabytes in size.

3. Verify the model was downloaded successfully by running:
   ```
   ollama list
   ```
   You should see `gemma:7b` in the list of available models.

## Using the Gemma 7B Model

The Gemma 7B model can be used for various natural language processing tasks. To run the model:

```
ollama run gemma:7b
```

This will start an interactive session where you can input prompts and receive responses from the model.

## Note

No code changes were made to the existing project as per requirements. This setup only adds the local model for use with Ollama.