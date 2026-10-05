import { cva, type VariantProps } from 'class-variance-authority';
import * as React from 'react';
import { cn } from '@/lib/utils';

const v = cva('inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-semibold', {
  variants: { variant: { default: 'border-transparent bg-primary text-primary-foreground', secondary: 'border-transparent bg-secondary text-secondary-foreground', success: 'border-transparent bg-success/15 text-success', warning: 'border-transparent bg-warning/25 text-warning-foreground', destructive: 'border-transparent bg-destructive/15 text-destructive', outline: 'text-foreground' } },
  defaultVariants: { variant: 'default' },
});
export const Badge = ({ className, variant, ...p }: React.HTMLAttributes<HTMLSpanElement> & VariantProps<typeof v>) => <span className={cn(v({ variant }), className)} {...p} />;
