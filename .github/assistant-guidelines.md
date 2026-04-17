# Assistant Guidelines for `.prompts` Storage

These guidelines tell the assistant exactly how to write prompt files in this repository.

<!-- Created for raptor-mini-preview -->

- Store every user prompt in the `.prompts/` directory.
- Use one file per prompt.
- When a user prompt is received, automatically create a new file in `.prompts/`.
- File names must follow the pattern:
  `YYYY-MM-DD-###-raptor-mini-preview.txt`
  - `YYYY-MM-DD` is the current date.
  - `###` is a zero-padded sequence number for that date.
  - `raptor-mini-preview` is the model name.
    Replace this model name with the actual AI model that you use.
- File content must contain only the raw prompt text from the user.
- Do not add headings, bullets, annotations, or any markup.
- Do not store assistant responses or metadata inside these files.
- If a file name already exists, choose the next available sequence number.
- If `.prompts/` does not exist, create it.
- `.prompts/committed` is reserved for prompts that are already included in commit messages.
  - Do not create new user prompt files in `.prompts/committed`.
  - Do not duplicate `.prompts/committed` entries as files directly in `.prompts/`.
- Do not use `/memories/` or any workspace-local memory for this storage rule.
- For a fresh clone, use this file as the canonical instruction source.
- If the user asks to store new prompts, then assure there is one file for each and all of the uncommitted prompts of that session.
  - Read the latest prompt file and find the prompts in your memory. Then store all prompts that came after this.
  - Check that prompts that are in the `.prompts/` directory are not duplicates.
  - Create a new file for each prompt that was prompted to you by the user in this session if it does not already exist.
  - Follow all above guidelines.
