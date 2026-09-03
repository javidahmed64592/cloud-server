// TypeScript types matching FastAPI Pydantic models

// Base response types
export interface BaseResponse {
  message: string;
  timestamp: string;
}

// Response types
export interface HealthResponse extends BaseResponse {}

export interface GetAuthEnabledResponse extends BaseResponse {
  auth_enabled: boolean;
}

// ---------------------------------------------------------------------------
// File models (mirrors cloud_server/models.py)
// ---------------------------------------------------------------------------

// FileMetadata — mirrors backend FileMetadata (id always present in API responses)
export interface FileMetadata {
  id: number;
  filename: string;
  parent_directory: string;
  mime_type: string;
  size: number;
  uploaded_at: number;
  updated_at: number;
}

// API response models (mirrors ListFilesResponse, UploadFileResponse, etc.)
export interface ListFilesResponse extends BaseResponse {
  filesMetadata: FileMetadata[];
}

export interface UploadFileResponse extends BaseResponse {
  fileMetadata: FileMetadata;
}

export interface DeleteFileResponse extends BaseResponse {
  fileMetadata: FileMetadata;
}

export interface UpdateFileMetadataResponse extends BaseResponse {
  fileMetadata: FileMetadata;
}

// API request models (mirrors UpdateFileMetadataRequest)
export interface UpdateFileMetadataRequest {
  filename?: string;
  parentDirectory?: string;
}

export interface MoveFolderRequest {
  newPath: string;
}

export interface MoveFolderResponse extends BaseResponse {
  filesUpdated: number;
}

export interface DeleteFolderResponse extends BaseResponse {
  filesDeleted: number;
}
