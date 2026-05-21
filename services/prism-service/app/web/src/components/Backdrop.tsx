/**
 * Static CSS backdrop — Hermes-style warm-glow vignette + noise.
 *
 * Lightweight stand-in for Hermes's r3f shader: a radial cream-glow center
 * over the dark teal canvas, plus an SVG turbulence noise overlay. Renders
 * absolutely-positioned behind everything via pointer-events:none.
 */
export default function Backdrop() {
  return (
    <>
      <div
        aria-hidden
        className="pointer-events-none fixed inset-0 -z-10"
        style={{
          background:
            "radial-gradient(60% 50% at 50% 35%, var(--warm-glow) 0%, transparent 70%)",
          mixBlendMode: "screen",
          opacity: 0.6,
        }}
      />
      <div
        aria-hidden
        className="pointer-events-none fixed inset-0 -z-10"
        style={{
          backgroundImage:
            "url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='220' height='220'><filter id='n'><feTurbulence baseFrequency='0.9' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 1  0 0 0 0 0.95  0 0 0 0 0.85  0 0 0 0.18 0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>\")",
          opacity: "calc(0.25 * var(--noise-opacity-mul, 1))",
        }}
      />
    </>
  );
}
