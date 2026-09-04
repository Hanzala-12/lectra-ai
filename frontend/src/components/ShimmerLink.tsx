import type { CSSProperties, ReactNode } from 'react';
import { Link, type LinkProps } from 'react-router-dom';
import { cn } from '../lib/utils';

/**
 * Navigation counterpart to MagicUI's ShimmerButton (src/components/ui/
 * shimmer-button.tsx). That component renders a <button>, which is wrong
 * for a route change — this renders a real <Link> so primary CTAs keep
 * anchor semantics (middle-click, "open in new tab", crawlability) while
 * getting the same shimmer treatment. Same CSS custom properties, same
 * `animate-shimmer-slide` / `animate-spin-around` keyframes already
 * registered in index.css by the shadcn pull — just a different root
 * element. Defaults are brand colors + this project's `rounded-lg` corner
 * radius instead of MagicUI's stock pill shape, so it matches every other
 * button on the site rather than standing out as an unstyled import.
 */
interface ShimmerLinkProps extends LinkProps {
  shimmerColor?: string;
  background?: string;
  borderRadius?: string;
  shimmerDuration?: string;
  className?: string;
  children?: ReactNode;
}

export function ShimmerLink({
  shimmerColor = '#ffffff',
  background = 'var(--color-primary)',
  borderRadius = '0.5rem',
  shimmerDuration = '2.5s',
  className,
  children,
  ...props
}: ShimmerLinkProps) {
  return (
    <Link
      {...props}
      style={
        {
          '--spread': '90deg',
          '--shimmer-color': shimmerColor,
          '--radius': borderRadius,
          '--speed': shimmerDuration,
          '--cut': '0.05em',
          '--bg': background,
        } as CSSProperties
      }
      className={cn(
        'group relative z-0 flex items-center justify-center gap-2 overflow-hidden [border-radius:var(--radius)] px-7 py-3.5 font-semibold text-white whitespace-nowrap [background:var(--bg)]',
        'transform-gpu transition-transform duration-300 ease-in-out hover:brightness-110 active:translate-y-px',
        className
      )}
    >
      <div className="-z-30 blur-[2px] @container-[size] absolute inset-0 overflow-visible">
        <div className="animate-shimmer-slide absolute inset-0 aspect-square h-[100cqh] rounded-none [mask:none]">
          <div className="animate-spin-around absolute -inset-full w-auto rotate-0 [translate:0_0] [background:conic-gradient(from_calc(270deg-(var(--spread)*0.5)),transparent_0,var(--shimmer-color)_var(--spread),transparent_var(--spread))]" />
        </div>
      </div>

      {children}

      <div
        className={cn(
          'absolute inset-0 size-full [border-radius:var(--radius)]',
          'shadow-[inset_0_-8px_10px_#ffffff1f]',
          'transform-gpu transition-all duration-300 ease-in-out',
          'group-hover:shadow-[inset_0_-6px_10px_#ffffff3f]',
          'group-active:shadow-[inset_0_-10px_10px_#ffffff3f]'
        )}
      />

      <div className="absolute inset-(--cut) -z-20 [border-radius:var(--radius)] [background:var(--bg)]" />
    </Link>
  );
}
