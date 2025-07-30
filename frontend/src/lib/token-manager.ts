interface TokenRefreshCache {
  promise: Promise<string | null> | null;
  timestamp: number;
  lastRefreshedToken: string | null;
}

class TokenManager {
  private static instance: TokenManager;
  private refreshCache: TokenRefreshCache = {
    promise: null,
    timestamp: 0,
    lastRefreshedToken: null,
  };

  // Cache duration: 30 seconds (to prevent rapid successive refresh attempts)
  private readonly CACHE_DURATION = 30 * 1000;
  // Token expiry buffer: 5 minutes
  private readonly EXPIRY_BUFFER = 5 * 60 * 1000;

  private constructor() {}

  public static getInstance(): TokenManager {
    if (!TokenManager.instance) {
      TokenManager.instance = new TokenManager();
    }
    return TokenManager.instance;
  }

  /**
   * Check if a token is expired or about to expire
   */
  public isTokenExpired(token: string): boolean {
    try {
      const tokenData = JSON.parse(atob(token.split(".")[1]));
      const expiresAt = tokenData.exp * 1000;
      const now = Date.now();

      return tokenData.exp && now >= expiresAt - this.EXPIRY_BUFFER;
    } catch (error) {
      console.error("Error checking token expiration:", error);
      return true; // Assume expired if we can't parse it
    }
  }

  /**
   * Refresh access token with caching to prevent multiple simultaneous requests
   */
  public async refreshAccessToken(
    refreshToken: string | undefined
  ): Promise<string | null> {
    if (!refreshToken) {
      console.error("No refresh token provided");
      return null;
    }

    // Check if there's already a refresh in progress
    const now = Date.now();
    if (
      this.refreshCache.promise &&
      now - this.refreshCache.timestamp < this.CACHE_DURATION
    ) {
      console.log(
        "Token refresh already in progress, waiting for existing request..."
      );
      return await this.refreshCache.promise;
    }

    // Create new refresh promise
    const refreshPromise = this.performTokenRefresh(refreshToken);

    // Store the promise in cache
    this.refreshCache.promise = refreshPromise;
    this.refreshCache.timestamp = now;

    const result = await refreshPromise;

    // Store the last refreshed token for comparison
    if (result) {
      this.refreshCache.lastRefreshedToken = result;
    }

    return result;
  }

  /**
   * Perform the actual token refresh API call
   */
  private async performTokenRefresh(
    refreshToken: string
  ): Promise<string | null> {
    try {
      console.log("Starting token refresh...");
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_URL}/auth/refresh`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            refresh_token: refreshToken,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || "Failed to refresh token");
      }

      console.log("✅ Token refresh successful");
      return data.access_token;
    } catch (error) {
      console.error("❌ Token refresh failed:", error);
      return null;
    } finally {
      // Clear the cache after completion (success or failure)
      this.refreshCache.promise = null;
      this.refreshCache.timestamp = 0;
    }
  }

  /**
   * Get a valid access token, refreshing if necessary
   */
  public async getValidAccessToken(
    currentToken: string,
    refreshToken: string | undefined
  ): Promise<string | null> {
    if (!currentToken) {
      return null;
    }

    // If token is not expired, return it as is
    if (!this.isTokenExpired(currentToken)) {
      return currentToken;
    }

    // Token is expired, refresh it if we have a refresh token
    if (!refreshToken) {
      console.error("Token expired but no refresh token available");
      return null;
    }

    console.log("Token expired or expiring soon, attempting refresh");
    return await this.refreshAccessToken(refreshToken);
  }

  /**
   * Clear the refresh cache (useful for testing or manual cache invalidation)
   */
  public clearCache(): void {
    this.refreshCache = {
      promise: null,
      timestamp: 0,
      lastRefreshedToken: null,
    };
  }
}

export const tokenManager = TokenManager.getInstance();
