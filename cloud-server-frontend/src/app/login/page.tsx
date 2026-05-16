"use client";

import { useState } from "react";

import { useAuth } from "@/contexts/AuthContext";

export default function LoginPage() {
  const [apiKey, setApiKey] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { login } = useAuth();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!apiKey.trim()) {
      setError("Please enter an API key");
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      await login(apiKey);
      // Redirect is handled by AuthContext
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Login failed. Please check your API key."
      );
      setIsLoading(false);
    }
  };

  return (
    <div className="-my-8 flex min-h-[calc(100vh-12rem)] items-center justify-center bg-background">
      <div className="w-full max-w-md space-y-6 p-8">
        {/* Header */}
        <div className="space-y-2 text-center">
          <h1 className="text-4xl font-bold text-text-primary">Cloud Server</h1>
          <p className="text-text-muted">A FastAPI-based local cloud server.</p>
        </div>

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <label
              htmlFor="apiKey"
              className="block text-sm font-medium text-text-primary"
            >
              API Key
            </label>
            <input
              id="apiKey"
              type="password"
              value={apiKey}
              onChange={e => setApiKey(e.target.value)}
              placeholder="Enter your API key"
              disabled={isLoading}
              className="w-full rounded-lg border border-terminal-border bg-terminal-bg px-4 py-3 text-text-primary placeholder-text-muted focus:outline-none focus:ring-2 focus:ring-neon-green disabled:opacity-50"
              autoComplete="off"
            />
          </div>

          {/* Error Display */}
          {error && (
            <div className="rounded-lg border border-neon-red bg-terminal-bg p-3">
              <p className="text-sm text-neon-red">❌ {error}</p>
            </div>
          )}

          {/* Submit Button */}
          <button
            type="submit"
            disabled={isLoading}
            className="w-full rounded-lg bg-neon-green px-4 py-3 font-medium text-background transition-all hover:opacity-80 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {isLoading ? "Authenticating..." : "Login"}
          </button>
        </form>

        {/* Help Text */}
        <div className="space-y-2 text-center">
          <p className="text-xs text-text-muted">
            Your API key is stored locally and used to authenticate with the
            backend server.
          </p>
        </div>
      </div>
    </div>
  );
}
