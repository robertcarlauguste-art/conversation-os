export function WaveformMark({ className = "" }: { className?: string }) {
  const bars = [5, 11, 16, 9, 14, 6, 12];
  return (
    <svg
      viewBox="0 0 60 20"
      className={className}
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
    >
      {bars.map((height, i) => (
        <rect
          key={i}
          x={i * 8.5}
          y={(20 - height) / 2}
          width="3.5"
          height={height}
          rx="1.75"
          fill="currentColor"
        />
      ))}
    </svg>
  );
}
