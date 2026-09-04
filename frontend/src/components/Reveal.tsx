import type { ReactNode } from 'react';
import { motion, type Variants } from 'motion/react';

/**
 * Shared scroll-entrance motion primitives for the marketing site. Two
 * pieces:
 *  - <Reveal> — a single block that fades/slides in once it scrolls into
 *    view. Use for standalone elements (section headings, standalone cards).
 *  - <StaggerGroup>/<StaggerItem> — a parent/children pair that reveals a
 *    grid or list one item after another instead of all at once. Wrap a
 *    grid in <StaggerGroup>, each cell in <StaggerItem>.
 *
 * Both trigger once (viewport.once) so content doesn't re-animate every
 * time the user scrolls back up past a section — this is a first-impression
 * flourish, not a decoration that should repeat on every pass.
 */

const EASE_OUT: [number, number, number, number] = [0.21, 0.47, 0.32, 0.98];

interface RevealProps {
  children: ReactNode;
  className?: string;
  /** Stagger offset in seconds when used standalone (not inside a group). */
  delay?: number;
  /** Starting vertical offset in px. */
  y?: number;
}

export function Reveal({ children, className, delay = 0, y = 18 }: RevealProps) {
  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: '-80px' }}
      transition={{ duration: 0.6, delay, ease: EASE_OUT }}
    >
      {children}
    </motion.div>
  );
}

const groupVariants: Variants = {
  hidden: {},
  show: {
    transition: { staggerChildren: 0.09, delayChildren: 0.04 },
  },
};

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 18 },
  show: { opacity: 1, y: 0, transition: { duration: 0.55, ease: EASE_OUT } },
};

export function StaggerGroup({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <motion.div
      className={className}
      initial="hidden"
      whileInView="show"
      viewport={{ once: true, margin: '-80px' }}
      variants={groupVariants}
    >
      {children}
    </motion.div>
  );
}

export function StaggerItem({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <motion.div className={className} variants={itemVariants}>
      {children}
    </motion.div>
  );
}
