class AppError(Exception):
    """Base class for application-level errors with an HTTP status mapping."""
    status_code = 500
    detail = "Internal server error"

    def __init__(self, detail: str | None = None):
        self.detail = detail or self.detail
        super().__init__(self.detail)


class UserAlreadyExistsError(AppError):
    status_code = 409
    detail = "Email already registered"


class InvalidCredentialsError(AppError):
    status_code = 401
    detail = "Incorrect email or password"


class UserNotFoundError(AppError):
    status_code = 404
    detail = "User not found"


class DocumentNotFoundError(AppError):
    status_code = 404
    detail = "Document not found"


class UnsupportedFileTypeError(AppError):
    status_code = 400
    detail = "Unsupported file type"


class FileTooLargeError(AppError):
    status_code = 413
    detail = "File exceeds maximum upload size"


class DocumentProcessingError(AppError):
    status_code = 500
    detail = "Failed to process document"


class NoDocumentsError(AppError):
    status_code = 404
    detail = "No documents found. Upload a document first."


class GenerationError(AppError):
    status_code = 502
    detail = "Failed to generate an answer"
