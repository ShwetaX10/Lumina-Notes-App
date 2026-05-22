{
  "entities": {
    "Note": {
      "title": "Note",
      "description": "An individual note written by a user.",
      "type": "object",
      "properties": {
        "id": {
          "type": "string",
          "description": "Unique identifier of the note"
        },
        "title": {
          "type": "string",
          "description": "Title of the note"
        },
        "content": {
          "type": "string",
          "description": "Markdown body content of the note"
        },
        "pinned": {
          "type": "boolean",
          "description": "Indicates whether the note is pinned"
        },
        "trashed": {
          "type": "boolean",
          "description": "Indicates whether the note is moved to trash"
        },
        "createdAt": {
          "type": "number",
          "description": "Epoch timestamp of creation"
        },
        "updatedAt": {
          "type": "number",
          "description": "Epoch timestamp of last update"
        },
        "summary": {
          "type": "string",
          "description": "AI-generated summary of the note content"
        },
        "tags": {
          "type": "array",
          "description": "Tags associated with the note"
        },
        "mood": {
          "type": "string",
          "description": "AI-identified mental/emotional vibe"
        },
        "userId": {
          "type": "string",
          "description": "Unique user ID of the owner"
        }
      },
      "required": ["id", "title", "content", "pinned", "trashed", "createdAt", "updatedAt", "userId"]
    }
  },
  "firestore": {
    "notes": {
      "schema": "Note",
      "description": "Global collection containing all notes, partitioned and secured by userId."
    }
  }
}

