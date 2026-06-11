/**
 * Avatar — user/entity image with initials fallback (component-inventory.md #15).
 * Wraps @radix-ui/react-avatar (Root/Image/Fallback); optional presence status dot.
 */
import { forwardRef } from "react";
import type { ComponentPropsWithoutRef, ElementRef } from "react";
import * as AvatarPrimitive from "@radix-ui/react-avatar";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const avatarVariants = cva(
  "relative inline-flex shrink-0 items-center justify-center overflow-visible rounded-full bg-surface border border-default",
  {
    variants: {
      size: {
        xs: "size-6 text-xs",
        sm: "size-8 text-xs",
        md: "size-10 text-sm",
        lg: "size-12 text-base",
        xl: "size-16 text-lg",
      },
    },
    defaultVariants: { size: "md" },
  },
);

const statusConfig = {
  online: { className: "bg-success-500", label: "В сети" },
  offline: { className: "bg-default", label: "Не в сети" },
  away: { className: "bg-warning-500", label: "Отошёл" },
  busy: { className: "bg-danger-600", label: "Занят" },
} as const;

const statusDotSize = {
  xs: "size-1.5",
  sm: "size-2",
  md: "size-2.5",
  lg: "size-3",
  xl: "size-3.5",
} as const;

type AvatarSize = NonNullable<VariantProps<typeof avatarVariants>["size"]>;
type AvatarStatus = keyof typeof statusConfig;

export interface AvatarProps
  extends Omit<ComponentPropsWithoutRef<typeof AvatarPrimitive.Root>, "children"> {
  src?: string;
  /** 1–2 initials shown while/if the image is unavailable. */
  fallback: string;
  size?: AvatarSize;
  status?: AvatarStatus;
  alt?: string;
}

export const Avatar = forwardRef<
  ElementRef<typeof AvatarPrimitive.Root>,
  AvatarProps
>(function Avatar(
  { className, src, fallback, size = "md", status, alt, ...props },
  ref,
) {
  return (
    <AvatarPrimitive.Root
      ref={ref}
      className={cn(avatarVariants({ size }), className)}
      {...props}
    >
      {src ? (
        <AvatarPrimitive.Image
          src={src}
          alt={alt ?? fallback}
          className="size-full rounded-full object-cover"
        />
      ) : null}
      <AvatarPrimitive.Fallback
        className="flex size-full items-center justify-center rounded-full font-medium text-secondary"
        // Omit delayMs when there is no image so the fallback renders immediately
        // (a delay would briefly leave an empty avatar). With a src, defer briefly
        // to avoid a flash of initials while the image loads.
        {...(src ? { delayMs: 200 } : {})}
      >
        {fallback}
      </AvatarPrimitive.Fallback>
      {status ? (
        <span
          role="status"
          aria-label={statusConfig[status].label}
          className={cn(
            "absolute right-0 bottom-0 block rounded-full border-2 border-page",
            statusConfig[status].className,
            statusDotSize[size],
          )}
        />
      ) : null}
    </AvatarPrimitive.Root>
  );
});
