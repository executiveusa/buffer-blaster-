export interface ParsedFrontmatter {
  data: Record<string, string>;
  content: string;
}

export function parseFrontmatter(source: string): ParsedFrontmatter;
