import axios from "axios";
import { useEffect, useState } from "react";

import { getApiKey } from "@/lib/auth";
import type {
  DeleteFileResponse,
  FileMetadata,
  HealthResponse,
  ListFilesResponse,
  LoginResponse,
  UpdateFileMetadataRequest,
  UpdateFileMetadataResponse,
  UploadFileResponse,
} from "@/lib/types";

// Determine the base URL based on environment
const getBaseURL = () => {
  if (typeof window === "undefined") return "";

  // In production static build, API is served from same origin
  if (process.env.NODE_ENV === "production") {
    return window.location.origin;
  }

  // In development, proxy to backend (handled by Next.js rewrites)
  return "";
};

// API client configuration
const api = axios.create({
  baseURL: getBaseURL() + "/api", // This will be proxied in dev, direct in production
  timeout: 60000, // 60 seconds timeout for LLM responses
  headers: {
    "Content-Type": "application/json",
  },
});

// Add request interceptor to include API key
api.interceptors.request.use(
  config => {
    const apiKey = getApiKey();
    if (apiKey) {
      config.headers["X-API-KEY"] = apiKey;
    }
    return config;
  },
  error => {
    return Promise.reject(error);
  }
);

// Health status type
export type HealthStatus = "online" | "offline" | "checking";

const extractErrorMessage = (error: unknown): string => {
  if (axios.isAxiosError(error)) {
    if (error.response) {
      const errorData = error.response.data;

      // Check for BaseResponse format with message field
      if (errorData?.message) {
        return errorData.message;
      }

      // Check for detail field (common in FastAPI errors)
      if (errorData?.detail) {
        return typeof errorData.detail === "string"
          ? errorData.detail
          : JSON.stringify(errorData.detail);
      }

      // Fallback to generic server error
      return `Server error: ${error.response.status} ${error.response.statusText}`;
    } else if (error.request) {
      return "No response from server. Please check if the backend is running.";
    } else {
      return `Request failed: ${error.message}`;
    }
  }
  return "An unexpected error occurred";
};

// API functions
export const getHealth = async (): Promise<HealthResponse> => {
  try {
    const response = await api.get<HealthResponse>("/health");
    return response.data;
  } catch (error) {
    throw new Error(extractErrorMessage(error));
  }
};

export const login = async (apiKey: string): Promise<LoginResponse> => {
  try {
    const response = await api.get<LoginResponse>("/login", {
      headers: {
        "X-API-KEY": apiKey,
      },
    });
    return response.data;
  } catch (error) {
    throw new Error(extractErrorMessage(error));
  }
};

// ---------------------------------------------------------------------------
// Files API (mirrors FilesRouter endpoints in cloud_server/routers/files_router.py)
// ---------------------------------------------------------------------------

// GET /files/ — list all files
export const listFiles = async (): Promise<FileMetadata[]> => {
  try {
    const response = await api.get<ListFilesResponse>("/files/");
    return response.data.filesMetadata;
  } catch (error) {
    throw new Error(extractErrorMessage(error));
  }
};

// POST /files/ — upload a file
export const uploadFile = async (
  file: File,
  parentDirectory: string
): Promise<FileMetadata> => {
  try {
    const formData = new FormData();
    formData.append("file", file);
    const response = await api.post<UploadFileResponse>("/files/", formData, {
      params: { parent_directory: parentDirectory },
      headers: { "Content-Type": "multipart/form-data" },
    });
    return response.data.fileMetadata;
  } catch (error) {
    throw new Error(extractErrorMessage(error));
  }
};

// GET /files/{file_id} — fetch file as a blob URL (caller must revoke when done)
export const getFileBlob = async (fileId: number): Promise<string> => {
  try {
    const response = await api.get(`/files/${fileId}`, {
      responseType: "blob",
    });
    return URL.createObjectURL(response.data as Blob);
  } catch (error) {
    throw new Error(extractErrorMessage(error));
  }
};

// DELETE /files/{file_id} — delete a file
export const deleteFile = async (fileId: number): Promise<FileMetadata> => {
  try {
    const response = await api.delete<DeleteFileResponse>(`/files/${fileId}`);
    return response.data.fileMetadata;
  } catch (error) {
    throw new Error(extractErrorMessage(error));
  }
};

// PATCH /files/{file_id}/metadata — rename or move a file
export const updateFileMetadata = async (
  fileId: number,
  request: UpdateFileMetadataRequest
): Promise<FileMetadata> => {
  try {
    const response = await api.patch<UpdateFileMetadataResponse>(
      `/files/${fileId}/metadata`,
      request
    );
    return response.data.fileMetadata;
  } catch (error) {
    throw new Error(extractErrorMessage(error));
  }
};

// GET /files/{file_id}/thumbnail — fetch thumbnail as a blob URL (caller must revoke when done)
export const getThumbnailBlob = async (fileId: number): Promise<string> => {
  try {
    const response = await api.get(`/files/${fileId}/thumbnail`, {
      responseType: "blob",
    });
    return URL.createObjectURL(response.data as Blob);
  } catch (error) {
    throw new Error(extractErrorMessage(error));
  }
};

// Health status hook
export function useHealthStatus(): HealthStatus {
  const [status, setStatus] = useState<HealthStatus>("checking");

  useEffect(() => {
    let isMounted = true;

    const checkHealth = async () => {
      try {
        await getHealth();
        if (isMounted) {
          setStatus("online");
        }
      } catch {
        if (isMounted) {
          setStatus("offline");
        }
      }
    };

    checkHealth();
    const interval = setInterval(checkHealth, 30000); // every 30s
    return () => {
      isMounted = false;
      clearInterval(interval);
    };
  }, []);

  return status;
}

export default api;
