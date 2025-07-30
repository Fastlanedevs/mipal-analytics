import "next-auth";

declare module "next-auth" {
  interface Session {
    accessToken?: string;
    user: {
      id: string;
      email: string;
      name: string;
    };
  }

  interface Token {
    accessToken?: string;
  }
}

export interface Tokens {
  access_token?: string;
  refresh_token?: string;
}

export interface AuthContextType {
  isAuthenticated: boolean;
  isLoading: boolean;
}
