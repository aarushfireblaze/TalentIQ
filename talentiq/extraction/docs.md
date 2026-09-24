# Talent IQ prototype

This prototype extracts role-related tags from three candidate materials using OpenRouter's `deepseek/deepseek-v4.1-flash` model. It returns JSON in this form:

```json
{"tags": ["Python", "personal software project"]}
```

Tags are selected from `tags.md`; unsupported capabilities are omitted.

## Files

- `src/extract.py` contains the `extract(resume, conversation, notes)` function.
- `src/questions.py` contains the resume-only `gen_questions(resume)` function.
- `src/openrouter.py` shares the OpenRouter model, key loading, and JSON request code between both functions.
- `src/server.py` serves the local test page and sample API.
- `samples/` contains four candidate packets, each with a resume, conversation, recruiter notes, and candidate metadata.
- `test/index.html` is the browser interface.

## Run

The local `api.rtf` file is read at runtime and is not included in source responses. On macOS, Python uses the built-in `textutil` command to read it. To use a plain text key file instead, set `OPENROUTER_API_KEY_FILE`; alternatively set `OPENROUTER_API_KEY` in the environment.

```sh
python3 src/server.py
```

Open [http://localhost:1341](http://localhost:1341), choose a candidate, review the three source texts, and select **Run extract**. The browser displays the returned JSON. Extraction requires internet access and a valid OpenRouter key.

The extraction function can also be called directly:

```python
from src.extract import extract

result = extract(resume_text, conversation_text, recruiter_notes)
```

## Resume follow-up questions

`src/questions.py` provides `gen_questions(resume)`. It uses the same OpenRouter model and local key setup to find details that would help a recruiter assess evidence more accurately for Software Engineering Intern and Product Owner roles. It returns 3–5 specific, neutral questions as a list of strings. It focuses on unclear contributions, skill depth, tools, outcomes, and relevant experience missing from the resume.

```python
from src.questions import gen_questions

questions = gen_questions(resume_text)
```

This function is available for backend use; the local test page does not call it.
