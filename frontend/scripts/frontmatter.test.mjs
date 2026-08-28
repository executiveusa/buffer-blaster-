import test from "node:test";
import assert from "node:assert/strict";

import { parseFrontmatter } from "../src/lib/frontmatter.mjs";

test("parses the flat string metadata used by Social Studio blog posts", () => {
  const source = `---\ntitle: "A title: with punctuation"\ndate: "2026-08-28"\nauthor: "Stavarai"\ncategory: "social-strategy"\nexcerpt: "A short description"\n---\n\n# Body\n\nHello.`;
  const parsed = parseFrontmatter(source);

  assert.deepEqual(parsed.data, {
    title: "A title: with punctuation",
    date: "2026-08-28",
    author: "Stavarai",
    category: "social-strategy",
    excerpt: "A short description",
  });
  assert.equal(parsed.content, "\n# Body\n\nHello.");
});

test("supports single-quoted and bare scalar values", () => {
  const source = `---\ntitle: 'Single quoted'\ncategory: tools\n---\nBody`;
  const parsed = parseFrontmatter(source);
  assert.equal(parsed.data.title, "Single quoted");
  assert.equal(parsed.data.category, "tools");
  assert.equal(parsed.content, "Body");
});

test("returns empty metadata when a document has no frontmatter", () => {
  assert.deepEqual(parseFrontmatter("# Plain body"), {
    data: {},
    content: "# Plain body",
  });
});

test("rejects malformed frontmatter rather than silently inventing metadata", () => {
  assert.throws(
    () => parseFrontmatter("---\ntitle without colon\n---\nBody"),
    /Invalid frontmatter line/,
  );
});
