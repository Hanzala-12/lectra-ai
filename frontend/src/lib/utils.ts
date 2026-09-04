import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

/**
 * Standard shadcn/MagicUI class-merging helper — combines conditional class
 * names (clsx) and resolves conflicting Tailwind utilities so the last one
 * wins instead of both landing in the DOM (tailwind-merge). Every MagicUI /
 * shadcn component pulled into this project imports this from '@/lib/utils'
 * by convention — keep it at this exact path.
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
