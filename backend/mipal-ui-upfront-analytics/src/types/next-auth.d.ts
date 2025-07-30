// next-auth.d.ts
import "next-auth";
import { DefaultSession, DefaultUser } from "next-auth";

// Define a custom interface for the account data from backend
interface BackendAuthData {
  access_token: string;
  refresh_token: string;
  user_id: string;
  role: string;
  joined_org: boolean;
}

// Extend the user properties
interface IUser extends DefaultUser {
  id: string;
  name: string;
  email: string;
  role?: string;
  joined_org?: boolean;
  image?: string;
  access_token?: string;
  refresh_token?: string;
}

declare module "next-auth" {
  interface Session {
    access_token?: string;
    accessToken?: string;
    refresh_token?: string;
    refreshToken?: string;
    user: {
      id: string;
      name: string;
      email: string;
      role?: string;
      joined_org?: boolean;
      access_token?: string;
      refresh_token?: string;
      image?: string;
    } & DefaultSession["user"];
  }

  // Extend User to include our custom fields
  interface User extends IUser {}
}

declare module "next-auth/jwt" {
  interface JWT {
    access_token?: string;
    accessToken?: string;
    refresh_token?: string;
    refreshToken?: string;
    role?: string;
    joined_org?: boolean;
    user?: {
      id: string;
      name: string;
      email: string;
      role?: string;
      joined_org?: boolean;
      access_token?: string;
      refresh_token?: string;
      image?: string;
    };
  }
}

export { BackendAuthData };
