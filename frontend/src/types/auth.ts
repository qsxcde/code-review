export interface AuthUser {
  id: number;
  email: string;
  created_at: string;
}

export interface AuthSession {
  user: AuthUser;
  access_token: string;
  refresh_token: string;
  token_type: string;
}
