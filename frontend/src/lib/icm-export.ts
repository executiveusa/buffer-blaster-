import { createHash } from "node:crypto";
import type { CreatorCard } from "@/lib/creator-demo";

const FIXED_DOS_TIME = 0;
const FIXED_DOS_DATE = 33; // 1980-01-01

function crc32(input: Buffer): number {
  let crc = 0xffffffff;
  for (const byte of input) {
    crc ^= byte;
    for (let bit = 0; bit < 8; bit += 1) {
      crc = (crc >>> 1) ^ (0xedb88320 & -(crc & 1));
    }
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function safeSlug(value: string): string {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "card";
}

function buildStoredZip(files: Array<{ name: string; content: Buffer }>): Buffer {
  const localParts: Buffer[] = [];
  const centralParts: Buffer[] = [];
  let offset = 0;

  for (const file of [...files].sort((a, b) => a.name.localeCompare(b.name))) {
    const name = Buffer.from(file.name, "utf8");
    const checksum = crc32(file.content);
    const local = Buffer.alloc(30);
    local.writeUInt32LE(0x04034b50, 0);
    local.writeUInt16LE(20, 4);
    local.writeUInt16LE(0, 6);
    local.writeUInt16LE(0, 8);
    local.writeUInt16LE(FIXED_DOS_TIME, 10);
    local.writeUInt16LE(FIXED_DOS_DATE, 12);
    local.writeUInt32LE(checksum, 14);
    local.writeUInt32LE(file.content.length, 18);
    local.writeUInt32LE(file.content.length, 22);
    local.writeUInt16LE(name.length, 26);
    local.writeUInt16LE(0, 28);
    localParts.push(local, name, file.content);

    const central = Buffer.alloc(46);
    central.writeUInt32LE(0x02014b50, 0);
    central.writeUInt16LE(20, 4);
    central.writeUInt16LE(20, 6);
    central.writeUInt16LE(0, 8);
    central.writeUInt16LE(0, 10);
    central.writeUInt16LE(FIXED_DOS_TIME, 12);
    central.writeUInt16LE(FIXED_DOS_DATE, 14);
    central.writeUInt32LE(checksum, 16);
    central.writeUInt32LE(file.content.length, 20);
    central.writeUInt32LE(file.content.length, 24);
    central.writeUInt16LE(name.length, 28);
    central.writeUInt16LE(0, 30);
    central.writeUInt16LE(0, 32);
    central.writeUInt16LE(0, 34);
    central.writeUInt16LE(0, 36);
    central.writeUInt32LE(0, 38);
    central.writeUInt32LE(offset, 42);
    centralParts.push(central, name);
    offset += local.length + name.length + file.content.length;
  }

  const centralDirectory = Buffer.concat(centralParts);
  const end = Buffer.alloc(22);
  end.writeUInt32LE(0x06054b50, 0);
  end.writeUInt16LE(0, 4);
  end.writeUInt16LE(0, 6);
  end.writeUInt16LE(files.length, 8);
  end.writeUInt16LE(files.length, 10);
  end.writeUInt32LE(centralDirectory.length, 12);
  end.writeUInt32LE(offset, 16);
  end.writeUInt16LE(0, 20);
  return Buffer.concat([...localParts, centralDirectory, end]);
}

export function buildSingleCardAgentPack(card: CreatorCard): { filename: string; bytes: Buffer; sha256: string } {
  if (!card.source.license_verified) throw new Error("Card license is not verified.");

  const category = safeSlug(card.category);
  const slug = safeSlug(card.slug || card.title);
  const promptHash = createHash("sha256").update(card.prompt.trim(), "utf8").digest("hex");
  const cardPath = `cards/${category}/${slug}`;
  const cardJson = {
    ...card,
    source: { ...card.source, content_hash: card.source.content_hash ?? promptHash },
    prompt_content_hash: promptHash,
    icm_path: cardPath,
  };
  const context = `# ${card.title}\n\n## Job\n${card.description}\n\n## Required inputs\n${card.required_inputs.map((item) => `- ${item}`).join("\n")}\n\n## Prompt\n${card.prompt}\n\n## Provenance\n- Source: ${card.source.attribution}\n- License: ${card.source.license}\n- Verified: yes\n- Source SHA-256: ${cardJson.source.content_hash}\n- Prompt SHA-256: ${promptHash}\n`;
  const manifest = {
    schema_version: 1,
    pack_type: "single-card",
    cards: [{ id: card.id, title: card.title, category: card.category, icm_path: cardPath, source: cardJson.source, prompt_content_hash: promptHash }],
  };
  const files = [
    { name: "AGENTS.md", content: Buffer.from("# Buffer Blaster Agent Pack\n\nRead CONTEXT.md first. Load only the selected card context. Keep generated work in output/. Human review is required before publishing.\n") },
    { name: "CONTEXT.md", content: Buffer.from(`# Context Router\n\nThis pack contains one selected recipe: ${card.title}. Read ${cardPath}/CONTEXT.md and ${cardPath}/card.json. Do not load unrelated libraries into context.\n`) },
    { name: "README.md", content: Buffer.from("# Buffer Blaster Portable Agent Pack\n\nA portable ICM package for one selected creator recipe.\n") },
    { name: "manifest.json", content: Buffer.from(`${JSON.stringify(manifest, null, 2)}\n`) },
    { name: `${cardPath}/card.json`, content: Buffer.from(`${JSON.stringify(cardJson, null, 2)}\n`) },
    { name: `${cardPath}/CONTEXT.md`, content: Buffer.from(context) },
    { name: "output/.gitkeep", content: Buffer.alloc(0) },
  ];
  const bytes = buildStoredZip(files);
  return {
    filename: `buffer-blaster-${slug}-agent-pack.zip`,
    bytes,
    sha256: createHash("sha256").update(bytes).digest("hex"),
  };
}
