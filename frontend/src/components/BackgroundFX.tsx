// Fixed backdrop: the pixel-art forest image (slow cinematic zoom) with a light
// veil, plus animated fireflies and campfire embers layered over the real art.
const FIREFLIES = [
  { left: "12%", top: "55%", delay: "0s" },
  { left: "22%", top: "70%", delay: "1.5s" },
  { left: "35%", top: "48%", delay: "3s" },
  { left: "60%", top: "62%", delay: "0.8s" },
  { left: "72%", top: "52%", delay: "2.2s" },
  { left: "84%", top: "68%", delay: "4s" },
  { left: "48%", top: "40%", delay: "5s" },
];

const EMBERS = [
  { left: "49%", delay: "0s" },
  { left: "51%", delay: "0.7s" },
  { left: "50%", delay: "1.4s" },
  { left: "52%", delay: "2.1s" },
  { left: "48.5%", delay: "2.8s" },
];

export default function BackgroundFX() {
  return (
    <div className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <div className="scene-img" />
      <div className="scene-veil" />

      {FIREFLIES.map((f, i) => (
        <span
          key={`fly-${i}`}
          className="fly firefly"
          style={{ left: f.left, top: f.top, animationDelay: f.delay }}
        />
      ))}
      {EMBERS.map((e, i) => (
        <span
          key={`spark-${i}`}
          className="spark ember"
          style={{ left: e.left, top: "72%", animationDelay: e.delay }}
        />
      ))}
    </div>
  );
}
