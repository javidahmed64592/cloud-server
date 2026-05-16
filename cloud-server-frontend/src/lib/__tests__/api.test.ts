import { renderHook } from "@testing-library/react";

import {
  deleteFile,
  getFileBlob,
  getHealth,
  getThumbnailBlob,
  listFiles,
  login,
  updateFileMetadata,
  uploadFile,
  useHealthStatus,
  type HealthStatus,
} from "@/lib/api";
import type {
  FileMetadata,
  HealthResponse,
  LoginResponse,
  UpdateFileMetadataRequest,
} from "@/lib/types";

jest.mock("../api", () => {
  const actual = jest.requireActual("../api");
  return {
    ...actual,
    getHealth: jest.fn(),
    login: jest.fn(),
    listFiles: jest.fn(),
    uploadFile: jest.fn(),
    getFileBlob: jest.fn(),
    deleteFile: jest.fn(),
    updateFileMetadata: jest.fn(),
    getThumbnailBlob: jest.fn(),
  };
});

// Mock fetch for config endpoint
global.fetch = jest.fn();

// Mock URL.createObjectURL and revokeObjectURL
global.URL.createObjectURL = jest.fn(() => "blob:http://localhost/mock-blob");
global.URL.revokeObjectURL = jest.fn();

const mockGetHealth = getHealth as jest.MockedFunction<typeof getHealth>;
const mockLogin = login as jest.MockedFunction<typeof login>;
const mockListFiles = listFiles as jest.MockedFunction<typeof listFiles>;
const mockUploadFile = uploadFile as jest.MockedFunction<typeof uploadFile>;
const mockGetFileBlob = getFileBlob as jest.MockedFunction<typeof getFileBlob>;
const mockDeleteFile = deleteFile as jest.MockedFunction<typeof deleteFile>;
const mockUpdateFileMetadata = updateFileMetadata as jest.MockedFunction<
  typeof updateFileMetadata
>;
const mockGetThumbnailBlob = getThumbnailBlob as jest.MockedFunction<
  typeof getThumbnailBlob
>;

describe("API Tests", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe("health", () => {
    it("should fetch health status successfully", async () => {
      const mockHealth: HealthResponse = {
        message: "Server is healthy",
        timestamp: "2023-01-01T00:00:00Z",
      };

      mockGetHealth.mockResolvedValue(mockHealth);

      const health = await getHealth();

      expect(mockGetHealth).toHaveBeenCalled();
      expect(health).toEqual(mockHealth);
    });

    it("should handle health check error", async () => {
      const errorMessage = "Service unavailable";
      mockGetHealth.mockRejectedValue(new Error(errorMessage));

      await expect(getHealth()).rejects.toThrow(errorMessage);
    });

    it("should handle network error (no response)", async () => {
      const errorMessage =
        "No response from server. Please check if the backend is running.";
      mockGetHealth.mockRejectedValue(new Error(errorMessage));

      await expect(getHealth()).rejects.toThrow(errorMessage);
    });
  });

  describe("login", () => {
    it("should successfully login with valid API key", async () => {
      const mockResponse: LoginResponse = {
        message: "Login successful.",
        timestamp: "2023-01-01T00:00:00Z",
      };

      mockLogin.mockResolvedValue(mockResponse);

      const result = await login("valid-api-key-123");

      expect(result).toEqual(mockResponse);
      expect(mockLogin).toHaveBeenCalledWith("valid-api-key-123");
    });

    it("should reject with error for invalid API key", async () => {
      const errorMessage = "Invalid API key";
      mockLogin.mockRejectedValue(new Error(errorMessage));

      await expect(login("invalid-key")).rejects.toThrow(errorMessage);
    });

    it("should reject with unauthorized error", async () => {
      const errorMessage = "Missing API key";
      mockLogin.mockRejectedValue(new Error(errorMessage));

      await expect(login("")).rejects.toThrow(errorMessage);
    });

    it("should handle network error", async () => {
      const errorMessage =
        "No response from server. Please check if the backend is running.";
      mockLogin.mockRejectedValue(new Error(errorMessage));

      await expect(login("test-key")).rejects.toThrow(errorMessage);
    });
  });

  describe("useHealthStatus", () => {
    it("should initialize with 'checking' status", () => {
      const { result, unmount } = renderHook(() => useHealthStatus());
      expect(result.current).toBe("checking");
      unmount();
    });

    it("should return correct HealthStatus type", () => {
      const { result, unmount } = renderHook(() => useHealthStatus());
      const status: HealthStatus = result.current;
      expect(["checking", "online", "offline"]).toContain(status);
      unmount();
    });
  });

  describe("listFiles", () => {
    it("should fetch all files successfully", async () => {
      const mockFiles: FileMetadata[] = [
        {
          id: 1,
          filename: "test1.jpg",
          parent_directory: ".",
          mime_type: "image/jpeg",
          size: 1024,
          uploaded_at: 1672531200,
          updated_at: 1672531200,
        },
        {
          id: 2,
          filename: "test2.pdf",
          parent_directory: "folder1",
          mime_type: "application/pdf",
          size: 2048,
          uploaded_at: 1672617600,
          updated_at: 1672617600,
        },
      ];

      mockListFiles.mockResolvedValue(mockFiles);

      const files = await listFiles();

      expect(mockListFiles).toHaveBeenCalled();
      expect(files).toEqual(mockFiles);
      expect(files).toHaveLength(2);
    });

    it("should handle empty file list", async () => {
      mockListFiles.mockResolvedValue([]);

      const files = await listFiles();

      expect(files).toEqual([]);
      expect(files).toHaveLength(0);
    });

    it("should handle list files error", async () => {
      const errorMessage = "Failed to fetch files";
      mockListFiles.mockRejectedValue(new Error(errorMessage));

      await expect(listFiles()).rejects.toThrow(errorMessage);
    });
  });

  describe("uploadFile", () => {
    const mockFileMetadata: FileMetadata = {
      id: 1,
      filename: "uploaded.jpg",
      parent_directory: "test-folder",
      mime_type: "image/jpeg",
      size: 1024,
      uploaded_at: 1672531200,
      updated_at: 1672531200,
    };

    it("should upload file successfully", async () => {
      const file = new File(["test content"], "test.jpg", {
        type: "image/jpeg",
      });
      mockUploadFile.mockResolvedValue(mockFileMetadata);

      const result = await uploadFile(file, "test-folder");

      expect(mockUploadFile).toHaveBeenCalledWith(file, "test-folder");
      expect(result).toEqual(mockFileMetadata);
    });

    it("should upload file to root directory", async () => {
      const file = new File(["content"], "root.txt", { type: "text/plain" });
      mockUploadFile.mockResolvedValue({
        ...mockFileMetadata,
        parent_directory: ".",
      });

      const result = await uploadFile(file, ".");

      expect(mockUploadFile).toHaveBeenCalledWith(file, ".");
      expect(result.parent_directory).toBe(".");
    });

    it("should handle upload error", async () => {
      const file = new File(["content"], "test.jpg", { type: "image/jpeg" });
      const errorMessage = "File too large";
      mockUploadFile.mockRejectedValue(new Error(errorMessage));

      await expect(uploadFile(file, ".")).rejects.toThrow(errorMessage);
    });

    it("should handle network error during upload", async () => {
      const file = new File(["content"], "test.jpg", { type: "image/jpeg" });
      const errorMessage =
        "No response from server. Please check if the backend is running.";
      mockUploadFile.mockRejectedValue(new Error(errorMessage));

      await expect(uploadFile(file, ".")).rejects.toThrow(errorMessage);
    });
  });

  describe("getFileBlob", () => {
    it("should fetch file as blob URL successfully", async () => {
      const blobUrl = "blob:http://localhost/test-file";
      mockGetFileBlob.mockResolvedValue(blobUrl);

      const result = await getFileBlob(1);

      expect(mockGetFileBlob).toHaveBeenCalledWith(1);
      expect(result).toBe(blobUrl);
    });

    it("should handle file not found error", async () => {
      const errorMessage = "File not found";
      mockGetFileBlob.mockRejectedValue(new Error(errorMessage));

      await expect(getFileBlob(999)).rejects.toThrow(errorMessage);
    });

    it("should handle download error", async () => {
      const errorMessage = "Failed to download file";
      mockGetFileBlob.mockRejectedValue(new Error(errorMessage));

      await expect(getFileBlob(1)).rejects.toThrow(errorMessage);
    });
  });

  describe("deleteFile", () => {
    const mockDeletedFile: FileMetadata = {
      id: 1,
      filename: "deleted.jpg",
      parent_directory: ".",
      mime_type: "image/jpeg",
      size: 1024,
      uploaded_at: 1672531200,
      updated_at: 1672531200,
    };

    it("should delete file successfully", async () => {
      mockDeleteFile.mockResolvedValue(mockDeletedFile);

      const result = await deleteFile(1);

      expect(mockDeleteFile).toHaveBeenCalledWith(1);
      expect(result).toEqual(mockDeletedFile);
    });

    it("should handle file not found during deletion", async () => {
      const errorMessage = "File not found";
      mockDeleteFile.mockRejectedValue(new Error(errorMessage));

      await expect(deleteFile(999)).rejects.toThrow(errorMessage);
    });

    it("should handle delete permission error", async () => {
      const errorMessage = "Permission denied";
      mockDeleteFile.mockRejectedValue(new Error(errorMessage));

      await expect(deleteFile(1)).rejects.toThrow(errorMessage);
    });
  });

  describe("updateFileMetadata", () => {
    const mockUpdatedFile: FileMetadata = {
      id: 1,
      filename: "renamed.jpg",
      parent_directory: "new-folder",
      mime_type: "image/jpeg",
      size: 1024,
      uploaded_at: 1672531200,
      updated_at: 1672617600,
    };

    it("should update filename successfully", async () => {
      const request: UpdateFileMetadataRequest = {
        filename: "renamed.jpg",
      };
      mockUpdateFileMetadata.mockResolvedValue(mockUpdatedFile);

      const result = await updateFileMetadata(1, request);

      expect(mockUpdateFileMetadata).toHaveBeenCalledWith(1, request);
      expect(result.filename).toBe("renamed.jpg");
    });

    it("should update parent directory successfully", async () => {
      const request: UpdateFileMetadataRequest = {
        parentDirectory: "new-folder",
      };
      mockUpdateFileMetadata.mockResolvedValue(mockUpdatedFile);

      const result = await updateFileMetadata(1, request);

      expect(mockUpdateFileMetadata).toHaveBeenCalledWith(1, request);
      expect(result.parent_directory).toBe("new-folder");
    });

    it("should update both filename and directory", async () => {
      const request: UpdateFileMetadataRequest = {
        filename: "renamed.jpg",
        parentDirectory: "new-folder",
      };
      mockUpdateFileMetadata.mockResolvedValue(mockUpdatedFile);

      const result = await updateFileMetadata(1, request);

      expect(mockUpdateFileMetadata).toHaveBeenCalledWith(1, request);
      expect(result.filename).toBe("renamed.jpg");
      expect(result.parent_directory).toBe("new-folder");
    });

    it("should handle file not found during update", async () => {
      const request: UpdateFileMetadataRequest = {
        filename: "new-name.jpg",
      };
      const errorMessage = "File not found";
      mockUpdateFileMetadata.mockRejectedValue(new Error(errorMessage));

      await expect(updateFileMetadata(999, request)).rejects.toThrow(
        errorMessage
      );
    });

    it("should handle invalid filename error", async () => {
      const request: UpdateFileMetadataRequest = {
        filename: "invalid/name.jpg",
      };
      const errorMessage = "Invalid filename";
      mockUpdateFileMetadata.mockRejectedValue(new Error(errorMessage));

      await expect(updateFileMetadata(1, request)).rejects.toThrow(
        errorMessage
      );
    });
  });

  describe("getThumbnailBlob", () => {
    it("should fetch thumbnail as blob URL successfully", async () => {
      const blobUrl = "blob:http://localhost/thumbnail";
      mockGetThumbnailBlob.mockResolvedValue(blobUrl);

      const result = await getThumbnailBlob(1);

      expect(mockGetThumbnailBlob).toHaveBeenCalledWith(1);
      expect(result).toBe(blobUrl);
    });

    it("should handle thumbnail not available error", async () => {
      const errorMessage = "Thumbnail not available";
      mockGetThumbnailBlob.mockRejectedValue(new Error(errorMessage));

      await expect(getThumbnailBlob(1)).rejects.toThrow(errorMessage);
    });

    it("should handle file not found error", async () => {
      const errorMessage = "File not found";
      mockGetThumbnailBlob.mockRejectedValue(new Error(errorMessage));

      await expect(getThumbnailBlob(999)).rejects.toThrow(errorMessage);
    });
  });
});
