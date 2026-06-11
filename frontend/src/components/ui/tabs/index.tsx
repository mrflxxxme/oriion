/**
 * Tabs — segmented panel switcher (component-inventory.md #16).
 * Wraps @radix-ui/react-tabs (ARIA roles + arrow-key roving handled by Radix).
 * Compound API: Tabs + Tabs.List / Tabs.Trigger / Tabs.Content (Object.assign).
 */
import { forwardRef } from "react";
import type { ComponentPropsWithoutRef, ComponentRef } from "react";
import * as TabsPrimitive from "@radix-ui/react-tabs";
import { cn } from "@/lib/utils";

const TabsRoot = forwardRef<
  ComponentRef<typeof TabsPrimitive.Root>,
  ComponentPropsWithoutRef<typeof TabsPrimitive.Root>
>(function TabsRoot({ className, ...props }, ref) {
  return <TabsPrimitive.Root ref={ref} className={cn("flex flex-col", className)} {...props} />;
});

const TabsList = forwardRef<
  ComponentRef<typeof TabsPrimitive.List>,
  ComponentPropsWithoutRef<typeof TabsPrimitive.List>
>(function TabsList({ className, ...props }, ref) {
  return (
    <TabsPrimitive.List
      ref={ref}
      className={cn("flex border-b border-default", className)}
      {...props}
    />
  );
});

const TabsTrigger = forwardRef<
  ComponentRef<typeof TabsPrimitive.Trigger>,
  ComponentPropsWithoutRef<typeof TabsPrimitive.Trigger>
>(function TabsTrigger({ className, ...props }, ref) {
  return (
    <TabsPrimitive.Trigger
      ref={ref}
      className={cn(
        "-mb-px border-b-2 border-transparent px-4 py-2 text-sm font-medium text-secondary transition-colors duration-150",
        "hover:text-primary focus-visible:outline-none focus-visible:shadow-focus-ring",
        "data-[state=active]:border-cta data-[state=active]:text-primary",
        "disabled:pointer-events-none disabled:opacity-50",
        className,
      )}
      {...props}
    />
  );
});

const TabsContent = forwardRef<
  ComponentRef<typeof TabsPrimitive.Content>,
  ComponentPropsWithoutRef<typeof TabsPrimitive.Content>
>(function TabsContent({ className, ...props }, ref) {
  return (
    <TabsPrimitive.Content
      ref={ref}
      className={cn("pt-4 focus-visible:outline-none focus-visible:shadow-focus-ring", className)}
      {...props}
    />
  );
});

export const Tabs = Object.assign(TabsRoot, {
  List: TabsList,
  Trigger: TabsTrigger,
  Content: TabsContent,
});
