export function BrandMark({ className = "h-11 w-11" }: { className?: string }) {
  return (
    <span className={`flex ${className} shrink-0 items-center justify-center rounded-xl bg-brand text-white`}>
      <svg viewBox="0 0 24 24" className="h-1/2 w-1/2 fill-none stroke-current" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M3 12h4l3-8 4 16 3-8h4" />
      </svg>
    </span>
  );
}
