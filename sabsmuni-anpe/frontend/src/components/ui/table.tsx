import * as React from 'react';
import { cn } from '@/lib/utils';

export const Table = ({ className, ...p }: React.TableHTMLAttributes<HTMLTableElement>) => <div className="w-full overflow-x-auto rounded-md border"><table className={cn('w-full caption-bottom text-sm', className)} {...p} /></div>;
export const THead = (p: React.HTMLAttributes<HTMLTableSectionElement>) => <thead className="bg-muted/60 text-left text-xs uppercase tracking-wide text-muted-foreground" {...p} />;
export const TR = ({ className, ...p }: React.HTMLAttributes<HTMLTableRowElement>) => <tr className={cn('border-b last:border-0 hover:bg-muted/30', className)} {...p} />;
export const TH = ({ className, ...p }: React.ThHTMLAttributes<HTMLTableCellElement>) => <th className={cn('px-3 py-2 font-medium', className)} {...p} />;
export const TD = ({ className, ...p }: React.TdHTMLAttributes<HTMLTableCellElement>) => <td className={cn('px-3 py-2 align-top', className)} {...p} />;
