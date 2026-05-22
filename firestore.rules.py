rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    
    // Global Safety Net catch-all block
    match /{document=**} {
      allow read, write: if false;
    }

    // Helper Functions
    function isSignedIn() {
      return request.auth != null;
    }

    function isValidId(id) {
      return id is string && id.size() <= 128 && id.matches('^[a-zA-Z0-9_\\-]+$');
    }

    function isValidNote(data) {
      return data.id is string 
        && isValidId(data.id)
        && data.title is string
        && data.title.size() <= 200
        && data.content is string
        && data.content.size() <= 50000
        && data.pinned is bool
        && data.trashed is bool
        && data.createdAt is int
        && data.updatedAt is int
        && data.userId is string
        && data.userId == request.auth.uid;
    }

    // Notes Collection Security Matches
    match /notes/{noteId} {
      // Secure reading: secure list queries enforced (checks resource.data.userId)
      allow get: if isSignedIn() && resource.data.userId == request.auth.uid;
      allow list: if isSignedIn() && resource.data.userId == request.auth.uid;

      // Secure write operations with temporal validation
      allow create: if isSignedIn() 
        && isValidId(noteId)
        && noteId == request.resource.data.id
        && isValidNote(request.resource.data)
        && request.resource.data.createdAt <= request.time.toMillis();

      // Secure update actions with partition constraints and immortal field protection
      allow update: if isSignedIn()
        && isValidNote(request.resource.data)
        && resource.data.userId == request.auth.uid
        && request.resource.data.userId == resource.data.userId
        && request.resource.data.id == resource.data.id
        && request.resource.data.createdAt == resource.data.createdAt
        && (
          // Action 1: Toggle Pin State
          (request.resource.data.diff(resource.data).affectedKeys().hasOnly(['pinned', 'updatedAt'])) ||
          // Action 2: Trash / Restore note
          (request.resource.data.diff(resource.data).affectedKeys().hasOnly(['trashed', 'updatedAt'])) ||
          // Action 3: Edit Title or Markdown Notes Body with AI Tagging / Summarizing
          (request.resource.data.diff(resource.data).affectedKeys().hasAny(['title', 'content', 'updatedAt', 'summary', 'tags', 'mood']))
        );

      allow delete: if isSignedIn() && resource.data.userId == request.auth.uid;
    }
  }
}
