import { create } from "zustand";
import { devtools } from "zustand/middleware";
import { useEffect } from "react";
import { cn } from "@/lib/cn";
import { X, CheckCircle, AlertTriangle, Info, XCircle } from "lucide-react";

// --- Toast store ---

export type ToastVariant = "success" | "error" | "warning" | "info";

export interface Toast {
  id: string;
  message: string;
  variant: ToastVariant;
  duration?: number;
}

interface ToastState {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, "id">) => void;
  removeToast: (id: string) => void;
}

let toastIdCounter = 0;

export const useToastStore = create<ToastState>()(
  devtools(
    (set) => ({
  toasts: [],
  addToast: (toast) => {
    const id = String(++toastIdCounter);
    set((state) => ({
      toasts: [...state.toasts, { ...toast, id }],
    }));

    // Auto-remove after duration
    const duration = toast.duration ?? 5000;
    if (duration > 0) {
      setTimeout(() => {
        set((state) => ({
          toasts: state.toasts.filter((t) => t.id !== id),
        }));
      }, duration);
    }
  },
  removeToast: (id) =>
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    })),
}),
    { name: "ToastStore" }
  )
);

// --- Convenience functions (can be called from anywhere, not just components) ---

export function toast(message: string, variant: ToastVariant = "info", duration?: number) {
  useToastStore.getState().addToast({ message, variant, duration });
}

export function toastSuccess(message: string) {
  toast(message, "success");
}

export function toastError(message: string) {
  toast(message, "error", 7000);
}

export function toastWarning(message: string) {
  toast(message, "warning");
}

// --- Component ---

const variantStyles: Record<ToastVariant, string> = {
  success: "bg-valorant-dark border-l-valorant-cyan text-valorant-cyan border-l-2",
  error: "bg-valorant-dark border-l-valorant-red text-valorant-red border-l-2",
  warning: "bg-valorant-dark border-l-valorant-gold text-valorant-gold border-l-2",
  info: "bg-valorant-dark border-l-valorant-gray text-valorant-light border-l-2",
};

const variantIcons: Record<ToastVariant, typeof CheckCircle> = {
  success: CheckCircle,
  error: XCircle,
  warning: AlertTriangle,
  info: Info,
};

function ToastItem({ toast: t, onDismiss }: { toast: Toast; onDismiss: () => void }) {
  const Icon = variantIcons[t.variant];

  useEffect(() => {
    // Animate in
    const el = document.getElementById(`toast-${t.id}`);
    if (el) {
      requestAnimationFrame(() => {
        el.style.transform = "translateX(0)";
        el.style.opacity = "1";
      });
    }
  }, [t.id]);

  return (
    <div
      id={`toast-${t.id}`}
      className={cn(
        "flex items-start gap-3 p-4 shadow-lg max-w-sm w-full",
        "transition-all duration-300 ease-out",
        variantStyles[t.variant]
      )}
      style={{ transform: "translateX(100%)", opacity: 0 }}
      role="alert"
    >
      <Icon className="h-5 w-5 shrink-0 mt-0.5" />
      <p className="text-sm flex-1">{t.message}</p>
      <button
        onClick={onDismiss}
        className="shrink-0 p-2 -m-2 rounded hover:bg-white/10 transition-colors"
        aria-label="Dismiss notification"
      >
        <X className="h-4 w-4" />
      </button>
    </div>
  );
}

export function ToastContainer() {
  const { toasts, removeToast } = useToastStore();

  if (toasts.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-[100] flex flex-col gap-2 pointer-events-none">
      {toasts.map((t) => (
        <div key={t.id} className="pointer-events-auto">
          <ToastItem toast={t} onDismiss={() => removeToast(t.id)} />
        </div>
      ))}
    </div>
  );
}
