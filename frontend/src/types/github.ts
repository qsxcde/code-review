export interface GitHubPRFile {
  filename: string;
  status: string;
  additions: number;
  deletions: number;
  changes: number;
  patch: string | null;
}

export interface GitHubPRResponse {
  owner: string;
  repo: string;
  number: number;
  title: string;
  body: string | null;
  state: string;
  author: string;
  html_url: string;
  base_branch: string;
  head_branch: string;
  head_sha: string;
  changed_files: number;
  additions: number;
  deletions: number;
  files: GitHubPRFile[];
}
