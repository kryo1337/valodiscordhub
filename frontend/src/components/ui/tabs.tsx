import * as TabsPrimitive from "@radix-ui/react-tabs";
import { cn } from "@/lib/cn";

export const Tabs = TabsPrimitive.Root;

export function TabsList({
  className,
  ...props
}: TabsPrimitive.TabsListProps) {
  return (
    <TabsPrimitive.List
      className={cn(
        "inline-flex h-10 items-center justify-center rounded-md bg-valorant-dark p-1",
        className
      )}
      {...props}
    />
  );
}

export function TabsTrigger({
  className,
  ...props
}: TabsPrimitive.TabsTriggerProps) {
  return (
    <TabsPrimitive.Trigger
      className={cn(
        "inline-flex items-center justify-center whitespace-nowrap rounded-sm px-3 py-1.5",
        "text-sm font-medium text-valorant-gray",
        "ring-offset-background transition-all",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-valorant-red focus-visible:ring-offset-2",
        "disabled:pointer-events-none disabled:opacity-50",
        "data-[state=active]:bg-valorant-red data-[state=active]:text-white data-[state=active]:shadow-sm",
        className
      )}
      {...props}
    />
  );
}

export function TabsContent({
  className,
  ...props
}: TabsPrimitive.TabsContentProps) {
  return (
    <TabsPrimitive.Content
      className={cn(
        "mt-2 ring-offset-background",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-valorant-red focus-visible:ring-offset-2",
        className
      )}
      {...props}
    />
  );
}
