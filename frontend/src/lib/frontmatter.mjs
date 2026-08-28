function decodeScalar(raw) {
  const value = raw.trim();
  if (value.length >= 2 && value.startsWith('"') && value.endsWith('"')) {
    try {
      return JSON.parse(value);
    } catch (error) {
      throw new Error(`Invalid double-quoted frontmatter value: ${value}`, { cause: error });
    }
  }
  if (value.length >= 2 && value.startsWith("'") && value.endsWith("'")) {
    return value.slice(1, -1).replaceAll("''", "'");
  }
  return value;
}

/**
 * Parse the deliberately small frontmatter contract used by content/blog/*.mdx.
 *
 * The blog metadata model is flat string scalars only. Keeping that contract
 * explicit avoids shipping a general YAML parser in the production frontend.
 * Nested YAML, arrays, block scalars, and duplicate keys are rejected instead
 * of being guessed at silently.
 *
 * @param {string} source
 * @returns {{ data: Record<string, string>, content: string }}
 */
export function parseFrontmatter(source) {
  const match = source.match(/^---\r?\n([\s\S]*?)\r?\n---(?:\r?\n)?/);
  if (!match) {
    return { data: {}, content: source };
  }

  const data = {};
  const lines = match[1].split(/\r?\n/);
  for (const [index, line] of lines.entries()) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;

    const separator = line.indexOf(":");
    if (separator <= 0) {
      throw new Error(`Invalid frontmatter line ${index + 1}: ${line}`);
    }

    const key = line.slice(0, separator).trim();
    if (!/^[A-Za-z0-9_-]+$/.test(key)) {
      throw new Error(`Invalid frontmatter key on line ${index + 1}: ${key}`);
    }
    if (Object.hasOwn(data, key)) {
      throw new Error(`Duplicate frontmatter key: ${key}`);
    }

    data[key] = decodeScalar(line.slice(separator + 1));
  }

  return {
    data,
    content: source.slice(match[0].length),
  };
}
