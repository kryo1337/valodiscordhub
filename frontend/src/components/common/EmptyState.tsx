interface EmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: React.ReactNode;
  headingLevel?: "h2" | "h3" | "h4";
}

export function EmptyState({
  icon,
  title,
  description,
  action,
  headingLevel: Heading = "h3",
}: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-6 py-16">
      {icon && (
        <div className="text-valorant-gray/20" aria-hidden="true">
          {icon}
        </div>
      )}
      <div className="h-px w-16 bg-valorant-gray/20" />
      <Heading className="text-sm font-bold text-valorant-light uppercase tracking-widest">
        {title}
      </Heading>
      {description && (
        <p className="text-sm text-valorant-gray text-center max-w-md">
          {description}
        </p>
      )}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
