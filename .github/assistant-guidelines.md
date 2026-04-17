# Assistant Guidelines for `.prompts` Storage

These guidelines tell the assistant exactly how to write prompt files in this repository.

- Store every user prompt in the `.prompts/` directory.
- Use one file per prompt.
- When a user prompt is received, automatically create a new file in `.prompts/`.
- File names must follow the pattern:
  `YYYY-MM-DD-###-raptor-mini-preview.txt`
  - `YYYY-MM-DD` is the current date.
  - `###` is a zero-padded sequence number for that date.
  - `raptor-mini-preview` is the model name.
- File content must contain only the raw prompt text from the user.
- Do not add headings, bullets, annotations, or any Markdown markup.
- Do not store assistant responses or metadata inside these files.
- If a file name already exists, choose the next available sequence number.
- If `.prompts/` does not exist, create it.
- Do not use `/memories/` or any workspace-local memory for this storage rule.
- For a fresh clone, use this file as the canonical instruction source.
