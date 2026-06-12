# Fixed-Copy Glyph Module

This optional module is a scaffold for packaged, deterministic UI copy.

Use it when:
1. mini-game text must be deterministic
2. runtime canvas text generation is too risky
3. a small set of known UI strings needs atlas coverage

After installing the module:
1. edit `src/ui/fixedCopyGlyph/strings.json`
2. run `npm run build:copy-glyph-atlas` or `make copy-glyph-atlas`
3. wire the generated manifest into your own text rendering flow

The scaffold does not force a text pipeline into your scenes. It only gives you a standard place to keep the fixed-copy inventory and generation step.
