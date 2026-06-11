/**
 * Dialog — blocking modal (component-inventory.md #10).
 * Wraps `@radix-ui/react-dialog`: Radix owns the focus trap, Esc handling,
 * focus restore, scroll lock and aria-labelledby/aria-describedby wiring
 * (driven by Dialog.Title / Dialog.Description). We own the tokenized chrome.
 *
 * Compound API (attached via Object.assign):
 *   <Dialog open onOpenChange={...}>
 *     <Dialog.Trigger />
 *     <Dialog.Content size="md">
 *       <Dialog.Header>
 *         <Dialog.Title /> <Dialog.Description />
 *       </Dialog.Header>
 *       <Dialog.Body /> <Dialog.Footer />
 *     </Dialog.Content>
 *   </Dialog>
 */
import { forwardRef } from "react";
import type { ComponentPropsWithoutRef, ComponentRef, HTMLAttributes } from "react";
import * as DialogPrimitive from "@radix-ui/react-dialog";
import { cva, type VariantProps } from "class-variance-authority";
import { X } from "lucide-react";
import { cn } from "@/lib/utils";

const Root = DialogPrimitive.Root;
const Trigger = DialogPrimitive.Trigger;
const Portal = DialogPrimitive.Portal;
const Close = DialogPrimitive.Close;

const Overlay = forwardRef<
  ComponentRef<typeof DialogPrimitive.Overlay>,
  ComponentPropsWithoutRef<typeof DialogPrimitive.Overlay>
>(function DialogOverlay({ className, ...props }, ref) {
  return (
    <DialogPrimitive.Overlay
      ref={ref}
      className={cn("fixed inset-0 z-overlay bg-overlay", className)}
      {...props}
    />
  );
});

const contentVariants = cva(
  "fixed left-1/2 top-1/2 z-modal w-full -translate-x-1/2 -translate-y-1/2 bg-surface border border-default rounded-lg shadow-xl p-6 focus-visible:outline-none",
  {
    variants: {
      size: {
        sm: "max-w-sm",
        md: "max-w-md",
        lg: "max-w-lg",
        xl: "max-w-2xl",
        full: "max-w-screen-lg",
      },
    },
    defaultVariants: { size: "md" },
  },
);

export interface DialogContentProps
  extends ComponentPropsWithoutRef<typeof DialogPrimitive.Content>,
    VariantProps<typeof contentVariants> {}

const Content = forwardRef<
  ComponentRef<typeof DialogPrimitive.Content>,
  DialogContentProps
>(function DialogContent({ className, size, children, ...props }, ref) {
  return (
    <Portal>
      <Overlay />
      <DialogPrimitive.Content
        ref={ref}
        className={cn(contentVariants({ size }), className)}
        {...props}
      >
        {children}
        <DialogPrimitive.Close
          aria-label="Закрыть"
          className="absolute right-4 top-4 rounded-sm text-tertiary transition-colors duration-150 hover:text-primary focus-visible:outline-none focus-visible:shadow-focus-ring"
        >
          <X className="size-4" aria-hidden="true" />
        </DialogPrimitive.Close>
      </DialogPrimitive.Content>
    </Portal>
  );
});

function Header({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("flex flex-col gap-1.5 pr-6", className)}
      {...props}
    />
  );
}

function Body({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("py-4 text-sm text-secondary", className)} {...props} />;
}

function Footer({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn("flex flex-col-reverse gap-2 sm:flex-row sm:justify-end", className)}
      {...props}
    />
  );
}

const Title = forwardRef<
  ComponentRef<typeof DialogPrimitive.Title>,
  ComponentPropsWithoutRef<typeof DialogPrimitive.Title>
>(function DialogTitle({ className, ...props }, ref) {
  return (
    <DialogPrimitive.Title
      ref={ref}
      className={cn("text-lg font-semibold text-primary", className)}
      {...props}
    />
  );
});

const Description = forwardRef<
  ComponentRef<typeof DialogPrimitive.Description>,
  ComponentPropsWithoutRef<typeof DialogPrimitive.Description>
>(function DialogDescription({ className, ...props }, ref) {
  return (
    <DialogPrimitive.Description
      ref={ref}
      className={cn("text-sm text-secondary", className)}
      {...props}
    />
  );
});

/** Compound Dialog — Radix Root with tokenized parts attached. */
export const Dialog = Object.assign(Root, {
  Trigger,
  Content,
  Header,
  Body,
  Footer,
  Title,
  Description,
  Close,
});
