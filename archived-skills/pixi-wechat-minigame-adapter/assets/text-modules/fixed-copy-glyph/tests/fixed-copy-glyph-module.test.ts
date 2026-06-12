import { readFile } from 'node:fs/promises';
import { join } from 'node:path';

import { describe, expect, test } from 'vitest';

describe('fixed-copy-glyph module scaffold', () => {
  test('ships a JSON string inventory', async () => {
    const strings = JSON.parse(
      await readFile(join(process.cwd(), 'src', 'ui', 'fixedCopyGlyph', 'strings.json'), 'utf8'),
    ) as unknown;

    expect(Array.isArray(strings)).toBe(true);
  });
});
