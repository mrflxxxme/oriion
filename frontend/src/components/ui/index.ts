/**
 * UI primitive barrel — the 18 Wave-0 components from
 * .planning/ui/component-inventory.md. Features import from here so the
 * AC5 inventory-consumption audit can grep a single surface.
 */

// Layout
export { AppShell } from "./app-shell";
export type { AppShellProps } from "./app-shell";
export { Card } from "./card";
export type { CardProps } from "./card";
export { Separator } from "./separator";
export type { SeparatorProps } from "./separator";

// Inputs
export { Button, buttonVariants } from "./button";
export type { ButtonProps } from "./button";
export { Input } from "./input";
export type { InputProps } from "./input";
export { Textarea } from "./textarea";
export type { TextareaProps, TextareaChangeHandler } from "./textarea";
export { Select } from "./select";
export type { SelectProps, SelectOption } from "./select";
export { Checkbox } from "./checkbox";
export type { CheckboxProps } from "./checkbox";
export { RadioGroup } from "./radio-group";
export type { RadioGroupProps, RadioOption } from "./radio-group";

// Feedback
export { Toaster, toast } from "./toast";
export { Dialog } from "./dialog";
export type { DialogContentProps } from "./dialog";
export { EmptyState } from "./empty-state";
export type { EmptyStateProps, EmptyStateAction } from "./empty-state";
export { Skeleton } from "./skeleton";
export type { SkeletonProps } from "./skeleton";

// Data display
export { Table } from "./table";
export type { TableProps } from "./table";
export { Badge, badgeVariants } from "./badge";
export type { BadgeProps } from "./badge";
export { Avatar } from "./avatar";
export type { AvatarProps } from "./avatar";
export { Tabs } from "./tabs";

// Navigation
export { Breadcrumb } from "./breadcrumb";
export type { BreadcrumbProps, BreadcrumbItem } from "./breadcrumb";
export { Pagination } from "./pagination";
export type { PaginationProps } from "./pagination";
